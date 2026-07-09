"""Cache Manager — Cache locale con TTL."""
from __future__ import annotations
import hashlib, logging
from pathlib import Path
from datetime import datetime, timedelta
logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, cache_dir="assets/backgrounds/cache"):
        self.cache_dir = Path(cache_dir); self.cache_dir.mkdir(parents=True, exist_ok=True); self.ttl_hours = 168
    def get_or_download(self, url, filename):
        key = hashlib.md5(url.encode()).hexdigest()[:12]
        cp = self.cache_dir / f"{key}_{filename}"
        if cp.exists() and not self._expired(cp): return str(cp)
        import requests
        r = requests.get(url, timeout=60, stream=True); r.raise_for_status()
        with open(cp, "wb") as f:
            for chunk in r.iter_content(8192): f.write(chunk)
        return str(cp)
    def _expired(self, path): return datetime.now() - datetime.fromtimestamp(path.stat().st_mtime) > timedelta(hours=self.ttl_hours)
