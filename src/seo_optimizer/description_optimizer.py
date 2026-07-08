"""
Description Optimizer - Genera descrizioni SEO-optimized con timestamp e CTA
"""

import json
from pathlib import Path
from typing import Dict, List


class DescriptionOptimizer:
    """Genera descrizioni complete per YouTube"""

    def __init__(self, config_path: str = "config/channels.yaml"):
        import yaml
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.seo_config = self.config.get('seo', {})

        with open(self.seo_config.get('target_keywords_file', 'config/seo_keywords.json')) as f:
            self.keywords = json.load(f)

    def generate_music_description(self, title: str, timestamps: List[Dict] = None) -> str:
        """Genera descrizione per video musicale"""
        lines = [
            f"🎵 {title}",
            "",
            "Welcome to the perfect soundtrack for your session.",
            "Put on your headphones, relax, and let the music take you away.",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        # Timestamp se disponibili
        if timestamps:
            lines.append("🕐 Timestamps:")
            for ts in timestamps:
                lines.append(f"{ts['time']} - {ts['label']}")
            lines.append("")

        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "🎧 Perfect for:",
            "• Studying & Focus",
            "• Working & Coding",
            "• Sleeping & Relaxing",
            "• Reading & Writing",
            "• Meditation & Mindfulness",
            "",
            "🎹 About the Music:",
            "All music is original and produced independently.",
            "Subscribe for new uploads every day.",
            "",
            "#lofi #ambient #studymusic #chillhop #relaxingmusic",
        ])

        return "\n".join(lines)

    def generate_reddit_description(self, post_data: Dict, script_summary: str = "") -> str:
        """Genera descrizione per video Reddit"""
        lines = [
            f"📖 {post_data.get('title', 'Reddit Story')}",
            "",
            "Original post:",
            f"{post_data.get('url', '')}",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        if script_summary:
            lines.extend([
                "📝 Story Summary:",
                script_summary[:500],
                "",
            ])

        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "🎮 Background Gameplay:",
            "All gameplay footage is original and copyright-free.",
            "",
            "🔔 Subscribe for daily Reddit stories!",
            "New video every day at 3 PM CET.",
            "",
            "#redditstories #reddit #storytime #narration",
        ])

        return "\n".join(lines)

    def add_affiliate_links(self, description: str, affiliate_links: List[Dict]) -> str:
        """Aggiunge link affiliate in fondo alla descrizione"""
        if not affiliate_links:
            return description

        lines = ["", "🛠️ Tools & Resources:", ""]
        for link in affiliate_links:
            lines.append(f"• {link['name']}: {link['url']}")

        return description + "\n" + "\n".join(lines)


if __name__ == "__main__":
    opt = DescriptionOptimizer()
    desc = opt.generate_music_description("Dark Ambient for Studying")
    print(desc[:500] + "...")
