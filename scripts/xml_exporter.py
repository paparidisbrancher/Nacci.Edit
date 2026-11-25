#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nacci.Edit Timeline XML Exporter
Exporta os Beats e B-Rolls aprovados para XML compatível com:
- Adobe Premiere Pro (FCP7 XML xmeml)
- DaVinci Resolve (FCP7 XML & FCPXML)
- CapCut Desktop Pro / Final Cut Pro
Coloca o vídeo bruto (A-Roll) na V1 e todos os B-Rolls aprovados na V2 nos timestamps exatos!
"""

import argparse
import html
import json
import sys
from pathlib import Path


def parse_timecode_to_frames(tc: str, fps: int = 30) -> int:
    """Converte 'MM:SS' ou 'HH:MM:SS' ou segundos para número de frames."""
    parts = [float(p) for p in tc.strip().split(":")]
    if len(parts) == 1:
        sec = parts[0]
    elif len(parts) == 2:
        sec = parts[0] * 60 + parts[1]
    else:
        sec = parts[0] * 3600 + parts[1] * 60 + parts[2]
    return int(round(sec * fps))


def build_xmeml(project_dir: Path, data: dict) -> str:
    fps = int(data.get("fps", 30))
    res = data.get("resolution", "1080x1920")
    width, height = [int(x) for x in res.lower().split("x")]
    title = html.escape(data.get("title", "Nacci_Edit_Sequence"))

    # Procurar A-Roll na pasta 01_RAW
    raw_dir = project_dir / "01_RAW"
    raw_files = sorted(raw_dir.glob("*.mp4")) + sorted(raw_dir.glob("*.mov"))
    aroll_path = raw_files[0].resolve().as_uri() if raw_files else "file:///01_RAW/aroll.mp4"
    aroll_name = html.escape(raw_files[0].name if raw_files else "A-Roll_Principal.mp4")

    beats = data.get("beats", [])
    max_frame = fps * 60
    v2_clipitems = []

    for idx, b in enumerate(beats, start=1):
        app = b.get("approved_candidate")
        if not app:
            continue
        st_frame = parse_timecode_to_frames(b.get("time_start", "00:00"), fps)
        en_frame = parse_timecode_to_frames(b.get("time_end", "00:04"), fps)
        dur_frames = max(1, en_frame - st_frame)
        max_frame = max(max_frame, en_frame + fps * 5)

        local_rel = app.get("local_file", "")
        local_full = (project_dir / local_rel).resolve()
        file_uri = local_full.as_uri() if local_full.exists() else html.escape(local_rel)
        clip_name = html.escape(Path(local_rel).name or f"{b.get('id')}_broll.mp4")

        v2_clipitems.append(f"""
          <clipitem id="broll-{idx}">
            <name>{clip_name}</name>
            <duration>{dur_frames}</duration>
            <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
            <start>{st_frame}</start>
            <end>{en_frame}</end>
            <in>0</in>
            <out>{dur_frames}</out>
            <file id="file-broll-{idx}">
              <name>{clip_name}</name>
              <pathurl>{file_uri}</pathurl>
              <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
              <duration>{dur_frames}</duration>
              <media><video><samplecharacteristics><width>{width}</width><height>{height}</height></samplecharacteristics></video></media>
            </file>
          </clipitem>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="4">
  <sequence id="nacci-sequence-1">
    <name>{title}</name>
    <duration>{max_frame}</duration>
    <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
    <timecode>
      <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
      <string>00:00:00:00</string>
      <frame>0</frame>
      <displayformat>NDF</displayformat>
    </timecode>
    <media>
      <video>
        <format>
          <samplecharacteristics>
            <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
            <width>{width}</width>
            <height>{height}</height>
            <pixelaspectratio>square</pixelaspectratio>
          </samplecharacteristics>
        </format>
        <!-- V1: A-ROLL (TALKING HEAD PRINCIPAL) -->
        <track>
          <clipitem id="aroll-main">
            <name>{aroll_name}</name>
            <duration>{max_frame}</duration>
            <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
            <start>0</start>
            <end>{max_frame}</end>
            <in>0</in>
            <out>{max_frame}</out>
            <file id="file-aroll-1">
              <name>{aroll_name}</name>
              <pathurl>{aroll_path}</pathurl>
            </file>
          </clipitem>
        </track>
        <!-- V2: B-ROLLS APROVADOS (NACCI.EDIT) -->
        <track>{''.join(v2_clipitems)}
        </track>
      </video>
    </media>
  </sequence>
</xmeml>
"""


def main():
    parser = argparse.ArgumentParser(description="Exporta a timeline de B-rolls aprovados para Premiere Pro / DaVinci Resolve / CapCut (XML)")
    parser.add_argument("--project", required=True, help="Caminho da pasta do projeto")
    args = parser.parse_args()

    project_dir = Path(args.project).resolve()
    pfile = project_dir / "project.json"
    if not pfile.exists():
        print(f"[ERRO] project.json não encontrado em {project_dir}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(pfile.read_text(encoding="utf-8"))
    out_xml = project_dir / "05_EXPORTS" / "timeline_premiere_davinci.xml"
    out_xml.parent.mkdir(parents=True, exist_ok=True)
    out_xml.write_text(build_xmeml(project_dir, data), encoding="utf-8")

    data["stage"] = "exported"
    pfile.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[SUCESSO] Timeline XML exportada em: {out_xml}")
    print("  -> Para abrir no Premiere Pro: File > Import > selecione timeline_premiere_davinci.xml")
    print("  -> Para abrir no DaVinci Resolve: File > Import > Timeline > selecione timeline_premiere_davinci.xml")


if __name__ == "__main__":
    main()
