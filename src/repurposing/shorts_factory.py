"""
Shorts Factory - Genera clip verticali 9:16 da contenuti esistenti
Converte video orizzontali in formato Shorts/Reels/TikTok

Usage:
    python shorts_factory.py --input output/music_video.mp4 --output output/shorts/
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional

from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, TextClip
from moviepy.video.fx.all import resize, crop
from PIL import Image, ImageDraw, ImageFont
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from seo_optimizer.title_generator import TitleGenerator


class ShortsFactory:
    """Factory per creazione clip verticali ottimizzati"""

    # Specifiche piattaforme
    PLATFORM_SPECS = {
        'youtube_shorts': {'width': 1080, 'height': 1920, 'max_duration': 60, 'format': 'mp4'},
        'instagram_reels': {'width': 1080, 'height': 1920, 'max_duration': 90, 'format': 'mp4'},
        'tiktok': {'width': 1080, 'height': 1920, 'max_duration': 180, 'format': 'mp4'},
    }

    def __init__(self, config_path: str = "config/channels.yaml"):
        import yaml
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.title_gen = TitleGenerator(config_path)
        self.output_dir = Path("output/shorts")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_music_short(self, video_path: str, segment_start: float = 0,
                          segment_duration: float = 60, platform: str = 'youtube_shorts') -> Dict:
        """
        Crea short da video musicale (crop + overlay)

        Strategia: prendi segmento centrale, aggiungi testo hook, 
        visualizzazione audio semplice
        """
        specs = self.PLATFORM_SPECS[platform]

        # Carica video
        video = VideoFileClip(video_path)
        audio = video.audio

        # Estrai segmento
        end = min(segment_start + segment_duration, video.duration)
        segment = video.subclip(segment_start, end)
        segment_audio = audio.subclip(segment_start, end) if audio else None

        # Ridimensiona a formato verticale (9:16)
        # Per video orizzontali: crop al centro o zoom
        w, h = segment.size
        target_w, target_h = specs['width'], specs['height']

        # Calcola scaling per riempire verticale
        scale = target_h / h
        new_w = int(w * scale)

        # Resize
        resized = segment.resize(height=target_h)

        # Crop orizzontale al centro
        x_center = new_w // 2
        x1 = max(0, x_center - target_w // 2)
        x2 = x1 + target_w

        cropped = resized.crop(x1=x1, x2=x2, y1=0, y2=target_h)

        # Genera overlay testo (hook)
        hook_text = self._generate_hook_text(video_path, platform)

        # Crea clip testo
        txt_clip = self._create_text_overlay(hook_text, target_w, target_h, segment.duration)

        # Componi
        final = CompositeVideoClip([cropped, txt_clip], size=(target_w, target_h))
        if segment_audio:
            final = final.set_audio(segment_audio)

        # Esporta
        output_path = self.output_dir / f"short_{Path(video_path).stem}_{platform}.mp4"
        final.write_videofile(
            str(output_path),
            fps=30,
            codec='libx264',
            audio_codec='aac',
            threads=4,
            preset='ultrafast',
            logger=None
        )

        video.close()
        segment.close()

        return {
            'success': True,
            'output_path': str(output_path),
            'platform': platform,
            'duration': segment.duration,
            'hook_text': hook_text
        }

    def create_reddit_short(self, video_path: str, script_text: str,
                           platform: str = 'youtube_shorts') -> Dict:
        """
        Crea short da video Reddit/TTS

        Strategia: video gameplay background + testo sovrapposto (subtitles style)
        """
        specs = self.PLATFORM_SPECS[platform]
        target_w, target_h = specs['width'], specs['height']

        # Carica video background (gameplay)
        bg_video = VideoFileClip(video_path)

        # Ridimensiona a verticale
        w, h = bg_video.size
        scale = target_h / h
        new_w = int(w * scale)
        resized = bg_video.resize(height=target_h)
        x_center = new_w // 2
        x1 = max(0, x_center - target_w // 2)
        cropped = resized.crop(x1=x1, x2=x1 + target_w, y1=0, y2=target_h)

        # Spezza script in segmenti per sottotitoli
        words = script_text.split()
        words_per_segment = 8
        segments = []
        for i in range(0, len(words), words_per_segment):
            segment_text = ' '.join(words[i:i + words_per_segment])
            segments.append(segment_text)

        # Calcola durata per segmento
        total_duration = min(bg_video.duration, specs['max_duration'])
        segment_duration = total_duration / max(len(segments), 1)

        # Crea clip sottotitoli
        subtitle_clips = []
        for i, text in enumerate(segments):
            start = i * segment_duration
            end = min((i + 1) * segment_duration, total_duration)

            txt_clip = self._create_subtitle_clip(text, target_w, target_h, 
                                                  end - start, start)
            subtitle_clips.append(txt_clip)

        # Componi
        final = CompositeVideoClip([cropped] + subtitle_clips, size=(target_w, target_h))

        # Esporta
        output_path = self.output_dir / f"reddit_short_{Path(video_path).stem}_{platform}.mp4"
        final.write_videofile(
            str(output_path),
            fps=30,
            codec='libx264',
            audio_codec='aac',
            threads=4,
            preset='ultrafast',
            logger=None
        )

        bg_video.close()

        return {
            'success': True,
            'output_path': str(output_path),
            'platform': platform,
            'duration': total_duration,
            'segments': len(segments)
        }

    def _generate_hook_text(self, video_path: str, platform: str) -> str:
        """Genera testo hook per catturare attenzione"""
        hooks = [
            "Wait for the drop... 🔥",
            "This hits different 🎵",
            "POV: You're in the zone",
            "Best part coming up...",
            "This changed everything",
            "Drop a ❤️ if you feel this",
            "Part 1 - Full version on YT",
            "This is your sign to relax",
        ]

        # Per TikTok, hook più brevi
        if platform == 'tiktok':
            return random.choice(hooks[:4])

        return random.choice(hooks)

    def _create_text_overlay(self, text: str, width: int, height: int, 
                            duration: float) -> TextClip:
        """Crea overlay testo stilizzato"""
        # Posizione: alto, centrato
        txt = TextClip(
            text,
            fontsize=60,
            color='white',
            font='DejaVu-Sans-Bold',
            stroke_color='black',
            stroke_width=2,
            method='caption',
            size=(width - 100, None),
            align='center'
        ).set_duration(duration).set_position(('center', 100))

        return txt

    def _create_subtitle_clip(self, text: str, width: int, height: int,
                             duration: float, start: float) -> TextClip:
        """Crea clip sottotitolo stile Reddit/TTS"""
        # Sfondo semi-trasparente
        txt = TextClip(
            text,
            fontsize=50,
            color='white',
            font='DejaVu-Sans',
            stroke_color='black',
            stroke_width=2,
            method='caption',
            size=(width - 80, None),
            align='center'
        ).set_duration(duration).set_start(start).set_position(('center', height - 300))

        return txt

    def batch_create_from_music(self, video_path: str, num_clips: int = 3) -> List[Dict]:
        """Crea multipli short da un video musicale"""
        video = VideoFileClip(video_path)
        duration = video.duration
        video.close()

        # Dividi in segmenti equidistanti
        segment_length = min(60, duration / num_clips)
        results = []

        for i in range(num_clips):
            start = (duration / (num_clips + 1)) * (i + 1) - segment_length / 2
            start = max(0, start)

            for platform in ['youtube_shorts', 'instagram_reels', 'tiktok']:
                result = self.create_music_short(
                    video_path, start, segment_length, platform
                )
                results.append(result)

        return results

    def create_static_music_short(self, audio_path: str, image_path: str,
                                  platform: str = 'youtube_shorts') -> Dict:
        """
        Crea short da audio + immagine statica (per musica ambient)
        Più efficiente, nessun video processing pesante
        """
        specs = self.PLATFORM_SPECS[platform]
        target_w, target_h = specs['width'], specs['height']
        max_duration = specs['max_duration']

        # Carica audio
        audio = AudioFileClip(audio_path)
        duration = min(audio.duration, max_duration)
        audio = audio.subclip(0, duration)

        # Carica/Crea immagine
        if image_path and Path(image_path).exists():
            img = Image.open(image_path)
        else:
            # Crea immagine default
            img = Image.new('RGB', (target_w, target_h), color='#0f0f23')
            draw = ImageDraw.Draw(img)

            # Gradient semplice
            for i in range(0, target_h, 4):
                alpha = int(255 * (1 - i / target_h))
                draw.line([(0, i), (target_w, i)], fill=(alpha, alpha, alpha + 50))

            # Testo
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
            except:
                font = ImageFont.load_default()

            title = Path(audio_path).stem.replace('_', ' ').title()
            draw.text((50, 200), title, font=font, fill='white')
            draw.text((50, 300), "🎵 Full version on YouTube", font=font, fill='#aaaaaa')

        # Ridimensiona
        img = img.resize((target_w, target_h))
        img.save('temp_short_bg.jpg')

        # Crea video
        video = ImageClip('temp_short_bg.jpg').set_duration(duration)
        video = video.set_audio(audio)

        # Esporta
        output_path = self.output_dir / f"short_{Path(audio_path).stem}_{platform}.mp4"
        video.write_videofile(
            str(output_path),
            fps=1,  # Basso FPS per immagine statica
            codec='libx264',
            audio_codec='aac',
            threads=4,
            preset='ultrafast',
            logger=None
        )

        audio.close()
        video.close()

        # Cleanup
        if Path('temp_short_bg.jpg').exists():
            os.remove('temp_short_bg.jpg')

        return {
            'success': True,
            'output_path': str(output_path),
            'platform': platform,
            'duration': duration
        }


def main():
    parser = argparse.ArgumentParser(description="Shorts Factory")
    parser.add_argument("--input", required=True, help="Path video/audio input")
    parser.add_argument("--output", default="output/shorts", help="Cartella output")
    parser.add_argument("--type", choices=['music', 'reddit'], default='music',
                       help="Tipo di contenuto")
    parser.add_argument("--platform", choices=['youtube_shorts', 'instagram_reels', 'tiktok'],
                       default='youtube_shorts', help="Piattaforma target")
    parser.add_argument("--image", help="Path immagine (per music static)")
    parser.add_argument("--script", help="Testo script (per reddit)")
    args = parser.parse_args()

    factory = ShortsFactory()
    factory.output_dir = Path(args.output)
    factory.output_dir.mkdir(parents=True, exist_ok=True)

    if args.type == 'music':
        if args.input.endswith(('.mp3', '.wav', '.m4a')):
            # Audio + immagine statica
            result = factory.create_static_music_short(args.input, args.image, args.platform)
        else:
            # Video esistente
            result = factory.create_music_short(args.input, platform=args.platform)
    else:
        if not args.script:
            print("❌ --script richiesto per tipo reddit")
            return
        result = factory.create_reddit_short(args.input, args.script, args.platform)

    print(f"\n✅ Short creato:")
    print(f"   Path: {result['output_path']}")
    print(f"   Platform: {result['platform']}")
    print(f"   Duration: {result['duration']:.1f}s")


if __name__ == "__main__":
    main()
