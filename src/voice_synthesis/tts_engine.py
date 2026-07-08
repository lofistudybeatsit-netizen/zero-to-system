"""
TTS Engine - Sintesi Vocale Gratuita
Usa edge-tts (Microsoft Edge voices, gratuito) o alternative open source

Installazione:
    pip install edge-tts

Usage:
    from voice_synthesis.tts_engine import TTSEngine
    engine = TTSEngine()
    engine.generate_sync("Your text here")
"""

import os
import sys
import yaml
import asyncio
from pathlib import Path
from typing import Optional, List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))


class TTSEngine:
    """Engine TTS gratuito usando edge-tts (Microsoft Edge voices)"""

    # Voci disponibili (gratuite, alta qualità)
    VOICES = {
        'en_us_male': 'en-US-GuyNeural',
        'en_us_female': 'en-US-JennyNeural',
        'en_uk_male': 'en-GB-RyanNeural',
        'en_uk_female': 'en-GB-SoniaNeural',
        'en_australian': 'en-AU-WilliamNeural',
        'en_indian': 'en-IN-PrabhatNeural',
    }

    def __init__(self, config_path: str = "config/channels.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.channel_config = self.config.get('channel_b_faceless', {})
        self.content_config = self.channel_config.get('content', {})
        self.voice = self.content_config.get('tts_voice', 'en-US-GuyNeural')

        self.output_dir = Path("output/tts_audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_speech(self, text: str, output_path: Optional[Path] = None, 
                            voice: Optional[str] = None) -> Path:
        """Genera file audio da testo usando edge-tts"""
        import edge_tts

        if output_path is None:
            output_path = self.output_dir / f"tts_{abs(hash(text)) % 1000000}.mp3"

        voice = voice or self.voice

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(output_path))

        return output_path

    def generate_sync(self, text: str, output_path: Optional[Path] = None,
                    voice: Optional[str] = None) -> Path:
        """Versione sincrona del TTS"""
        return asyncio.run(self.generate_speech(text, output_path, voice))

    def batch_generate(self, scripts: List[str], output_dir: Optional[Path] = None) -> List[Dict]:
        """Genera TTS per batch di script"""
        if output_dir is None:
            output_dir = self.output_dir

        results = []
        for i, script in enumerate(scripts):
            output_path = output_dir / f"tts_batch_{i}.mp3"
            try:
                result_path = self.generate_sync(script, output_path)
                results.append({'success': True, 'path': str(result_path)})
            except Exception as e:
                results.append({'success': False, 'error': str(e)})

        return results


class FallbackTTSEngine:
    """Engine TTS fallback usando gTTS (Google Text-to-Speech, gratuito)"""

    def __init__(self):
        self.output_dir = Path("output/tts_audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, text: str, output_path: Optional[Path] = None, lang: str = 'en') -> Path:
        """Genera TTS con gTTS (richiede: pip install gtts)"""
        from gtts import gTTS

        if output_path is None:
            output_path = self.output_dir / f"gtts_{abs(hash(text)) % 1000000}.mp3"

        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(str(output_path))

        return output_path


if __name__ == "__main__":
    # Test
    try:
        engine = TTSEngine()
        test_text = "This is a test of the Reddit story narration system."
        result = engine.generate_sync(test_text)
        print(f"✅ Audio generato: {result}")
    except ImportError:
        print("⚠️ edge-tts non installato. Usa: pip install edge-tts")
        print("   Oppure usa FallbackTTSEngine con: pip install gtts")
