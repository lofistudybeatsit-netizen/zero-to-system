"""Asset Selector — Video/immagini da Pexels, Pixabay, locale, Pollinations."""
from __future__ import annotations
import os, random, logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import quote
logger = logging.getLogger(__name__)

class AssetSelector:
    def __init__(self, concept_config, api_client, cache_manager):
        self.concept = concept_config; self.api = api_client; self.cache = cache_manager
        self.providers = {
            "pexels": PexelsProvider(api_client, cache_manager),
            "pixabay": PixabayProvider(api_client, cache_manager),
            "unsplash": UnsplashProvider(api_client, cache_manager),
            "pollinations_ai": PollinationsProvider(cache_manager),
            "local_catalog": LocalCatalogProvider(concept_config),
            "local_gameplay": LocalGameplayProvider(concept_config),
        }

    def select_video(self, concept, mood, duration, query_context=""):
        sources = self.concept.asset_sources.get("video", [])
        for source in sources:
            pn = source.get("provider", "pexels")
            provider = self.providers.get(pn)
            if not provider: continue
            query = self._build_query(source.get("query_templates",[]), mood, query_context)
            try:
                result = provider.search_video(query, source.get("min_duration",10), source.get("preferred_orientation","landscape"))
                if result:
                    cached = self.cache.get_or_download(result["url"], result["filename"])
                    logger.info(f"Video: {pn} — {result['title'][:50]}")
                    return cached
            except Exception as e: logger.warning(f"{pn} failed: {e}")
        raise ValueError("No video found")

    def select_image_for_promo(self, song_title, hook):
        """Per Idea 1: priorità catalogo locale, poi stock."""
        # Prova locale
        local = self.providers.get("local_catalog")
        if local:
            try: return local.get_random()
            except: pass
        # Fallback stock
        return self.select_image(self.concept.name, "emotional", "cinematic")

    def select_image(self, concept, mood, style="anime"):
        sources = self.concept.asset_sources.get("image", [])
        for source in sources:
            pn = source.get("provider", "unsplash")
            provider = self.providers.get(pn)
            if not provider: continue
            query = self._build_query(source.get("query_templates",[]), mood, style)
            try:
                result = provider.search_image(query, source.get("orientation","landscape"), source.get("width",1920), source.get("height",1080))
                if result:
                    cached = self.cache.get_or_download(result["url"], result["filename"])
                    return cached
            except Exception as e: logger.warning(f"{pn} img failed: {e}")
        raise ValueError("No image found")

    def _build_query(self, templates, mood, context):
        import random
        t = random.choice(templates) if templates else "{mood} {context}"
        return t.format(mood=mood, context=context)[:100]

class PexelsProvider:
    def __init__(self, api, cache): self.api = api; self.cache = cache; self.key = os.getenv("PEXELS_API_KEY","")
    def search_video(self, query, min_duration=10, orientation="landscape"):
        if not self.key: return None
        url = "https://api.pexels.com/videos/search"
        r = self.api.get(url, headers={"Authorization":self.key}, params={"query":query,"per_page":5,"orientation":orientation}).json()
        for v in r.get("videos",[]):
            for f in v.get("video_files",[]):
                if f.get("quality") in ["hd","sd"]:
                    return {"url":f["link"],"title":v.get("url",""),"filename":f"pexels_{v['id']}.mp4","duration":v.get("duration",0),"width":f.get("width",0),"height":f.get("height",0)}
        return None
    def search_image(self, query, orientation="landscape", width=1920, height=1080):
        if not self.key: return None
        url = "https://api.pexels.com/v1/search"
        r = self.api.get(url, headers={"Authorization":self.key}, params={"query":query,"per_page":5,"orientation":orientation}).json()
        for p in r.get("photos",[]):
            src = p.get("src",{})
            return {"url":src.get("large2x",src.get("large",src.get("original"))),"title":p.get("url",""),"filename":f"pexels_{p['id']}.jpg","width":p.get("width",0),"height":p.get("height",0)}
        return None

class PixabayProvider:
    def __init__(self, api, cache): self.api = api; self.cache = cache; self.key = os.getenv("PIXABAY_API_KEY","")
    def search_video(self, query, **kwargs):
        if not self.key: return None
        r = self.api.get("https://pixabay.com/api/videos/", params={"key":self.key,"q":quote(query),"per_page":5}).json()
        for h in r.get("hits",[]): return {"url":h.get("videos",{}).get("large",{}).get("url",""),"title":h.get("pageURL",""),"filename":f"pixabay_{h['id']}.mp4","duration":h.get("duration",0)}
        return None
    def search_image(self, query, **kwargs):
        if not self.key: return None
        r = self.api.get("https://pixabay.com/api/", params={"key":self.key,"q":quote(query),"per_page":5,"image_type":"photo"}).json()
        for h in r.get("hits",[]): return {"url":h.get("largeImageURL",h.get("webformatURL","")),"title":h.get("pageURL",""),"filename":f"pixabay_{h['id']}.jpg"}
        return None

class UnsplashProvider:
    def __init__(self, api, cache): self.api = api; self.cache = cache; self.key = os.getenv("UNSPLASH_ACCESS_KEY","")
    def search_image(self, query, orientation="landscape", **kwargs):
        if not self.key: return None
        r = self.api.get("https://api.unsplash.com/search/photos", headers={"Authorization":f"Client-ID {self.key}"}, params={"query":query,"per_page":5,"orientation":orientation}).json()
        for res in r.get("results",[]):
            urls = res.get("urls",{})
            return {"url":urls.get("regular",urls.get("small","")),"title":res.get("description",""),"filename":f"unsplash_{res['id']}.jpg"}
        return None

class PollinationsProvider:
    def __init__(self, cache): self.cache = cache
    def search_image(self, query, width=1920, height=1080, **kwargs):
        import random
        enc = quote(query)
        url = f"https://image.pollinations.ai/prompt/{enc}?width={width}&height={height}&nologo=true&seed={random.randint(1,999999)}"
        return {"url":url,"title":query[:50],"filename":f"pollinations_{abs(hash(query))%1000000}.png"}

class LocalCatalogProvider:
    """Catalogo foto locale per promo canzoni."""
    def __init__(self, concept_config):
        self.concept = concept_config
        cfg = self.concept.asset_sources.get("local_catalog", {})
        self.dir = Path(cfg.get("pool_dir", "assets/photos/promo_catalog"))
        self.types = cfg.get("file_types", [".jpg",".jpeg",".png"])
    def get_random(self):
        if not self.dir.exists(): raise FileNotFoundError(self.dir)
        files = [f for f in self.dir.iterdir() if f.suffix.lower() in self.types]
        if not files: raise FileNotFoundError(f"No images in {self.dir}")
        return str(random.choice(files))

class LocalGameplayProvider:
    def __init__(self, concept_config):
        self.concept = concept_config
        cfg = self.concept.asset_sources.get("local_gameplay", {})
        self.dir = Path(cfg.get("pool_dir", "assets/gameplay"))
        self.files = cfg.get("pool_files", [])
    def get_random(self):
        if self.files:
            f = random.choice(self.files)
            p = self.dir / f
            if p.exists(): return str(p)
        if self.dir.exists():
            vids = list(self.dir.glob("*.mp4")) + list(self.dir.glob("*.mov"))
            if vids: return str(random.choice(vids))
        raise FileNotFoundError(f"No gameplay in {self.dir}")
