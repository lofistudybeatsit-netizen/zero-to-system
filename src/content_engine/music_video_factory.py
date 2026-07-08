"""
CANALE A: YouTube Music Video Factory
Genera video YouTube da file audio + immagine statica
Cross-posta automaticamente su Instagram Reels e TikTok

Usage:
    python music_video_factory.py --config config/channels.yaml --channel channel_a_music
"""

import os
import sys
import json
import random
import yaml
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Video processing
try: 
    from moviepy.editor import AudioFileClip, ImageClip, CompositeVideoClip, TextClip 
except ImportError:     
    from moviepy import AudioFileClip, ImageClip, CompositeVideoClip, TextClip
from moviepy.video.fx.all import fadein, fadeout
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# SEO
sys.path.insert(0, str(Path(__file__).parent.parent))
from seo_optimizer.title_generator import TitleGenerator
from seo_optimizer.description_optimizer import DescriptionOptimizer
from seo_optimizer.hashtag_engine import HashtagEngine


class MusicVideoFactory:
    """Factory per generazione video musicali automatizzati"""

    def __init__(self, config_path: str, channel_key: str = "channel_a_music"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.channel_config = self.config[channel_key]
        self.content_config = self.channel_config['content']
        self.cross_config = self.config.get('cross_platform', {})

        # Inizializza SEO engines
        self.title_gen = TitleGenerator(config_path)
        self.desc_gen = DescriptionOptimizer(config_path)
        self.hashtag_eng = HashtagEngine(config_path)

        # Path
        self.music_folder = Path(self.content_config['music_folder'])
        self.output_folder = Path("output/music_videos")
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def get_music_files(self) -> list:
        """Recupera tutti i file audio disponibili"""
        extensions = ['.mp3', '.wav', '.flac', '.m4a', '.ogg']
        files = []
        for ext in extensions:
            files.extend(self.music_folder.glob(f'*{ext}'))
        return sorted(files)

    def generate_title(self, music_file: Path) -> str:
        """Genera titolo SEO-optimized per il video musicale"""
        metadata = {
            'genre': random.choice(self.title_gen.keywords['music_genres']),
            'mood': random.choice(self.title_gen.keywords['moods']),
            'activity': random.choice(self.title_gen.keywords['activities']),
            'duration': '1' if self.content_config['video_duration'] >= 3600 else '0.5'
        }
        return self.title_gen.generate_music_title(metadata)

    def generate_thumbnail(self, title: str, output_path: Path) -> Path:
        """Genera thumbnail programmatica"""
        # Dimensioni YouTube thumbnail: 1280x720
        width, height = 1280, 720

        # Crea sfondo gradient
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)

        # Aggiungi pattern/texture semplice
        for i in range(0, height, 4):
            alpha = int(255 * (1 - i / height))
            draw.line([(0, i), (width, i)], fill=(alpha, alpha, alpha + 50))

        # Testo principale
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except:
            font_large = ImageFont.load_default()
            font_small = font_large

        # Wrapping testo
        words = title.split()
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font_large)
            if bbox[2] - bbox[0] < width - 100:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))

        # Disegna testo
        y_offset = height // 2 - (len(lines) * 80) // 2
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font_large)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2

            # Ombra
            draw.text((x+3, y_offset+3), line, font=font_large, fill='#000000')
            # Testo
            draw.text((x, y_offset), line, font=font_large, fill='#ffffff')
            y_offset += 80

        # Subtitle
        subtitle = "🎵 Listen & Relax"
        bbox = draw.textbbox((0, 0), subtitle, font=font_small)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        draw.text((x, y_offset + 20), subtitle, font=font_small, fill='#aaaaaa')

        img.save(output_path)
        return output_path

    def create_video(self, music_file: Path, title: str) -> dict:
        """Crea video completo da file audio"""
        print(f"🎵 Creazione video per: {music_file.name}")

        # Carica audio
        audio = AudioFileClip(str(music_file))
        duration = min(audio.duration, self.content_config['video_duration'])
        audio = audio.subclip(0, duration)

        # Crea clip immagine statica
        static_image = self.content_config.get('static_image', 'assets/templates/music_background.jpg')
        if not Path(static_image).exists():
            # Crea immagine di default
            img = Image.new('RGB', (1920, 1080), color='#0f0f23')
            Path('assets/templates').mkdir(parents=True, exist_ok=True)
            img.save('assets/templates/music_background.jpg')
            static_image = 'assets/templates/music_background.jpg'

        video = ImageClip(static_image).set_duration(duration)
        video = video.set_audio(audio)

        # Aggiungi overlay testo (opzionale, sottile)
        # Per musica ambient, meno è meglio

        # Fade in/out audio
        audio_faded = audio.audio_fadein(3).audio_fadeout(5)
        video = video.set_audio(audio_faded)

        # Genera thumbnail
        thumb_path = self.output_folder / f"thumb_{music_file.stem}.jpg"
        self.generate_thumbnail(title, thumb_path)

        # Esporta video
        output_path = self.output_folder / f"{music_file.stem}.mp4"
        video.write_videofile(
            str(output_path),
            fps=1,  # Basso FPS per immagine statica (risparmia spazio)
            codec='libx264',
            audio_codec='aac',
            threads=4,
            preset='ultrafast',
            logger=None
        )

        # Genera descrizione e hashtag
        description = self.desc_gen.generate_music_description(title)
        hashtags = self.hashtag_eng.get_music_hashtags()

        # Aggiungi affiliate links
        affiliates = self.config.get('monetization', {}).get('affiliate_links', [])
        affiliate_text = "\n\n🎧 Tools I Use:\n"
        for aff in affiliates:
            affiliate_text += f"• {aff['name']}: {aff['url']}\n"

        full_description = description + affiliate_text + "\n\n" + " ".join(hashtags)

        return {
            'video_path': str(output_path),
            'thumbnail_path': str(thumb_path),
            'title': title,
            'description': full_description,
            'tags': hashtags,
            'duration': duration,
            'music_file': str(music_file)
        }

    def create_shorts(self, music_file: Path, title: str) -> list:
        """Crea YouTube Shorts/Instagram Reels/TikTok clips da musica"""
        print(f"✂️ Creazione shorts da: {music_file.name}")

        audio = AudioFileClip(str(music_file))
        duration = audio.duration

        shorts = []
        # Crea 3 clip da 60 secondi ciascuna (diversi segmenti)
        segments = [
            (0, 60),
            (duration // 3, duration // 3 + 60),
            (duration * 2 // 3, duration * 2 // 3 + 60)
        ]

        for i, (start, end) in enumerate(segments):
            if end > duration:
                end = duration
            if end - start < 30:  # Minimo 30 secondi
                continue

            clip_audio = audio.subclip(start, end)

            # Per shorts: formato verticale 9:16 (1080x1920)
            # Usa visualizzatore audio semplice o immagine
            img = Image.new('RGB', (1080, 1920), color='#0f0f23')

            # Aggiungi testo "hook"
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
            except:
                font = ImageFont.load_default()

            hook_text = f"🎵 {title[:40]}..."
            bbox = draw.textbbox((0, 0), hook_text, font=font)
            text_width = bbox[2] - bbox[0]
            x = (1080 - text_width) // 2
            draw.text((x, 200), hook_text, font=font, fill='#ffffff')

            # Salva immagine temporanea
            temp_img = f"temp_short_{i}.jpg"
            img.save(temp_img)

            video = ImageClip(temp_img).set_duration(end - start)
            video = video.set_audio(clip_audio)

            short_path = self.output_folder / f"short_{music_file.stem}_{i}.mp4"
            video.write_videofile(
                str(short_path),
                fps=1,
                codec='libx264',
                audio_codec='aac',
                threads=4,
                preset='ultrafast',
                logger=None
            )

            os.remove(temp_img)

            shorts.append({
                'path': str(short_path),
                'title': f"{title} (Clip {i+1})",
                'duration': end - start,
                'platforms': ['youtube_shorts', 'instagram_reels', 'tiktok']
            })

        return shorts

    def process_next(self) -> dict:
        """Processa il prossimo file musicale in coda"""
        music_files = self.get_music_files()

        if not music_files:
            print("❌ Nessun file musicale trovato in", self.music_folder)
            return None

        # Prendi il primo file non ancora processato (check via log)
        processed_log = self.output_folder / ".processed.json"
        processed = []
        if processed_log.exists():
            with open(processed_log) as f:
                processed = json.load(f)

        for music_file in music_files:
            if str(music_file) not in processed:
                title = self.generate_title(music_file)
                video_data = self.create_video(music_file, title)
                shorts_data = self.create_shorts(music_file, title)

                # Salva log
                processed.append(str(music_file))
                with open(processed_log, 'w') as f:
                    json.dump(processed, f)

                return {
                    'video': video_data,
                    'shorts': shorts_data,
                    'timestamp': datetime.now().isoformat()
                }

        print("✅ Tutti i file musicali sono stati processati")
        return None


def main():
    parser = argparse.ArgumentParser(description="Music Video Factory")
    parser.add_argument("--config", default="config/channels.yaml", help="Path config file")
    parser.add_argument("--channel", default="channel_a_music", help="Channel key")
    args = parser.parse_args()

    factory = MusicVideoFactory(args.config, args.channel)
    result = factory.process_next()

    if result:
        print(f"\n✅ Video creato:")
        print(f"   Titolo: {result['video']['title']}")
        print(f"   File: {result['video']['video_path']}")
        print(f"   Shorts: {len(result['shorts'])} clip generate")

        # Salva metadata per upload
        metadata_path = Path(result['video']['video_path']).parent / f"metadata_{Path(result['video']['video_path']).stem}.json"
        with open(metadata_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"   Metadata: {metadata_path}")
    else:
        print("\n⚠️ Nessun video da processare")


if __name__ == "__main__":
    main()
