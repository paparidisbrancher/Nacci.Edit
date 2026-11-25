#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nacci.Edit FFmpeg Surgery Tools - Ferramentas Locais de Edição de Vídeo
Corte automático de silêncios, normalização -14 LUFS para Reels, reenquadramento 9:16,
inserção de B-Roll sobre A-Roll e queima de legendas dinâmicas.
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def require_ffmpeg():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("[ERRO] FFmpeg não encontrado no PATH do sistema. Instale com 'winget install Gyan.FFmpeg'.", file=sys.stderr)
        sys.exit(1)
    return ffmpeg


def get_duration(ffmpeg: str, input_path: Path) -> float:
    res = subprocess.run([ffmpeg, "-i", str(input_path)], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if not m:
        return 0.0
    h, m_, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + m_ * 60 + s


def cmd_cut_silence(args):
    """Remove pausas e silêncios ('dead air') automaticamente usando silencedetect do FFmpeg."""
    ffmpeg = require_ffmpeg()
    inp = Path(args.input).resolve()
    out = Path(args.output).resolve()

    print(f"[1/2] Detectando silêncios em {inp.name} (threshold={args.noise}, min_duration={args.min_silence}s)...")
    detect_cmd = [
        ffmpeg, "-i", str(inp),
        "-af", f"silencedetect=noise={args.noise}:d={args.min_silence}",
        "-f", "null", "-"
    ]
    res = subprocess.run(detect_cmd, capture_output=True, text=True)
    total_dur = get_duration(ffmpeg, inp)

    starts = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", res.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([0-9.]+)", res.stderr)]

    if not starts:
        print("[OK] Nenhum silêncio longo detectado. Copiando arquivo original.")
        shutil.copy2(inp, out)
        return

    # Construir intervalos de fala com padding suave (margin)
    margin = float(args.padding)
    speech_segments = []
    cursor = 0.0
    for s_start, s_end in zip(starts, ends):
        seg_end = max(cursor, s_start + margin)
        if seg_end - cursor >= 0.25:
            speech_segments.append((cursor, seg_end))
        cursor = max(seg_end, s_end - margin)
    if total_dur - cursor >= 0.25:
        speech_segments.append((cursor, total_dur))

    print(f"[2/2] Cortando {len(starts)} pausa(s) e mantendo {len(speech_segments)} segmento(s) de fala...")
    v_filters = []
    a_filters = []
    concat_inputs = []
    for idx, (st, en) in enumerate(speech_segments):
        v_filters.append(f"[0:v]trim=start={st:.3f}:end={en:.3f},setpts=PTS-STARTPTS[v{idx}];")
        a_filters.append(f"[0:a]atrim=start={st:.3f}:end={en:.3f},asetpts=PTS-STARTPTS[a{idx}];")
        concat_inputs.append(f"[v{idx}][a{idx}]")

    filter_complex = (
        "".join(v_filters)
        + "".join(a_filters)
        + "".join(concat_inputs)
        + f"concat=n={len(speech_segments)}:v=1:a=1[outv][outa]"
    )

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
        tf.write(filter_complex)
        filter_script = tf.name

    out.parent.mkdir(parents=True, exist_ok=True)
    render_cmd = [
        ffmpeg, "-y", "-i", str(inp),
        "-filter_complex_script", filter_script,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        str(out)
    ]
    subprocess.run(render_cmd, check=True)
    Path(filter_script).unlink(missing_ok=True)
    saved_sec = total_dur - get_duration(ffmpeg, out)
    print(f"[SUCESSO] Vídeo sem silêncios salvo em: {out} (Economizados {saved_sec:.1f}s!)")


def cmd_normalize_audio(args):
    """Normaliza o áudio do vídeo para o padrão de Reels/TikTok (-14 LUFS)."""
    ffmpeg = require_ffmpeg()
    inp = Path(args.input).resolve()
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"[ÁUDIO] Normalizando {inp.name} para {args.lufs} LUFS...")
    cmd = [
        ffmpeg, "-y", "-i", str(inp),
        "-af", f"loudnorm=I={args.lufs}:TP=-1.5:LRA=11",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        str(out)
    ]
    subprocess.run(cmd, check=True)
    print(f"[SUCESSO] Áudio normalizado salvo em: {out}")


def cmd_reframe_9x16(args):
    """Converte um vídeo horizontal (16:9) ou quadrado para vertical (9:16 - 1080x1920)."""
    ffmpeg = require_ffmpeg()
    inp = Path(args.input).resolve()
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.mode == "crop":
        vf = "scale=-1:1920,crop=1080:1920"
    else:
        # Modo blur background (ótimo para B-rolls horizontais ou prints de artigos científicos!)
        vf = (
            "split[original][copy];"
            "[copy]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
            "[original]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )

    print(f"[REFRAME 9:16] Convertendo {inp.name} no modo '{args.mode}'...")
    cmd = [
        ffmpeg, "-y", "-i", str(inp),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        str(out)
    ]
    subprocess.run(cmd, check=True)
    print(f"[SUCESSO] Vídeo 9:16 salvo em: {out}")


def cmd_overlay_broll(args):
    """Cobre o vídeo principal (A-Roll) com um B-Roll entre os segundos start e end mantendo a voz do A-Roll."""
    ffmpeg = require_ffmpeg()
    aroll = Path(args.aroll).resolve()
    broll = Path(args.broll).resolve()
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    st = float(args.start)
    en = float(args.end)
    dur = en - st

    print(f"[OVERLAY B-ROLL] Inserindo {broll.name} sobre {aroll.name} de {st}s até {en}s...")
    filter_complex = (
        f"[1:v]trim=0:{dur},setpts=PTS-STARTPTS+{st}/TB,"
        f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[broll];"
        f"[0:v][broll]overlay=0:0:enable='between(t,{st},{en})'[outv]"
    )
    cmd = [
        ffmpeg, "-y",
        "-i", str(aroll),
        "-stream_loop", "-1", "-i", str(broll),
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        str(out)
    ]
    subprocess.run(cmd, check=True)
    print(f"[SUCESSO] Vídeo com B-roll aplicado salvo em: {out}")


def main():
    parser = argparse.ArgumentParser(description="Nacci.Edit FFmpeg Tools - Cirurgia Local de Vídeo")
    sub = parser.add_subparsers(dest="command", required=True)

    # cut-silence
    p_cut = sub.add_parser("cut-silence", help="Remove pausas e silêncios automaticamente")
    p_cut.add_argument("--input", required=True, help="Vídeo de entrada")
    p_cut.add_argument("--output", required=True, help="Vídeo de saída sem silêncios")
    p_cut.add_argument("--noise", default="-35dB", help="Limite de ruído considerado silêncio (default: -35dB)")
    p_cut.add_argument("--min-silence", type=float, default=0.45, help="Duração mínima do silêncio em segundos (default: 0.45)")
    p_cut.add_argument("--padding", type=float, default=0.08, help="Respiro mantido nas bordas da fala em segundos (default: 0.08)")
    p_cut.set_defaults(func=cmd_cut_silence)

    # normalize-audio
    p_norm = sub.add_parser("normalize-audio", help="Normaliza áudio para -14 LUFS (padrão Reels/TikTok)")
    p_norm.add_argument("--input", required=True)
    p_norm.add_argument("--output", required=True)
    p_norm.add_argument("--lufs", type=float, default=-14.0)
    p_norm.set_defaults(func=cmd_normalize_audio)

    # reframe-9x16
    p_ref = sub.add_parser("reframe-9x16", help="Converte vídeo/B-roll horizontal para vertical 9:16 (1080x1920)")
    p_ref.add_argument("--input", required=True)
    p_ref.add_argument("--output", required=True)
    p_ref.add_argument("--mode", default="crop", choices=["crop", "blur"], help="crop central ou fundo desfocado (blur)")
    p_ref.set_defaults(func=cmd_reframe_9x16)

    # overlay-broll
    p_ov = sub.add_parser("overlay-broll", help="Insere um B-roll no intervalo exato mantendo o áudio do A-roll")
    p_ov.add_argument("--aroll", required=True, help="Vídeo principal (talking-head)")
    p_ov.add_argument("--broll", required=True, help="Arquivo de B-roll aprovado")
    p_ov.add_argument("--start", type=float, required=True, help="Segundo inicial na timeline (ex: 3.5)")
    p_ov.add_argument("--end", type=float, required=True, help="Segundo final na timeline (ex: 7.0)")
    p_ov.add_argument("--output", required=True, help="Vídeo resultante")
    p_ov.set_defaults(func=cmd_overlay_broll)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
