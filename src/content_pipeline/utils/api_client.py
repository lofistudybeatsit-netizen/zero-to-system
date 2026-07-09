"""API Client — HTTP con retry."""
from __future__ import annotations
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class APIClient:
    def __init__(self, max_retries=3, backoff_factor=2.0, timeout=30):
        self.session = requests.Session()
        retry = Retry(total=max_retries, backoff_factor=backoff_factor, status_forcelist=[429,500,502,503,504], allowed_methods=["GET","POST"])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.timeout = timeout
    def get(self, url, **kwargs): kwargs.setdefault("timeout", self.timeout); return self.session.get(url, **kwargs)
    def post(self, url, **kwargs): kwargs.setdefault("timeout", self.timeout); return self.session.post(url, **kwargs)
    def download(self, url, output_path, chunk_size=8192):
        r = self.get(url, stream=True); r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk: f.write(chunk)
        return output_path
