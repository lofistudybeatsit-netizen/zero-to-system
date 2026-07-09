"""
Instagram Uploader - Instagram Graph API
Supporta upload via Cloudflare R2 (primario, con pulizia auto) o host temporanei (fallback)

Requisiti: Instagram Business Account + Facebook Page + Meta Developer App
Prerequisiti:
1. Converti account IG in Business Account
2. Collega a Facebook Page
3. Crea app in Meta Developers
4. Richiedi permessi: instagram_business_basic, instagram_business_content_publish
5. Ottieni Page Access Token (long-lived)

Quota: 200 call/ora, 4800 call/giorno, 100 post/24h

Usage:
    python instagram_uploader.py --video output/reel.mp4 --caption "My reel #music"
    python instagram_uploader.py --test-connectivity  # Testa R2 + host temporanei
    python instagram_uploader.py --cleanup-r2  # Cancella TUTTO da R2 (safety net)
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

    # Host temporanei fallback (solo se R2 fallisce)
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
        self._r2_client = None
        self._r2_bucket = None

    def _log(self, message: str):
        """Stampa messaggio con timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}", flush=True)

    def _create_session(self) -> requests.Session:
        """Crea session requests con retry configurato"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "POST", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    # ═══════════════════════════════════════════════════════════════
    # R2 CLIENT (riutilizzabile)
    # ═══════════════════════════════════════════════════════════════

    def _get_r2_client(self):
        """Inizializza e cachea client R2"""
        if self._r2_client is not None:
            return self._r2_client, self._r2_bucket

        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            return None, None

        bucket = os.environ.get('R2_BUCKET_NAME')
        endpoint = os.environ.get('R2_ENDPOINT')
        access_key = os.environ.get('R2_ACCESS_KEY_ID')
        secret_key = os.environ.get('R2_SECRET_ACCESS_KEY')

        if not all([bucket, endpoint, access_key, secret_key]):
            missing = [k for k, v in {
                'R2_BUCKET_NAME': bucket,
                'R2_ENDPOINT': endpoint,
                'R2_ACCESS_KEY_ID': access_key,
                'R2_SECRET_ACCESS_KEY': secret_key
            }.items() if not v]
            self._log(f"   ⚠️ Credenziali R2 incomplete: mancano {missing}")
            return None, None

        try:
            self._r2_client = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version='s3v4'),
                region_name='auto'
            )
            self._r2_bucket = bucket
            return self._r2_client, self._r2_bucket
        except Exception as e:
            self._log(f"   ⚠️ Errore inizializzazione R2: {str(e)[:100]}")
            return None, None

    # ═══════════════════════════════════════════════════════════════
    # R2 CLEANUP (SAFETY NET - cancella TUTTO)
    # ═══════════════════════════════════════════════════════════════

    def cleanup_r2_all(self, prefix: str = "reels/") -> Dict:
        """
        Cancella TUTTI gli oggetti da R2 con il prefisso specificato.
        Safety net: eseguire all'inizio di ogni run per pulire eventuali residui.

        Args:
            prefix: Prefisso da cancellare (default "reels/")

        Returns:
            Dict con count oggetti cancellati e eventuali errori
        """
        s3, bucket = self._get_r2_client()
        if s3 is None:
            self._log("   ⚠️ R2 non disponibile, skip cleanup")
            return {'success': False, 'deleted': 0, 'error': 'R2 non configurato'}

        try:
            self._log(f"🧹 Cleanup R2: cerco oggetti con prefisso '{prefix}'...")

            # Lista tutti gli oggetti con il prefisso
            paginator = s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

            deleted_count = 0
            errors = []

            for page in pages:
                objects = page.get('Contents', [])
                if not objects:
                    continue

                # Prepara batch di cancellazione (max 1000 per chiamata)
                delete_keys = [{'Key': obj['Key']} for obj in objects]

                try:
                    response = s3.delete_objects(
                        Bucket=bucket,
                        Delete={'Objects': delete_keys, 'Quiet': True}
                    )
                    deleted = len(response.get('Deleted', []))
                    deleted_count += deleted

                    errors_in_batch = response.get('Errors', [])
                    if errors_in_batch:
                        errors.extend(errors_in_batch)

                except Exception as e:
                    errors.append(str(e))
                    self._log(f"   ⚠️ Errore batch delete: {str(e)[:100]}")

            if deleted_count > 0:
                self._log(f"   ✅ Cleanup R2 completato: {deleted_count} oggetti eliminati")
            else:
                self._log(f"   ✅ Cleanup R2: nessun oggetto da eliminare")

            if errors:
                self._log(f"   ⚠️ Errori durante cleanup: {len(errors)}")

            return {
                'success': True,
                'deleted': deleted_count,
                'errors': len(errors),
                'prefix': prefix
            }

        except Exception as e:
            self._log(f"   ❌ Errore cleanup R2: {str(e)[:200]}")
            return {'success': False, 'deleted': 0, 'error': str(e)}

    # ═══════════════════════════════════════════════════════════════
    # R2 UPLOAD (PRIMARIO)
    # ═══════════════════════════════════════════════════════════════

    def _upload_to_r2(self, video_path: str) -> Optional[str]:
        """
        Upload video su Cloudflare R2 (S3-compatible).
        Richiede env vars: R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, 
                           R2_BUCKET_NAME, R2_ENDPOINT, R2_PUBLIC_DOMAIN (opzionale)
        """
        s3, bucket = self._get_r2_client()
        if s3 is None:
            self._log("   ⚠️ R2 non configurato o boto3 mancante")
            return None

        try:
            filename = f"reels/{int(time.time())}_{os.path.basename(video_path)}"
            self._log(f"   📤 Upload su R2: {bucket}/{filename}")

            s3.upload_file(
                video_path,
                bucket,
                filename,
                ExtraArgs={'ContentType': 'video/mp4'}
            )

            # URL pubblico
            custom_domain = os.environ.get('R2_PUBLIC_DOMAIN')
            endpoint = os.environ.get('R2_ENDPOINT', '')

            if custom_domain:
                url = f"https://{custom_domain}/{filename}"
            else:
                url = f"{endpoint}/{bucket}/{filename}"

            self._log(f"   ✅ URL R2: {url[:80]}...")
            return url

        except Exception as e:
            self._log(f"   ❌ Errore R2 upload: {str(e)[:200]}")
            return None

    def _delete_from_r2(self, r2_key: str) -> bool:
        """
        Cancella file da R2 per liberare storage.
        Estrae la key dall'URL o usa la key diretta.
        """
        s3, bucket = self._get_r2_client()
        if s3 is None or not r2_key:
            return False

        try:
            # Se passo un URL, estrai la key (tutto dopo il dominio)
            if r2_key.startswith('http'):
                from urllib.parse import urlparse
                parsed = urlparse(r2_key)
                path = parsed.path.lstrip('/')
                # Se il path inizia con il bucket name, rimuovilo
                if path.startswith(bucket + '/'):
                    r2_key = path[len(bucket) + 1:]
                else:
                    r2_key = path

            self._log(f"   🗑️  Pulizia R2: {r2_key}")
            s3.delete_object(Bucket=bucket, Key=r2_key)
            self._log(f"   ✅ File eliminato da R2")
            return True

        except Exception as e:
            self._log(f"   ⚠️ Errore cancellazione R2: {str(e)[:150]}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # TEMP HOSTS (FALLBACK)
    # ═══════════════════════════════════════════════════════════════

    def _upload_to_temp_host(self, video_path: str) -> Optional[str]:
        """
        Upload su host temporanei con retry e fallback.
        NOTA: Su GitHub Actions questi host sono spesso bloccati dalla rete.
        """
        filename = os.path.basename(video_path)
        file_size = os.path.getsize(video_path)
        self._log(f"   📤 Upload temporaneo: {filename} ({file_size:,} bytes)")

        session = self._create_session()

        for url_template, method, file_key, headers in self.TEMP_HOSTS:
            host_name = url_template.split("//")[1].split("/")[0]
            max_attempts = 2

            for attempt in range(max_attempts):
                try:
                    self._log(f"   🌐 Host {host_name} (tentativo {attempt + 1}/{max_attempts})")

                    url = url_template.format(filename) if "{}" in url_template else url_template
                    req_headers = headers or {}
                    req_headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'

                    with open(video_path, 'rb') as f:
                        if file_key:
                            files = {file_key: (filename, f, 'video/mp4')}
                            response = session.post(url, files=files, headers=req_headers, timeout=(10, 60))
                        else:
                            response = session.put(url, data=f, headers=req_headers, timeout=(10, 60))

                    if response.status_code in (200, 201):
                        content_type = response.headers.get('Content-Type', '')
                        if 'json' in content_type:
                            try:
                                data = response.json()
                                public_url = (
                                    data.get('link') or
                                    data.get('url') or
                                    data.get('data', {}).get('link') or
                                    data.get('file', {}).get('url')
                                )
                            except (json.JSONDecodeError, AttributeError):
                                public_url = response.text.strip()
                        else:
                            public_url = response.text.strip()

                        if public_url and public_url.startswith(('http://', 'https://')):
                            self._log(f"   ✅ URL temporaneo ({host_name}): {public_url[:80]}...")
                            return public_url

                except requests.exceptions.ConnectionError:
                    self._log(f"   ⚠️ ConnectionError {host_name}")
                    if attempt < max_attempts - 1:
                        time.sleep(2 ** attempt * 5)
                except requests.exceptions.Timeout:
                    self._log(f"   ⚠️ Timeout {host_name}")
                    if attempt < max_attempts - 1:
                        time.sleep(5)
                except Exception as e:
                    self._log(f"   ❌ Errore {host_name}: {str(e)[:150]}")
                    break

            self._log(f"   ⏭️ Passo al prossimo host...")

        self._log("   ❌ Tutti gli host temporanei falliti")
        return None

    # ═══════════════════════════════════════════════════════════════
    # API INSTAGRAM
    # ═══════════════════════════════════════════════════════════════

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
                    share_to_feed: bool = True,
                    r2_key_to_cleanup: Optional[str] = None) -> Dict:
        """
        Upload Reel su Instagram (3-step container flow).
        Se r2_key_to_cleanup è fornito, cancella il file da R2 dopo il processing.
        """
        self._log(f"📤 Upload Reel: {caption[:50]}...")

        container_data = {
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': caption,
            'share_to_feed': str(share_to_feed).lower()
        }
        if cover_url:
            container_data['cover_url'] = cover_url

        result = self._api_call(f"{self.ig_user_id}/media", method="POST", data=container_data)
        if not result['success']:
            return result

        container_id = result['data'].get('id')
        self._log(f"   📦 Container creato: {container_id}")

        # Poll status
        for attempt in range(30):
            status_result = self._api_call(
                f"{container_id}",
                method="GET",
                data={'fields': 'status_code'}
            )
            if not status_result['success']:
                return status_result

            status_code = status_result['data'].get('status_code', 'UNKNOWN')
            self._log(f"   ⏳ Status: {status_code} ({attempt + 1}/30)")

            if status_code == 'FINISHED':
                break
            elif status_code == 'ERROR':
                return {'success': False, 'error': 'Container processing failed'}
            time.sleep(5)
        else:
            return {'success': False, 'error': 'Timeout polling container status'}

        # Publish
        publish_result = self._api_call(
            f"{self.ig_user_id}/media_publish",
            method="POST",
            data={'creation_id': container_id}
        )

        if publish_result['success']:
            media_id = publish_result['data'].get('id')
            self._log(f"   ✅ Reel pubblicato! Media ID: {media_id}")

            # PULIZIA R2: cancella il file temporaneo
            if r2_key_to_cleanup:
                self._delete_from_r2(r2_key_to_cleanup)

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
            data={'media_type': 'STORIES', 'image_url': image_url}
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

    # ═══════════════════════════════════════════════════════════════
    # UPLOAD LOCALE (R2 → fallback host temporanei)
    # ═══════════════════════════════════════════════════════════════

    def upload_local_video(self, video_path: str, caption: str) -> Dict:
        """
        Upload video locale su Instagram.
        1. Upload su R2 (primario)
        2. Fallback su host temporanei (se R2 fallisce)
        3. Upload su Instagram via Graph API
        4. Pulizia automatica R2 dopo pubblicazione
        """
        self._log(f"📤 Upload locale Instagram: {video_path}")

        if not os.path.exists(video_path):
            return {'success': False, 'error': f'File non trovato: {video_path}'}

        r2_key = None
        video_url = None

        # Step 1: Prova R2 prima (affidabile, non bloccato da GitHub)
        video_url = self._upload_to_r2(video_path)
        if video_url:
            # Estrai la key per la pulizia
            from urllib.parse import urlparse
            parsed = urlparse(video_url)
            r2_key = parsed.path.lstrip('/')
            # Se il path inizia con bucket name, rimuovilo per avere la key pura
            bucket = os.environ.get('R2_BUCKET_NAME', '')
            if r2_key.startswith(bucket + '/'):
                r2_key = r2_key[len(bucket) + 1:]

        # Step 2: Fallback su host temporanei
        if not video_url:
            self._log("   ⏭️ R2 fallito, provo host temporanei...")
            video_url = self._upload_to_temp_host(video_path)
            r2_key = None  # Non c'è nulla da pulire su R2

        if not video_url:
            return {
                'success': False,
                'error': 'Impossibile ottenere URL pubblico (R2 e host temporanei falliti)'
            }

        # Step 3: Upload su Instagram + pulizia R2
        return self.upload_reel(video_url, caption, r2_key_to_cleanup=r2_key)

    # ═══════════════════════════════════════════════════════════════
    # TEST CONNETTIVITÀ
    # ═══════════════════════════════════════════════════════════════

    def test_connectivity(self) -> Dict[str, bool]:
        """
        Testa connettività verso R2, host temporanei e Graph API.
        Utile per diagnosticare problemi in CI/CD.
        """
        self._log("🔌 Test connettività...")
        results = {}
        session = self._create_session()

        # Test R2 endpoint
        endpoint = os.environ.get('R2_ENDPOINT', '')
        if endpoint:
            try:
                resp = session.get(endpoint, timeout=(10, 10))
                results["r2_endpoint"] = resp.status_code < 500
                self._log(f"   R2 endpoint: {'✅ OK' if results['r2_endpoint'] else f'⚠️ Status {resp.status_code}'}")
            except Exception as e:
                results["r2_endpoint"] = False
                self._log(f"   R2 endpoint: ❌ {str(e)[:80]}")
        else:
            results["r2_endpoint"] = False
            self._log("   R2 endpoint: ⚠️ Non configurato (R2_ENDPOINT mancante)")

        # Test host temporanei (solo HEAD, veloce)
        for url_template, _, _, _ in self.TEMP_HOSTS:
            host_name = url_template.split("//")[1].split("/")[0]
            try:
                resp = session.head(f"https://{host_name}", timeout=(5, 5), allow_redirects=True)
                results[host_name] = resp.status_code < 500
                self._log(f"   {host_name}: {'✅ OK' if results[host_name] else f'⚠️ Status {resp.status_code}'}")
            except Exception as e:
                results[host_name] = False
                self._log(f"   {host_name}: ❌ {str(e)[:80]}")

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


def main():
    parser = argparse.ArgumentParser(description="Instagram Reel Uploader")
    parser.add_argument("--video-url", help="URL pubblico del video")
    parser.add_argument("--video-path", help="Path locale (upload automatico a R2/host temporaneo)")
    parser.add_argument("--caption", required=True, help="Didascalia")
    parser.add_argument("--access-token", help="Instagram Access Token")
    parser.add_argument("--ig-user-id", help="Instagram User ID")
    parser.add_argument("--test-connectivity", action="store_true", help="Testa connettività")
    parser.add_argument("--cleanup-r2", action="store_true", help="Cancella TUTTO da R2 (safety net)")
    args = parser.parse_args()

    access_token = args.access_token or os.environ.get('INSTAGRAM_ACCESS_TOKEN')
    ig_user_id = args.ig_user_id or os.environ.get('INSTAGRAM_USER_ID')

    if not access_token or not ig_user_id:
        print("❌ Access Token e IG User ID richiesti")
        print("   Imposta env vars INSTAGRAM_ACCESS_TOKEN e INSTAGRAM_USER_ID")
        return

    uploader = InstagramUploader(access_token, ig_user_id)

    # Safety net: cleanup R2
    if args.cleanup_r2:
        result = uploader.cleanup_r2_all()
        print(f"\n🧹 Cleanup R2: {json.dumps(result, indent=2)}")
        return

    if args.test_connectivity:
        uploader.test_connectivity()
        return

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