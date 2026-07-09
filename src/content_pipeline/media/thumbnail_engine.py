"""Thumbnail Engine — PIL thumbnail per tutti i concept."""
from __future__ import annotations
import os, logging
from pathlib import Path
from typing import Optional
logger = logging.getLogger(__name__)

class ThumbnailEngine:
    def __init__(self, concept_config): self.concept = concept_config

    def generate_promo(self, hook, background, output_path):
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        bg = Image.open(background).convert("RGB").resize((1280,720), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=2))
        draw = ImageDraw.Draw(bg)
        try: font = ImageFont.truetype("assets/templates/fonts/BebasNeue-Regular.ttf", 100)
        except: font = ImageFont.load_default()
        text = hook[:30].upper()
        bbox = draw.textbbox((0,0), text, font=font)
        x, y = (1280-(bbox[2]-bbox[0]))//2, (720-(bbox[3]-bbox[1]))//2 - 50
        for dx,dy in [(-3,-3),(3,-3),(-3,3),(3,3)]: draw.text((x+dx,y+dy), text, font=font, fill="#1a1a2e")
        draw.text((x,y), text, font=font, fill="#ff6b9d")
        bg.save(output_path, "JPEG", quality=90)
        logger.info(f"Thumb promo: {output_path}")

    def generate_lofi(self, title, background_frame, output_path, concept):
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        bg = Image.open(background_frame).convert("RGB").resize((1280,720), Image.LANCZOS)
        overlay = Image.new("RGBA", (1280,720), (0,0,0,100))
        bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
        bg = bg.filter(ImageFilter.GaussianBlur(radius=2))
        draw = ImageDraw.Draw(bg)
        try: font = ImageFont.truetype("assets/templates/fonts/Montserrat-Bold.ttf", 120)
        except: font = ImageFont.load_default()
        words = title.split()[:3]; main = " ".join(words).upper()
        bbox = draw.textbbox((0,0), main, font=font)
        x, y = (1280-(bbox[2]-bbox[0]))//2, (720-(bbox[3]-bbox[1]))//2 - 50
        for dx,dy in [(-3,-3),(3,-3),(-3,3),(3,3)]: draw.text((x+dx,y+dy), main, font=font, fill="#1a1a2e")
        draw.text((x,y), main, font=font, fill="#eaeaea")
        bg.save(output_path, "JPEG", quality=90)
        logger.info(f"Thumb lofi: {output_path}")
