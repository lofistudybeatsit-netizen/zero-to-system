
"""
Setup Render - Configurazione deploy su Render.com Free Tier

Usage:
    python setup_render.py --generate-files
    python setup_render.py --github-actions
"""

import os
import json
import argparse
from pathlib import Path


def generate_render_files():
    """Genera file necessari per deploy su Render"""
    print("Generazione file per Render.com...")

    # render.yaml
    render_yaml = """services:
  - type: cron
    name: content-scheduler
    runtime: python
    schedule: "0 9 * * *"
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python scripts/deploy/cron_scheduler.py --run-now all"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: CONFIG_PATH
        value: config/channels.yaml

  - type: web
    name: zero-to-system-api
    runtime: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python scripts/deploy/web_server.py"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
"""

    with open("render.yaml", "w") as f:
        f.write(render_yaml)
    print("   Creato: render.yaml")

    # web_server.py
    web_server = """from flask import Flask, jsonify
import os
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def health_check():
    return jsonify({
        'status': 'running',
        'service': 'zero-to-system',
        'timestamp': str(datetime.now())
    })

@app.route('/trigger/<channel>')
def trigger_channel(channel):
    return jsonify({'triggered': channel, 'status': 'started'})

@app.route('/status')
def get_status():
    from pathlib import Path
    output_dir = Path('output')
    status = {
        'videos_generated': len(list(output_dir.glob('music_videos/*.mp4'))) if output_dir.exists() else 0,
        'stories_processed': len(list(output_dir.glob('stories/*.json'))) if output_dir.exists() else 0,
    }
    return jsonify(status)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
"""

    os.makedirs("scripts/deploy", exist_ok=True)
    with open("scripts/deploy/web_server.py", "w") as f:
        f.write(web_server)
    print("   Creato: scripts/deploy/web_server.py")

    # Dockerfile
    dockerfile = """FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg fonts-dejavu && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p output assets/music_input assets/templates assets/gameplay assets/stories

CMD ["python", "scripts/deploy/cron_scheduler.py", "--run-now", "all"]
"""

    with open("Dockerfile", "w") as f:
        f.write(dockerfile)
    print("   Creato: Dockerfile")

    print("\nIstruzioni deploy:")
    print("1. Crea repo GitHub con questi file")
    print("2. Vai su render.com -> New -> Blueprint")
    print("3. Connetti repo GitHub")
    print("4. Render leggera render.yaml e creera i servizi")


def generate_github_actions():
    """Genera workflow GitHub Actions"""
    print("Generazione GitHub Actions workflow...")

    workflow = """name: Content Scheduler

on:
  schedule:
    - cron: '0 9,15 * * *'
  workflow_dispatch:

jobs:
  publish-content:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install system dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y ffmpeg fonts-dejavu

    - name: Install Python dependencies
      run: pip install -r requirements.txt

    - name: Run Content Scheduler
      env:
        YOUTUBE_CLIENT_ID: ${{ secrets.YOUTUBE_CLIENT_ID }}
        YOUTUBE_CLIENT_SECRET: ${{ secrets.YOUTUBE_CLIENT_SECRET }}
        YOUTUBE_REFRESH_TOKEN: ${{ secrets.YOUTUBE_REFRESH_TOKEN }}
        INSTAGRAM_ACCESS_TOKEN: ${{ secrets.INSTAGRAM_ACCESS_TOKEN }}
        INSTAGRAM_USER_ID: ${{ secrets.INSTAGRAM_USER_ID }}
      run: python scripts/deploy/cron_scheduler.py --run-now all

    - name: Upload artifacts
      uses: actions/upload-artifact@v4
      with:
        name: generated-content
        path: output/
        retention-days: 7
"""

    os.makedirs(".github/workflows", exist_ok=True)
    with open(".github/workflows/content-scheduler.yml", "w") as f:
        f.write(workflow)

    print("   Creato: .github/workflows/content-scheduler.yml")
    print("\nPer GitHub Actions:")
    print("1. Aggiungi secrets in GitHub Repo -> Settings -> Secrets")
    print("2. Lo scheduler gira automaticamente 2 volte al giorno")
    print("3. Per trigger manuale: Actions tab -> Content Scheduler -> Run workflow")


def main():
    parser = argparse.ArgumentParser(description="Setup Render Deploy")
    parser.add_argument("--generate-files", action="store_true", help="Genera file deploy")
    parser.add_argument("--github-actions", action="store_true", help="Genera GitHub Actions workflow")
    args = parser.parse_args()

    if args.generate_files:
        generate_render_files()

    if args.github_actions:
        generate_github_actions()

    if not args.generate_files and not args.github_actions:
        print("Usage:")
        print("  python setup_render.py --generate-files")
        print("  python setup_render.py --github-actions")
        print("  python setup_render.py --generate-files --github-actions")


if __name__ == "__main__":
    main()
