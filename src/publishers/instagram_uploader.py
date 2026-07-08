"""
Instagram Uploader - Instagram Graph API (Content Publishing)
Requisiti: Instagram Business Account + Facebook Page + Meta Developer App

Prerequisiti:
1. Converti account IG in Business Account (Settings -> Account -> Switch to Professional)
2. Collega a Facebook Page
3. Crea app in Meta Developers (developers.facebook.com)
4. Richiedi permessi: instagram_business_basic, instagram_business_content_publish
5. Ottieni Page Access Token (long-lived)

Quota: 200 call/ora, 4800 call/giorno, 100 post/24h

Usage:
    python instagram_uploader.py --video output/reel.mp4 --caption "My reel #music"
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from typing import Dict, Optional


class InstagramUploader:
    """Uploader Instagram via Graph API (gratuito, ufficiale)"""

    API_BASE = "https://graph.facebook.com/v21.0"

    def __init__(self, access_token: str, ig_user_id: str):
        self.access_token = access_token
        self.ig_user_id = ig_user_id
        self.output_dir = Path("output/instagram_uploads")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _api_call(self, endpoint: str, method: str = "GET", data: Optional[dict] = None) -> Dict:
        """Chiamata API con gestione errori"""
        url = f"{self.API_BASE}/{endpoint}"

        params = {'access_token': self.access_token}
        if data and method == "GET":
            params.update(data)

        try:
            if method == "GET":
                response = requests.get(url, params=params)
            else:
                response = requests.post(url, params=params, data=data)

            result = response.json()

            if 'error' in result:
                print(f"❌ API Error: {result['error']}")
                return {'success': False, 'error': result['error']}

            return {'success': True, 'data': result}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _upload_to_temp_host(self, video_path: str) -> Optional[str]:
        """
        Upload video su transfer.sh (gratuito, 14 giorni) per ottenere URL pubblico.
        Instagram Graph API richiede che il video sia accessibile pubblicamente.
        """
        print(f"   📤 Upload temporaneo su transfer.sh: {video_path}")
        try:
            filename = os.path.basename(video_path)
            with open(video_path, 'rb') as f:
                response = requests.put(
                    f'https://transfer.sh/{filename}',
                    data=f,
                    timeout=120
                )
            
            print(f"   DEBUG status: {response.status_code}")
            print(f"   DEBUG body: {response.text[:200]}")
            
            if response.status_code == 200:
                url = response.text.strip()
                print(f"   ✅ URL temporaneo: {url}")
                return url
            else:
                print(f"   ❌ transfer.sh error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"   ❌ Errore upload temporaneo: {e}")
            import traceback
            traceback.print_exc()
            return None

    def upload_reel(self, video_url: str, caption: str,
                    cover_url: Optional[str] = None,
                    share_to_feed: bool = True) -> Dict:
        """
        Upload Reel su Instagram (3-step container flow)

        Args:
            video_url: URL pubblico del video (deve essere accessibile da Meta)
            caption: Didascalia con hashtag
            cover_url: URL copertina (opzionale)
            share_to_feed: Condividi anche nel feed principale

        Returns:
            Dict con media_id o error
        """
        print(f"📤 Upload Reel: {caption[:50]}...")

        # Step 1: Crea container
        container_data = {
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': caption,
            'share_to_feed': str(share_to_feed).lower()
        }

        if cover_url:
            container_data['cover_url'] = cover_url

        result = self._api_call(
            f"{self.ig_user_id}/media",
            method="POST",
            data=container_data
        )

        if not result['success']:
            return result

        container_id = result['data'].get('id')
        print(f"   📦 Container creato: {container_id}")

        # Step 2: Poll status fino a FINISHED
        max_attempts = 30
        for attempt in range(max_attempts):
            status_result = self._api_call(
                f"{container_id}",
                method="GET",
                data={'fields': 'status_code'}
            )

            if not status_result['success']:
                return status_result

            status_code = status_result['data'].get('status_code', 'UNKNOWN')
            print(f"   ⏳ Status: {status_code} (attempt {attempt + 1}/{max_attempts})")

            if status_code == 'FINISHED':
                break
            elif status_code == 'ERROR':
                return {'success': False, 'error': 'Container processing failed'}

            time.sleep(5)  # Attendi 5 secondi
        else:
            return {'success': False, 'error': 'Timeout polling container status'}

        # Step 3: Publish
        publish_result = self._api_call(
            f"{self.ig_user_id}/media_publish",
            method="POST",
            data={'creation_id': container_id}
        )

        if publish_result['success']:
            media_id = publish_result['data'].get('id')
            print(f"   ✅ Reel pubblicato! Media ID: {media_id}")
            return {
                'success': True,
                'media_id': media_id,
                'container_id': container_id,
                'url': f"https://instagram.com/reel/{media_id}"
            }

        return publish_result

    def upload_story(self, image_url: str) -> Dict:
        """Upload Story (immagine)"""
        # Step 1: Container
        result = self._api_call(
            f"{self.ig_user_id}/media",
            method="POST",
            data={
                'media_type': 'STORIES',
                'image_url': image_url
            }
        )

        if not result['success']:
            return result

        container_id = result['data'].get('id')

        # Step 2: Poll
        for _ in range(20):
            status = self._api_call(
                f"{container_id}",
                method="GET",
                data={'fields': 'status_code'}
            )
            if status['success'] and status['data'].get('status_code') == 'FINISHED':
                break
            time.sleep(3)

        # Step 3: Publish
        return self._api_call(
            f"{self.ig_user_id}/media_publish",
            method="POST",
            data={'creation_id': container_id}
        )

    def check_publishing_limit(self) -> Dict:
        """Controlla limite pubblicazioni rimanenti"""
        result = self._api_call(
            f"{self.ig_user_id}/content_publishing_limit",
            method="GET",
            data={'fields': 'config,quota_usage'}
        )

        if result['success']:
            data = result['data']
            return {
                'success': True,
                'quota_usage': data.get('quota_usage', 0),
                'limit': 100,  # Limite standard
                'remaining': 100 - data.get('quota_usage', 0)
            }

        return result

    def upload_local_video(self, video_path: str, caption: str) -> Dict:
        """
        Upload video locale su Instagram.
        1. Upload su file.io per ottenere URL pubblico
        2. Usa upload_reel con l'URL
        """
        print(f"📤 Upload locale Instagram: {video_path}")

        # Step 1: Ottieni URL pubblico
        video_url = self._upload_to_temp_host(video_path)
        if not video_url:
            return {
                'success': False,
                'error': 'Impossibile ottenere URL pubblico per il video'
            }

        # Step 2: Upload su Instagram
        return self.upload_reel(video_url, caption)


def main():
    parser = argparse.ArgumentParser(description="Instagram Reel Uploader")
    parser.add_argument("--video-url", help="URL pubblico del video")
    parser.add_argument("--video-path", help="Path locale (upload automatico a URL temporaneo)")
    parser.add_argument("--caption", required=True, help="Didascalia")
    parser.add_argument("--access-token", help="Instagram Access Token")
    parser.add_argument("--ig-user-id", help="Instagram User ID")
    args = parser.parse_args()

    # Carica da env se non forniti
    access_token = args.access_token or os.environ.get('INSTAGRAM_ACCESS_TOKEN')
    ig_user_id = args.ig_user_id or os.environ.get('INSTAGRAM_USER_ID')

    if not access_token or not ig_user_id:
        print("❌ Access Token e IG User ID richiesti")
        print("   Imposta env vars INSTAGRAM_ACCESS_TOKEN e INSTAGRAM_USER_ID")
        print("   Oppure passa --access-token e --ig-user-id")
        return

    uploader = InstagramUploader(access_token, ig_user_id)

    # Controlla limite
    limit = uploader.check_publishing_limit()
    if limit['success']:
        print(f"📊 Pubblicazioni rimanenti: {limit['remaining']}/100 (24h)")

    if args.video_url:
        result = uploader.upload_reel(args.video_url, args.caption)
    elif args.video_path:
        result = uploader.upload_local_video(args.video_path, args.caption)
    else:
        print("❌ Specifica --video-url o --video-path")
        return

    print(f"\n✅ Risultato: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    main()