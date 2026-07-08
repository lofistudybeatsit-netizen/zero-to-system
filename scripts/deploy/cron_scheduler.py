"""
Cron Scheduler - Gestione scheduling automatico dei contenuti

Usage:
    python cron_scheduler.py --run-now
    python cron_scheduler.py --daemon
    python cron_scheduler.py --run-now story --test-connectivity  # Testa rete prima
"""

import os
import sys
import json
import yaml
import time
import argparse
import schedule
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# === IMPORT MOVIEPY ===
from moviepy.editor import AudioFileClip, ImageClip
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from content_engine.music_video_factory import MusicVideoFactory
from content_engine.story_scraper import StoryScraper
from voice_synthesis.tts_engine import TTSEngine

# === IMPORT PUBLISHER ===
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

        # === INIZIALIZZA PUBLISHER ===
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
        """Job Canale Musica: genera video + upload YouTube + upload Instagram Reels (shorts musicali)"""
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
            self.log("   Generazione completata, avvio upload...")

            # === BLOCCO 1: UPLOAD YOUTUBE (video completo) ===
            self.log("   --- BLOCCO 1: Upload YouTube ---")
            if self.youtube_uploader:
                try:
                    video_path = video_data.get("video_path", "")
                    self.log(f"   DEBUG: video_path = {video_path}")
                    self.log(f"   DEBUG: exists? {os.path.exists(video_path) if video_path else 'N/A'}")

                    if video_path and Path(video_path).exists():
                        self.log(f"   Upload YouTube: {video_path}")
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
                    import traceback
                    self.log(f"   TRACEBACK: {traceback.format_exc()}")
            else:
                self.log("   ⏭️ YouTube: uploader non configurato")

            # === BLOCCO 2: UPLOAD INSTAGRAM REELS (shorts musicali) ===
            self.log("   --- BLOCCO 2: Upload Instagram Reels (shorts musica) ---")
            if self.instagram_uploader:
                try:
                    self.log(f"   DEBUG: shorts trovati = {len(shorts)}")

                    for i, short_path in enumerate(shorts[:3]):
                        self.log(f"   DEBUG: short {i+1} path = {short_path}")
                        self.log(f"   DEBUG: short {i+1} exists? {os.path.exists(short_path) if short_path else 'N/A'}")

                        if short_path and Path(short_path).exists():
                            self.log(f"   Upload Instagram Reel {i+1}: {short_path}")

                            # DEBUG: verifica dimensione file
                            file_size = os.path.getsize(short_path)
                            self.log(f"   DEBUG: file size = {file_size} bytes")

                            ig_result = self.instagram_uploader.upload_local_video(
                                video_path=short_path,
                                caption=f"{video_data.get('title', 'Lofi')} #lofi #studybeats #shorts"
                            )

                            self.log(f"   DEBUG: ig_result type = {type(ig_result)}")
                            self.log(f"   DEBUG: ig_result = {json.dumps(ig_result, indent=2)[:500]}")

                            if ig_result.get("success"):
                                self.log(f"   ✅ Instagram Reel {i+1}: pubblicato - {ig_result.get('url', 'OK')}")
                            else:
                                self.log(f"   ⚠️ Instagram Reel {i+1}: FALLITO")
                                self.log(f"   ⚠️ Status: {ig_result.get('status', 'errore')}")
                                self.log(f"   ⚠️ Error: {ig_result.get('error', 'nessun dettaglio')}")
                        else:
                            self.log(f"   ⚠️ Short {i+1} path non valido o file mancante: {short_path}")

                except Exception as e:
                    self.log(f"   ❌ ERRORE Instagram upload: {str(e)}")
                    import traceback
                    self.log(f"   TRACEBACK: {traceback.format_exc()}")
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
                sources=["hackernews", "wikipedia", "trivia", "jokes"],
                limit=20
            )

            if not stories:
                self.log("   Nessuna storia trovata")
                return

            self.log(f"   Trovate {len(stories)} storie")

            # === FASE 2: Generazione TTS (audio) ===
            self.log("   --- FASE 2: Generazione audio TTS ---")
            story_audio_files = []

            for i, story in enumerate(stories[:5]):  # Max 5 storie
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

            # === FASE 3: Generazione video dalle storie ===
            self.log("   --- FASE 3: Generazione video storie ---")
            story_video_files = []

            for i, story_data in enumerate(story_audio_files):
                try:
                    # Crea video semplice con audio + immagine statica
                    video_path = self._create_story_video(
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

            # === BLOCCO 4: UPLOAD INSTAGRAM REELS (storie) ===
            self.log("   --- BLOCCO 4: Upload Instagram Reels (storie) ---")
            if self.instagram_uploader and story_video_files:
                try:
                    for i, story_video in enumerate(story_video_files[:3]):  # Max 3 reel
                        video_path = story_video["video_path"]
                        title = story_video["title"]

                        self.log(f"   DEBUG: storia video {i+1} path = {video_path}")
                        self.log(f"   DEBUG: exists? {os.path.exists(video_path)}")

                        if video_path and os.path.exists(video_path):
                            file_size = os.path.getsize(video_path)
                            self.log(f"   DEBUG: file size = {file_size} bytes")

                            self.log(f"   Upload Instagram Reel storia {i+1}: {title}")

                            ig_result = self.instagram_uploader.upload_local_video(
                                video_path=video_path,
                                caption=f"{title} #story #daily #facts"
                            )

                            self.log(f"   DEBUG: ig_result = {json.dumps(ig_result, indent=2)[:500]}")

                            if ig_result.get("success"):
                                self.log(f"   ✅ Instagram Storia Reel {i+1}: pubblicata")
                            else:
                                self.log(f"   ⚠️ Instagram Storia Reel {i+1}: FALLITA")
                                self.log(f"   ⚠️ Status: {ig_result.get('status', 'errore')}")
                                self.log(f"   ⚠️ Error: {ig_result.get('error', 'nessun dettaglio')}")
                        else:
                            self.log(f"   ⚠️ Video storia {i+1} non trovato: {video_path}")

                except Exception as e:
                    self.log(f"   ❌ ERRORE Instagram upload storie: {str(e)}")
                    import traceback
                    self.log(f"   TRACEBACK: {traceback.format_exc()}")
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

    def _create_story_video(self, audio_path: str, title: str, output_path: str) -> Optional[str]:
        """
        Crea un video semplice da un file audio + immagine statica.
        Usa moviepy per combinare audio e immagine.
        """
        try:
            from moviepy.editor import AudioFileClip, ImageClip, CompositeVideoClip

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Carica audio
            audio = AudioFileClip(audio_path)
            duration = audio.duration

            # Crea clip video con immagine statica
            # Usa un'immagine di default o genera una semplice
            img_path = "assets/templates/story_background.jpg"
            if not os.path.exists(img_path):
                # Se non c'è immagine, crea una nera
                from PIL import Image
                img = Image.new('RGB', (1080, 1920), color='black')
                img_path = "output/story_videos/temp_bg.jpg"
                Path(img_path).parent.mkdir(parents=True, exist_ok=True)
                img.save(img_path)

            video = ImageClip(img_path, duration=duration)
            video = video.set_audio(audio)

            # Salva video
            video.write_videofile(
                str(output_path),
                fps=24,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='output/story_videos/temp-audio.m4a',
                remove_temp=True
            )

            audio.close()
            video.close()

            return str(output_path)

        except Exception as e:
            self.log(f"   ❌ Errore creazione video storia: {e}")
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
        self.log("   Premi Ctrl+C per terminare")
        self.setup_schedule()
        while True:
            schedule.run_pending()
            time.sleep(60)

    def run_now(self, channel: Optional[str] = None, test_connectivity: bool = False):
        self.log("Esecuzione immediata")
        
        # Test connettività se richiesto
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