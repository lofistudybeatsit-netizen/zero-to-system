"""
Cron Scheduler v2 — Aggiornato con Content Factory (Blocchi 0-5).

Blocchi:
  0. Content Generation (NUOVO) — genera contenuti per tutti i concept attivi
  1. Instagram Upload (esistente)
  2. YouTube Upload (esistente)
  3. TikTok Upload (esistente)
  4. Facebook Upload (NUOVO — per Idea 4)
  5. Cleanup & Report
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# =============================================================================
# BLOCCO 0: CONTENT GENERATION
# =============================================================================
print("=" * 60)
print("BLOCCO 0: Content Factory — Generazione contenuti")
print("=" * 60)

from src.content_pipeline.core.pipeline import ContentPipeline
from src.content_pipeline.core.config_manager import ConfigManager

config = ConfigManager()
generated = []

for concept_name in config.list_concepts():
    try:
        print(f"\n🎬 Generazione: {concept_name}")
        pipeline = ContentPipeline(concept_name)
        results = pipeline.run_daily_generation()
        generated.extend(results)
        for r in results:
            print(f"  ✅ {r.get('song_title', r.get('story_id', 'unknown'))}")
            print(f"     Video: {r.get('video', 'N/A')}")
    except Exception as e:
        print(f"  ❌ Errore {concept_name}: {e}")

print(f"\nTotale generati: {len(generated)}")

# =============================================================================
# BLOCCHI 1-4: Pipeline esistente (invariata)
# =============================================================================
# Inserisci qui il tuo codice esistente per upload IG, YT, TikTok, FB
# I file generati si trovano in:
#   output/promo_videos/     (Idea 1)
#   output/lofi_videos/      (Idea 2)
#   output/confession_videos/ (Idea 4)
# =============================================================================
