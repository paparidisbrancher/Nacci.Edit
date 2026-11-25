"""Checagem rápida da lógica pura do ffmpeg_tools. Rode: python tests/test_ffmpeg_tools.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from ffmpeg_tools import (ass_color, ass_time, build_ass, chunk_words, client_colors,  # noqa: E402
                          pack_words, speech_segments, srt_time)

W = [{"w": "Você", "start": 0.0, "end": 0.3}, {"w": "acorda", "start": 0.35, "end": 0.7},
     {"w": "cansada?", "start": 0.75, "end": 1.2}, {"w": "Isso", "start": 2.5, "end": 2.8},
     {"w": "tem", "start": 2.85, "end": 3.0}, {"w": "nome.", "start": 3.05, "end": 3.4}]

# Silêncio de 2,0 a 3,0 vira dois trechos com 0,1 s de respiro; silêncio sem fim vai até o fim do arquivo
assert speech_segments([2.0], [3.0], 5.0, 0.1) == [(0.0, 2.1), (2.9, 5.0)]
assert speech_segments([2.0], [], 5.0, 0.1) == [(0.0, 2.1)]

# Fim de frase e pausa longa quebram o bloco antes de chegar ao limite de palavras
assert [[w["w"] for w in c] for c in chunk_words(W, 2)] == [["Você", "acorda"], ["cansada?"], ["Isso", "tem"], ["nome."]]
seven = [{"w": f"p{k}", "start": k * 0.3, "end": k * 0.3 + 0.2} for k in range(7)]
assert [len(c) for c in chunk_words(seven, 3)] == [3, 2, 2]  # sem palavra sozinha no fim
assert pack_words(W).splitlines() == ["[0000.00-0001.20] Você acorda cansada?", "[0002.50-0003.40] Isso tem nome."]

assert ass_time(3723.456) == "1:02:03.46"
assert srt_time(3723.456) == "01:02:03,456"
assert ass_color("#D4AF37") == "&H0037AFD4"
assert client_colors("_template")["secondary"] == "#FFFFFF"

ass = build_ass(W, 1080, 1920, {"secondary": "#D4AF37"}, "Arial", 80, 3, False, True)
assert ass.count("Dialogue:") == len(W)  # um evento por palavra falada, com a palavra da vez destacada
assert "{\\c&H0037AFD4}Você{\\c&H00FFFFFF} acorda cansada?" in ass

rev = build_ass(W, 1080, 1920, {}, "Arial", 80, 3, False, False, reveal=True)
assert "{\\c&H0000D4FF}Você{\\c&H00FFFFFF} {\\alpha&HFF&}acorda cansada?" in rev  # o que não foi dito não aparece
assert "Você {\\c&H0000D4FF}acorda{\\c&H00FFFFFF} {\\alpha&HFF&}cansada?" in rev

print("OK: todas as checagens passaram")
