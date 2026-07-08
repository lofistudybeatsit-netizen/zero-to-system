# 🚀 GUIDA DEPLOY - ZERO TO SYSTEM

## Panoramica
Questa guida ti porta da zero a sistema automatizzato in produzione.

---

## 📋 STEP 1: PREPARAZIONE AMBIENTE LOCALE

### 1.1 Installa Python 3.10+
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv

# macOS
brew install python

# Windows
# Scarica da python.org
```

### 1.2 Installa FFmpeg (ESSENZIALE per video processing)
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Scarica da ffmpeg.org, aggiungi a PATH
```

### 1.3 Clona repository e setup
```bash
git clone <your-repo-url> zero-to-system
cd zero-to-system
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🔑 STEP 2: CONFIGURAZIONE API E CREDENZIALI

### 2.1 YouTube Data API v3 (GRATIS)

**Costo**: €0 | **Quota**: 10,000 units/giorno (~6 upload/giorno)

1. Vai su [Google Cloud Console](https://console.cloud.google.com)
2. Crea nuovo progetto
3. APIs & Services -> Library -> Cerca "YouTube Data API v3" -> Enable
4. APIs & Services -> Credentials -> Create Credentials -> OAuth 2.0 Client ID
5. Tipo applicazione: "Desktop app"
6. Scarica `client_secrets.json`
7. Copia in `config/client_secrets.json`

**Primo auth (una tantum)**:
```bash
python src/publishers/youtube_uploader.py --video test.mp4 --metadata test.json
# Si aprirà browser per autorizzazione
# Il token refresh viene salvato automaticamente
```

**Ottieni Channel ID**:
- Vai su YouTube Studio -> Settings -> Channel -> Advanced settings
- O usa: https://www.youtube.com/account_advanced

### 2.2 Reddit API (GRATIS)

**Costo**: €0 | **Quota**: 60 req/minuto

1. Vai su [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Crea app "script"
3. Ottieni `client_id` e `client_secret`
4. Inserisci in `config/channels.yaml`

### 2.3 Instagram Graph API (GRATIS)

**Costo**: €0 | **Quota**: 200 call/ora, 100 post/24h

**Requisiti**:
- Account Instagram convertito a **Business Account**
- Collegato a Facebook Page

1. Converti IG in Business: Settings -> Account -> Switch to Professional Account -> Business
2. Collega a Facebook Page esistente (o creane una)
3. Vai su [Meta Developers](https://developers.facebook.com)
4. Crea app -> Tipo "Business"
5. Aggiungi prodotto "Instagram"
6. Richiedi permessi: `instagram_business_basic`, `instagram_business_content_publish`
7. Genera Access Token (long-lived, 60 giorni)
8. Ottieni Instagram User ID: `https://graph.facebook.com/v21.0/me?fields=instagram_business_account`

**Nota**: App review richiede 2-4 settimane. Per testing, puoi usare account test.

### 2.4 TikTok Upload (GRATIS - Browser Automation)

**Costo**: €0 | **Metodo**: Browser automation (non API ufficiale)

1. Installa estensione browser "Get cookies.txt LOCALLY"
2. Vai su tiktok.com, effettua login
3. Esporta cookies con estensione
4. Salva come `config/tiktok_cookies.txt`
5. Installa browser automation:
```bash
pip install tiktok-uploader playwright
playwright install chromium
```

**Alternativa**: `pip install tiktokautouploader` (più features, include scheduling)

---

## 🎵 STEP 3: PREPARA CONTENUTI

### 3.1 Canale A: Musica
```bash
# Crea directory
mkdir -p assets/music_input

# Copia i tuoi file audio
# Formati supportati: .mp3, .wav, .flac, .m4a, .ogg
# I file verranno processati automaticamente
```

### 3.2 Canale B: Reddit/TTS
```bash
# Crea directory per gameplay background (opzionale)
mkdir -p assets/gameplay

# Scarica video gameplay copyright-free:
# - Minecraft parkour
# - GTA driving
# - Subway Surfers
# - Satisfying gameplay
# 
# Fonti gratuite:
# - YouTube Creative Commons
# - Pexels Videos
# - Pixabay
```

---

## ⚙️ STEP 4: CONFIGURA IL SISTEMA

### 4.1 Modifica `config/channels.yaml`

Compila TUTTI i campi `YOUR_*` con i tuoi dati reali.

```yaml
# Esempio valori compilati
channel_a_music:
  youtube:
    client_id: "123456789-abc123.apps.googleusercontent.com"
    client_secret: "GOCSPX-xxxxxxxx"
    channel_id: "UCxxxxxxxxxxxxxxxxxxx"

channel_b_faceless:
  reddit:
    client_id: "abc123def456"
    client_secret: "xyz789uvw012"
    user_agent: "ZeroToSystem/1.0 by YourUsername"

  youtube:
    client_id: "123456789-abc123.apps.googleusercontent.com"
    # Stesso client di sopra, o diverso per quota separata
```

**Trick quota**: Crea MULTIPLE Google Cloud projects per quota separata (6 upload/project/giorno)

### 4.2 Verifica configurazione
```bash
python -c "import yaml; yaml.safe_load(open('config/channels.yaml'))"
# Se non dà errori, la sintassi è corretta
```

---

## 🧪 STEP 5: TEST LOCALE

### 5.1 Test Canale A (Musica)
```bash
# Genera video da primo file musicale
python src/content_engine/music_video_factory.py --config config/channels.yaml

# Output in: output/music_videos/
# Verifica il video generato
```

### 5.2 Test Canale B (Reddit)
```bash
# Scrapa Reddit e genera script
python src/content_engine/reddit_scraper.py --config config/channels.yaml

# Output in: output/reddit_stories/
# Verifica script generati
```

### 5.3 Test TTS
```bash
# Genera audio da script
python src/voice_synthesis/tts_engine.py
# Verifica output/tts_audio/
```

### 5.4 Test Shorts
```bash
# Crea short da video musicale
python src/repurposing/shorts_factory.py --input output/music_videos/*.mp4 --type music
```

### 5.5 Test Upload YouTube (MANUALE - richiede auth)
```bash
# Primo upload richiede autorizzazione browser
python src/publishers/youtube_uploader.py   --video output/music_videos/your_video.mp4   --metadata output/music_videos/metadata_your_video.json
```

---

## 🚀 STEP 6: DEPLOY AUTOMATIZZATO

### Opzione A: GitHub Actions (GRATIS, Consigliato)

**Vantaggi**: Gratis, affidabile, nessun server da gestire

1. Genera workflow:
```bash
python scripts/deploy/setup_render.py --github-actions
```

2. Crea repository GitHub e pusha codice

3. Configura Secrets in GitHub:
   - Repo -> Settings -> Secrets and variables -> Actions
   - Aggiungi:
     - `YOUTUBE_CLIENT_ID`
     - `YOUTUBE_CLIENT_SECRET`
     - `YOUTUBE_REFRESH_TOKEN` (ottenuto dopo primo auth locale)
     - `REDDIT_CLIENT_ID`
     - `REDDIT_CLIENT_SECRET`
     - `INSTAGRAM_ACCESS_TOKEN` (se disponibile)
     - `INSTAGRAM_USER_ID` (se disponibile)

4. Lo scheduler gira automaticamente 2 volte al giorno

### Opzione B: Render.com Free Tier

**Vantaggi**: Più controllo, API web

1. Genera file deploy:
```bash
python scripts/deploy/setup_render.py --generate-files
```

2. Crea repo GitHub e pusha

3. Vai su [render.com](https://render.com) -> New -> Blueprint

4. Connetti repo GitHub

5. Render legge `render.yaml` e crea servizi

6. Configura env vars in Render Dashboard

**Limiti Free Tier**:
- Web Service: si spegne dopo 15 min inattività
- Cron Job: max 1h execution, 512 MB RAM
- Per produzione: upgrade a Starter ($7/mese)

### Opzione C: VPS Economico (Hetzner/Contabo)

**Vantaggi**: 24/7, pieno controllo, costo basso

**Costo**: ~€4-5/mese (Hetzner CX11)

1. Crea VPS Ubuntu 22.04
2. SSH nel server
3. Clona repo e installa dipendenze
4. Configura cron job:
```bash
# Edita crontab
crontab -e

# Aggiungi (esegue alle 9:00 e 15:00 UTC)
0 9 * * * cd /path/to/zero-to-system && python scripts/deploy/cron_scheduler.py --run-now music
0 15 * * * cd /path/to/zero-to-system && python scripts/deploy/cron_scheduler.py --run-now reddit
```

5. Installa e configura `systemd` service per daemon:
```bash
sudo nano /etc/systemd/system/zero-to-system.service

[Unit]
Description=Zero To System Content Scheduler
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/zero-to-system
ExecStart=/path/to/venv/bin/python scripts/deploy/cron_scheduler.py --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable zero-to-system
sudo systemctl start zero-to-system
sudo systemctl status zero-to-system
```

---

## 📊 STEP 7: MONITORING E OTTIMIZZAZIONE

### 7.1 Log e Analytics
```bash
# Visualizza log scheduler
tail -f output/scheduler.log

# Contenuti generati
ls -la output/music_videos/
ls -la output/reddit_stories/
ls -la output/shorts/
```

### 7.2 YouTube Analytics
- Vai su YouTube Studio -> Analytics
- Monitora: CTR (click-through rate), AVD (average view duration), RPM
- Ottimizza titoli basati su performance

### 7.3 A/B Testing Titoli
Modifica `src/seo_optimizer/title_generator.py`:
```python
# Aggiungi varianti testate
if random.random() > 0.5:
    title = f"POV: {title}"  # Test POV prefix
```

---

## 🛠️ TROUBLESHOOTING

### Errore: "Quota exceeded"
- **Causa**: Limite 10,000 units/giorno di YouTube API
- **Fix**: Crea nuovo Google Cloud project, usa nuove credentials
- **Long-term**: Richiedi quota increase su Google Cloud Console

### Errore: "Invalid credentials"
- **Causa**: Token scaduto o credentials errate
- **Fix**: Rimuovi `config/youtube_token.pickle` e ri-autentica

### Errore: "Video processing failed"
- **Causa**: Formato video non supportato
- **Fix**: Verifica video sia MP4, H.264, AAC audio

### Errore: "TikTok upload failed"
- **Causa**: Cookies scaduti o browser automation rilevata
- **Fix**: Riesporta cookies da TikTok.com, aggiorna `config/tiktok_cookies.txt`

---

## 🎯 PROSSIMI STEP (Dopo primo guadagno)

1. **€50-100/mese**: Upgrade a VPS dedicato (Hetzner €5/mese)
2. **€200/mese**: Aggiungi canale C (News/Facts faceless)
3. **€500/mese**: Assumi VA per editing avanzato, thumbnail professionali
4. **€1000/mese**: Sviluppa SaaS proprio, vendi il sistema ad altri creator

---

## 📞 SUPPORTO

- Documentazione API: [Google YouTube Data API](https://developers.google.com/youtube/v3)
- Reddit API: [PRAW Documentation](https://praw.readthedocs.io/)
- Instagram Graph API: [Meta Developers](https://developers.facebook.com/docs/instagram-platform)
- TikTok Uploader: [PyPI tiktok-uploader](https://pypi.org/project/tiktok-uploader/)

**Buona automazione! 🤖🚀**
