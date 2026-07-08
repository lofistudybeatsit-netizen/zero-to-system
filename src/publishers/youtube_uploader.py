"""
YouTube Uploader - Upload video via YouTube Data API v3
Quota: 1,600 units per upload (max ~6 video/giorno con quota default 10,000)

Prerequisiti:
1. Google Cloud Console -> abilita YouTube Data API v3
2. Crea OAuth 2.0 credentials (Desktop app)
3. Scarica client_secrets.json
4. Esegui primo auth per ottenere refresh_token

Usage:
    python youtube_uploader.py --video output/video.mp4 --metadata output/metadata.json
"""

import os
import sys
import json
import pickle
import argparse
from pathlib import Path
from typing import Dict, Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Scopes necessari
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


class YouTubeUploader:
    """Uploader YouTube con OAuth 2.0 e resumable upload"""

    def __init__(self, client_secrets_path: str = "config/client_secrets.json",
                 token_path: str = "config/youtube_token.pickle"):
        self.client_secrets_path = client_secrets_path
        self.token_path = token_path
        self.service = self._authenticate()

    def _authenticate(self):
        """Autenticazione OAuth 2.0 con refresh token"""
        creds = None

        # Carica token esistente
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        # Se non validi, refresh o nuovo auth
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.client_secrets_path):
                    raise FileNotFoundError(
                        f"client_secrets.json non trovato in {self.client_secrets_path}.\n"
                        "Crea credentials in Google Cloud Console -> APIs & Services -> Credentials"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Salva token per usi futuri
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        return build('youtube', 'v3', credentials=creds)

    def upload_video(self, video_path: str, title: str, description: str,
                    tags: list = None, category_id: str = "10",
                    privacy_status: str = "public",
                    publish_at: Optional[str] = None,
                    thumbnail_path: Optional[str] = None) -> Dict:
        """
        Upload video con resumable upload

        Args:
            video_path: Path al file video
            title: Titolo video (max 100 char)
            description: Descrizione completa
            tags: Lista tag (max 500 char totali)
            category_id: ID categoria (10 = Music, 24 = Entertainment)
            privacy_status: public | private | unlisted
            publish_at: ISO 8601 per scheduling (richiede privacyStatus=private)
            thumbnail_path: Path a thumbnail (1280x720, <2MB)
        """

        # Body del video
        body = {
            'snippet': {
                'title': title[:100],
                'description': description,
                'tags': tags or [],
                'categoryId': category_id,
                'defaultLanguage': 'en',
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False,
            }
        }

        # Scheduling: deve essere private + publishAt
        if publish_at:
            body['status']['privacyStatus'] = 'private'
            body['status']['publishAt'] = publish_at

        # Media upload con resumable
        media = MediaFileUpload(
            video_path,
            mimetype='video/mp4',
            resumable=True,
            chunksize=256 * 1024  # 256 KB chunks
        )

        request = self.service.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )

        # Upload con progress tracking
        response = None
        retry = 0
        max_retries = 5

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    print(f"Upload progress: {int(status.progress() * 100)}%")
            except Exception as e:
                retry += 1
                if retry > max_retries:
                    raise
                import time
                sleep_time = 2 ** retry
                print(f"Errore, retry {retry}/{max_retries} in {sleep_time}s...")
                time.sleep(sleep_time)

        video_id = response['id']
        print(f"✅ Video uploadato: https://youtube.com/watch?v={video_id}")

        # Upload thumbnail separato (50 quota units)
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                self.service.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path, mimetype='image/jpeg')
                ).execute()
                print(f"✅ Thumbnail impostato")
            except Exception as e:
                print(f"⚠️ Errore thumbnail: {e}")

        return {
            'video_id': video_id,
            'url': f"https://youtube.com/watch?v={video_id}",
            'title': title,
            'privacy_status': privacy_status,
            'publish_at': publish_at
        }

    def upload_short(self, video_path: str, title: str, description: str,
                    tags: list = None, **kwargs) -> Dict:
        """Upload YouTube Short (stesso endpoint, video verticale <60s)"""
        # Aggiungi #Shorts al titolo per migliore discovery
        if '#Shorts' not in title:
            title = f"{title} #Shorts"

        return self.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            category_id="24",  # Entertainment
            **kwargs
        )

    def check_quota_usage(self) -> Dict:
        """Controlla quota rimanente (approssimativo)"""
        # La quota esatta richiede monitoring via Cloud Console
        # Questo è un tracker locale
        quota_file = Path("config/quota_tracker.json")

        if quota_file.exists():
            with open(quota_file) as f:
                data = json.load(f)
        else:
            data = {'used_today': 0, 'last_reset': ''}

        # Reset giornaliero (midnight PT)
        from datetime import datetime, timezone, timedelta
        pt_now = datetime.now(timezone(timedelta(hours=-7)))
        today_str = pt_now.strftime('%Y-%m-%d')

        if data.get('last_reset') != today_str:
            data = {'used_today': 0, 'last_reset': today_str}

        remaining = 10000 - data['used_today']
        uploads_remaining = remaining // 1600

        return {
            'used_today': data['used_today'],
            'remaining': remaining,
            'uploads_remaining': uploads_remaining,
            'resets_at': f"{today_str} 23:59 PT"
        }

    def track_quota(self, units: int):
        """Traccia uso quota locale"""
        quota_file = Path("config/quota_tracker.json")

        data = {'used_today': 0, 'last_reset': ''}
        if quota_file.exists():
            with open(quota_file) as f:
                data = json.load(f)

        from datetime import datetime, timezone, timedelta
        pt_now = datetime.now(timezone(timedelta(hours=-7)))
        today_str = pt_now.strftime('%Y-%m-%d')

        if data.get('last_reset') != today_str:
            data = {'used_today': 0, 'last_reset': today_str}

        data['used_today'] += units

        with open(quota_file, 'w') as f:
            json.dump(data, f)


def main():
    parser = argparse.ArgumentParser(description="YouTube Video Uploader")
    parser.add_argument("--video", required=True, help="Path al video")
    parser.add_argument("--metadata", required=True, help="Path al file metadata JSON")
    parser.add_argument("--thumbnail", help="Path al thumbnail")
    parser.add_argument("--schedule", help="Data pubblicazione ISO 8601 (es. 2026-07-08T15:00:00Z)")
    parser.add_argument("--short", action="store_true", help="Upload come Short")
    args = parser.parse_args()

    # Carica metadata
    with open(args.metadata) as f:
        metadata = json.load(f)

    uploader = YouTubeUploader()

    # Controlla quota
    quota = uploader.check_quota_usage()
    print(f"📊 Quota: {quota['used_today']}/10000 usata, {quota['uploads_remaining']} upload rimanenti")

    if quota['uploads_remaining'] <= 0:
        print("❌ Quota esaurita per oggi. Riprova domani.")
        return

    # Upload
    if args.short:
        result = uploader.upload_short(
            video_path=args.video,
            title=metadata['title'],
            description=metadata['description'],
            tags=metadata.get('tags', []),
            thumbnail_path=args.thumbnail,
            publish_at=args.schedule
        )
    else:
        result = uploader.upload_video(
            video_path=args.video,
            title=metadata['title'],
            description=metadata['description'],
            tags=metadata.get('tags', []),
            thumbnail_path=args.thumbnail,
            publish_at=args.schedule
        )

    # Traccia quota
    uploader.track_quota(1600)  # Costo upload
    if args.thumbnail:
        uploader.track_quota(50)  # Costo thumbnail

    print(f"\n✅ Upload completato!")
    print(f"   URL: {result['url']}")
    print(f"   ID: {result['video_id']}")


if __name__ == "__main__":
    main()
