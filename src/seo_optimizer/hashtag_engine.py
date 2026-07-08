"""
Hashtag Engine - Gestione hashtag ottimizzata per piattaforma
"""

import json
import random
from pathlib import Path
from typing import List, Dict


class HashtagEngine:
    """Genera hashtag ottimizzati per ogni piattaforma"""

    PLATFORM_LIMITS = {
        'youtube': 15,      # YT consiglia max 15 tag
        'instagram': 30,    # IG max 30 hashtag
        'tiktok': 5,        # TikTok consiglia 3-5
        'twitter': 3,       # X/Twitter 2-3
    }

    def __init__(self, config_path: str = "config/channels.yaml"):
        import yaml
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        with open('config/seo_keywords.json') as f:
            self.keywords = json.load(f)

    def get_music_hashtags(self, platform: str = 'youtube') -> List[str]:
        """Hashtag per contenuti musicali"""
        base = self.keywords['hashtags_music']

        # Aggiungi trending (simulato, in produzione fetch da API)
        trending = ['#viral', '#trending', '#fyp', '#foryou']

        all_tags = base + random.sample(trending, min(2, len(trending)))

        limit = self.PLATFORM_LIMITS.get(platform, 15)
        return all_tags[:limit]

    def get_reddit_hashtags(self, platform: str = 'youtube') -> List[str]:
        """Hashtag per contenuti Reddit"""
        base = self.keywords['hashtags_reddit']

        trending = ['#viral', '#trending', '#fyp', '#foryoupage']
        all_tags = base + random.sample(trending, min(2, len(trending)))

        limit = self.PLATFORM_LIMITS.get(platform, 15)
        return all_tags[:limit]

    def format_for_platform(self, hashtags: List[str], platform: str) -> str:
        """Formatta hashtag per la piattaforma target"""
        if platform == 'youtube':
            # YT usa tag separati da virgola
            return ", ".join([h.replace('#', '') for h in hashtags])
        elif platform in ['instagram', 'tiktok']:
            # IG/TikTok: hashtag nel caption
            return " ".join(hashtags)
        else:
            return " ".join(hashtags)


if __name__ == "__main__":
    engine = HashtagEngine()
    yt_tags = engine.get_music_hashtags('youtube')
    ig_tags = engine.get_music_hashtags('instagram')

    print(f"YouTube: {engine.format_for_platform(yt_tags, 'youtube')}")
    print(f"Instagram: {engine.format_for_platform(ig_tags, 'instagram')}")
