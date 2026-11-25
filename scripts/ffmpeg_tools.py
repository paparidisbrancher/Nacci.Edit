#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nacci.Edit FFmpeg Surgery Tools - Ferramentas Locais de Edição de Vídeo
Corte automático de silêncios, normalização -14 LUFS para Reels, reenquadramento 9:16,
inserção de B-Roll sobre A-Roll, transcrição palavra a palavra, legendas animadas
e verificação do arquivo final.

Regra de ouro (ideia do ffmpeg-skill e do Kinocut): nenhum comando sobrescreve o
arquivo de entrada, e um arquivo de saída que já existe só é substituído com --overwrite.
"""

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
FADE = 0.03  # 30 ms de fade em cada corte: o corte não estala (ideia do video-use)


def require_ffmpeg():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("[ERRO] FFmpeg não encontrado no PATH do sistema. Instale com 'winget install Gyan.FFmpeg'.", file=sys.stderr)
        sys.exit(1)
    return ffmpeg


def safe_output(inputs, output, overwrite: bool) -> Path:
    """Protege o bruto: recusa saída igual à entrada e não substitui arquivo existente sem --overwrite."""
    out = Path(output).resolve()
    for inp in inputs:
        if Path(inp).resolve() == out:
            sys.exit(f"[ERRO] A saída '{out.name}' é o próprio arquivo de entrada. Use outro nome: o bruto nunca é sobrescrito.")
    if out.exists() and not overwrite:
        sys.exit(f"[ERRO] '{out}' já existe. Use --overwrite para substituir.")
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def get_duration(ffmpeg: str, input_path: Path) -> float:
    res = subprocess.run([ffmpeg, "-i", str(input_path)], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if not m:
        return 0.0
    h, m_, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + m_ * 60 + s


def probe(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        sys.exit("[ERRO] ffprobe não encontrado no PATH (vem junto com o FFmpeg).")
    res = subprocess.run(
        [ffprobe, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(res.stdout)


# ============================================================================
# CORTE DE SILÊNCIO
# ============================================================================
def speech_segments(starts, ends, total_dur, margin, min_len=0.25):
    """Converte os silêncios detectados em trechos de fala, deixando `margin` de respiro nas bordas."""
    ends = list(ends) + [total_dur] * (len(starts) - len(ends))  # silêncio que vai até o fim do arquivo
    segments = []
    cursor = 0.0
    for s_start, s_end in zip(starts, ends):
        seg_end = max(cursor, s_start + margin)
        if seg_end - cursor >= min_len:
            segments.append((cursor, seg_end))
        cursor = max(seg_end, s_end - margin)
    if total_dur - cursor >= min_len:
        segments.append((cursor, total_dur))
    return segments


def cmd_cut_silence(args):
    """Remove pausas e silêncios ('dead air') automaticamente usando silencedetect do FFmpeg."""
    ffmpeg = require_ffmpeg()
    inp = Path(args.input).resolve()
    out = safe_output([inp], args.output, args.overwrite)

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

    segs = speech_segments(starts, ends, total_dur, float(args.padding))

    print(f"[2/2] Cortando {len(starts)} pausa(s) e mantendo {len(segs)} segmento(s) de fala...")
    v_filters = []
    a_filters = []
    concat_inputs = []
    for idx, (st, en) in enumerate(segs):
        fade_out_at = max(0.0, (en - st) - FADE)
        v_filters.append(f"[0:v]trim=start={st:.3f}:end={en:.3f},setpts=PTS-STARTPTS[v{idx}];")
        a_filters.append(
            f"[0:a]atrim=start={st:.3f}:end={en:.3f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:d={FADE},afade=t=out:st={fade_out_at:.3f}:d={FADE}[a{idx}];"
        )
        concat_inputs.append(f"[v{idx}][a{idx}]")

    filter_complex = (
        "".join(v_filters)
        + "".join(a_filters)
        + "".join(concat_inputs)
        + f"concat=n={len(segs)}:v=1:a=1[outv][outa]"
    )

    # Filtro curto vai direto na linha de comando (qualquer versão do FFmpeg). Muito longo para o Windows
    # vai em arquivo com '-/filter_complex' (FFmpeg 7+; o antigo '-filter_complex_script' sumiu no FFmpeg 8).
    filter_script = None
    if len(filter_complex) < 24000:
        filter_args = ["-filter_complex", filter_complex]
    else:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
            tf.write(filter_complex)
            filter_script = tf.name
        filter_args = ["-/filter_complex", filter_script]

    render_cmd = [
        ffmpeg, "-y", "-i", str(inp),
        *filter_args,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        str(out)
    ]
    subprocess.run(render_cmd, check=True)
    if filter_script:
        Path(filter_script).unlink(missing_ok=True)
    saved_sec = total_dur - get_duration(ffmpeg, out)
    print(f"[SUCESSO] Vídeo sem silêncios salvo em: {out} (Economizados {saved_sec:.1f}s!)")
    print("  -> A transcrição do bruto não vale mais para este arquivo: rode 'transcribe' de novo nele.")


def cmd_normalize_audio(args):
    """Normaliza o áudio do vídeo para o padrão de Reels/TikTok (-14 LUFS)."""
    ffmpeg = require_ffmpeg()
    inp = Path(args.input).resolve()
    out = safe_output([inp], args.output, args.overwrite)

    print(f"[ÁUDIO] Normalizando {inp.name} para {args.lufs} LUFS (2 passadas: mede, depois aplica)...")
    target = f"loudnorm=I={args.lufs}:TP=-2:LRA=11"  # -2 dB: o AAC cria picos acima do que o loudnorm prevê
    # 1ª passada só mede. Uma passada única erra em clipe curto (deu -12,2 com alvo -14 num Reel de 19 s).
    res = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", str(inp), "-af", f"{target}:print_format=json",
                          "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(res.stderr[res.stderr.rfind("{"):res.stderr.rfind("}") + 1])
    af = (f"{target}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    cmd = [
        ffmpeg, "-y", "-i", str(inp),
        "-af", af, "-ar", "48000",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        str(out)
    ]
    subprocess.run(cmd, check=True)
    print(f"[SUCESSO] Áudio normalizado salvo em: {out}")


def cmd_reframe_9x16(args):
    """Converte um vídeo horizontal (16:9) ou quadrado para vertical (9:16 - 1080x1920)."""
    ffmpeg = require_ffmpeg()
    inp = Path(args.input).resolve()
    out = safe_output([inp], args.output, args.overwrite)

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
    out = safe_output([aroll, broll], args.output, args.overwrite)

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


# ============================================================================
# TRANSCRIÇÃO PALAVRA A PALAVRA (local, faster-whisper)
# A ideia de dar ao agente a fala em texto com tempos, em vez de frames, é do video-use.
# ============================================================================
def transcribe_words(path: Path, model_name: str = "small", language: str = "pt"):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("[ERRO] faster-whisper não instalado. Rode: pip install faster-whisper "
                 "(roda na máquina; o áudio não é enviado a lugar nenhum).")
    import numpy as np  # vem junto com o faster-whisper
    # O FFmpeg decodifica o áudio (16 kHz mono); assim o faster-whisper não depende da versão do PyAV instalada.
    raw = subprocess.run([require_ffmpeg(), "-v", "error", "-i", str(path), "-vn", "-f", "s16le", "-ac", "1",
                          "-ar", "16000", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    model = WhisperModel(model_name, device="auto", compute_type="default")
    segments, info = model.transcribe(audio, language=language or None, word_timestamps=True, vad_filter=True)
    words = [
        {"w": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)}
        for seg in segments for w in (seg.words or []) if w.word.strip()
    ]
    return words, info


def pack_words(words, max_gap: float = 0.5) -> str:
    """Agrupa as palavras em frases '[ini-fim] texto' (pausa maior que max_gap ou fim de frase quebra a linha)."""
    lines, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > max_gap or cur[-1]["w"][-1:] in ".?!"):
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    return "\n".join(
        f"[{ln[0]['start']:07.2f}-{ln[-1]['end']:07.2f}] " + " ".join(w["w"] for w in ln) for ln in lines
    )


def cmd_transcribe(args):
    inp = Path(args.input).resolve()
    out = Path(args.output).resolve() if args.output else inp.with_suffix(".transcricao.json")
    out = safe_output([inp], out, args.overwrite)
    print(f"[TRANSCRIÇÃO] {inp.name} com faster-whisper '{args.model}' (a primeira vez baixa o modelo)...")
    words, info = transcribe_words(inp, args.model, args.language)
    out.write_text(json.dumps({
        "source": inp.name,
        "language": info.language,
        "duration": round(info.duration, 2),
        "words": words,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    md = out.with_name(out.name.replace(".json", "") + ".md")
    md.write_text(f"# Transcrição: {inp.name}\n\n```\n{pack_words(words)}\n```\n", encoding="utf-8")
    print(f"[SUCESSO] {len(words)} palavras com tempo -> {out}")
    print(f"  -> Leitura rápida para o agente: {md}")


# ============================================================================
# LEGENDAS ANIMADAS (ASS palavra a palavra, cores do cliente, área segura do Reels)
# ============================================================================
def client_colors(client: str) -> dict:
    """Lê as cores '#RRGGBB' do YAML do cliente (aceita o id, ex. 'minha-cliente', ou o caminho)."""
    path = Path(client)
    if not path.exists():
        path = SKILL_DIR / "clients" / f"{client}.yaml"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    return {k: v for k, v in re.findall(r'^\s*(\w+):\s*"?(#[0-9A-Fa-f]{6})"?', text, re.M)}


def ass_color(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def ass_time(t: float) -> str:
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def chunk_words(words, n: int, max_gap: float = 0.6):
    """Blocos de até n palavras; pausa longa ou fim de frase começa bloco novo.
    Cada frase é dividida em blocos equilibrados (7 palavras viram 3+2+2, não 3+3+1 com uma palavra sozinha)."""
    phrases, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > max_gap or cur[-1]["w"][-1:] in ".?!"):
            phrases.append(cur)
            cur = []
        cur.append(w)
    if cur:
        phrases.append(cur)
    chunks = []
    for ph in phrases:
        k = math.ceil(len(ph) / n)
        sizes = [len(ph) // k + (1 if r < len(ph) % k else 0) for r in range(k)]
        pos = 0
        for size in sizes:
            chunks.append(ph[pos:pos + size])
            pos += size
    return chunks


def ass_text(text: str, upper: bool) -> str:
    text = text.replace("\\", "/").replace("{", "(").replace("}", ")")
    text = text.rstrip(",.;:") or text  # legenda de Reels não leva ponto nem vírgula; ? e ! ficam
    return text.upper() if upper else text


def build_ass(words, width, height, colors, font, size, n_words, upper, pop, reveal=False) -> str:
    base = ass_color(colors.get("text_light", "#FFFFFF"))
    high = ass_color(colors.get("secondary", "#FFD400"))
    outline = ass_color(colors.get("text_dark", "#000000"))
    margin_v = round(height * 0.30)  # acima da legenda e dos botões do Instagram/TikTok
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}", "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding",
        # Margens da área segura do Reels: 60 px à esquerda, 120 px à direita (coluna de curtir e comentar).
        # Sombra na cor do contorno, 55% opaca.
        f"Style: Nacci,{font},{size},{base},{high},{outline},{outline.replace('&H00', '&H73', 1)},-1,0,0,0,100,100,0,0,1,"
        f"{max(2, size // 13)},3,2,60,120,{margin_v},1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for chunk in chunk_words(words, n_words):
        for i, w in enumerate(chunk):
            start = chunk[0]["start"] if i == 0 else w["start"]
            end = chunk[i + 1]["start"] if i + 1 < len(chunk) else chunk[-1]["end"]
            parts = []
            for j, other in enumerate(chunk):
                t = ass_text(other["w"], upper)
                if j == i:
                    t = f"{{\\c{high}}}{t}{{\\c{base}}}"
                elif reveal and j == i + 1:
                    t = "{\\alpha&HFF&}" + t  # ainda não foi dita: guarda o lugar, mas não aparece
                parts.append(t)
            anim = "{\\fscx85\\fscy85\\t(0,90,\\fscx100\\fscy100)}" if (pop and i == 0) else ""
            lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Nacci,,0,0,0,,{anim}{' '.join(parts)}")
    return "\n".join(lines) + "\n"


def build_srt(words, n_words) -> str:
    blocks = []
    for k, chunk in enumerate(chunk_words(words, n_words), 1):
        text = " ".join(w["w"] for w in chunk)
        blocks.append(f"{k}\n{srt_time(chunk[0]['start'])} --> {srt_time(chunk[-1]['end'])}\n{text}\n")
    return "\n".join(blocks)


def cmd_captions(args):
    ffmpeg = require_ffmpeg()
    inp = Path(args.input).resolve()
    out = safe_output([inp], args.output, args.overwrite)
    words = json.loads(Path(args.transcript).read_text(encoding="utf-8"))["words"]
    if not words:
        sys.exit("[ERRO] A transcrição não tem palavras.")
    v = next(s for s in probe(inp)["streams"] if s["codec_type"] == "video")
    width, height = int(v["width"]), int(v["height"])
    colors = client_colors(args.client) if args.client else {}
    if args.color:
        colors["text_light"] = args.color
    if args.highlight:
        colors["secondary"] = args.highlight
    size = args.size or round(width * 0.075)

    ass_path = out.with_suffix(".ass")
    ass_path.write_text(build_ass(words, width, height, colors, args.font, size, args.words, args.upper,
                                  not args.no_pop, args.reveal), encoding="utf-8")
    out.with_suffix(".srt").write_text(build_srt(words, args.words), encoding="utf-8")

    print(f"[LEGENDAS] Queimando {len(words)} palavras em blocos de {args.words} ({args.font} {size}px)...")
    # O filtro 'ass' do FFmpeg se perde com 'C:\' no caminho; rodando na pasta do .ass basta o nome do arquivo.
    vf = f"ass={ass_path.name}"
    if args.fontsdir:  # fonte da marca sem precisar instalar no sistema
        vf += ":fontsdir='" + str(Path(args.fontsdir).resolve()).replace("\\", "/").replace(":", "\\:") + "'"
    cmd = [ffmpeg, "-y", "-i", str(inp), "-vf", vf,
           "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "copy", str(out)]
    subprocess.run(cmd, check=True, cwd=ass_path.parent)
    print(f"[SUCESSO] Vídeo legendado: {out}")
    print(f"  -> Legendas editáveis: {ass_path.name} (estilo) e {out.with_suffix('.srt').name} (CapCut/Premiere)")


# ============================================================================
# VERIFICAÇÃO DO ARQUIVO FINAL (o agente confere antes de dizer "pronto")
# Ideia do ffmpeg-skill (check + contact sheet), do Kinocut (portões de qualidade) e do video-use (self-eval).
# ============================================================================
PLATFORMS = {
    "reels": (1080, 1920), "tiktok": (1080, 1920), "shorts": (1080, 1920), "feed": (1080, 1350), "youtube": (1920, 1080),
}


def cmd_check(args):
    ffmpeg = require_ffmpeg()
    inp = Path(args.input).resolve()
    info = probe(inp)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    duration = float(info["format"].get("duration", 0))

    res = subprocess.run(
        [ffmpeg, "-hide_banner", "-nostats", "-i", str(inp), "-vf", "blackdetect=d=0.4:pix_th=0.10",
         "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    summary = res.stderr[res.stderr.rfind("Summary:"):] if "Summary:" in res.stderr else ""
    lufs = re.search(r"I:\s*(-?[\d.]+) LUFS", summary)
    peak = re.search(r"Peak:\s*(-?[\d.]+|-inf) dBFS", summary)
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", res.stderr)

    results = []

    def item(name, ok, value):
        results.append(ok)
        print(f"  [{'OK' if ok else 'FALHOU'}] {name}: {value}")

    print(f"[VERIFICAÇÃO] {inp.name} para '{args.platform}'")
    want = PLATFORMS[args.platform]
    if v:
        num, den = (v.get("r_frame_rate") or "0/1").split("/")
        fps = float(num) / float(den or 1)
        item("Resolução", (int(v["width"]), int(v["height"])) == want, f"{v['width']}x{v['height']} (esperado {want[0]}x{want[1]})")
        item("Quadros por segundo", 23.9 <= fps <= 60.1, f"{fps:.2f}")
        item("Codec de vídeo", v.get("codec_name") == "h264", v.get("codec_name"))
    else:
        item("Vídeo", False, "nenhuma faixa de vídeo")
    item("Áudio", a is not None, a.get("codec_name") if a else "sem faixa de áudio")
    if lufs:
        item("Volume (LUFS)", abs(float(lufs.group(1)) - args.lufs) <= 1.5, f"{lufs.group(1)} (alvo {args.lufs} ±1,5)")
    if peak and peak.group(1) != "-inf":
        item("Pico", float(peak.group(1)) <= -0.5, f"{peak.group(1)} dBFS (máx. -0,5)")
    item("Tela preta", not blacks, ", ".join(f"{float(s):.1f}-{float(e):.1f}s" for s, e in blacks) or "nenhuma")
    print(f"  [INFO] Duração: {duration:.2f}s")

    # Folha de contato: um quadro em cada tempo pedido (ex.: cada corte e cada B-roll) ou 12 espalhados
    times = [float(t) for t in args.times.split(",") if t.strip()] if args.times else \
        [duration * (k + 0.5) / 12 for k in range(12)]
    times = [min(max(t, 0.0), max(duration - 0.05, 0.0)) for t in times]
    sheet = Path(args.sheet).resolve() if args.sheet else inp.with_name(inp.stem + "_conferencia.jpg")
    with tempfile.TemporaryDirectory() as tmp:
        for k, t in enumerate(times):
            subprocess.run([ffmpeg, "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(inp), "-frames:v", "1",
                            "-vf", "scale=270:-2", str(Path(tmp) / f"f_{k:03d}.jpg")], check=True)
        cols = min(4, len(times))
        rows = math.ceil(len(times) / cols)
        subprocess.run([ffmpeg, "-y", "-v", "error", "-i", str(Path(tmp) / "f_%03d.jpg"),
                        "-vf", f"tile={cols}x{rows}:padding=6:margin=6", "-frames:v", "1", str(sheet)], check=True)
    print(f"  [INFO] Folha de contato ({len(times)} quadros, em ordem: {', '.join(f'{t:.1f}s' for t in times)}): {sheet}")
    print("  -> Agente: abra a folha de contato e olhe cada quadro antes de entregar.")
    if not all(results):
        sys.exit(1)


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # acentos certos no terminal do Windows
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Nacci.Edit FFmpeg Tools - Cirurgia Local de Vídeo")
    sub = parser.add_subparsers(dest="command", required=True)
    ow = argparse.ArgumentParser(add_help=False)
    ow.add_argument("--overwrite", action="store_true", help="Permite substituir um arquivo de saída que já existe")

    # cut-silence
    p_cut = sub.add_parser("cut-silence", parents=[ow], help="Remove pausas e silêncios automaticamente")
    p_cut.add_argument("--input", required=True, help="Vídeo de entrada")
    p_cut.add_argument("--output", required=True, help="Vídeo de saída sem silêncios")
    p_cut.add_argument("--noise", default="-35dB", help="Limite de ruído considerado silêncio (default: -35dB)")
    p_cut.add_argument("--min-silence", type=float, default=0.45, help="Duração mínima do silêncio em segundos (default: 0.45)")
    p_cut.add_argument("--padding", type=float, default=0.08, help="Respiro mantido nas bordas da fala em segundos (default: 0.08)")
    p_cut.set_defaults(func=cmd_cut_silence)

    # normalize-audio
    p_norm = sub.add_parser("normalize-audio", parents=[ow], help="Normaliza áudio para -14 LUFS (padrão Reels/TikTok)")
    p_norm.add_argument("--input", required=True)
    p_norm.add_argument("--output", required=True)
    p_norm.add_argument("--lufs", type=float, default=-14.0)
    p_norm.set_defaults(func=cmd_normalize_audio)

    # reframe-9x16
    p_ref = sub.add_parser("reframe-9x16", parents=[ow], help="Converte vídeo/B-roll horizontal para vertical 9:16 (1080x1920)")
    p_ref.add_argument("--input", required=True)
    p_ref.add_argument("--output", required=True)
    p_ref.add_argument("--mode", default="crop", choices=["crop", "blur"], help="crop central ou fundo desfocado (blur)")
    p_ref.set_defaults(func=cmd_reframe_9x16)

    # overlay-broll
    p_ov = sub.add_parser("overlay-broll", parents=[ow], help="Insere um B-roll no intervalo exato mantendo o áudio do A-roll")
    p_ov.add_argument("--aroll", required=True, help="Vídeo principal (talking-head)")
    p_ov.add_argument("--broll", required=True, help="Arquivo de B-roll aprovado")
    p_ov.add_argument("--start", type=float, required=True, help="Segundo inicial na timeline (ex: 3.5)")
    p_ov.add_argument("--end", type=float, required=True, help="Segundo final na timeline (ex: 7.0)")
    p_ov.add_argument("--output", required=True, help="Vídeo resultante")
    p_ov.set_defaults(func=cmd_overlay_broll)

    # transcribe
    p_tr = sub.add_parser("transcribe", parents=[ow], help="Transcreve a fala com o tempo de cada palavra (faster-whisper, local)")
    p_tr.add_argument("--input", required=True, help="Vídeo ou áudio")
    p_tr.add_argument("--output", default="", help="JSON de saída (default: <entrada>.transcricao.json, mais um .md legível)")
    p_tr.add_argument("--model", default="small", help="Modelo do Whisper: tiny, base, small, medium, large-v3 (default: small)")
    p_tr.add_argument("--language", default="pt", help="Idioma da fala (default: pt; vazio detecta sozinho)")
    p_tr.set_defaults(func=cmd_transcribe)

    # captions
    p_cap = sub.add_parser("captions", parents=[ow], help="Queima legendas animadas palavra a palavra com as cores do cliente")
    p_cap.add_argument("--input", required=True, help="Vídeo já cortado (a transcrição precisa ser deste arquivo)")
    p_cap.add_argument("--transcript", required=True, help="JSON gerado pelo 'transcribe'")
    p_cap.add_argument("--output", required=True, help="Vídeo legendado")
    p_cap.add_argument("--client", default="", help="Cliente (id ou caminho do YAML): usa text_light e secondary como cores")
    p_cap.add_argument("--color", default="", help="Cor do texto (#RRGGBB), sobrepõe o cliente")
    p_cap.add_argument("--highlight", default="", help="Cor da palavra falada (#RRGGBB), sobrepõe o cliente")
    p_cap.add_argument("--font", default="Arial", help="Fonte instalada na máquina (default: Arial)")
    p_cap.add_argument("--size", type=int, default=0, help="Tamanho em px (default: 7,5%% da largura)")
    p_cap.add_argument("--words", type=int, default=3, help="Palavras por bloco (default: 3)")
    p_cap.add_argument("--upper", action="store_true", help="Tudo em maiúsculas")
    p_cap.add_argument("--no-pop", action="store_true", help="Sem a animação de entrada de cada bloco")
    p_cap.add_argument("--reveal", action="store_true", help="Cada palavra só aparece quando é falada")
    p_cap.add_argument("--fontsdir", default="", help="Pasta com os .ttf/.otf da fonte (não precisa instalar)")
    p_cap.set_defaults(func=cmd_captions)

    # check
    p_chk = sub.add_parser("check", help="Confere o arquivo final (resolução, fps, LUFS, pico, tela preta) e gera folha de contato")
    p_chk.add_argument("--input", required=True)
    p_chk.add_argument("--platform", default="reels", choices=sorted(PLATFORMS))
    p_chk.add_argument("--lufs", type=float, default=-14.0)
    p_chk.add_argument("--times", default="", help="Segundos para a folha de contato, ex. '0.5,3.2,8' (cortes e B-rolls)")
    p_chk.add_argument("--sheet", default="", help="Caminho da folha de contato (default: <entrada>_conferencia.jpg)")
    p_chk.set_defaults(func=cmd_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
