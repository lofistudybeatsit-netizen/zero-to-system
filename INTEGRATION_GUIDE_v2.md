# Zero to System v2.3 — Content Factory v2 Integration Guide

## Novità rispetto a v1

- **4 Concept**: Lost Love Promo, LoFi Study Beats, Text Confessions, Dark Confessions
- **Telegram Curation**: 3 varianti generate → bot Telegram → scelta umana
- **Asset multipli**: catalogo locale + Pexels + Pixabay + Unsplash + Pollinations AI
- **Output multi-piattaforma**: YT, IG, TikTok, Facebook

## Installazione

### 1. Estrai lo ZIP
```bash
cd C:\Users\andre\OneDrive\Desktop\zero_to_system_v2
# Estrai zero_to_system_v2_content_factory_v2.zip
```

### 2. Installa dipendenze
```bash
pip install requests pyyaml python-dotenv pillow numpy ffmpeg-python pydub openai-whisper tenacity diskcache tqdm
```

### 3. Configura .env
```bash
# Telegram Bot (per curatela)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# API Asset (opzionali ma consigliati)
PEXELS_API_KEY=your_key
PIXABAY_API_KEY=your_key
UNSPLASH_ACCESS_KEY=your_key
```

### 4. Popola asset
```bash
# Idea 1: foto per promo canzoni
mkdir -p assets/photos/promo_catalog
# Copia qui le foto del tuo catalogo

# Idea 2: musica lofi
mkdir -p assets/music/lofi
# Copia qui i tuoi MP3 lofi

# Idea 4: sound per confessions
mkdir -p assets/music/confessions
# Copia qui sound emotivi brevi (5-15s)

# Font
mkdir -p assets/templates/fonts
# Scarica: Montserrat, BebasNeue, Inter, Creepster (opzionali)
```

### 5. Aggiorna cron_scheduler.py
Sostituisci il contenuto con `scripts/deploy/cron_scheduler_v2.py` oppure aggiungi il Blocco 0 all'inizio del tuo file esistente.

## Uso

### Generare promo canzone (Idea 1)
```python
from src.content_pipeline.core.pipeline import ContentPipeline
p = ContentPipeline("lost_love_promo")
result = p.generate_promo("assets/music/promo/mia_canzone.mp3", "My Song")
# Riceverai 3 varianti su Telegram, scegli la migliore
```

### Generare LoFi (Idea 2)
```python
p = ContentPipeline("lofi_study_beats")
result = p.generate_lofi("assets/music/lofi/chill_beats.mp3", "Chill Study Session")
# 3 varianti video background su Telegram
```

### Generare Confession (Idea 4)
```python
p = ContentPipeline("text_confessions")
result = p.generate_confession()
# 3 varianti (frase+video+sound) su Telegram
```

## Architettura

```
Input (MP3 / Frase) → Generazione 3 varianti → Upload anteprime R2 → 
→ Notifica Telegram → Scelta umana (1,2,3) → Esporta finale → 
→ Pipeline esistente (IG/YT/TT/FB)
```

## Aggiungere nuovo concept

1. Crea `config/concepts/nome.yaml`
2. Aggiungi entry in `config/concepts/concept_registry.yaml`
3. Riavvia — zero codice

## Troubleshooting

| Problema | Soluzione |
|----------|-----------|
| Telegram non invia | Verifica TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID |
| Nessun asset trovato | Popola assets/photos/ o configura API keys |
| Font mancante | Usa font di sistema (fallback automatico) |
| FFmpeg error | Verifica FFmpeg installato e nel PATH |
| Qualità bassa | Aumenta CRF a 18 o usa preset slower |
