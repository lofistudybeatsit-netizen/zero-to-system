"""
Cron Scheduler - DEBUG VERSION
"""

import os
import sys
import json
import yaml
import time
import argparse
import schedule
import subprocess
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# DEBUG: log prima di ogni import
print(f"[DEBUG] Inizio import...", flush=True)

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

print(f"[DEBUG] Import music_video_factory...", flush=True)
from content_engine.music_video_factory import MusicVideoFactory

print(f"[DEBUG] Import story_scraper...", flush=True)
from content_engine.story_scraper import StoryScraper

print(f"[DEBUG] Import tts_engine...", flush=True)
from voice_synthesis.tts_engine import TTSEngine

print(f"[DEBUG] Import publishers...", flush=True)
from publishers.youtube_uploader import YouTubeUploader
from publishers.instagram_uploader import InstagramUploader

print(f"[DEBUG] Tutti gli import OK", flush=True)


class ContentScheduler:
    def __init__(self, config_path: str = "config/channels.yaml"):
        print(f"[DEBUG] ContentScheduler.__init__ start", flush=True)
        
        print(f"[DEBUG] Leggo config: {config_path}", flush=True)
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        print(f"[DEBUG] Config letto", flush=True)

        self.config_path = config_path
        self.log_file = Path("output/scheduler.log")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        print(f"[DEBUG] Inizializzo factory...", flush=True)
        self.music_factory = MusicVideoFactory(config_path, "channel_a_music")
        print(f"[DEBUG] Factory OK", flush=True)

        print(f"[DEBUG] Inizializzo scraper...", flush=True)
        self.story_scraper = StoryScraper(config_path)
        print(f"[DEBUG] Scraper OK", flush=True)

        print(f"[DEBUG] Inizializzo TTS...", flush=True)
        self.tts_engine = TTSEngine(config_path)
        print(f"[DEBUG] TTS OK", flush=True)

        print(f"[DEBUG] Inizializzo publishers...", flush=True)
        self._init_publishers()
        print(f"[DEBUG] Publishers OK", flush=True)
        
        print(f"[DEBUG] ContentScheduler.__init__ completato", flush=True)

    def _init_publishers(self):
        """Inizializza i publisher con credenziali da env vars"""
        # YouTube
        try:
            yt_client_id = os.environ.get('YOUTUBE_CLIENT_ID')
            yt_client_secret = os.environ.get('YOUTUBE_CLIENT_SECRET')
            yt_refresh_token = os.environ.get('YOUTUBE_REFRESH_TOKEN')

            if all([yt_client_id, yt_client_secret, yt_refresh_token]):
                self.youtube_uploader = YouTubeUploader()
                self.log("   YouTube uploader inizializzato")
            else:
                self.youtube_uploader = None
                self.log("   ⚠️ YouTube uploader: credenziali mancanti")
        except Exception as e:
            self.youtube_uploader = None
            self.log(f"   ⚠️ YouTube uploader non disponibile: {e}")

        # Instagram
        try:
            ig_token = os.environ.get('INSTAGRAM_ACCESS_TOKEN')
            ig_user_id = os.environ.get('INSTAGRAM_USER_ID')

            if all([ig_token, ig_user_id]):
                self.instagram_uploader = InstagramUploader(
                    access_token=ig_token,
                    ig_user_id=ig_user_id
                )
                self.log("   Instagram uploader inizializzato")
            else:
                self.instagram_uploader = None
                self.log("   ⚠️ Instagram uploader: credenziali mancanti")
        except Exception as e:
            self.instagram_uploader = None
            self.log(f"   ⚠️ Instagram uploader non disponibile: {e}")

    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line, flush=True)
        with open(self.log_file, "a") as f:
            f.write(log_line + "\n")

    def job_music_channel(self):
        """Job Canale Musica"""
        self.log("=" * 60)
        self.log("JOB: Music Channel - Inizio processing")
        try:
            result = self.music_factory.process_next()
            if not result:
                self.log("   Nessun nuovo file musicale da processare")
                return

            video_data = result["video"]
            shorts = result.get("shorts", [])

            self.log(f"   Video creato: {video_data['title']}")
            self.log(f"   Shorts generati: {len(shorts)}")
            
            # DEBUG: mostra tipo e contenuto di shorts
            self.log(f"   DEBUG: shorts type = {type(shorts)}")
            if shorts:
                self.log(f"   DEBUG: shorts[0] type = {type(shorts[0])}")
                self.log(f"   DEBUG: shorts[0] = {str(shorts[0])[:200]}")

            # === BLOCCO 1: UPLOAD YOUTUBE ===
            self.log("   --- BLOCCO 1: Upload YouTube ---")
            if self.youtube_uploader:
                try:
                    video_path = video_data.get("video_path", "")
                    if video_path and Path(video_path).exists():
                        yt_result = self.youtube_uploader.upload_video(
                            video_path=video_path,
                            title=video_data.get("title", "Lofi Study Beats"),
                            description=video_data.get("description", "Relaxing lofi music"),
                            tags=video_data.get("tags", ["lofi", "study", "beats"]),
                            category_id="10",
                            privacy_status="public"
                        )
                        self.log(f"   ✅ YouTube: {yt_result.get('url', 'OK')}")
                    else:
                        self.log(f"   ⚠️ Video path non valido: {video_path}")
                except Exception as e:
                    self.log(f"   ❌ ERRORE YouTube upload: {str(e)}")
                    self.log(traceback.format_exc())
            else:
                self.log("   ⏭️ YouTube: uploader non configurato")

            # === BLOCCO 2: UPLOAD INSTAGRAM REELS ===
            self.log("   --- BLOCCO 2: Upload Instagram Reels ---")
            if self.instagram_uploader:
                try:
                    self.log(f"   DEBUG: shorts = {shorts}")
                    
                    for i, short_item in enumerate(shorts[:3]):
                        self.log(f"   DEBUG: short {i+1} type = {type(short_item)}")
                        
                        # Estrai path se è un dict
                        if isinstance(short_item, dict):
                            short_path = short_item.get("path") or short_item.get("video_path") or short_item.get("file_path")
                            self.log(f"   DEBUG: estratto path da dict: {short_path}")
                        else:
                            short_path = short_item
                            self.log(f"   DEBUG: short_path diretto: {short_path}")
                        
                        self.log(f"   DEBUG: short {i+1} path = {short_path}")
                        self.log(f"   DEBUG: exists? {os.path.exists(short_path) if short_path else 'N/A'}")

                        if short_path and Path(short_path).exists():
                            file_size = os.path.getsize(short_path)
                            self.log(f"   DEBUG: file size = {file_size} bytes")
                            
                            self.log(f"   Upload Instagram Reel {i+1}: {short_path}")

                            ig_result = self.instagram_uploader.upload_local_video(
                                video_path=short_path,
                                caption=f"{video_data.get('title', 'Lofi')} #lofi #studybeats #shorts"
                            )

                            self.log(f"   DEBUG: ig_result = {json.dumps(ig_result, indent=2)[:500]}")

                            if ig_result.get("success"):
                                self.log(f"   ✅ Instagram Reel {i+1}: pubblicato")
                            else:
                                self.log(f"   ⚠️ Instagram Reel {i+1}: FALLITA")
                                self.log(f"   ⚠️ Error: {ig_result.get('error', 'nessun dettaglio')}")
                        else:
                            self.log(f"   ⚠️ Short {i+1} path non valido o file mancante: {short_path}")

                except Exception as e:
                    self.log(f"   ❌ ERRORE Instagram upload: {str(e)}")
                    self.log(traceback.format_exc())
            else:
                self.log("   ⏭️ Instagram: uploader non configurato")

            self.log("JOB: Music Channel - Completato")

        except Exception as e:
            self.log(f"   ERRORE Music Channel: {str(e)}")
            self.log(traceback.format_exc())

    def job_story_channel(self):
        """Job Canale Storie"""
        self.log("=" * 60)
        self.log("JOB: Story Channel - Inizio processing")
        
        # DEBUG: log prima di ogni operazione
        self.log("[DEBUG] Step 1: Avvio scraping...")
        
        try:
            # FASE 1: Scraping
            self.log("   --- FASE 1: Scraping storie ---")
            self.log("[DEBUG] Chiamo story_scraper.run()...")
            
            stories = self.story_scraper.run(
                sources=["hackernews", "trivia", "jokes"],
                limit=20
            )
            
            self.log(f"[DEBUG] Scraping completato, trovate {len(stories)} storie")

            if not stories:
                self.log("   Nessuna storia trovata")
                return

            self.log(f"   Trovate {len(stories)} storie")

            # FILTRO
            MAX_SCRIPT_LENGTH = 500
            MAX_STORIES = 2
            
            self.log("[DEBUG] Inizio filtro storie...")
            filtered_stories = []
            for story in stories:
                script = story.get("script", "")
                if len(script) <= MAX_SCRIPT_LENGTH:
                    filtered_stories.append(story)
                if len(filtered_stories) >= MAX_STORIES:
                    break
            
            self.log(f"[DEBUG] Filtrate {len(filtered_stories)} storie")
            
            if not filtered_stories:
                self.log(f"   ⚠️ Nessuna storia sotto i {MAX_SCRIPT_LENGTH} caratteri")
                return

            self.log(f"   Selezionate {len(filtered_stories)} storie corte")

            # FASE 2: TTS
            self.log(f"   --- FASE 2: Generazione audio TTS ---")
            story_audio_files = []

            for i, story in enumerate(filtered_stories):
                self.log(f"   [DEBUG] TTS storia {i+1}...")
                try:
                    audio_path = self.tts_engine.generate_sync(
                        story["script"],
                        output_path=Path(f"output/tts_audio/story_{i}.mp3")
                    )
                    self.log(f"   ✅ Audio generato: {audio_path}")
                    story_audio_files.append({
                        "audio_path": str(audio_path),
                        "title": story.get("story", {}).get("title", f"Story {i+1}"),
                        "script": story.get("script", "")
                    })
                except Exception as e:
                    self.log(f"   ❌ Errore TTS storia {i+1}: {e}")

            self.log(f"   Audio generati: {len(story_audio_files)}")

            # FASE 3: Video
            self.log("   --- FASE 3: Generazione video storie ---")
            story_video_files = []

            for i, story_data in enumerate(story_audio_files):
                self.log(f"   [DEBUG] Genero video {i+1}...")
                try:
                    video_path = self._create_story_video_ffmpeg(
                        audio_path=story_data["audio_path"],
                        title=story_data["title"],
                        output_path=f"output/story_videos/story_{i}.mp4"
                    )
                    if video_path:
                        story_video_files.append({
                            "video_path": video_path,
                            "title": story_data["title"]
                        })
                        self.log(f"   ✅ Video storia {i+1}: {video_path}")
                    else:
                        self.log(f"   ⚠️ Video storia {i+1}: ritornato None")
                except Exception as e:
                    self.log(f"   ❌ Errore video storia {i+1}: {e}")
                    self.log(traceback.format_exc())

            self.log(f"   Video storie generati: {len(story_video_files)}")

            # FASE 4: Upload
            self.log("   --- FASE 4: Upload Instagram Reels ---")
            if self.instagram_uploader and story_video_files:
                try:
                    for i, story_video in enumerate(story_video_files):
                        video_path = story_video["video_path"]
                        title = story_video["title"]

                        self.log(f"   [DEBUG] Upload storia {i+1}: {video_path}")
                        self.log(f"   [DEBUG] exists? {os.path.exists(video_path)}")

                        if video_path and os.path.exists(video_path):
                            file_size = os.path.getsize(video_path)
                            self.log(f"   Upload storia {i+1}: {title} ({file_size:,} bytes)")

                            ig_result = self.instagram_uploader.upload_local_video(
                                video_path=video_path,
                                caption=f"{title} #story #daily #facts"
                            )

                            self.log(f"   [DEBUG] ig_result = {json.dumps(ig_result, indent=2)[:500]}")

                            if ig_result.get("success"):
                                self.log(f"   ✅ Instagram Storia {i+1}: pubblicata")
                            else:
                                self.log(f"   ⚠️ Instagram Storia {i+1}: FALLITA")
                                self.log(f"   ⚠️ Error: {ig_result.get('error', 'nessun dettaglio')}")
                        else:
                            self.log(f"   ⚠️ Video storia {i+1} non trovato: {video_path}")
                except Exception as e:
                    self.log(f"   ❌ ERRORE Instagram upload: {str(e)}")
                    self.log(traceback.format_exc())
            else:
                if not self.instagram_uploader:
                    self.log("   ⏭️ Instagram: uploader non configurato")
                if not story_video_files:
                    self.log("   ⏭️ Nessun video storia da caricare")

            self.log("JOB: Story Channel - Completato")

        except Exception as e:
            self.log(f"   ERRORE Story Channel: {str(e)}")
            self.log(traceback.format_exc())

    def _create_story_video_ffmpeg(self, audio_path: str, title: str, output_path: str) -> Optional[str]:
        """Crea video con ffmpeg"""
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self.log(f"   [DEBUG] Creo immagine per: {title[:50]}")

            # Crea immagine
            img_path = output_path.with_suffix('.jpg')
            
            from PIL import Image, ImageDraw, ImageFont
            
            img = Image.new('RGB', (1080, 1920), color=(25, 25, 40))
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("arial.ttf", 50)
            except:
                font = ImageFont.load_default()
            
            display_title = title[:60] if len(title) > 60 else title
            
            bbox = draw.textbbox((0, 0), display_title, font=font)
            w = bbox[2] - bbox[0]
            x = (1080 - w) // 2
            draw.text((x, 850), display_title, fill=(255, 255, 255), font=font)
            
            img.save(img_path)
            self.log(f"   [DEBUG] Immagine salvata: {img_path}")

            # Durata audio
            self.log(f"   [DEBUG] Ottengo durata audio...")
            duration_cmd = [
                'ffprobe', '-v', 'error', 
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', 
                audio_path
            ]
            result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=30)
            duration = float(result.stdout.strip())
            self.log(f"   [DEBUG] Durata: {duration:.1f}s")

            # ffmpeg
            self.log(f"   [DEBUG] Avvio ffmpeg...")
            cmd = [
                'ffmpeg', '-y',
                '-loop', '1',
                '-i', str(img_path),
                '-i', audio_path,
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '28',
                '-c:a', 'aac',
                '-b:a', '96k',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                '-shortest',
                '-t', str(min(duration, 60)),
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            
            # Pulisci
            if img_path.exists():
                img_path.unlink()

            if result.returncode == 0 and output_path.exists():
                self.log(f"   [DEBUG] ffmpeg OK: {output_path.name}")
                return str(output_path)
            else:
                self.log(f"   ❌ ffmpeg error (code {result.returncode})")
                self.log(f"   stderr: {result.stderr[:500]}")
                return None

        except subprocess.TimeoutExpired:
            self.log(f"   ❌ Timeout ffmpeg (180s)")
            return None
        except Exception as e:
            self.log(f"   ❌ Errore generazione video: {e}")
            self.log(traceback.format_exc())
            return None

    def run_now(self, channel: Optional[str] = None, test_connectivity: bool = False):
        self.log("=" * 60)
        self.log("Esecuzione immediata AVVIATA")
        self.log(f"   Channel: {channel or 'all'}")
        
        if test_connectivity:
            self.log("   → Avvio test connettività...")
            self.test_connectivity()
        
        if channel == "music" or channel is None:
            self.log("   → Avvio job_music_channel...")
            self.job_music_channel()
        if channel == "story" or channel is None:
            self.log("   → Avvio job_story_channel...")
            self.job_story_channel()
        
        self.log("Esecuzione completata")


def main():
    parser = argparse.ArgumentParser(description="Content Scheduler")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--run-now", choices=["music", "story", "all"], default="all")
    parser.add_argument("--config", default="config/channels.yaml")
    parser.add_argument("--test-connectivity", action="store_true")
    args = parser.parse_args()

    print(f"[DEBUG] Avvio scheduler...", flush=True)
    scheduler = ContentScheduler(args.config)
    print(f"[DEBUG] Scheduler creato", flush=True)

    if args.daemon:
        scheduler.run_daemon()
    else:
        channel = None if args.run_now == "all" else args.run_now
        scheduler.run_now(channel, test_connectivity=args.test_connectivity)


if __name__ == "__main__":
    main()