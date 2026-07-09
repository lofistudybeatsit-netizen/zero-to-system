"""Video Assembler — FFmpeg assembly per tutti i concept."""
from __future__ import annotations
import subprocess, logging
from pathlib import Path
from typing import Dict, List, Optional, Any
logger = logging.getLogger(__name__)

class VideoAssembler:
    def __init__(self, concept_config): self.concept = concept_config

    def assemble_promo_reel(self, mp3_path, background, hook, song_title, output_path, duration=30):
        """Idea 1: Reel promo canzone — foto + hook + audio."""
        # Crea video da foto + audio tagliato a duration
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", background,
            "-i", str(mp3_path),
            "-t", str(duration),
            "-vf", f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,drawtext=text='{hook}':fontsize=64:fontcolor=#ff6b9d:x=(w-text_w)/2:y=(h-text_h)/2:shadowcolor=black@0.8:shadowx=3:shadowy=3",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        logger.info(f"Promo reel: {output_path}")

    def assemble_lofi(self, audio_path, video_asset, output_path, song_title, audio_info, concept):
        """Idea 2: LoFi video lungo — video loop + audio + overlay."""
        overlays = concept.overlays
        vf = "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
        eff = concept.visual_identity.get("effects",{})
        if eff.get("film_grain",0)>0: vf += f",noise=c0s={eff['film_grain']*30}:allf=t+u"
        if eff.get("vignette",0)>0: vf += f",vignette=PI/{2+(1-eff['vignette'])*4}"
        if eff.get("slow_zoom",False): vf += f",zoompan=z='min(zoom+{eff.get('zoom_speed',0.0003)},1.5)':d=999999:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080"
        vf += "[bg]"

        if overlays.get("waveform",{}).get("enabled",False):
            wf = overlays["waveform"]; c = wf.get("color","#e94560").lstrip("#")
            vf += f";[1:a]showwaves=mode={wf.get('style','cline')}:s=1920x{wf.get('height',150)}:colors={c}@{wf.get('opacity',0.4)}[wave];[bg][wave]overlay=0:H-h-{wf.get('y_offset',50)}[v1]"
            last = "v1"
        else: last = "bg"

        if overlays.get("progress_bar",{}).get("enabled",False):
            pb = overlays["progress_bar"]
            vf += f";[{last}]drawbox=y=ih-{pb.get('y_offset',20)}-4:color={pb.get('bg_color','#16213e').lstrip('#')}@0.8:width=iw:height={pb.get('height',4)}:t=fill[pb_bg];[pb_bg]drawbox=y=ih-{pb.get('y_offset',20)}-4:color={pb.get('color','#e94560').lstrip('#')}@1:width='iw*t/{audio_info.get('duration',3600)}':height={pb.get('height',4)}:t=fill[v2]"
            last = "v2"

        if overlays.get("title",{}).get("enabled",False):
            tc = overlays["title"]; vf += f";[{last}]drawtext=text='{song_title}':fontsize={tc.get('font_size',36)}:fontcolor={tc.get('color','#eaeaea').lstrip('#')}:x=(w-text_w)/2:y=50:shadowcolor=black@0.5:shadowx=2:shadowy=2[v3]"
            last = "v3"

        vf = vf.replace(f"[{last}]","[out]")
        if not vf.endswith("[out]"): vf += f";[{last}]copy[out]"

        cmd = ["ffmpeg","-y","-stream_loop","-1","-i",video_asset,"-i",str(audio_path),"-filter_complex",vf,"-map","[out]","-map","1:a","-c:v","libx264","-preset","fast","-crf","23","-c:a","aac","-b:a","192k","-shortest",str(output_path)]
        subprocess.run(cmd, check=True, capture_output=True, timeout=3600)
        logger.info(f"LoFi: {output_path}")

    def assemble_confession(self, frase, background_video, sound_path, output_path, concept):
        """Idea 4: Confession — video + frase + sound."""
        # Se sound esiste, mixa; altrimenti solo video
        inputs = ["-stream_loop","-1","-i",background_video]
        maps = ["-map","0:v"]
        if sound_path and Path(sound_path).exists():
            inputs += ["-i", sound_path]
            maps += ["-map","1:a","-shortest"]
        else:
            # Genera silent audio
            inputs += ["-f","lavfi","-i","anullsrc=r=44100:cl=stereo"]
            maps += ["-map","1:a","-shortest"]

        # Frase formattata per righe
        words = frase.split()
        lines = []; cur = []
        for w in words:
            if sum(len(x) for x in cur) + len(cur) + len(w) <= 20: cur.append(w)
            else: lines.append(" ".join(cur)); cur = [w]
        if cur: lines.append(" ".join(cur))
        text = "\n".join(lines[:3])

        vf = f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,drawtext=text='{text}':fontsize=56:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:shadowcolor=black@0.8:shadowx=3:shadowy=3:line_spacing=10"

        cmd = ["ffmpeg","-y"] + inputs + ["-vf",vf] + maps + ["-c:v","libx264","-preset","fast","-crf","23","-c:a","aac","-b:a","192k","-t","15",str(output_path)]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        logger.info(f"Confession: {output_path}")
