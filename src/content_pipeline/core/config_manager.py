"""Config Manager — Carica concept YAML."""
from __future__ import annotations
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import logging
logger = logging.getLogger(__name__)

@dataclass
class ConceptConfig:
    name: str; tagline: str; brand_voice: str
    visual_identity: Dict[str, Any]; video_style: Dict[str, Any]
    audio_identity: Dict[str, Any]; content_rules: Dict[str, Any]
    platforms: Dict[str, Any]; active: bool = True
    output_dir: str = ""; schedule: List[str] = field(default_factory=list)

    @property
    def color_palette(self): return self.visual_identity.get("color_palette", {})
    @property
    def fonts(self): return self.visual_identity.get("fonts", {})
    @property
    def asset_sources(self): return self.video_style.get("asset_sources", {})
    @property
    def overlays(self): return self.video_style.get("overlays", {})
    @property
    def target_lufs(self): return self.audio_identity.get("mastering", {}).get("target_lufs", -14)
    @property
    def min_duration(self): return self.content_rules.get("min_duration_sec", 60)
    @property
    def max_duration(self): return self.content_rules.get("max_duration_sec", 600)

    def apply_title_template(self, variables: Dict[str, str]) -> str:
        templates = self.content_rules.get("title_templates", ["{name}"])
        import random
        template = random.choice(templates)
        try: return template.format(**variables)
        except KeyError: return template

    def get_tags(self, platform: str) -> List[str]:
        return self.content_rules.get("tags", {}).get(platform, [])

    def get_hook(self) -> str:
        hooks = self.content_rules.get("hook_templates", [])
        if hooks:
            import random
            return random.choice(hooks)
        return "Check this out..."

class ConfigManager:
    _instance: Optional[ConfigManager] = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_dir: str = "config/concepts"):
        if self._initialized: return
        self.config_dir = Path(config_dir)
        self.registry_path = self.config_dir / "concept_registry.yaml"
        self._registry = None
        self._concepts: Dict[str, ConceptConfig] = {}
        self._initialized = True
        self._load_all()

    def _load_all(self):
        with open(self.registry_path, "r", encoding="utf-8") as f:
            self._registry = yaml.safe_load(f)
        for concept_name, meta in self._registry.get("concepts", {}).items():
            if not meta.get("active", False): continue
            cf = self.config_dir / f"{concept_name}.yaml"
            if not cf.exists(): continue
            with open(cf, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            self._concepts[concept_name] = ConceptConfig(
                name=data.get("name", concept_name), tagline=data.get("tagline", ""),
                brand_voice=data.get("brand_voice", ""),
                visual_identity=data.get("visual_identity", {}),
                video_style=data.get("video_style", {}),
                audio_identity=data.get("audio_identity", {}),
                content_rules=data.get("content_rules", {}),
                platforms=data.get("platforms", {}),
                active=meta.get("active", True), output_dir=meta.get("output_dir", ""),
                schedule=meta.get("schedule", [])
            )
            logger.info(f"Concept caricato: {concept_name}")

    def get_concept(self, name: str) -> ConceptConfig:
        if name not in self._concepts: raise KeyError(f"Concept '{name}' non trovato")
        return self._concepts[name]
    def list_concepts(self): return list(self._concepts.keys())
    def get_setting(self, key: str, default: Any = None):
        return (self._registry.get("settings", {}) if self._registry else {}).get(key, default)
    def get_telegram_config(self): return self.get_setting("telegram", {})
    def reload(self): self._concepts.clear(); self._registry = None; self._load_all()

def get_config(): return ConfigManager()
