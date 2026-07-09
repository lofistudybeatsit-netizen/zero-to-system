"""
Inspiration Engine — Database hook e template ispirazione.
Gestisce hook testati, li seleziona per categoria, traccia performance.
"""

from __future__ import annotations

import json
import random
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class InspirationEngine:
    """
    Gestisce database locale di hook e template.
    Seleziona in base a categoria, performance storica, e contenuto.
    """

    def __init__(self, concept_config):
        self.concept = concept_config
        self.db_path = Path("config/hooks")
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._hooks_db = self._load_hooks_db()

    def _load_hooks_db(self) -> Dict:
        """Carica database hook da JSON."""
        db_file = self.db_path / f"{self.concept.name.lower().replace(' ', '_')}_hooks.json"

        if db_file.exists():
            with open(db_file, "r", encoding="utf-8") as f:
                return json.load(f)

        # Database di default
        return self._get_default_hooks()

    def _get_default_hooks(self) -> Dict:
        """Hook di default per concept horror."""
        return {
            "hooks": [
                {"template": "You won't believe what they found in the {place}...", "category": "mystery", "avg_ctr": 0.08, "uses": 0},
                {"template": "POV: You're the last one to leave {place}", "category": "pov", "avg_ctr": 0.09, "uses": 0},
                {"template": "The {thing} in my {place} wasn't human...", "category": "creature", "avg_ctr": 0.10, "uses": 0},
                {"template": "Nobody believed me until I showed them the {evidence}...", "category": "evidence", "avg_ctr": 0.07, "uses": 0},
                {"template": "Wait until you hear what happened at {place}...", "category": "suspense", "avg_ctr": 0.08, "uses": 0},
                {"template": "This {thing} changed everything...", "category": "transformation", "avg_ctr": 0.06, "uses": 0},
                {"template": "The reason they closed {place} is shocking...", "category": "mystery", "avg_ctr": 0.09, "uses": 0},
                {"template": "I shouldn't have opened the {thing}...", "category": "regret", "avg_ctr": 0.11, "uses": 0},
                {"template": "What I saw in the {place} still haunts me...", "category": "trauma", "avg_ctr": 0.10, "uses": 0},
                {"template": "They told me {place} was safe. They lied.", "category": "betrayal", "avg_ctr": 0.09, "uses": 0}
            ],
            "variables": {
                "place": ["basement", "attic", "hospital", "forest", "school", "house", "road", "room", "closet", "mirror"],
                "thing": ["voice", "shadow", "noise", "figure", "message", "door", "mirror", "photo", "letter", "box"],
                "evidence": ["photo", "video", "recording", "diary", "letter", "footage"]
            }
        }

    def select_hook(self, category: Optional[str] = None) -> str:
        """
        Seleziona hook ottimizzato.
        Priorità: CTR storico > varietà (meno usati) > categoria.
        """
        hooks = self._hooks_db.get("hooks", [])
        variables = self._hooks_db.get("variables", {})

        if category:
            hooks = [h for h in hooks if h.get("category") == category]

        if not hooks:
            hooks = self._hooks_db.get("hooks", [])

        # Score combinato: CTR * freshness (meno usato = più fresco)
        for hook in hooks:
            uses = hook.get("uses", 0)
            ctr = hook.get("avg_ctr", 0.05)
            freshness = max(0.3, 1.0 - (uses * 0.05))  # Decresce con gli usi
            hook["_score"] = ctr * freshness

        # Weighted random selection
        total_score = sum(h["_score"] for h in hooks)
        r = random.uniform(0, total_score)
        cumulative = 0

        for hook in hooks:
            cumulative += hook["_score"]
            if r <= cumulative:
                hook["uses"] = hook.get("uses", 0) + 1
                self._save_hooks_db()
                return self._fill_template(hook["template"], variables)

        # Fallback
        hook = random.choice(hooks)
        return self._fill_template(hook["template"], variables)

    def _fill_template(self, template: str, variables: Dict) -> str:
        """Riempie variabili nel template."""
        result = template
        for key, values in variables.items():
            if f"{{{key}}}" in result:
                result = result.replace(f"{{{key}}}", random.choice(values))
        return result

    def _save_hooks_db(self) -> None:
        """Salva database aggiornato."""
        db_file = self.db_path / f"{self.concept.name.lower().replace(' ', '_')}_hooks.json"
        with open(db_file, "w", encoding="utf-8") as f:
            json.dump(self._hooks_db, f, indent=2, ensure_ascii=False)

    def add_hook(self, template: str, category: str, ctr: float = 0.05) -> None:
        """Aggiunge nuovo hook al database."""
        self._hooks_db["hooks"].append({
            "template": template,
            "category": category,
            "avg_ctr": ctr,
            "uses": 0
        })
        self._save_hooks_db()
