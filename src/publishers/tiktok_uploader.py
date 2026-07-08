"""
TikTok Uploader - Upload via browser automation (Selenium/Playwright)
Alternativa gratuita all'API ufficiale (che richiede approvazione)

Usa tiktok-uploader (PyPI) o TikTokAutoUploader per upload automatizzato

Prerequisiti:
1. pip install tiktok-uploader playwright
2. playwright install chromium
3. Esporta cookies da TikTok.com (estensione Get cookies.txt)

Usage:
    python tiktok_uploader.py --video output/short.mp4 --caption "My caption #fyp"
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Optional


class TikTokUploader:
    """Uploader TikTok via browser automation (gratuito)"""

    def __init__(self, cookies_path: str = "config/tiktok_cookies.txt"):
        self.cookies_path = cookies_path
        self.output_dir = Path("output/tiktok_uploads")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def upload_with_tiktok_uploader(self, video_path: str, caption: str,
                                     hashtags: list = None,
                                     headless: bool = True) -> Dict:
        """
        Upload usando tiktok-uploader (PyPI)

        Args:
            video_path: Path al video (mp4, verticale 9:16, <60s per best results)
            caption: Didascalia con hashtag
            hashtags: Lista hashtag separati
            headless: True per esecuzione in background
        """
        try:
            from tiktok_uploader.upload import upload_video

            # Combina caption e hashtag
            full_caption = caption
            if hashtags:
                full_caption += " " + " ".join(hashtags)

            # Upload
            result = upload_video(
                filename=video_path,
                description=full_caption,
                cookies=self.cookies_path,
                headless=headless
            )

            return {
                'success': True,
                'video_path': video_path,
                'caption': full_caption,
                'method': 'tiktok-uploader'
            }

        except ImportError:
            print("⚠️ tiktok-uploader non installato. Provo metodo alternativo...")
            return self._fallback_upload(video_path, caption, hashtags)

    def upload_with_tiktokautouploader(self, video_path: str, caption: str,
                                        account_name: str,
                                        hashtags: list = None,
                                        schedule: Optional[str] = None) -> Dict:
        """
        Upload usando TikTokAutoUploader (più features, include scheduling)

        Args:
            video_path: Path al video
            caption: Didascalia
            account_name: Nome account TikTok
            hashtags: Lista hashtag
            schedule: Orario scheduling "HH:MM" (opzionale, max 10 giorni)
        """
        try:
            from tiktokautouploader import upload_tiktok

            full_caption = caption
            if hashtags:
                full_caption += " " + " ".join(hashtags)

            kwargs = {
                'video': video_path,
                'description': full_caption,
                'accountname': account_name,
                'hashtags': hashtags or [],
                'headless': True,
                'stealth': True
            }

            if schedule:
                kwargs['schedule'] = schedule

            result = upload_tiktok(**kwargs)

            return {
                'success': True,
                'video_path': video_path,
                'caption': full_caption,
                'scheduled': schedule is not None,
                'method': 'TikTokAutoUploader'
            }

        except ImportError:
            print("⚠️ TikTokAutoUploader non installato.")
            return {'success': False, 'error': 'Libreria non installata'}

    def _fallback_upload(self, video_path: str, caption: str, hashtags: list = None) -> Dict:
        """Metodo fallback: salva per upload manuale"""
        print("⚠️ Fallback: salvo file per upload manuale")

        # Salva metadata per upload manuale
        metadata = {
            'video_path': video_path,
            'caption': caption,
            'hashtags': hashtags or [],
            'uploaded_at': None,
            'status': 'pending_manual'
        }

        meta_path = self.output_dir / f"{Path(video_path).stem}_tiktok_meta.json"
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"📋 Metadata salvato: {meta_path}")
        print(f"   Carica manualmente su TikTok: {video_path}")
        print(f"   Caption: {caption}")

        return {
            'success': False,
            'status': 'pending_manual',
            'metadata_path': str(meta_path),
            'video_path': video_path
        }

    def batch_upload(self, video_folder: str, captions: list,
                     method: str = 'tiktok-uploader') -> list:
        """Upload batch di video"""
        video_files = sorted(Path(video_folder).glob("*.mp4"))
        results = []

        for i, video_path in enumerate(video_files):
            caption = captions[i] if i < len(captions) else "Check out this video! #fyp"

            if method == 'tiktok-uploader':
                result = self.upload_with_tiktok_uploader(str(video_path), caption)
            elif method == 'tiktokautouploader':
                result = self.upload_with_tiktokautouploader(str(video_path), caption, "your_account")
            else:
                result = self._fallback_upload(str(video_path), caption)

            results.append(result)

        return results


def main():
    parser = argparse.ArgumentParser(description="TikTok Video Uploader")
    parser.add_argument("--video", required=True, help="Path al video")
    parser.add_argument("--caption", required=True, help="Didascalia")
    parser.add_argument("--hashtags", nargs="+", help="Hashtag (es. #fyp #viral)")
    parser.add_argument("--method", default="tiktok-uploader", 
                       choices=["tiktok-uploader", "tiktokautouploader", "fallback"])
    parser.add_argument("--account", help="Nome account TikTok (per TikTokAutoUploader)")
    parser.add_argument("--schedule", help="Orario scheduling HH:MM")
    args = parser.parse_args()

    uploader = TikTokUploader()

    if args.method == "tiktok-uploader":
        result = uploader.upload_with_tiktok_uploader(
            args.video, args.caption, args.hashtags
        )
    elif args.method == "tiktokautouploader":
        if not args.account:
            print("❌ --account richiesto per TikTokAutoUploader")
            return
        result = uploader.upload_with_tiktokautouploader(
            args.video, args.caption, args.account, args.hashtags, args.schedule
        )
    else:
        result = uploader._fallback_upload(args.video, args.caption, args.hashtags)

    print(f"\n✅ Risultato: {result}")


if __name__ == "__main__":
    main()
