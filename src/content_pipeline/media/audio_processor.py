"""Audio Processor — Analisi e mastering."""
from __future__ import annotations
import subprocess, json, logging
from pathlib import Path
from typing import Dict, Optional
logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self, concept_config): self.concept = concept_config

    def analyze(self, audio_path: Path) -> Dict:
        r = subprocess.run(["ffprobe","-v","quiet","-print_format","json","-show_format","-show_streams",str(audio_path)], capture_output=True, text=True)
        p = json.loads(r.stdout)
        dur = float(p.get("format",{}).get("duration",0))
        return {"duration":dur, "bpm":80, "energy":0.5, "sample_rate":int(p.get("streams",[{}])[0].get("sample_rate",44100)), "channels":int(p.get("streams",[{}])[0].get("channels",2))}

    def process(self, input_path, output_path, target_lufs=-14.0):
        m = self.concept.audio_identity.get("mastering",{})
        af = f"loudnorm=I={target_lufs}:TP={m.get('true_peak_db',-1.0)}:LRA=11"
        for b in m.get("eq_bands",[]): 
            t = "q"
            if b.get("type","").startswith(("l","h")): t = "s"
            af += f",equalizer=f={b.get('freq',1000)}:g={b.get('gain',0)}:t={t}"
        cmd = ["ffmpeg","-y","-i",str(input_path),"-af",af,"-c:a","libmp3lame","-b:a","192k",str(output_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Audio: {output_path}")
