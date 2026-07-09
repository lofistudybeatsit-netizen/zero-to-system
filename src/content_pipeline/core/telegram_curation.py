"""Telegram Curation Bot — Invia 3 opzioni, attende scelta."""
from __future__ import annotations
import os, json, time, logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
logger = logging.getLogger(__name__)

class TelegramCurationBot:
    def __init__(self, token=None, chat_id=None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.timeout_hours = 24; self.max_options = 3
        if not self.token or not self.chat_id:
            logger.warning("Telegram non configurato")

    def is_configured(self): return bool(self.token and self.chat_id)

    def send_candidates(self, candidates, concept_name, caption=""):
        if not self.is_configured(): return ""
        poll_id = f"{concept_name}_{int(time.time())}"
        text = f"🎬 <b>{concept_name}</b>\n{caption}\n\nScegli (rispondi 1, 2 o 3):\n"
        for i, c in enumerate(candidates, 1):
            text += f"\n{i}. {c.get('metadata',{}).get('hook','')[:50]}..."

        # Invia prima immagine con caption
        first = candidates[0]
        preview = first.get("preview_path", "")
        if preview and Path(preview).exists():
            is_video = preview.endswith((".mp4",".mov"))
            url = f"{self.base_url}/send{'Video' if is_video else 'Photo'}"
            files = {("video" if is_video else "photo"): open(preview, "rb")}
            payload = {"chat_id": self.chat_id, "caption": text, "parse_mode": "HTML"}
            try:
                requests.post(url, data=payload, files=files, timeout=60)
            except Exception as e: logger.error(f"Errore invio: {e}")
            finally: files[("video" if is_video else "photo")].close()
        else:
            self._send_message(text)

        self._save_poll_state(poll_id, candidates)
        return poll_id

    def wait_for_choice(self, poll_id, timeout_hours=None):
        if not self.is_configured(): return 0
        timeout = timeout_hours or self.timeout_hours
        deadline = time.time() + timeout * 3600
        while time.time() < deadline:
            choice = self._check_response()
            if choice is not None: return choice
            time.sleep(300)
        return -1

    def _check_response(self):
        try:
            url = f"{self.base_url}/getUpdates"
            r = requests.get(url, timeout=30).json()
            for up in r.get("result", []):
                msg = up.get("message", {})
                if str(msg.get("chat",{}).get("id")) != self.chat_id: continue
                t = msg.get("text","").strip().lower()
                if t in ["1","2","3","uno","due","tre","first","second","third"]:
                    return {"1":0,"2":1,"3":2,"uno":0,"due":1,"tre":2,"first":0,"second":1,"third":2}.get(t,0)
        except Exception as e: logger.debug(f"Polling err: {e}")
        return None

    def _send_message(self, text):
        try:
            requests.post(f"{self.base_url}/sendMessage", json={"chat_id":self.chat_id,"text":text,"parse_mode":"HTML"}, timeout=30)
        except Exception as e: logger.error(f"Msg err: {e}")

    def _save_poll_state(self, poll_id, candidates):
        f = Path("output/telegram_polls") / f"{poll_id}.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "w") as fh: json.dump({"poll_id":poll_id,"candidates":candidates,"status":"pending","created_at":time.time()}, fh)

    def auto_select_best(self, candidates): return 0
