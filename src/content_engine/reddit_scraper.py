"""
CANALE B: Reddit Scraper & Story Generator
Estrae post virali da Reddit e genera script narrativi per video TTS

Usage:
    python reddit_scraper.py --config config/channels.yaml --subreddit AskReddit --limit 10
"""

import os
import sys
import json
import yaml
import argparse
import re
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import praw
from praw.models import Submission

sys.path.insert(0, str(Path(__file__).parent.parent))
from seo_optimizer.title_generator import TitleGenerator


class RedditScraper:
    """Scraper avanzato per post Reddit virali"""

    def __init__(self, config_path: str, channel_key: str = "channel_b_faceless"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.channel_config = self.config[channel_key]
        self.reddit_config = self.channel_config['reddit']

        # Inizializza client Reddit
        self.reddit = praw.Reddit(
            client_id=self.reddit_config['client_id'],
            client_secret=self.reddit_config['client_secret'],
            user_agent=self.reddit_config['user_agent']
        )

        self.title_gen = TitleGenerator(config_path)
        self.min_upvotes = self.reddit_config.get('min_upvotes', 500)
        self.max_posts = self.reddit_config.get('max_posts_per_day', 3)

        # Cache per evitare duplicati
        self.cache_file = Path("output/reddit_cache.json")
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.processed_ids = self._load_cache()

    def _load_cache(self) -> set:
        """Carica ID già processati"""
        if self.cache_file.exists():
            with open(self.cache_file) as f:
                return set(json.load(f))
        return set()

    def _save_cache(self):
        """Salva cache ID processati"""
        with open(self.cache_file, 'w') as f:
            json.dump(list(self.processed_ids), f)

    def clean_text(self, text: str) -> str:
        """Pulizia testo Reddit per TTS"""
        # Rimuovi markdown
        text = re.sub(r'\*\*', '', text)  # Bold
        text = re.sub(r'\*', '', text)      # Italic
        text = re.sub(r'`[^`]*`', '', text)  # Code
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)  # Images
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)   # Links

        # Rimuovi emoji e caratteri speciali problematici per TTS
        text = re.sub(r'[^\w\s.,!?;:\-\'"()]', ' ', text)

        # Normalizza spazi
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def fetch_hot_posts(self, subreddit_name: str, limit: int = 50) -> List[Dict]:
        """Recupera post hot da un subreddit"""
        print(f"🔍 Scraping r/{subreddit_name}...")

        subreddit = self.reddit.subreddit(subreddit_name)
        posts = []

        for submission in subreddit.hot(limit=limit):
            # Salta post già processati
            if submission.id in self.processed_ids:
                continue

            # Filtra per upvotes
            if submission.score < self.min_upvotes:
                continue

            # Salva post sticky/announcement
            if submission.stickied:
                continue

            # Pulisci testo
            clean_title = self.clean_text(submission.title)
            clean_body = self.clean_text(submission.selftext)

            # Calcola engagement score
            engagement = submission.score + (submission.num_comments * 10)

            post_data = {
                'id': submission.id,
                'subreddit': subreddit_name,
                'title': clean_title,
                'body': clean_body,
                'upvotes': submission.score,
                'num_comments': submission.num_comments,
                'engagement_score': engagement,
                'url': f"https://reddit.com{submission.permalink}",
                'created_utc': submission.created_utc,
                'author': str(submission.author) if submission.author else '[deleted]'
            }

            posts.append(post_data)

        # Ordina per engagement
        posts.sort(key=lambda x: x['engagement_score'], reverse=True)
        return posts

    def fetch_top_comments(self, post_id: str, limit: int = 5) -> List[str]:
        """Recupera top comment per arricchire la narrazione"""
        submission = self.reddit.submission(id=post_id)
        submission.comment_sort = 'top'
        submission.comments.replace_more(limit=0)

        comments = []
        for comment in submission.comments[:limit]:
            if comment.body and len(comment.body) > 50:
                clean = self.clean_text(comment.body)
                comments.append(clean)

        return comments

    def generate_script(self, post: Dict) -> str:
        """Genera script narrativo completo per TTS"""
        script = []

        # Intro hook
        hooks = [
            f"This story from r/{post['subreddit']} got {post['upvotes']} upvotes.",
            f"People on r/{post['subreddit']} are going crazy over this.",
            f"Here is what happened on r/{post['subreddit']}.",
            f"This r/{post['subreddit']} post has {post['num_comments']} comments."
        ]
        script.append(random.choice(hooks))

        # Titolo
        script.append(f"The post is titled: {post['title']}")

        # Corpo
        if post['body']:
            # Spezza in paragrafi se troppo lungo
            body = post['body']
            if len(body) > 3000:
                body = body[:3000] + "... (continues in comments)"
            script.append(body)

        # Top comments
        comments = self.fetch_top_comments(post['id'], limit=3)
        if comments:
            script.append("Here are the top comments:")
            for i, comment in enumerate(comments, 1):
                if len(comment) > 500:
                    comment = comment[:500] + "..."
                script.append(f"Comment {i}: {comment}")

        # Outro
        outros = [
            "What do you think? Let me know in the comments.",
            "Subscribe for more Reddit stories every day.",
            "Drop a like if this story hit different.",
            "Follow for more daily Reddit content."
        ]
        script.append(random.choice(outros))

        return "\n\n".join(script)

    def select_best_posts(self, all_posts: List[Dict]) -> List[Dict]:
        """Seleziona i migliori post per video"""
        # Raggruppa per subreddit
        by_subreddit = {}
        for post in all_posts:
            sub = post['subreddit']
            if sub not in by_subreddit:
                by_subreddit[sub] = []
            by_subreddit[sub].append(post)

        # Seleziona top per subreddit, max totale
        selected = []
        for sub, posts in by_subreddit.items():
            selected.extend(posts[:2])  # Max 2 per subreddit

        selected.sort(key=lambda x: x['engagement_score'], reverse=True)
        return selected[:self.max_posts]

    def run(self) -> List[Dict]:
        """Esegue pipeline completa: scrape -> select -> script"""
        all_posts = []

        for subreddit in self.reddit_config['subreddits']:
            try:
                posts = self.fetch_hot_posts(subreddit, limit=30)
                all_posts.extend(posts)
                print(f"   ✅ Trovati {len(posts)} post validi da r/{subreddit}")
            except Exception as e:
                print(f"   ❌ Errore r/{subreddit}: {e}")

        # Seleziona migliori
        best_posts = self.select_best_posts(all_posts)
        print(f"\n📊 Selezionati {len(best_posts)} post per video")

        # Genera script
        results = []
        for post in best_posts:
            script = self.generate_script(post)

            # Genera titolo video
            video_title = self.title_gen.generate_reddit_title({
                'subreddit': post['subreddit'],
                'topic': post['title'][:50],
                'emotion': random.choice(self.title_gen.keywords['reddit_emotions'])
            })

            result = {
                'post': post,
                'script': script,
                'video_title': video_title,
                'word_count': len(script.split()),
                'estimated_duration': len(script.split()) / 150 * 60  # ~150 WPM
            }

            results.append(result)
            self.processed_ids.add(post['id'])

        self._save_cache()
        return results


def main():
    parser = argparse.ArgumentParser(description="Reddit Scraper & Story Generator")
    parser.add_argument("--config", default="config/channels.yaml", help="Path config file")
    parser.add_argument("--subreddit", help="Specific subreddit to scrape")
    parser.add_argument("--limit", type=int, default=50, help="Posts to fetch per subreddit")
    args = parser.parse_args()

    scraper = RedditScraper(args.config)

    if args.subreddit:
        # Scrape singolo subreddit
        posts = scraper.fetch_hot_posts(args.subreddit, args.limit)
        print(f"\n📊 Trovati {len(posts)} post da r/{args.subreddit}")
        for post in posts[:5]:
            print(f"   • {post['title'][:60]}... ({post['upvotes']} upvotes)")
    else:
        # Pipeline completa
        results = scraper.run()

        # Salva output
        output_dir = Path("output/reddit_stories")
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, result in enumerate(results):
            output_file = output_dir / f"story_{i}_{result['post']['id']}.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)

            # Salva anche script testo per TTS
            script_file = output_dir / f"script_{i}_{result['post']['id']}.txt"
            with open(script_file, 'w') as f:
                f.write(result['script'])

            print(f"\n✅ Story {i+1}:")
            print(f"   Titolo: {result['video_title']}")
            print(f"   Parole: {result['word_count']}")
            print(f"   Durata stimata: {result['estimated_duration']:.0f}s")
            print(f"   Salvato: {output_file}")


if __name__ == "__main__":
    main()
