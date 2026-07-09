"""
Trend Researcher — Ricerca e acquisizione contenuto da fonti esterne.
Reddit, Hacker News, NewsAPI, Wikipedia, Project Gutenberg.
"""

from __future__ import annotations

import os
import re
import json
import logging
import random
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TrendResearcher:
    """
    Ricerca storie e contenuti da fonti multiple.
    Filtra per engagement, lunghezza, qualità narrativa.
    """

    def __init__(self, api_client, cache_manager):
        self.api = api_client
        self.cache = cache_manager
        self.reddit_token = None

    # ===================================================================
    # REDDIT
    # ===================================================================
    def fetch_reddit_story(self, subreddit: Optional[str] = None,
                           min_upvotes: int = 500,
                           max_length: int = 800,
                           time_period: str = "week") -> Dict[str, str]:
        """
        Recupera storia da Reddit.

        Args:
            subreddit: Subreddit target (default: nosleep, shortscarystories)
            min_upvotes: Minimo upvotes per considerare il post
            max_length: Max parole della storia
            time_period: periodo (hour, day, week, month, year, all)
        """
        subreddits = [subreddit] if subreddit else ["nosleep", "shortscarystories", "creepypasta"]

        for sub in subreddits:
            try:
                posts = self._reddit_get_posts(sub, time_period, limit=25)

                for post in posts:
                    if post.get("score", 0) < min_upvotes:
                        continue

                    text = post.get("selftext", "")
                    word_count = len(text.split())

                    if word_count < 100 or word_count > max_length:
                        continue

                    # Valuta qualità narrativa
                    quality_score = self._score_story_quality(text)
                    if quality_score < 0.5:
                        continue

                    logger.info(f"Storia Reddit trovata: r/{sub} — {post['title'][:50]}... ({word_count} parole, {post['score']} upvotes)")

                    return {
                        "title": post["title"],
                        "text": self._clean_reddit_text(text),
                        "author": post.get("author", "unknown"),
                        "upvotes": post["score"],
                        "url": f"https://reddit.com{post.get('permalink', '')}",
                        "source": f"reddit/r/{sub}",
                        "quality_score": quality_score
                    }

            except Exception as e:
                logger.warning(f"Errore Reddit r/{sub}: {e}")
                continue

        raise ValueError("Nessuna storia valida trovata su Reddit")

    def _reddit_get_posts(self, subreddit: str, time: str, limit: int = 25) -> List[Dict]:
        """Recupera post da Reddit via OAuth."""
        # Usa Reddit JSON API (pubblica, no auth per read)
        url = f"https://www.reddit.com/r/{subreddit}/top.json"
        params = {"t": time, "limit": limit}
        headers = {"User-Agent": "ZeroToSystemBot/2.3"}

        response = self.api.get(url, params=params, headers=headers)
        data = response.json()

        return [child["data"] for child in data.get("data", {}).get("children", [])]

    def _clean_reddit_text(self, text: str) -> str:
        """Pulizia testo Reddit."""
        # Rimuovi markdown
        text = re.sub(r'\*\*?([^\*]+)\*\*?', r'\1', text)  # bold/italic
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'\1', text)  # links
        text = re.sub(r'^\s*>\s?', '', text, flags=re.MULTILINE)  # quotes
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # extra newlines
        text = re.sub(r'Edit:.*$', '', text, flags=re.MULTILINE | re.IGNORECASE)  # edit notes
        text = re.sub(r'TL;DR:.*$', '', text, flags=re.MULTILINE | re.IGNORECASE)  # tldr
        return text.strip()

    # ===================================================================
    # HACKER NEWS
    # ===================================================================
    def fetch_hn_story(self, min_score: int = 50) -> Dict[str, str]:
        """Recupera storia interessante da Hacker News."""
        try:
            # Top stories
            top_ids = self.api.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()[:50]

            for story_id in random.sample(top_ids, min(20, len(top_ids))):
                story = self.api.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json").json()

                if not story or story.get("score", 0) < min_score:
                    continue

                # Cerca solo storie con testo (Ask HN, Show HN)
                text = story.get("text", "")
                if not text or len(text.split()) < 50:
                    continue

                return {
                    "title": story.get("title", "HN Story"),
                    "text": self._clean_html(text),
                    "author": story.get("by", "unknown"),
                    "upvotes": story.get("score", 0),
                    "url": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                    "source": "hackernews"
                }

        except Exception as e:
            logger.warning(f"Errore HN: {e}")

        raise ValueError("Nessuna storia valida trovata su Hacker News")

    # ===================================================================
    # NEWS API
    # ===================================================================
    def fetch_news_story(self, query: str = "strange unexplained",
                         category: str = "general") -> Dict[str, str]:
        """Recupera articolo da NewsAPI."""
        api_key = os.getenv("NEWSAPI_KEY")
        if not api_key:
            raise ValueError("NEWSAPI_KEY non configurata")

        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "sortBy": "popularity",
            "pageSize": 10,
            "language": "en",
            "apiKey": api_key
        }

        response = self.api.get(url, params=params)
        articles = response.json().get("articles", [])

        for article in articles:
            text = article.get("content", "") or article.get("description", "")
            if len(text.split()) < 100:
                continue

            return {
                "title": article.get("title", "News Story"),
                "text": self._clean_html(text),
                "author": article.get("author", "unknown"),
                "source": article.get("source", {}).get("name", "newsapi"),
                "url": article.get("url", ""),
                "published": article.get("publishedAt", "")
            }

        raise ValueError("Nessun articolo valido trovato")

    # ===================================================================
    # URL GENERICO
    # ===================================================================
    def fetch_from_url(self, url: str) -> Dict[str, str]:
        """Estrae testo da URL generico (usa readability)."""
        try:
            response = self.api.get(url, timeout=30)
            from html.parser import HTMLParser

            # Estrazione semplice testo da HTML
            text = self._extract_text_from_html(response.text)

            # Estrai titolo
            title_match = re.search(r'<title>([^<]+)</title>', response.text, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else "Story from URL"

            return {
                "title": title,
                "text": text[:5000],  # Limita lunghezza
                "source": "url",
                "url": url
            }
        except Exception as e:
            logger.error(f"Errore fetch URL {url}: {e}")
            raise

    # ===================================================================
    # UTILITY
    # ===================================================================
    def _score_story_quality(self, text: str) -> float:
        """Score qualità narrativa 0.0-1.0."""
        score = 0.5

        # Dialogo
        if '"' in text or "'" in text:
            score += 0.1

        # Descrizione ambientale
        env_words = ["room", "house", "door", "window", "street", "forest", "dark", "light"]
        if any(w in text.lower() for w in env_words):
            score += 0.1

        # Tensione
        tension_words = ["suddenly", "heart", "breath", "silent", "noise", "shadow", "cold"]
        tension_count = sum(text.lower().count(w) for w in tension_words)
        score += min(tension_count * 0.02, 0.15)

        # Lunghezza ottimale
        words = len(text.split())
        if 200 <= words <= 600:
            score += 0.15

        return min(score, 1.0)

    def _clean_html(self, text: str) -> str:
        """Rimuovi tag HTML base."""
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&\w+;', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_text_from_html(self, html: str) -> str:
        """Estrae testo leggibile da HTML."""
        # Rimuovi script e style
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        # Estrai testo
        text = re.sub(r'<[^>]+>', ' ', html)
        text = self._clean_html(text)
        # Filtra linee corte (probabilmente menu/nav)
        lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 30]
        return '\n\n'.join(lines[:50])  # Prime 50 linee significative
