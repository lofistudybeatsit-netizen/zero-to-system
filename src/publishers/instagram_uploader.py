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
    python instagram_uploader.py --test-connectivity  # Testa i host temporanei
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class InstagramUploader:
    """Uploader Instagram via Graph API (gratuito, ufficiale)"""

    API_BASE = "https://graph.facebook.com/v21.0"

    # Host temporanei con fallback: (url_template, metodo, file_key, extra_headers)
    TEMP_HOSTS: List[Tuple[str, str, Optional[str], Optional[dict]]] = [
        ("https://transfer.sh/{}", "put", None, {"Max-Days": "1"}),
        ("https://0x0.st", "post", "file", None),
        ("https://file.io", "post", "file", {"expires": "1d"}),
        ("https://tmp.link", "post", "file", None),
    ]

    def __init__(self, access_token: str, ig_user_id: str):
        self.access_token = access_token
        self.ig_user_id = ig_user_id
        self.output_dir = Path("output/instagram_uploads")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _log(self, message: str):
        """Stampa messaggio con timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def _create_session(self) -> requests.Session:
        """Crea session requests con retry configurato"""
        session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "POST", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def test_connectivity(self) -> Dict[str, bool]:
        """
        Testa la connettività verso tutti gli host temporanei.
        Utile per diagnosticare problemi di rete in CI/CD.
        """
        self._log("🔌 Test connettività host temporanei...")
        results = {}

        session = self._create_session()

        # Test transfer.sh
        try:
            resp = session.get("https://transfer.sh", timeout=(10, 10))
            results["transfer.sh"] = resp.status_code < 500
            self._log(f"   transfer.sh: {'✅ OK' if results['transfer.sh'] else f'⚠️ Status {resp.status_code}'}")
        except Exception as e:
            results["transfer.sh"] = False
            self._log(f"   transfer.sh: ❌ {str(e)[:80]}")

        # Test 0x0.st
        try:
            resp = session.get("https://0x0.st", timeout=(10, 10))
            results["0x0.st"] = resp.status_code < 500
            self._log(f"   0x0.st: {'✅ OK' if results['0x0.st'] else f'⚠️ Status {resp.status_code}'}")
        except Exception as e:
            results["0x0.st"] = False
            self._log(f"   0x0.st: ❌ {str(e)[:80]}")

        # Test file.io
        try:
            resp = session.get("https://file.io", timeout=(10, 10))
            results["file.io"] = resp.status_code < 500
            self._log(f"   file.io: {'✅ OK' if results['file.io'] else f'⚠️ Status {resp.status_code}'}")
        except Exception as e:
            results["file.io"] = False
            self._log(f"   file.io: ❌ {str(e)[:80]}")

        # Test Meta Graph API
        try:
            resp = session.get(
                f"{self.API_BASE}/me",
                params={"access_token": self.access_token},
                timeout=(10, 10)
            )
            results["graph_api"] = resp.status_code == 200
            self._log(f"   Graph API: {'✅ OK' if results['graph_api'] else f'⚠️ Status {resp.status_code}'}")
        except Exception as e:
            results["graph_api"] = False
            self._log(f"   Graph API: ❌ {str(e)[:80]}")

        any_ok = any(results.values())
        self._log(f"{'✅' if any_ok else '❌'} Connettività: {sum(results.values())}/{len(results)} host OK")
        return results

    def _upload_to_temp_host(self, video_path: str) -> Optional[str]:
        """
        Upload video su host temporaneo con retry e fallback multipli.
        Prova transfer.sh, poi 0x0.st, poi file.io, ecc.
        """
        filename = os.path.basename(video_path)
        file_size = os.path.getsize(video_path)
        self._log(f"   📤 Upload temporaneo: {filename} ({file_size:,} bytes)")

        session = self._create_session()

        for host_idx, (url_template, method, file_key, headers) in enumerate(self.TEMP_HOSTS):
            host_name = url_template.split("//")[1].split("/")[0]
            max_attempts = 3

            for attempt in range(max_attempts):
                try:
                    self._log(f"   🌐 Host {host_name} (tentativo {attempt + 1}/{max_attempts})")

                    # Prepara URL
                    if "{}" in url_template:
                        url = url_template.format(filename)
                    else:
                        url = url_template

                    # Prepara file e headers
                    req_headers = headers or {}
                    req_headers.update({
                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
                    })

                    with open(video_path, 'rb') as f:
                        if file_key:
                            files = {file_key: (filename, f, 'video/mp4')}
                            response = session.post(
                                url,
                                files=files,
                                headers=req_headers,
                                timeout=(30, 300)
                            )
                        else:
                            response = session.put(
                                url,
                                data=f,
                                headers=req_headers,
                                timeout=(30, 300)
                            )

                    self._log(f"   DEBUG status: {response.status_code}")

                    if response.status_code in (200, 201):
                        # Estrai URL dalla risposta
                        content_type = response.headers.get('Content-Type', '')

                        if 'json' in content_type:
                            try:
                                data = response.json()
                                # Formati diversi per host diversi
                                public_url = (
                                    data.get('link') or
                                    data.get('url') or
                                    data.get('data', {}).get('link') or
                                    data.get('file', {}).get('url')
                                )
                            except json.JSONDecodeError:
                                public_url = response.text.strip()
                        else:
                            public_url = response.text.strip()

                        # Validazione URL
                        if public_url and public_url.startswith(('http://', 'https://')):
                            self._log(f"   ✅ URL temporaneo ({host_name}): {public_url[:80]}...")
                            return public_url
                        else:
                            self._log(f"   ⚠️ Risposta non valida da {host_name}: {public_url[:100]}")

                    else:
                        body_preview = response.text[:200].replace('\n', ' ')
                        self._log(f"   ⚠️ Status {response.status_code}: {body_preview}")

                except requests.exceptions.ConnectionError as e:
                    self._log(f"   ⚠️ ConnectionError: {str(e)[:100]}")
                    if attempt < max_attempts - 1:
                        wait_time = 2 ** attempt * 5
                        self._log(f"   ⏳ Attesa {wait_time}s...")
                        time.sleep(wait_time)
                except requests.exceptions.Timeout as e:
                    self._log(f"   ⚠️ Timeout: {str(e)[:100]}")
                    if attempt < max_attempts - 1:
                        time.sleep(5)
                except Exception as e:
                    self._log(f"   ❌ Errore {host_name}: {str(e)[:150]}")
                    break  # Passa al prossimo host

            # Se tutti i tentativi per questo host falliscono, passa al prossimo
            self._log(f"   ⏭️ Passo al prossimo host...")

        self._log("   ❌ Tutti gli host temporanei hanno fallito")
        return None

    def _api_call(self, endpoint: str, method: str = "GET", data: Optional[dict] = None) -> Dict:
        """Chiamata API con gestione errori"""
        url = f"{self.API_BASE}/{endpoint}"

        params = {'access_token': self.access_token}
        if data and method == "GET":
            params.update(data)

        try:
            if method == "GET":
                response = requests.get(url, params=params, timeout=30)
            else:
                response = requests.post(url, params=params, data=data, timeout=30)

            result = response.json()

            if 'error' in result:
                self._log(f"❌ API Error: {result['error']}")
                return {'success': False, 'error': result['error']}

            return {'success': True, 'data': result}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def upload_reel(self, video_url: str, caption: str,
                    cover_url: Optional[str] = None,
                    share_to_feed: bool = True) -> Dict:
        """
        Upload Reel su Instagram (3-step container flow)
        """
        self._log(f"📤 Upload Reel: {caption[:50]}...")

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
        self._log(f"   📦 Container creato: {container_id}")

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
            self._log(f"   ⏳ Status: {status_code} ({attempt + 1}/{max_attempts})")

            if status_code == 'FINISHED':
                break
            elif status_code == 'ERROR':
                return {'success': False, 'error': 'Container processing failed'}

            time.sleep(5)
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
            self._log(f"   ✅ Reel pubblicato! Media ID: {media_id}")
            return {
                'success': True,
                'media_id': media_id,
                'container_id': container_id,
                'url': f"https://instagram.com/reel/{media_id}"
            }

        return publish_result

    def upload_story(self, image_url: str) -> Dict:
        """Upload Story (immagine)"""
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

        for _ in range(20):
            status = self._api_call(
                f"{container_id}",
                method="GET",
                data={'fields': 'status_code'}
            )
            if status['success'] and status['data'].get('status_code') == 'FINISHED':
                break
            time.sleep(3)

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
                'limit': 100,
                'remaining': 100 - data.get('quota_usage', 0)
            }

        return result

    def upload_local_video(self, video_path: str, caption: str) -> Dict:
        """
        Upload video locale su Instagram.
        1. Upload su host temporaneo per ottenere URL pubblico
        2. Usa upload_reel con l'URL
        """
        self._log(f"📤 Upload locale Instagram: {video_path}")

        if not os.path.exists(video_path):
            return {
                'success': False,
                'error': f'File non trovato: {video_path}'
            }

        # Step 1: Ottieni URL pubblico (con fallback multipli)
        video_url = self._upload_to_temp_host(video_path)
        if not video_url:
            return {
                'success': False,
                'error': 'Impossibile ottenere URL pubblico per il video (tutti gli host falliti)'
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
    parser.add_argument("--test-connectivity", action="store_true", help="Testa connettività host")
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

    # Test connettività se richiesto
    if args.test_connectivity:
        uploader.test_connectivity()
        return

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