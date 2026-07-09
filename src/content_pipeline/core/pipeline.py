"""Content Pipeline v2 — Orchestratore 4 concept con Telegram Curation."""
from __future__ import annotations
import os, json, logging, time, shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from .config_manager import ConfigManager
from ..utils.api_client import APIClient
from ..utils.cache_manager import CacheManager
from ..assets.asset_selector import AssetSelector
from ..media.video_assembler import VideoAssembler
from ..media.thumbnail_engine import ThumbnailEngine
from ..media.audio_processor import AudioProcessor
from .telegram_curation import TelegramCurationBot
logger = logging.getLogger(__name__)

class ContentPipeline:
    def __init__(self, concept_name, config_dir="config/concepts"):
        self.config = ConfigManager(config_dir)
        self.concept = self.config.get_concept(concept_name)
        self.concept_name = concept_name
        self.api_client = APIClient()
        self.cache = CacheManager(self.config.get_setting("cache_dir", "assets/backgrounds/cache"))
        self.asset_selector = AssetSelector(self.concept, self.api_client, self.cache)
        self.video_assembler = VideoAssembler(self.concept)
        self.thumbnail_engine = ThumbnailEngine(self.concept)
        self.audio_processor = AudioProcessor(self.concept)
        tg = self.config.get_telegram_config()
        self.telegram = TelegramCurationBot(
            token=tg.get("bot_token","").replace("${TELEGRAM_BOT_TOKEN}", os.getenv("TELEGRAM_BOT_TOKEN","")),
            chat_id=tg.get("chat_id","").replace("${TELEGRAM_CHAT_ID}", os.getenv("TELEGRAM_CHAT_ID",""))
        )
        self.telegram_timeout = tg.get("poll_timeout_hours", 24)
        self.telegram_fallback = tg.get("fallback_auto_select", True)
        from ..utils.logger import setup_logger
        setup_logger(self.config.get_setting("log_level","INFO"), self.config.get_setting("log_file","output/content_pipeline.log"))
        logger.info(f"Pipeline: {concept_name}")

    def generate_promo(self, mp3_path, song_title=None):
        mp3_path = Path(mp3_path)
        if not mp3_path.exists(): raise FileNotFoundError(mp3_path)
        song_title = song_title or mp3_path.stem
        work_dir = Path(self.concept.output_dir) / song_title.replace(" ", "_")
        work_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"=== PROMO: {song_title} ===")

        candidates = []
        hooks = self.concept.content_rules.get("hook_templates", [])[:3]
        for i, hook in enumerate(hooks):
            vd = work_dir / f"v{i}"; vd.mkdir(exist_ok=True)
            photo = self.asset_selector.select_image_for_promo(song_title, hook)
            vp = vd / "reel.mp4"
            self.video_assembler.assemble_promo_reel(mp3_path, photo, hook, song_title, vp, self.concept.content_rules.get("reel_duration_sec",30))
            tp = vd / "thumb.jpg"
            self.thumbnail_engine.generate_promo(hook, photo, tp)
            candidates.append({"index":i,"preview_path":str(vp),"thumbnail":str(tp),"metadata":{"hook":hook,"song_title":song_title},"score":0.5})

        selected = self._curation(candidates, f"Promo: {song_title}")
        return self._export_promo(candidates[selected], work_dir, song_title)

    def generate_lofi(self, mp3_path, song_title=None):
        mp3_path = Path(mp3_path)
        if not mp3_path.exists(): raise FileNotFoundError(mp3_path)
        song_title = song_title or mp3_path.stem
        work_dir = Path(self.concept.output_dir) / song_title.replace(" ", "_")
        work_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"=== LOFI: {song_title} ===")
        audio_info = self.audio_processor.analyze(mp3_path)

        candidates = []
        for i, mood in enumerate(["calm","cozy","rainy"]):
            vd = work_dir / f"v{i}"; vd.mkdir(exist_ok=True)
            vbg = self.asset_selector.select_video(self.concept_name, mood, audio_info["duration"], song_title)
            vp = vd / "video.mp4"
            self.video_assembler.assemble_lofi(mp3_path, vbg, vp, song_title, audio_info, self.concept)
            tp = vd / "thumb.jpg"
            self.thumbnail_engine.generate_lofi(song_title, vbg, tp, self.concept)
            candidates.append({"index":i,"preview_path":str(vp),"thumbnail":str(tp),"metadata":{"mood":mood,"song_title":song_title},"score":0.5})

        selected = self._curation(candidates, f"LoFi: {song_title}")
        return self._export_lofi(candidates[selected], work_dir, song_title, audio_info)

    def generate_confession(self, frase_id=None):
        work_dir = Path(self.concept.output_dir); work_dir.mkdir(parents=True, exist_ok=True)
        logger.info("=== CONFESSION ===")
        frases = self._load_frases()
        selected = self._select_frases(frases, 3)
        candidates = []
        for i, fd in enumerate(selected):
            vd = work_dir / f"c{int(time.time())}_{i}"; vd.mkdir(exist_ok=True)
            vbg = self.asset_selector.select_video(self.concept_name, fd["category"], 15, fd["text"])
            sound = self._select_sound(fd["category"])
            vp = vd / "video.mp4"
            self.video_assembler.assemble_confession(fd["text"], vbg, sound, vp, self.concept)
            candidates.append({"index":i,"preview_path":str(vp),"metadata":{"hook":fd["text"],"category":fd["category"]},"score":0.5})

        selected_idx = self._curation(candidates, "Text Confession")
        return self._export_confession(candidates[selected_idx], work_dir)

    def _curation(self, candidates, caption):
        if not self.telegram.is_configured(): return 0
        poll_id = self.telegram.send_candidates(candidates, self.concept_name, caption)
        if not poll_id: return 0
        choice = self.telegram.wait_for_choice(poll_id, self.telegram_timeout)
        if choice == -1 and self.telegram_fallback: choice = 0
        elif choice == -1: raise TimeoutError("No curation")
        return choice

    def _export_promo(self, c, wd, st):
        od = wd / "final"; od.mkdir(exist_ok=True)
        shutil.copy(c["preview_path"], od/"reel.mp4")
        shutil.copy(c["thumbnail"], od/"thumbnail.jpg")
        m = c["metadata"]
        (od/"title.txt").write_text(f"{m['hook']} | {st}")
        (od/"description.txt").write_text(f"Original music — {st}\n\n{m['hook']}")
        (od/"tags.txt").write_text(",".join(self.concept.get_tags("youtube")))
        return {"concept":self.concept_name,"song_title":st,"video":str(od/"reel.mp4"),"thumbnail":str(od/"thumbnail.jpg"),"metadata":m,"work_dir":str(od)}

    def _export_lofi(self, c, wd, st, ai):
        od = wd / "final"; od.mkdir(exist_ok=True)
        shutil.copy(c["preview_path"], od/"video.mp4")
        shutil.copy(c["thumbnail"], od/"thumbnail.jpg")
        title = self.concept.apply_title_template({"mood":"Chill","activity":"Studying","time_of_day":"Late Night","duration":str(int(ai["duration"]//60))})
        (od/"title.txt").write_text(title)
        (od/"description.txt").write_text(f"LoFi Study Beats — {st}\n\nPerfect for focus.")
        (od/"tags.txt").write_text(",".join(self.concept.get_tags("youtube")))
        return {"concept":self.concept_name,"song_title":st,"video":str(od/"video.mp4"),"thumbnail":str(od/"thumbnail.jpg"),"metadata":{"title":title},"work_dir":str(od)}

    def _export_confession(self, c, wd):
        od = wd / f"c{int(time.time())}_final"; od.mkdir(exist_ok=True)
        shutil.copy(c["preview_path"], od/"video.mp4")
        m = c["metadata"]
        (od/"title.txt").write_text(m["hook"])
        (od/"hashtags.txt").write_text(" ".join(self.concept.get_tags("instagram")))
        return {"concept":self.concept_name,"video":str(od/"video.mp4"),"metadata":m,"work_dir":str(od)}

    def _load_frases(self):
        src = self.concept.content_rules.get("frases_source", "config/frases/confessions_100.json")
        p = Path(src)
        if not p.exists(): return []
        with open(p) as f: data = json.load(f)
        frases = []
        for cat, dc in data.get("categories", {}).items():
            for t in dc.get("frases", []): frases.append({"text":t,"category":cat,"color":dc.get("color","#fff")})
        return frases

    def _select_frases(self, frases, count=3):
        import random
        uf = Path("output/used_frases.json")
        used = json.load(open(uf)) if uf.exists() else []
        avail = [f for f in frases if f["text"] not in used] or frases
        sel = random.sample(avail, min(count, len(avail)))
        used.extend([f["text"] for f in sel]); used = used[-100:]
        with open(uf, "w") as f: json.dump(used, f)
        return sel

    def _select_sound(self, category):
        import random
        ld = Path("assets/music/confessions")
        if not ld.exists(): return None
        cd = ld / category
        if cd.exists() and list(cd.glob("*.mp3")): return str(random.choice(list(cd.glob("*.mp3"))))
        all_t = list(ld.rglob("*.mp3"))
        return str(random.choice(all_t)) if all_t else None

    def run_daily_generation(self):
        results = []
        if self.concept_name == "lost_love_promo":
            for mp3 in Path("assets/music/promo").glob("*.mp3"):
                try: results.append(self.generate_promo(str(mp3)))
                except Exception as e: logger.error(f"Promo err {mp3}: {e}")
        elif self.concept_name == "lofi_study_beats":
            for mp3 in Path("assets/music/lofi").glob("*.mp3"):
                try: results.append(self.generate_lofi(str(mp3)))
                except Exception as e: logger.error(f"LoFi err {mp3}: {e}")
        elif self.concept_name == "text_confessions":
            try: results.append(self.generate_confession())
            except Exception as e: logger.error(f"Confession err: {e}")
        logger.info(f"Done: {len(results)} contents")
        return results
