
"""
Script Generator - Generazione script narrativi con AI
Supporta Groq, OpenRouter, Ollama locale

Usage:
    from script_generator import ScriptGenerator
    gen = ScriptGenerator()
    script = gen.generate_reddit_script(post_data)
"""

import os
import json
import yaml
import random
from pathlib import Path
from typing import Dict, Optional, List


class ScriptGenerator:
    """Genera script narrativi usando LLM via API"""

    def __init__(self, config_path: str = "config/channels.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.ai_config = self.config.get('ai_config', {})
        self.provider = self.ai_config.get('provider', 'groq')

        # Carica API key
        self.api_key = None
        if self.provider == 'groq':
            self.api_key = self.ai_config.get('groq', {}).get('api_key')
            self.model = self.ai_config.get('groq', {}).get('model', 'llama-3.1-70b-versatile')
            self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        elif self.provider == 'openrouter':
            self.api_key = self.ai_config.get('openrouter', {}).get('api_key')
            self.model = self.ai_config.get('openrouter', {}).get('model', 'meta-llama/llama-3.1-70b-instruct')
            self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def _call_api(self, messages: List[Dict], temperature: float = 0.7) -> str:
        """Chiama API LLM"""
        import requests

        if not self.api_key:
            return self._fallback_generate(messages)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        if self.provider == 'openrouter':
            headers["HTTP-Referer"] = "https://zero-to-system.local"
            headers["X-Title"] = "Zero To System"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 2000
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except Exception as e:
            print(f"⚠️ API Error: {e}")
            return self._fallback_generate(messages)

    def _fallback_generate(self, messages: List[Dict]) -> str:
        """Fallback se API non disponibile"""
        # Estrai il prompt dell'utente
        user_prompt = ""
        for msg in messages:
            if msg['role'] == 'user':
                user_prompt = msg['content']
                break

        # Genera risposta basata su template
        if "reddit" in user_prompt.lower():
            return self._template_reddit_script(user_prompt)
        elif "title" in user_prompt.lower():
            return self._template_title(user_prompt)
        else:
            return "[Fallback: API non disponibile. Configura API key in config/channels.yaml]"

    def _template_reddit_script(self, prompt: str) -> str:
        """Template fallback per script Reddit"""
        return """This story from Reddit got thousands of upvotes. Here is what happened.

The original post reads: [Title from prompt]

[Body of the story, adapted for narration]

People in the comments had a lot to say. The top comment said: [Comment summary]

What do you think about this? Let me know in the comments below. And subscribe for more Reddit stories every day."""

    def _template_title(self, prompt: str) -> str:
        """Template fallback per titoli"""
        hooks = [
            "This Changed Everything",
            "You Won't Believe What Happened",
            "The Truth About",
            "What Nobody Tells You"
        ]
        return f"{random.choice(hooks)} | Reddit Stories"

    def generate_reddit_script(self, post_data: Dict, comments: List[str] = None) -> str:
        """
        Genera script narrativo avanzato da post Reddit
        Ottimizzato per retention e engagement
        """

        system_prompt = """You are an expert narrator for Reddit story videos. 
Your scripts are engaging, natural, and optimized for YouTube retention.

Rules:
- Hook immediately in the first 15 seconds
- Use conversational tone, not robotic
- Break story into digestible segments
- Include emotional reactions
- End with CTA (subscribe, comment, like)
- Total length: 800-1500 words (5-10 minutes narration)
- Use "you" and "I" to create connection
- Add dramatic pauses with [pause] markers
- Include sound effect suggestions with [sound: description]
"""

        user_prompt = f"""Create a narration script for this Reddit post:

SUBREDDIT: r/{post_data.get('subreddit', 'AskReddit')}
TITLE: {post_data.get('title', '')}
BODY: {post_data.get('body', '')[:2000]}

COMMENTS:
"""

        if comments:
            for i, comment in enumerate(comments[:3], 1):
                user_prompt += f"\nComment {i}: {comment[:300]}\n"

        user_prompt += """

Format the script as:
1. HOOK (0:00-0:15)
2. INTRO (0:15-0:30)
3. STORY PART 1 (0:30-2:00)
4. STORY PART 2 (2:00-4:00)
5. REACTION/COMMENTS (4:00-5:00)
6. OUTRO + CTA (5:00-5:30)

Make it engaging and natural."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return self._call_api(messages, temperature=0.8)

    def generate_title_variants(self, topic: str, subreddit: str, num_variants: int = 3) -> List[str]:
        """Genera varianti di titolo per A/B testing"""

        system_prompt = """You are a YouTube title optimization expert. 
Create click-worthy titles that follow YouTube best practices:
- Use power words (Shocking, Unbelievable, Heartbreaking)
- Create curiosity gaps
- Include numbers when relevant
- Keep under 60 characters for mobile
- Avoid clickbait that disappoints
"""

        user_prompt = f"""Generate {num_variants} YouTube title variants for a Reddit story video.

Topic: {topic}
Subreddit: r/{subreddit}

Requirements:
- Each title must be under 70 characters
- Include "r/{subreddit}" or "Reddit" 
- Create curiosity gap
- One variant should use numbers
- One variant should use emotional trigger
- One variant should be short and punchy

Return ONLY the titles, one per line, no numbering."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = self._call_api(messages, temperature=0.9)

        # Parse response
        titles = [line.strip() for line in response.split('\n') if line.strip() and not line.startswith('#')]
        return titles[:num_variants]

    def generate_description(self, title: str, script_summary: str = "", platform: str = 'youtube') -> str:
        """Genera descrizione ottimizzata per piattaforma"""

        system_prompt = f"""You are a social media description writer.
Create engaging descriptions for {platform}.

Rules:
- First 2 lines are crucial (visible before "more")
- Include relevant keywords naturally
- Add CTA
- Use emojis sparingly
- Include timestamps if relevant
"""

        user_prompt = f"""Write a description for:
Title: {title}
Summary: {script_summary[:500]}

Platform: {platform}
Include relevant hashtags at the end."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return self._call_api(messages, temperature=0.7)

    def generate_music_description(self, title: str, genre: str, mood: str, duration: int) -> str:
        """Genera descrizione per video musicale"""

        system_prompt = """You are a music description writer for YouTube.
Create atmospheric, engaging descriptions for ambient/lofi music videos.

Rules:
- Set the mood immediately
- Describe the ideal listening scenario
- Include timestamps for different sections
- Mention benefits (focus, relaxation, sleep)
- Keep it poetic but not pretentious
"""

        user_prompt = f"""Write a description for this music video:

Title: {title}
Genre: {genre}
Mood: {mood}
Duration: {duration} hours

Include:
- Atmospheric intro
- Timestamps (if applicable)
- Benefits/Use cases
- CTA to subscribe
- Hashtags"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return self._call_api(messages, temperature=0.8)


if __name__ == "__main__":
    # Test
    gen = ScriptGenerator()

    # Test con dati fittizi
    test_post = {
        'subreddit': 'AskReddit',
        'title': 'What is the creepiest thing that happened to you at night?',
        'body': 'I was walking home from work around 2 AM when I heard footsteps behind me...'
    }

    print("📝 Generazione script test...")
    script = gen.generate_reddit_script(test_post)
    print(script[:500] + "...")

    print("\n🎬 Generazione titoli test...")
    titles = gen.generate_title_variants(test_post['title'], 'AskReddit')
    for t in titles:
        print(f"   - {t}")
