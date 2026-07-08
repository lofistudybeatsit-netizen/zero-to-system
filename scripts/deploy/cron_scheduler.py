
"""
Cron Scheduler - Gestione scheduling automatico dei contenuti

Usage:
    python cron_scheduler.py --run-now
    python cron_scheduler.py --daemon
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

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from content_engine.music_video_factory import MusicVideoFactory
from content_engine.story_scraper import StoryScraper
from voice_synthesis.tts_engine import TTSEngine


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

    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        with open(self.log_file, "a") as f:
            f.write(log_line + "\n")

    def job_music_channel(self):
        self.log("JOB: Music Channel - Inizio processing")
        try:
            result = self.music_factory.process_next()
            if not result:
                self.log("   Nessun nuovo file musicale da processare")
                return

            video_data = result["video"]
            self.log(f"   Video creato: {video_data['title']}")
            self.log(f"   Shorts generati: {len(result['shorts'])}")
            self.log("JOB: Music Channel - Completato")

        except Exception as e:
            self.log(f"   ERRORE Music Channel: {str(e)}")

    def job_story_channel(self):
        self.log("JOB: Story Channel - Inizio processing")
        try:
            stories = self.story_scraper.run(
                sources=["hackernews", "wikipedia", "trivia", "jokes"],
                limit=20
            )

            if not stories:
                self.log("   Nessuna storia trovata")
                return

            self.log(f"   Trovate {len(stories)} storie")

            for i, story in enumerate(stories):
                self.log(f"   Generazione TTS per storia {i+1}...")

                script_path = Path(f"output/stories/script_{i}_{story['story']['id']}.txt")

                try:
                    audio_path = self.tts_engine.generate_sync(
                        story["script"],
                        output_path=Path(f"output/tts_audio/story_{i}.mp3")
                    )
                    self.log(f"   Audio generato: {audio_path}")
                except Exception as e:
                    self.log(f"   Errore TTS: {e}")

            self.log("JOB: Story Channel - Completato")

        except Exception as e:
            self.log(f"   ERRORE Story Channel: {str(e)}")

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
        temp_dirs = ["output/tts_audio", "output/tiktok_uploads", "output/instagram_uploads"]
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

    def run_now(self, channel: str = None):
        self.log("Esecuzione immediata")
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
    args = parser.parse_args()

    scheduler = ContentScheduler(args.config)

    if args.daemon:
        scheduler.run_daemon()
    else:
        channel = None if args.run_now == "all" else args.run_now
        scheduler.run_now(channel)


if __name__ == "__main__":
    main()
