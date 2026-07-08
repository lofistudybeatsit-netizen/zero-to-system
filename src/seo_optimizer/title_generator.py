
"""
Title Generator - Generazione titoli SEO-optimized
"""

import json
import random
from pathlib import Path
from typing import Dict, List


class TitleGenerator:
    def __init__(self, config_path: str = "config/channels.yaml"):
        import yaml
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.seo_config = self.config.get("seo", {})
        self.keywords_file = self.seo_config.get("target_keywords_file", "config/seo_keywords.json")

        with open(self.keywords_file) as f:
            self.keywords = json.load(f)

        self.templates = self.seo_config.get("title_templates", {})

    def generate_music_title(self, metadata: Dict) -> str:
        templates = self.templates.get("music", [
            "{mood} {genre} for {activity} | {duration} Hours",
            "{genre} Playlist to {activity} | {mood} Vibes",
            "{mood} {genre} Mix | Perfect for {activity}"
        ])

        template = random.choice(templates)

        title = template.format(
            mood=metadata.get("mood", random.choice(self.keywords["moods"])),
            genre=metadata.get("genre", random.choice(self.keywords["music_genres"])),
            activity=metadata.get("activity", random.choice(self.keywords["activities"])),
            duration=metadata.get("duration", "1")
        )

        power_words = ["Ultimate", "Best", "Perfect", "Deep", "Intense", "Relaxing"]
        if random.random() > 0.5:
            title = f"{random.choice(power_words)} {title}"

        if len(title) > 100:
            title = title[:97] + "..."

        return title

    def generate_story_title(self, metadata: Dict) -> str:
        """Genera titolo per video storie (ex-reddit)"""
        templates = self.templates.get("story", [
            "{hook} | Daily Stories",
            "People Share {topic} | {source}",
            "{emotion} Story from {source}"
        ])

        template = random.choice(templates)

        title = template.format(
            hook=random.choice(self.keywords.get("reddit_hooks", ["This Changed Everything", "You Won't Believe This"])),
            topic=metadata.get("topic", "Their Secrets"),
            source=metadata.get("source", "Hacker News"),
            emotion=metadata.get("emotion", random.choice(self.keywords.get("reddit_emotions", ["Heartbreaking", "Hilarious"])))
        )

        if random.random() > 0.7:
            title = f"{random.randint(1, 10)} {title}"

        if len(title) > 100:
            title = title[:97] + "..."

        return title

    def generate_reddit_title(self, metadata: Dict) -> str:
        """Backward compatibility - alias per generate_story_title"""
        return self.generate_story_title(metadata)

    def generate_short_title(self, original_title: str, platform: str = "youtube") -> str:
        hooks = ["POV:", "Wait for it...", "This is crazy", "Part 1", "The truth about"]

        if platform == "tiktok":
            return f"{random.choice(hooks)} {original_title[:40]}"
        elif platform == "instagram":
            return f"{original_title[:60]}"
        else:
            return f"{random.choice(hooks)} {original_title[:50]}"


if __name__ == "__main__":
    gen = TitleGenerator()

    music_title = gen.generate_music_title({
        "mood": "Dark",
        "genre": "Ambient",
        "activity": "Studying",
        "duration": "2"
    })
    print(f"Music Title: {music_title}")

    story_title = gen.generate_story_title({
        "source": "Hacker News",
        "topic": "Startup Failures",
        "emotion": "Shocking"
    })
    print(f"Story Title: {story_title}")
