"""
Cron Scheduler - Gestione scheduling automatico dei contenuti

Usage:
    python cron_scheduler.py --run-now
    python cron_scheduler.py --daemon
    python cron_scheduler.py --run-now story --test-connectivity
"""

import os
import sys
import json
import yaml
import time
import argparse
import schedule
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from content_engine.music_video_factory import MusicVideoFactory
from content_engine.story_scraper import StoryScraper
from voice_synthesis.tts_engine import TTSEngine

from publishers.youtube_uploader import YouTubeUploader
from publishers.instagram_uploader import InstagramUploader


class ContentScheduler:
    def __init__(self, config_path: str = "config/channels.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.config_path = config_path
        self.log_file = Path("output/scheduler.log")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        self.music_factory = MusicVideoFactory(config_path, "channel_a_music")
        self.story_scraper = StoryScraper(config_path)
        self.tts_engine = TTSEngine(config_path)

        self._init_publishers()

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
        print(log_line)
        with open(self.log_file, "a") as f:
            f.write(log_line + "\n")

    def test_connectivity(self) -> bool:
        """Testa connettività di rete prima di iniziare i job"""
        self.log("🔌 Test connettività di rete...")
        
        if not self.instagram_uploader:
            self.log("   ⚠️ Instagram uploader non disponibile, skip test")
            return False

        try:
            results = self.instagram_uploader.test_connectivity()
            ok_count = sum(1 for v in results.values() if v)
            total = len(results)
            self.log(f"   Risultato: {ok_count}/{total} servizi raggiungibili")
            return ok_count > 0
        except Exception as e:
            self.log(f"   ❌ Errore durante test connettività: {e}")
            return False

    def job_music_channel(self):
        """Job Canale Musica: genera video + upload YouTube + upload Instagram Reels"""
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
            else:
                self.log("   ⏭️ YouTube: uploader non configurato")

            # === BLOCCO 2: UPLOAD INSTAGRAM REELS (shorts musicali) ===
            self.log("   --- BLOCCO 2: Upload Instagram Reels ---")
            if self.instagram_uploader:
                try:
                    for i, short_path in enumerate(shorts[:3]):
                        if short_path and Path(short_path).exists():
                            ig_result = self.instagram_uploader.upload_local_video(
                                video_path=short_path,
                                caption=f"{video_data.get('title', 'Lofi')} #lofi #studybeats #shorts"
                            )
                            if ig_result.get("success"):
                                self.log(f"   ✅ Instagram Reel {i+1}: pubblicato")
                            else:
                                self.log(f"   ⚠️ Instagram Reel {i+1}: FALLITO - {ig_result.get('error')}")
                        else:
                            self.log(f"   ⚠️ Short {i+1} non trovato")
                except Exception as e:
                    self.log(f"   ❌ ERRORE Instagram upload: {str(e)}")
            else:
                self.log("   ⏭️ Instagram: uploader non configurato")

            self.log("JOB: Music Channel - Completato")

        except Exception as e:
            self.log(f"   ERRORE Music Channel: {str(e)}")
            import traceback
            self.log(f"   TRACEBACK: {traceback.format_exc()}")

    def job_story_channel(self):
        """Job Canale Storie: genera storie + upload Instagram Reels (storie)"""
        self.log("=" * 60)
        self.log("JOB: Story Channel - Inizio processing")
        try:
            # === FASE 1: Scraping storie ===
            self.log("   --- FASE 1: Scraping storie ---")
            stories = self.story_scraper.run(
                sources=["hackernews", "trivia", "jokes"],  # RIMOSSO wikipedia
                limit=20
            )

            if not stories:
                self.log("   Nessuna storia trovata")
                return

            self.log(f"   Trovate {len(stories)} storie")

            # === FILTRO: scegli solo storie corte (max 500 caratteri) ===
            MAX_SCRIPT_LENGTH = 500
            MAX_STORIES = 2  # ← Solo 2 storie per evitare timeout
            
            filtered_stories = []
            for story in stories:
                script = story.get("script", "")
                if len(script) <= MAX_SCRIPT_LENGTH:
                    filtered_stories.append(story)
                if len(filtered_stories) >= MAX_STORIES:
                    break
            
            if not filtered_stories:
                self.log(f"   ⚠️ Nessuna storia sotto i {MAX_SCRIPT_LENGTH} caratteri")
                return

            self.log(f"   Selezionate {len(filtered_stories)} storie corte")

            # === FASE 2: Generazione TTS ===
            self.log(f"   --- FASE 2: Generazione audio TTS ---")
            story_audio_files = []

            for i, story in enumerate(filtered_stories):
                self.log(f"   Generazione TTS per storia {i+1}...")
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

            # === FASE 3: Generazione video con ffmpeg (alternativa a MoviePy) ===
            self.log("   --- FASE 3: Generazione video storie ---")
            story_video_files = []

            for i, story_data in enumerate(story_audio_files):
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
                except Exception as e:
                    self.log(f"   ❌ Errore video storia {i+1}: {e}")

            self.log(f"   Video storie generati: {len(story_video_files)}")

            # === BLOCCO 4: UPLOAD INSTAGRAM ===
            self.log("   --- BLOCCO 4: Upload Instagram Reels ---")
            if self.instagram_uploader and story_video_files:
                try:
                    for i, story_video in enumerate(story_video_files):
                        video_path = story_video["video_path"]
                        title = story_video["title"]

                        if video_path and os.path.exists(video_path):
                            file_size = os.path.getsize(video_path)
                            self.log(f"   Upload storia {i+1}: {title} ({file_size:,} bytes)")

                            ig_result = self.instagram_uploader.upload_local_video(
                                video_path=video_path,
                                caption=f"{title} #story #daily #facts"
                            )

                            if ig_result.get("success"):
                                self.log(f"   ✅ Instagram Storia {i+1}: pubblicata")
                            else:
                                self.log(f"   ⚠️ Instagram Storia {i+1}: FALLITA")
                                self.log(f"   ⚠️ Error: {ig_result.get('error', 'nessun dettaglio')}")
                        else:
                            self.log(f"   ⚠️ Video storia {i+1} non trovato")
                except Exception as e:
                    self.log(f"   ❌ ERRORE Instagram upload: {str(e)}")
            else:
                if not self.instagram_uploader:
                    self.log("   ⏭️ Instagram: uploader non configurato")
                if not story_video_files:
                    self.log("   ⏭️ Nessun video storia da caricare")

            self.log("JOB: Story Channel - Completato")

        except Exception as e:
            self.log(f"   ERRORE Story Channel: {str(e)}")
            import traceback
            self.log(f"   TRACEBACK: {traceback.format_exc()}")

    def _create_story_video_ffmpeg(self, audio_path: str, title: str, output_path: str) -> Optional[str]:
        """
        Crea video con ffmpeg direttamente (più affidabile di MoviePy su CI/CD).
        Usa immagine statica + audio = video MP4.
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Crea immagine di background con PIL
            img_path = "assets/templates/story_background.jpg"
            if not os.path.exists(img_path):
                from PIL import Image, ImageDraw, ImageFont
                
                # Crea sfondo scuro
                img = Image.new('RGB', (1080, 1920), color=(25, 25, 40))
                draw = ImageDraw.Draw(img)
                
                # Aggiungi testo
                try:
                    font = ImageFont.truetype("arial.ttf", 50)
                except:
                    font = ImageFont.load_default()
                
                # Wrapping semplice
                words = title.split()
                lines = []
                line = ""
                for word in words:
                    test_line = line + " " + word if line else word
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    if bbox[2] - bbox[0] < 900:
                        line = test_line
                    else:
                        if line:
                            lines.append(line)
                        line = word
                if line:
                    lines.append(line)
                
                # Disegna testo centrato
                y = 750
                for line in lines[:6]:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    w = bbox[2] - bbox[0]
                    x = (1080 - w) // 2
                    draw.text((x, y), line, fill=(255, 255, 255), font=font)
                    y += 70
                
                img_path = "output/story_videos/temp_bg.jpg"
                Path(img_path).parent.mkdir(parents=True, exist_ok=True)
                img.save(img_path)

            # Ottieni durata audio con ffprobe
            duration_cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
            ]
            result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=30)
            duration = float(result.stdout.strip())

            # Genera video con ffmpeg
            self.log(f"   🎬 ffmpeg: genero video ({duration:.1f}s)")
            
            cmd = [
                'ffmpeg', '-y',
                '-loop', '1',
                '-i', img_path,
                '-i', audio_path,
                '-c:v', 'libx264',
                '-tune', 'stillimage',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-pix_fmt', 'yuv420p',
                '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2',
                '-shortest',
                '-t', str(min(duration, 60)),  # Max 60 secondi
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and output_path.exists():
                self.log(f"   ✅ ffmpeg OK: {output_path.name}")
                return str(output_path)
            else:
                self.log(f"   ❌ ffmpeg error: {result.stderr[:300]}")
                return None

        except subprocess.TimeoutExpired:
            self.log(f"   ❌ Timeout ffmpeg (120s)")
            return None
        except Exception as e:
            self.log(f"   ❌ Errore generazione video: {e}")
            return None

    def setup_schedule(self):
        music_schedule = self.config.get("channel_a_music", {}).get("publishing", {}).get("schedule", "0 9 * * *")
        parts = music_schedule.split()
        if len(parts) == 5:
            minute, hour = parts[0], parts[1]
            schedule.every().day.at(f"{hour.zfill(2)}:{minute.zfill(2)}").do(self.job_music_channel)
            self.log(f"Music Channel schedulato: ogni giorno alle {hour}:{minute}")

        story_schedule = self.config.get("channel_b_faceless", {}).get("publishing", {}).get("schedule", "0 15 * * *")
        parts = story_schedule.split()
        if len(parts) == 5:
            minute, hour = parts[0], parts[1]
            schedule.every().day.at(f"{hour.zfill(2)}:{minute.zfill(2)}").do(self.job_story_channel)
            self.log(f"Story Channel schedulato: ogni giorno alle {hour}:{minute}")

        schedule.every().sunday.at("02:00").do(self.cleanup_old_files)
        schedule.every().monday.at("08:00").do(self.weekly_report)

    def cleanup_old_files(self):
        self.log("Pulizia file temporanei...")
        temp_dirs = ["output/tts_audio", "output/tiktok_uploads", "output/instagram_uploads", "output/story_videos"]
        for dir_path in temp_dirs:
            path = Path(dir_path)
            if not path.exists():
                continue
            cutoff = datetime.now() - timedelta(days=7)
            for file in path.iterdir():
                if file.is_file() and file.stat().st_mtime < cutoff.timestamp():
                    try:
                        file.unlink()
                        self.log(f"   Rimosso: {file.name}")
                    except Exception as e:
                        self.log(f"   Errore rimozione {file.name}: {e}")
        self.log("Pulizia completata")

    def weekly_report(self):
        self.log("Generazione report settimanale...")
        video_dir = Path("output/music_videos")
        video_count = len(list(video_dir.glob("*.mp4"))) if video_dir.exists() else 0
        story_dir = Path("output/stories")
        story_count = len(list(story_dir.glob("*.json"))) if story_dir.exists() else 0
        report = f"""WEEKLY REPORT
Video musicali generati: {video_count}
Storie processate: {story_count}
Periodo: {datetime.now() - timedelta(days=7)} -> {datetime.now()}
"""
        report_path = Path("output/weekly_report.txt")
        with open(report_path, "w") as f:
            f.write(report)
        self.log(f"Report salvato: {report_path}")

    def run_daemon(self):
        self.log("Content Scheduler Daemon avviato")
        self.setup_schedule()
        while True:
            schedule.run_pending()
            time.sleep(60)

    def run_now(self, channel: Optional[str] = None, test_connectivity: bool = False):
        self.log("Esecuzione immediata")
        if test_connectivity:
            self.test_connectivity()
        if channel == "music" or channel is None:
            self.job_music_channel()
        if channel == "story" or channel is None:
            self.job_story_channel()


def main():
    parser = argparse.ArgumentParser(description="Content Scheduler")
    parser.add_argument("--daemon", action="store_true", help="Avvia daemon continuo")
    parser.add_argument("--run-now", choices=["music", "story", "all"],
                       default="all", help="Esegui job immediatamente")
    parser.add_argument("--config", default="config/channels.yaml", help="Path config")
    parser.add_argument("--test-connectivity", action="store_true", 
                       help="Testa connettività di rete prima di eseguire")
    args = parser.parse_args()

    scheduler = ContentScheduler(args.config)

    if args.daemon:
        scheduler.run_daemon()
    else:
        channel: Optional[str] = None if args.run_now == "all" else args.run_now
        scheduler.run_now(channel, test_connectivity=args.test_connectivity)


if __name__ == "__main__":
    main()