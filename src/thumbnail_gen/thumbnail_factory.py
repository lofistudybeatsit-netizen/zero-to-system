
"""
Thumbnail Factory - Generazione thumbnail programmatica
Ottimizzati per CTR (Click-Through Rate)

Usage:
    from thumbnail_factory import ThumbnailFactory
    factory = ThumbnailFactory()
    factory.create_music_thumbnail("Dark Ambient for Studying", "output/thumb.jpg")
"""

import os
import random
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np


class ThumbnailFactory:
    """Genera thumbnail ottimizzati per YouTube"""

    # Dimensioni YouTube thumbnail
    WIDTH = 1280
    HEIGHT = 720

    # Palette colori (dark academia / ambient)
    PALETTES = {
        'dark_academia': {
            'bg': '#1a1a2e',
            'primary': '#e94560',
            'secondary': '#ffffff',
            'accent': '#c9b037',
            'gradient': ['#16213e', '#0f3460', '#1a1a2e']
        },
        'lofi': {
            'bg': '#f4e4c1',
            'primary': '#2d3436',
            'secondary': '#e17055',
            'accent': '#fdcb6e',
            'gradient': ['#ffeaa7', '#fab1a0', '#fd79a8']
        },
        'ambient': {
            'bg': '#0f0f23',
            'primary': '#00d2ff',
            'secondary': '#ffffff',
            'accent': '#3a7bd5',
            'gradient': ['#0f0f23', '#1a1a3e', '#16213e']
        },
        'reddit': {
            'bg': '#ff4500',
            'primary': '#ffffff',
            'secondary': '#1a1a2e',
            'accent': '#ff6347',
            'gradient': ['#ff4500', '#ff6347', '#ff7f50']
        }
    }

    def __init__(self, fonts_dir: str = "assets/fonts"):
        self.fonts_dir = Path(fonts_dir)
        self.fonts_dir.mkdir(parents=True, exist_ok=True)

        # Carica font di sistema
        self.fonts = self._load_fonts()

    def _load_fonts(self) -> Dict:
        """Carica font disponibili"""
        fonts = {}

        # Font di sistema comuni
        system_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
            "C:/Windows/Fonts/arialbd.ttf",  # Windows
        ]

        for font_path in system_fonts:
            if os.path.exists(font_path):
                try:
                    fonts['bold'] = ImageFont.truetype(font_path, 72)
                    fonts['regular'] = ImageFont.truetype(font_path.replace('Bold', '').replace('bd', ''), 36)
                    break
                except:
                    pass

        # Fallback
        if 'bold' not in fonts:
            fonts['bold'] = ImageFont.load_default()
            fonts['regular'] = fonts['bold']

        return fonts

    def _create_gradient_background(self, palette: Dict, width: int, height: int) -> Image:
        """Crea sfondo gradient"""
        img = Image.new('RGB', (width, height), palette['bg'])
        draw = ImageDraw.Draw(img)

        gradient_colors = palette.get('gradient', [palette['bg']])

        # Gradient verticale semplice
        for i in range(height):
            ratio = i / height
            color_idx = int(ratio * (len(gradient_colors) - 1))
            color_idx = min(color_idx, len(gradient_colors) - 1)

            # Interpolazione semplice
            color = gradient_colors[color_idx]
            draw.line([(0, i), (width, i)], fill=color)

        return img

    def _add_noise_texture(self, img: Image, intensity: float = 0.02) -> Image:
        """Aggiunge texture noise per profondità"""
        arr = np.array(img)
        noise = np.random.normal(0, 255 * intensity, arr.shape).astype(np.int16)
        arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(arr)

    def _wrap_text(self, text: str, font: ImageFont, max_width: int) -> list:
        """Spezza testo in linee che entrano in max_width"""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            # Stima larghezza (approssimativa)
            bbox = font.getbbox(test_line) if hasattr(font, 'getbbox') else (0, 0, len(test_line) * font.size * 0.6, font.size)
            text_width = bbox[2] - bbox[0] if bbox else len(test_line) * font.size * 0.6

            if text_width < max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return lines

    def _add_text_with_shadow(self, draw: ImageDraw, text: str, font: ImageFont,
                             position: Tuple[int, int], color: str, shadow_color: str = '#000000',
                             shadow_offset: int = 3, align: str = 'center') -> None:
        """Disegna testo con ombra"""
        x, y = position

        # Ombra
        draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color, anchor=align)
        # Testo principale
        draw.text((x, y), text, font=font, fill=color, anchor=align)

    def create_music_thumbnail(self, title: str, output_path: str,
                               palette_name: str = 'ambient',
                               subtitle: str = "🎵 Listen & Relax",
                               duration: str = "1 Hour") -> str:
        """
        Crea thumbnail per video musicale

        Args:
            title: Titolo video
            output_path: Path output
            palette_name: Tema colore
            subtitle: Sottotitolo
            duration: Durata (es. "1 Hour", "2 Hours")
        """
        palette = self.PALETTES.get(palette_name, self.PALETTES['ambient'])

        # Crea sfondo
        img = self._create_gradient_background(palette, self.WIDTH, self.HEIGHT)
        img = self._add_noise_texture(img, 0.015)

        draw = ImageDraw.Draw(img)

        # Aggiungi pattern geometrico sottile
        for i in range(0, self.WIDTH, 40):
            alpha = 20
            draw.line([(i, 0), (i, self.HEIGHT)], fill=(alpha, alpha, alpha + 30), width=1)

        # Titolo principale
        font_title = self.fonts.get('bold')
        lines = self._wrap_text(title, font_title, self.WIDTH - 200)

        # Calcola posizione centrata
        line_height = font_title.size + 10
        total_text_height = len(lines) * line_height
        start_y = (self.HEIGHT - total_text_height) // 2 - 50

        for i, line in enumerate(lines):
            y = start_y + i * line_height
            self._add_text_with_shadow(
                draw, line, font_title,
                (self.WIDTH // 2, y),
                palette['secondary'],
                align='mt'  # middle-top
            )

        # Sottotitolo
        font_sub = self.fonts.get('regular')
        self._add_text_with_shadow(
            draw, subtitle, font_sub,
            (self.WIDTH // 2, start_y + total_text_height + 30),
            palette['accent'],
            align='mt'
        )

        # Durata badge
        badge_text = f"⏱️ {duration}"
        font_badge = self.fonts.get('regular')
        bbox = font_badge.getbbox(badge_text) if hasattr(font_badge, 'getbbox') else None
        badge_width = (bbox[2] - bbox[0] + 20) if bbox else 200
        badge_height = font_badge.size + 10

        # Badge background
        badge_x = self.WIDTH - badge_width - 30
        badge_y = 30
        draw.rounded_rectangle(
            [(badge_x, badge_y), (badge_x + badge_width, badge_y + badge_height)],
            radius=10,
            fill=palette['primary']
        )
        draw.text(
            (badge_x + badge_width // 2, badge_y + badge_height // 2),
            badge_text,
            font=font_badge,
            fill='white',
            anchor='mm'
        )

        # Salva
        img.save(output_path, quality=95)
        return output_path

    def create_reddit_thumbnail(self, title: str, output_path: str,
                                 subreddit: str = "AskReddit",
                                 upvotes: str = "15K",
                                 palette_name: str = 'reddit') -> str:
        """
        Crea thumbnail per video Reddit

        Args:
            title: Titolo post/titolo video
            output_path: Path output
            subreddit: Nome subreddit
            upvotes: Numero upvotes (es. "15K", "500")
            palette_name: Tema colore
        """
        palette = self.PALETTES.get(palette_name, self.PALETTES['reddit'])

        # Sfondo
        img = self._create_gradient_background(palette, self.WIDTH, self.HEIGHT)
        img = self._add_noise_texture(img, 0.02)

        draw = ImageDraw.Draw(img)

        # Header con subreddit
        font_header = self.fonts.get('regular')
        header_text = f"r/{subreddit}"
        self._add_text_with_shadow(
            draw, header_text, font_header,
            (self.WIDTH // 2, 80),
            palette['secondary'],
            align='mt'
        )

        # Titolo principale (più grande, centrato)
        font_title = self.fonts.get('bold')
        # Limita lunghezza per thumbnail
        display_title = title[:60] + "..." if len(title) > 60 else title
        lines = self._wrap_text(display_title, font_title, self.WIDTH - 150)

        line_height = font_title.size + 8
        total_height = len(lines) * line_height
        start_y = (self.HEIGHT - total_height) // 2

        for i, line in enumerate(lines):
            y = start_y + i * line_height
            self._add_text_with_shadow(
                draw, line, font_title,
                (self.WIDTH // 2, y),
                'white',
                shadow_color='#000000',
                shadow_offset=4,
                align='mt'
            )

        # Upvotes badge
        badge_text = f"🔥 {upvotes} upvotes"
        font_badge = self.fonts.get('regular')
        bbox = font_badge.getbbox(badge_text) if hasattr(font_badge, 'getbbox') else None
        badge_width = (bbox[2] - bbox[0] + 30) if bbox else 250
        badge_height = font_badge.size + 15

        badge_x = 30
        badge_y = self.HEIGHT - badge_height - 30
        draw.rounded_rectangle(
            [(badge_x, badge_y), (badge_x + badge_width, badge_y + badge_height)],
            radius=15,
            fill='#ff4500'
        )
        draw.text(
            (badge_x + badge_width // 2, badge_y + badge_height // 2),
            badge_text,
            font=font_badge,
            fill='white',
            anchor='mm'
        )

        # CTA
        font_cta = self.fonts.get('regular')
        draw.text(
            (self.WIDTH - 30, self.HEIGHT - 30),
            "Watch the full story ▶",
            font=font_cta,
            fill=palette['accent'],
            anchor='rb'
        )

        img.save(output_path, quality=95)
        return output_path

    def create_short_thumbnail(self, title: str, output_path: str,
                               palette_name: str = 'ambient') -> str:
        """
        Crea thumbnail per Shorts/Reels/TikTok (1080x1920)

        Nota: YouTube Shorts usano frame dal video, ma questo serve per altre piattaforme
        """
        width, height = 1080, 1920
        palette = self.PALETTES.get(palette_name, self.PALETTES['ambient'])

        img = Image.new('RGB', (width, height), palette['bg'])
        draw = ImageDraw.Draw(img)

        # Gradient semplice
        for i in range(height):
            ratio = i / height
            r = int(int(palette['bg'][1:3], 16) * (1 - ratio * 0.3))
            g = int(int(palette['bg'][3:5], 16) * (1 - ratio * 0.3))
            b = int(int(palette['bg'][5:7], 16) * (1 - ratio * 0.3))
            draw.line([(0, i), (width, i)], fill=(r, g, b))

        # Titolo (grande, in alto)
        font_title = ImageFont.truetype(self.fonts['bold'].path, 100) if hasattr(self.fonts['bold'], 'path') else self.fonts['bold']
        lines = self._wrap_text(title, font_title, width - 100)

        line_height = 110
        start_y = 200

        for i, line in enumerate(lines[:3]):  # Max 3 linee
            y = start_y + i * line_height
            self._add_text_with_shadow(
                draw, line, font_title,
                (width // 2, y),
                'white',
                shadow_offset=5,
                align='mt'
            )

        # Hook text
        font_hook = ImageFont.truetype(self.fonts['regular'].path, 60) if hasattr(self.fonts['regular'], 'path') else self.fonts['regular']
        hooks = ["Wait for it...", "This is crazy", "You won't believe this"]
        hook = random.choice(hooks)

        draw.text(
            (width // 2, height - 300),
            hook,
            font=font_hook,
            fill=palette['accent'],
            anchor='mm'
        )

        img.save(output_path, quality=95)
        return output_path


if __name__ == "__main__":
    factory = ThumbnailFactory()

    # Test music thumbnail
    print("🎵 Generazione thumbnail music...")
    path = factory.create_music_thumbnail(
        "Dark Ambient for Studying",
        "output/test_music_thumb.jpg",
        palette_name='dark_academia',
        duration="2 Hours"
    )
    print(f"   ✅ Salvato: {path}")

    # Test Reddit thumbnail
    print("📖 Generazione thumbnail Reddit...")
    path = factory.create_reddit_thumbnail(
        "What is the creepiest thing that happened to you at night?",
        "output/test_reddit_thumb.jpg",
        subreddit="AskReddit",
        upvotes="15K"
    )
    print(f"   ✅ Salvato: {path}")
