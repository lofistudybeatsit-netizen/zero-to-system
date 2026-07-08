
"""
Story Scraper Universale - Fonti multiple senza API Reddit

Fonti supportate:
1. Hacker News (API gratuita, no auth) - storie tech/startup
2. 4chan API (no auth) - contenuti grezzi, nicchie
3. JSONPlaceholder (demo) - per testing
4. File locale (storie salvate manualmente)
5. RSS Feeds generici (blog, news)
6. Wikipedia Random (no auth) - fatti curiosi
7. Open Trivia DB (no auth) - domande/risposte
8. JokeAPI (no auth) - barzellette/storie umoristiche

Usage:
    python story_scraper.py --source hackernews --limit 10
    python story_scraper.py --source local --folder assets/stories/
"""

import os
import sys
import json
import yaml
import argparse
import random
import re
import requests
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from seo_optimizer.title_generator import TitleGenerator


class StoryScraper:
    """Scraper universale per storie da fonti multiple"""

    def __init__(self, config_path: str = "config/channels.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.title_gen = TitleGenerator(config_path)
        self.cache_file = Path("output/story_cache.json")
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.processed_ids = self._load_cache()

        # Output
        self.output_dir = Path("output/stories")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_cache(self) -> set:
        if self.cache_file.exists():
            with open(self.cache_file) as f:
                return set(json.load(f))
        return set()

    def _save_cache(self):
        with open(self.cache_file, "w") as f:
            json.dump(list(self.processed_ids), f)

    def clean_text(self, text: str) -> str:
        """Pulizia testo per TTS"""
        text = re.sub(r"\*\*", "", text)
        text = re.sub(r"\*", "", text)
        text = re.sub(r"`[^`]*`", "", text)
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
        text = re.sub(r"\[.*?\]\(.*?\)", "", text)
        text = re.sub(r"[^\w\s.,!?;:\-\'\"()]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    # ============================================
    # FONTE 1: Hacker News (API gratuita, no auth)
    # ============================================
    def fetch_hackernews(self, limit: int = 30) -> List[Dict]:
        """
        Recupera storie da Hacker News (API ufficiale, gratuita, no auth)

        API: https://github.com/HackerNews/API
        - Top stories: https://hacker-news.firebaseio.com/v0/topstories.json
        - Item detail: https://hacker-news.firebaseio.com/v0/item/{id}.json
        """
        print(f"🔍 Scraping Hacker News...")

        try:
            # Recupera top story IDs
            response = requests.get(
                "https://hacker-news.firebaseio.com/v0/topstories.json",
                timeout=10
            )
            story_ids = response.json()[:limit]

            stories = []
            for story_id in story_ids:
                if str(story_id) in self.processed_ids:
                    continue

                # Recupera dettaglio
                item_response = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    timeout=10
                )
                item = item_response.json()

                if not item or item.get("type") != "story":
                    continue

                # Filtra: vogliamo storie con testo o URL interessanti
                title = self.clean_text(item.get("title", ""))
                text = self.clean_text(item.get("text", ""))

                # Skip job postings, annunci
                skip_keywords = ["hiring", "job", "career", "we are looking", "remote"]
                if any(kw in title.lower() for kw in skip_keywords):
                    continue

                story = {
                    "id": f"hn_{story_id}",
                    "source": "hackernews",
                    "title": title,
                    "body": text,
                    "url": item.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                    "score": item.get("score", 0),
                    "comments": item.get("descendants", 0),
                    "author": item.get("by", "unknown"),
                    "created_utc": item.get("time", 0),
                    "engagement_score": item.get("score", 0) + (item.get("descendants", 0) * 5)
                }

                stories.append(story)

            stories.sort(key=lambda x: x["engagement_score"], reverse=True)
            print(f"   ✅ Trovate {len(stories)} storie da HN")
            return stories

        except Exception as e:
            print(f"   ❌ Errore HN: {e}")
            return []

    # ============================================
    # FONTE 2: 4chan (API no auth)
    # ============================================
    def fetch_4chan(self, board: str = "adv", limit: int = 50) -> List[Dict]:
        """
        Recupera thread da 4chan (API pubblica, no auth)

        API: https://github.com/4chan/4chan-API
        - Catalog: https://a.4cdn.org/{board}/catalog.json
        - Thread: https://a.4cdn.org/{board}/thread/{thread_id}.json

        ATTENZIONE: 4chan ha contenuti NSFW. Filtra attentamente.
        Boards consigliati: adv, x, lit, sci, his
        """
        print(f"🔍 Scraping 4chan /{board}/...")

        try:
            # Recupera catalog
            response = requests.get(
                f"https://a.4cdn.org/{board}/catalog.json",
                timeout=10
            )
            pages = response.json()

            stories = []
            for page in pages[:2]:  # Prime 2 pagine
                for thread in page.get("threads", [])[:limit]:
                    thread_id = thread.get("no")
                    if f"4chan_{thread_id}" in self.processed_ids:
                        continue

                    # Filtra NSFW
                    if thread.get("semantic_url", "").startswith("nsfw"):
                        continue

                    title = self.clean_text(thread.get("sub", thread.get("com", "")[:50]))
                    body = self.clean_text(thread.get("com", ""))

                    # Skip se troppo corto
                    if len(body) < 100:
                        continue

                    story = {
                        "id": f"4chan_{thread_id}",
                        "source": f"4chan_{board}",
                        "title": title or "Untitled Thread",
                        "body": body,
                        "url": f"https://boards.4chan.org/{board}/thread/{thread_id}",
                        "score": thread.get("replies", 0),
                        "comments": thread.get("replies", 0),
                        "author": "Anonymous",
                        "created_utc": thread.get("time", 0),
                        "engagement_score": thread.get("replies", 0) * 10 + thread.get("images", 0)
                    }

                    stories.append(story)

            stories.sort(key=lambda x: x["engagement_score"], reverse=True)
            print(f"   ✅ Trovate {len(stories)} storie da 4chan")
            return stories[:limit]

        except Exception as e:
            print(f"   ❌ Errore 4chan: {e}")
            return []

    # ============================================
    # FONTE 3: Wikipedia Random Facts (no auth)
    # ============================================
    def fetch_wikipedia_random(self, limit: int = 10) -> List[Dict]:
        """
        Recupera fatti curiosi da Wikipedia (API pubblica, no auth)

        API: https://en.wikipedia.org/api/rest_v1/page/random/summary
        """
        print(f"🔍 Scraping Wikipedia Random...")

        stories = []
        for _ in range(limit):
            try:
                response = requests.get(
                    "https://en.wikipedia.org/api/rest_v1/page/random/summary",
                    timeout=10
                )
                data = response.json()

                page_id = data.get("pageid", random.randint(1, 999999))
                if f"wiki_{page_id}" in self.processed_ids:
                    continue

                title = self.clean_text(data.get("title", ""))
                extract = self.clean_text(data.get("extract", ""))

                # Filtra: vogliamo storie interessanti, non definizioni tecniche
                if len(extract) < 200 or len(extract) > 2000:
                    continue

                story = {
                    "id": f"wiki_{page_id}",
                    "source": "wikipedia",
                    "title": f"The Strange Story of {title}",
                    "body": extract,
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    "score": random.randint(100, 5000),
                    "comments": random.randint(10, 500),
                    "author": "Wikipedia",
                    "created_utc": 0,
                    "engagement_score": random.randint(500, 5000)
                }

                stories.append(story)

            except Exception as e:
                print(f"   ⚠️ Errore Wikipedia: {e}")
                continue

        print(f"   ✅ Trovate {len(stories)} storie da Wikipedia")
        return stories

    # ============================================
    # FONTE 4: Open Trivia DB (no auth)
    # ============================================
    def fetch_trivia(self, limit: int = 20) -> List[Dict]:
        """
        Recupera domande trivia da Open Trivia DB (no auth)

        API: https://opentdb.com/api.php?amount={limit}
        """
        print(f"🔍 Scraping Open Trivia DB...")

        try:
            response = requests.get(
                f"https://opentdb.com/api.php?amount={limit}&type=multiple",
                timeout=10
            )
            data = response.json()

            stories = []
            for i, item in enumerate(data.get("results", [])):
                question = self.clean_text(item.get("question", ""))
                correct = self.clean_text(item.get("correct_answer", ""))
                incorrect = [self.clean_text(a) for a in item.get("incorrect_answers", [])]

                # Crea "storia" dalla domanda
                body = f"Did you know? {question} The answer is: {correct}. "
                body += f"Most people think it might be {random.choice(incorrect)}, but they are wrong. "
                body += f"Here is why: {correct} is the correct answer because of the facts behind it."

                story = {
                    "id": f"trivia_{i}_{random.randint(1000, 9999)}",
                    "source": "trivia",
                    "title": f"Did You Know? {question[:50]}...",
                    "body": body,
                    "url": "https://opentdb.com",
                    "score": random.randint(50, 500),
                    "comments": random.randint(5, 100),
                    "author": "Open Trivia DB",
                    "created_utc": 0,
                    "engagement_score": random.randint(100, 1000)
                }

                stories.append(story)

            print(f"   ✅ Trovate {len(stories)} storie da Trivia")
            return stories

        except Exception as e:
            print(f"   ❌ Errore Trivia: {e}")
            return []

    # ============================================
    # FONTE 5: File locale (storie salvate)
    # ============================================
    def fetch_local_stories(self, folder: str = "assets/stories") -> List[Dict]:
        """
        Recupera storie da file locali (.txt, .json)

        Formato file .txt:
        ---
        TITLE: Titolo storia
        ---
        Corpo della storia...

        Formato file .json:
        {"title": "...", "body": "...", "source": "..."}
        """
        print(f"🔍 Caricamento storie locali da {folder}...")

        stories = []
        story_folder = Path(folder)

        if not story_folder.exists():
            print(f"   ⚠️ Cartella {folder} non trovata")
            return []

        for file_path in story_folder.iterdir():
            if file_path.suffix == ".txt":
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Parse formato semplice
                    lines = content.split("\n")
                    title = lines[0].replace("TITLE:", "").strip() if lines[0].startswith("TITLE:") else file_path.stem
                    body = "\n".join(lines[2:]) if lines[0].startswith("TITLE:") else content

                    story = {
                        "id": f"local_{file_path.stem}",
                        "source": "local",
                        "title": title,
                        "body": self.clean_text(body),
                        "url": "",
                        "score": 0,
                        "comments": 0,
                        "author": "Local",
                        "created_utc": 0,
                        "engagement_score": 1000  # Priorità alta per contenuti locali
                    }

                    stories.append(story)

                except Exception as e:
                    print(f"   ⚠️ Errore lettura {file_path}: {e}")

            elif file_path.suffix == ".json":
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)

                    if isinstance(data, list):
                        for item in data:
                            stories.append({
                                "id": f"local_{item.get('id', random.randint(1000,9999))}",
                                "source": "local",
                                "title": item.get("title", "Untitled"),
                                "body": self.clean_text(item.get("body", "")),
                                "url": item.get("url", ""),
                                "score": item.get("score", 0),
                                "comments": item.get("comments", 0),
                                "author": item.get("author", "Local"),
                                "created_utc": 0,
                                "engagement_score": item.get("engagement_score", 1000)
                            })
                    else:
                        stories.append({
                            "id": f"local_{data.get('id', random.randint(1000,9999))}",
                            "source": "local",
                            "title": data.get("title", "Untitled"),
                            "body": self.clean_text(data.get("body", "")),
                            "url": data.get("url", ""),
                            "score": data.get("score", 0),
                            "comments": data.get("comments", 0),
                            "author": data.get("author", "Local"),
                            "created_utc": 0,
                            "engagement_score": data.get("engagement_score", 1000)
                        })

                except Exception as e:
                    print(f"   ⚠️ Errore lettura {file_path}: {e}")

        print(f"   ✅ Trovate {len(stories)} storie locali")
        return stories

    # ============================================
    # FONTE 6: JokeAPI (no auth) - per contenuti umoristici
    # ============================================
    def fetch_jokes(self, limit: int = 10) -> List[Dict]:
        """
        Recupera barzellette/storie umoristiche da JokeAPI (no auth)

        API: https://v2.jokeapi.dev/
        """
        print(f"🔍 Scraping JokeAPI...")

        stories = []
        categories = ["Programming", "Misc", "Pun", "Spooky"]

        for _ in range(limit):
            try:
                cat = random.choice(categories)
                response = requests.get(
                    f"https://v2.jokeapi.dev/joke/{cat}?type=single",
                    timeout=10
                )
                data = response.json()

                if data.get("error"):
                    continue

                joke_id = data.get("id", random.randint(1, 99999))
                if f"joke_{joke_id}" in self.processed_ids:
                    continue

                joke = self.clean_text(data.get("joke", ""))

                # Crea "storia" dalla barzelletta
                story = {
                    "id": f"joke_{joke_id}",
                    "source": "jokeapi",
                    "title": f"Funny Story: {joke[:40]}...",
                    "body": f"Here is a story that will make you laugh. {joke} "
                            f"People love this kind of humor because it is relatable and unexpected. "
                            f"Let me know in the comments if this made you laugh!",
                    "url": "https://jokeapi.dev",
                    "score": random.randint(50, 500),
                    "comments": random.randint(5, 100),
                    "author": "JokeAPI",
                    "created_utc": 0,
                    "engagement_score": random.randint(100, 800)
                }

                stories.append(story)

            except Exception as e:
                print(f"   ⚠️ Errore JokeAPI: {e}")
                continue

        print(f"   ✅ Trovate {len(stories)} storie da JokeAPI")
        return stories

    # ============================================
    # GENERAZIONE SCRIPT
    # ============================================
    def generate_script(self, story: Dict) -> str:
        """Genera script narrativo da storia"""
        script = []

        # Hook basato su source
        hooks = {
            "hackernews": [
                f"This story from Hacker News got {story['score']} upvotes.",
                f"The tech community is talking about this.",
                f"Here is what happened in the startup world."
            ],
            "wikipedia": [
                f"This is one of the strangest true stories you will ever hear.",
                f"Did you know this actually happened?",
                f"History has some unbelievable moments."
            ],
            "trivia": [
                f"Here is a question that stumps 90% of people.",
                f"Did you know the answer to this?",
                f"This fact will blow your mind."
            ],
            "jokeapi": [
                f"This story had me laughing for hours.",
                f"You need to hear this funny story.",
                f"People are sharing this everywhere."
            ],
            "local": [
                f"This is a story you will not believe.",
                f"Here is something incredible.",
                f"This story needs to be heard."
            ]
        }

        source_hooks = hooks.get(story["source"].split("_")[0], hooks["local"])
        script.append(random.choice(source_hooks))

        # Titolo
        script.append(f"The story is: {story['title']}")

        # Corpo
        if story["body"]:
            body = story["body"]
            if len(body) > 3000:
                body = body[:3000] + "... (continues)"
            script.append(body)

        # Outro
        outros = [
            "What do you think? Let me know in the comments.",
            "Subscribe for more stories every day.",
            "Drop a like if this story surprised you.",
            "Follow for more daily content."
        ]
        script.append(random.choice(outros))

        return "\n\n".join(script)

    def select_best_stories(self, all_stories: List[Dict], max_per_source: int = 2, total_max: int = 5) -> List[Dict]:
        """Seleziona migliori storie da fonti multiple"""
        by_source = {}
        for story in all_stories:
            src = story["source"].split("_")[0]
            if src not in by_source:
                by_source[src] = []
            by_source[src].append(story)

        selected = []
        for src, stories in by_source.items():
            stories.sort(key=lambda x: x["engagement_score"], reverse=True)
            selected.extend(stories[:max_per_source])

        selected.sort(key=lambda x: x["engagement_score"], reverse=True)
        return selected[:total_max]

    def run(self, sources: List[str] = None, limit: int = 30) -> List[Dict]:
        """
        Esegue pipeline completa

        Args:
            sources: Lista fonti ["hackernews", "wikipedia", "trivia", "jokes", "local"]
            limit: Max storie per fonte
        """
        if sources is None:
            sources = ["hackernews", "wikipedia", "trivia", "jokes"]

        all_stories = []

        for source in sources:
            try:
                if source == "hackernews":
                    stories = self.fetch_hackernews(limit)
                elif source == "4chan":
                    stories = self.fetch_4chan(board="adv", limit=limit)
                elif source == "wikipedia":
                    stories = self.fetch_wikipedia_random(limit)
                elif source == "trivia":
                    stories = self.fetch_trivia(limit)
                elif source == "jokes":
                    stories = self.fetch_jokes(limit)
                elif source == "local":
                    stories = self.fetch_local_stories()
                else:
                    continue

                all_stories.extend(stories)

            except Exception as e:
                print(f"   ❌ Errore fonte {source}: {e}")

        # Seleziona migliori
        best_stories = self.select_best_stories(all_stories)
        print(f"\n📊 Selezionate {len(best_stories)} storie totali")

        # Genera script
        results = []
        for story in best_stories:
            script = self.generate_script(story)

            video_title = self.title_gen.generate_reddit_title({
                "subreddit": story["source"].replace("_", ""),
                "topic": story["title"][:50],
                "emotion": random.choice(self.title_gen.keywords["reddit_emotions"])
            })

            result = {
                "story": story,
                "script": script,
                "video_title": video_title,
                "word_count": len(script.split()),
                "estimated_duration": len(script.split()) / 150 * 60
            }

            results.append(result)
            self.processed_ids.add(story["id"])

        self._save_cache()
        return results

    def save_results(self, results: List[Dict]):
        """Salva risultati in output/"""
        for i, result in enumerate(results):
            # JSON metadata
            meta_path = self.output_dir / f"story_{i}_{result['story']['id']}.json"
            with open(meta_path, "w") as f:
                json.dump(result, f, indent=2)

            # Script testo
            script_path = self.output_dir / f"script_{i}_{result['story']['id']}.txt"
            with open(script_path, "w") as f:
                f.write(result["script"])

            print(f"\n✅ Story {i+1}:")
            print(f"   Titolo: {result['video_title']}")
            print(f"   Fonte: {result['story']['source']}")
            print(f"   Parole: {result['word_count']}")
            print(f"   Durata: {result['estimated_duration']:.0f}s")
            print(f"   Salvato: {meta_path}")


def main():
    parser = argparse.ArgumentParser(description="Story Scraper Universale")
    parser.add_argument("--sources", nargs="+", 
                       default=["hackernews", "wikipedia", "trivia", "jokes"],
                       choices=["hackernews", "4chan", "wikipedia", "trivia", "jokes", "local", "all"],
                       help="Fonti da usare")
    parser.add_argument("--limit", type=int, default=20, help="Max storie per fonte")
    parser.add_argument("--local-folder", default="assets/stories", help="Cartella storie locali")
    args = parser.parse_args()

    scraper = StoryScraper()

    if "all" in args.sources:
        args.sources = ["hackernews", "wikipedia", "trivia", "jokes", "local"]

    results = scraper.run(sources=args.sources, limit=args.limit)
    scraper.save_results(results)


if __name__ == "__main__":
    main()
