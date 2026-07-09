"""Quality Checker — Validazione pre-pubblicazione."""
from __future__ import annotations
import json, subprocess, logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
logger = logging.getLogger(__name__)

@dataclass
class QualityReport:
    passed: bool = True
    checks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_check(self, name, passed, value=None, min_val=None, max_val=None, message=""):
        self.checks[name] = {"passed": passed, "value": value, "min": min_val, "max": max_val, "message": message}
        if not passed: self.passed = False; self.errors.append(f"[{name}] {message}")
    def to_json(self, indent=2): return json.dumps({"passed":self.passed,"checks":self.checks,"warnings":self.warnings,"errors":self.errors}, indent=indent, ensure_ascii=False)

class QualityChecker:
    def __init__(self, concept_config=None):
        self.concept = concept_config
        self.ffprobe_cmd = "ffprobe"

    def check_video(self, video_path, concept=None):
        report = QualityReport()
        if not Path(video_path).exists(): report.add_check("file_exists", False, message=f"Not found: {video_path}"); return report
        probe = self._probe(video_path)
        if not probe: report.add_check("probe", False, message="Cannot probe"); return report
        dur = float(probe.get("format",{}).get("duration",0))
        c = concept or self.concept
        report.add_check("duration", c.min_duration <= dur <= c.max_duration, dur, c.min_duration, c.max_duration, f"Duration: {dur:.1f}s")
        vs = self._stream(probe, "video")
        if vs:
            w, h = int(vs.get("width",0)), int(vs.get("height",0))
            report.add_check("resolution", w >= 1080 and h >= 1080, f"{w}x{h}", message=f"Res: {w}x{h}")
            report.add_check("fps", eval(vs.get("r_frame_rate","0/1")) >= 24, eval(vs.get("r_frame_rate","0/1")), 24, message=f"FPS")
        else: report.add_check("video_stream", False, message="No video stream")
        as_ = self._stream(probe, "audio")
        if as_: report.add_check("audio_codec", as_.get("codec_name","") in ["aac","mp3","opus"], as_.get("codec_name"), message=f"Audio: {as_.get('codec_name','')}")
        else: report.add_check("audio_stream", False, message="No audio stream")
        br = int(probe.get("format",{}).get("bit_rate",0))
        report.add_check("bitrate", br >= 2000000, br, 2000000, message=f"Bitrate: {br/1e6:.1f} Mbps")
        return report

    def _probe(self, path):
        try:
            r = subprocess.run([self.ffprobe_cmd, "-v","quiet","-print_format","json","-show_format","-show_streams",path], capture_output=True, text=True, timeout=30)
            return json.loads(r.stdout)
        except Exception as e: logger.error(f"ffprobe: {e}"); return None
    def _stream(self, probe, ctype):
        for s in probe.get("streams",[]): 
            if s.get("codec_type") == ctype: return s
        return None
