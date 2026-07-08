#!/usr/bin/env python3
"""
sync_local_to_github.py
Eseguito sul PC locale. Sincronizza assets/ con GitHub prima del run schedulato.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO_PATH = Path.home() / "path" / "to" / "zero-to-system"  # <-- MODIFICA QUESTO
ASSETS_DIRS = ["assets/music_input", "assets/stories"]

def run(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd or REPO_PATH)
    if result.returncode != 0:
        print(f"❌ ERRORE: {cmd}")
        print(result.stderr)
        return False
    print(f"✅ {cmd}")
    return True

def sync():
    print("=" * 50)
    print("🔄 SYNC: Locale → GitHub")
    print("=" * 50)
    
    # 1. Verifica che ci siano file nuovi
    for d in ASSETS_DIRS:
        full_path = REPO_PATH / d
        files = list(full_path.glob("*")) if full_path.exists() else []
        print(f"📁 {d}: {len(files)} file")
        for f in files:
            print(f"   - {f.name}")
    
    # 2. Git add + commit + push
    if not run("git add assets/"):
        return False
    
    # Verifica se ci sono cambiamenti
    status = subprocess.run("git diff --cached --quiet", shell=True, cwd=REPO_PATH)
    if status.returncode == 0:
        print("ℹ️ Nessun cambiamento da sincronizzare")
        return True
    
    if not run('git commit -m "Auto-sync assets from local PC"'):
        return False
    
    if not run("git push origin main"):
        return False
    
    print("✅ Sincronizzazione completata!")
    return True

if __name__ == "__main__":
    sync()
