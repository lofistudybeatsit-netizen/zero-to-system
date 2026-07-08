
"""
Cross Poster - Automazione cross-posting multi-piattaforma
Coordina upload su YouTube, Instagram, TikTok

Usage:
    python cross_poster.py --content-type music --content-path output/video.mp4
"""

import os
import sys
import json
import yaml
import argparse
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from publishers.youtube_uploader import YouTubeUploader
from publishers.instagram_uploader import InstagramUploader
from publishers.tiktok_uploader import TikTokUploader
from shorts_factory import ShortsFactory


class CrossPoster:
    def __init__(self, config_path: str = "config/channels.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.cross_config = self.config.get("cross_platform", {})
        self.factory = ShortsFactory(config_path)
        self.uploaders = {}

        yt_config = self.config.get("channel_a_music", {}).get("youtube", {})
        if yt_config.get("client_id"):
            self.uploaders["youtube"] = YouTubeUploader()

        ig_config = self.cross_config.get("instagram", {})
        if ig_config.get("enabled") and ig_config.get("access_token"):
            self.uploaders["instagram"] = InstagramUploader(
                ig_config["access_token"],
                ig_config["page_id"]
            )

        tk_config = self.cross_config.get("tiktok", {})
        if tk_config.get("enabled"):
            self.uploaders["tiktok"] = TikTokUploader()

    def cross_post_music(self, video_path: str, metadata: Dict) -> Dict:
        results = {
            "youtube_long": None,
            "youtube_shorts": [],
            "instagram_reels": [],
            "tiktok": []
        }

        if "youtube" in self.uploaders:
            print("Upload YouTube (long-form)...")
            try:
                yt_result = self.uploaders["youtube"].upload_video(
                    video_path=video_path,
                    title=metadata["title"],
                    description=metadata["description"],
                    tags=metadata.get("tags", []),
                    category_id="10",
                    thumbnail_path=metadata.get("thumbnail_path")
                )
                results["youtube_long"] = yt_result
                print(f"   YouTube: {yt_result['url']}")
            except Exception as e:
                print(f"   YouTube error: {e}")
                results["youtube_long"] = {"error": str(e)}

        print("Generazione shorts...")
        shorts = self.factory.batch_create_from_music(video_path, num_clips=3)

        for short in shorts:
            if not short["success"]:
                continue

            short_path = short["output_path"]
            platform = short["platform"]
            short_title = f"{metadata['title'][:50]} (Clip)"
            short_desc = f"{metadata['description'][:100]}... Full version on YouTube!"

            if platform == "youtube_shorts" and "youtube" in self.uploaders:
                try:
                    result = self.uploaders["youtube"].upload_short(
                        video_path=short_path,
                        title=short_title,
                        description=short_desc,
                        tags=metadata.get("tags", [])[:5]
                    )
                    results["youtube_shorts"].append(result)
                    print(f"   YT Short: {result['url']}")
                except Exception as e:
                    print(f"   YT Short error: {e}")

            elif platform == "instagram_reels" and "instagram" in self.uploaders:
                print(f"   IG Reel: richiede URL pubblico per {short_path}")
                results["instagram_reels"].append({
                    "status": "needs_public_url",
                    "path": short_path
                })

            elif platform == "tiktok" and "tiktok" in self.uploaders:
                try:
                    hashtags = metadata.get("tags", [])[:5]
                    result = self.uploaders["tiktok"].upload_with_tiktok_uploader(
                        short_path,
                        short_title,
                        hashtags
                    )
                    results["tiktok"].append(result)
                    print(f"   TikTok: {result.get('success', False)}")
                except Exception as e:
                    print(f"   TikTok error: {e}")

        return results

    def cross_post_story(self, video_path: str, script_path: str, metadata: Dict) -> Dict:
        results = {
            "youtube": None,
            "instagram_reels": [],
            "tiktok": []
        }

        if "youtube" in self.uploaders:
            try:
                result = self.uploaders["youtube"].upload_video(
                    video_path=video_path,
                    title=metadata["title"],
                    description=metadata["description"],
                    tags=["story", "narration", "daily"],
                    category_id="24"
                )
                results["youtube"] = result
            except Exception as e:
                results["youtube"] = {"error": str(e)}

        return results

    def generate_report(self, results: Dict) -> str:
        lines = ["CROSS-POSTING REPORT", "=" * 50, ""]
        for platform, data in results.items():
            lines.append(f"\n{platform.upper()}")
            if isinstance(data, dict) and "url" in data:
                lines.append(f"   {data['url']}")
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        if "url" in item:
                            lines.append(f"   {item['url']}")
                        elif "status" in item:
                            lines.append(f"   {item['status']}: {item.get('path', '')}")
                        else:
                            lines.append(f"   {item}")
            elif isinstance(data, dict) and "error" in data:
                lines.append(f"   Error: {data['error']}")
            else:
                lines.append(f"   {data}")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Cross Poster")
    parser.add_argument("--content-type", choices=["music", "story"], required=True)
    parser.add_argument("--video-path", required=True, help="Path video principale")
    parser.add_argument("--metadata", required=True, help="Path metadata JSON")
    parser.add_argument("--script", help="Path script testo (per story)")
    args = parser.parse_args()

    with open(args.metadata) as f:
        metadata = json.load(f)

    poster = CrossPoster()

    if args.content_type == "music":
        results = poster.cross_post_music(args.video_path, metadata)
    else:
        if not args.script:
            print("--script richiesto per content-type story")
            return
        results = poster.cross_post_story(args.video_path, args.script, metadata)

    report = poster.generate_report(results)
    print(report)

    report_path = Path("output/cross_post_report.txt")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport salvato: {report_path}")


if __name__ == "__main__":
    main()
