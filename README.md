# 🚀 ZERO TO SYSTEM - Content Automation Pipeline

## Panoramica
Sistema completo di automazione contenuti per avviare business da zero con budget zero.
Due canali paralleli:
- **Canale A**: YouTube Music (il tuo esistente) + cross-posting IG/TikTok
- **Canale B**: Faceless Reddit/TTS Channel (nuovo asset)

## Architettura
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  CONTENT MINE   │────▶│  AI FACTORY     │────▶│  PUBLISH HUB    │
│                 │     │                 │     │                 │
│ • Reddit API    │     │ • Script Gen    │     │ • YouTube       │
│ • RSS Feeds     │     │ • TTS Engine    │     │ • TikTok        │
│ • Your Music    │     │ • Thumbnails    │     │ • Instagram     │
│ • Trend APIs    │     │ • SEO Optimize  │     │ • Scheduling    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Requisiti
- Python 3.10+
- FFmpeg installato
- Account Google Cloud (per YT API)
- Account TikTok Developer (per TikTok API)
- Instagram Business/Creator Account + Facebook Page
- Server: Render.com Free Tier / GitHub Actions / VPS proprio

## Costo Totale: €0
- YouTube Data API v3: GRATIS (10,000 quota units/giorno, upload ~100 video/giorno)
- TikTok API: GRATIS (con approvazione app)
- Instagram Graph API: GRATIS (200 call/ora)
- AI Text: Groq API (free tier) o Ollama locale
- TTS: edge-tts (gratuito, Microsoft) o Coqui TTS (open source)
- Hosting: Render Free Tier o PC sempre acceso

## Installazione
```bash
pip install -r requirements.txt
python scripts/deploy/setup_render.py
```

## Struttura File
```
zero_to_system/
├── src/
│   ├── content_engine/        # Generazione contenuti
│   ├── voice_synthesis/        # Sintesi vocale
│   ├── thumbnail_gen/          # Generazione thumbnails
│   ├── repurposing/            # Creazione shorts/clips
│   ├── publishers/             # Upload multi-piattaforma
│   └── seo_optimizer/          # Titoli, descrizioni, hashtag
├── config/                     # Configurazione canali
├── assets/                     # Template e input
├── scripts/deploy/             # Deploy e scheduling
└── docs/                       # Documentazione completa
```

## Avvio Rapido
1. Configura `config/channels.yaml` con i tuoi dati
2. Esegui `python src/content_engine/music_video_factory.py` per Canale A
3. Esegui `python src/content_engine/reddit_scraper.py` per Canale B
4. Configura cron job per esecuzione automatica

## Monetizzazione Roadmap
Vedi `docs/MONETIZATION_ROADMAP.md`


## 🔄 Fonti Storie Alternative (No Reddit API)

Se non riesci a creare app Reddit, il sistema usa automaticamente fonti alternative:

| Fonte | Auth | Tipo Contenuto | Quota |
|-------|------|----------------|-------|
| **Hacker News** | No | Tech/Startup/Science | Illimitata |
| **Wikipedia Random** | No | Fatti storici/curiosi | Illimitata |
| **Open Trivia DB** | No | Domande/Risposte | Illimitata |
| **JokeAPI** | No | Umorismo | Illimitata |
| **File Locali** | No | Storie tue/curate | Illimitata |
| **4chan** | No | Contenuti grezzi | Illimitata |

### Aggiungere Storie Locali

Crea file `.txt` in `assets/stories/` con formato:
```
TITLE: Titolo della storia
---
Corpo della storia...
```

Oppure file `.json`:
```json
[
  {"title": "...", "body": "...", "author": "..."},
  {"title": "...", "body": "...", "author": "..."}
]
```

Le storie locali hanno **priorità massima** nel sistema (engagement_score=1000).
