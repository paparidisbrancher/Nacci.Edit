#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nacci.Edit CLI - Motor Open-Source de B-Rolls, Análise de Referências e Gestão de Edição
Criado para agências de marketing e editores de vídeo (Compatível com Antigravity & Claude Code).
Zero dependências externas obrigatórias de Python (usa stdlib + ffmpeg / yt-dlp opcionais).
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

VERSION = "1.0.0"
USER_AGENT = "NacciEdit/1.0 (https://github.com/nacci-edit; OpenSource Video Agency Skill)"


def load_env(root_dir: Path):
    """Carrega variáveis de um arquivo .env se existir."""
    for env_path in [root_dir / ".env", Path.cwd() / ".env", Path.home() / ".nacci-edit.env"]:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:
                    os.environ[k] = v


def http_get_json(url: str, headers: dict = None) -> dict:
    req_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def download_file(url: str, dest: Path, headers: dict = None) -> bool:
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out)
    return dest.exists() and dest.stat().st_size > 0


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-")[:45] or "clip"


def load_project(project_dir: Path) -> dict:
    pfile = project_dir / "project.json"
    if not pfile.exists():
        print(f"[ERRO] project.json não encontrado em {project_dir}. Rode 'setup' primeiro.", file=sys.stderr)
        sys.exit(1)
    return json.loads(pfile.read_text(encoding="utf-8"))


def save_project(project_dir: Path, data: dict):
    data["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    pfile = project_dir / "project.json"
    pfile.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ============================================================================
# 1. SETUP DO PROJETO
# ============================================================================
def cmd_setup(args):
    project_dir = Path(args.project).resolve()
    folders = [
        "01_RAW",
        "02_REFS_INSTAGRAM",
        "03_BROLLS_PREVIEW",
        "04_BROLLS_APPROVED",
        "05_EXPORTS",
    ]
    for f in folders:
        (project_dir / f).mkdir(parents=True, exist_ok=True)

    pfile = project_dir / "project.json"
    if pfile.exists() and not args.force:
        print(f"[OK] Projeto já existe em: {project_dir}")
        return

    project_data = {
        "schema": "nacci.edit/v1",
        "version": VERSION,
        "title": args.title or project_dir.name,
        "client_id": args.client or "dra-marina",
        "aspect_ratio": args.aspect or "9:16",
        "resolution": "1080x1920" if (args.aspect or "9:16") == "9:16" else "1920x1080",
        "fps": 30,
        "stage": "setup",
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "references": [],
        "beats": [],
    }
    save_project(project_dir, project_data)

    roteiro_path = project_dir / "ROTEIRO.md"
    if not roteiro_path.exists():
        roteiro_path.write_text(
            f"# Roteiro / Transcrição: {project_data['title']}\n"
            f"**Cliente:** {project_data['client_id']}\n"
            f"**Formato:** {project_data['aspect_ratio']} ({project_data['resolution']})\n\n"
            "## Fala / A-Roll\n"
            "Cole aqui o roteiro ou a transcrição com timestamps do vídeo bruto colocado em `01_RAW/`.\n\n"
            "Exemplo:\n"
            "[00:00 - 00:03] (GANCHO) Você acorda cansada mesmo dormindo 8 horas por noite?\n"
            "[00:03 - 00:09] Um estudo publicado na Nature mostrou que a inflamação silenciosa afeta...\n"
            "[00:09 - 00:15] No consultório, avaliamos três marcadores essenciais antes de suplementar...\n",
            encoding="utf-8",
        )

    origem_path = project_dir / "ORIGEM.md"
    if not origem_path.exists():
        origem_path.write_text(
            f"# Rastreabilidade de Mídia e Direitos Autorais (ORIGEM.md)\n"
            f"**Projeto:** {project_data['title']} | **Cliente:** {project_data['client_id']}\n"
            f"**Gerado por:** Nacci.Edit v{VERSION}\n\n"
            "> Este documento registra a origem, licença e aprovação humana de todos os B-rolls e inserts utilizados na timeline.\n\n"
            "| Beat | Arquivo Local | Fonte / Provedor | Título Original | Autor / Canal | Licença | Link Original | Data Aprovação |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n",
            encoding="utf-8",
        )

    print(f"[SUCESSO] Projeto Nacci.Edit inicializado em: {project_dir}")
    print(f"  -> Cliente: {project_data['client_id']}")
    print(f"  -> Pastas criadas: {', '.join(folders)}")
    print(f"  -> Arquivos criados: project.json, ROTEIRO.md, ORIGEM.md")


# ============================================================================
# 2. STATUS DO PROJETO
# ============================================================================
def cmd_status(args):
    project_dir = Path(args.project).resolve()
    data = load_project(project_dir)
    beats = data.get("beats", [])
    approved_beats = [b for b in beats if b.get("approved_candidate")]
    total_candidates = sum(len(b.get("candidates", [])) for b in beats)

    print("=" * 68)
    print(f" NACCI.EDIT STATUS | Projeto: {data.get('title')} (Cliente: {data.get('client_id')})")
    print("=" * 68)
    print(f" Etapa Atual        : {data.get('stage', 'setup').upper()}")
    print(f" Formato            : {data.get('aspect_ratio')} ({data.get('resolution')} @ {data.get('fps')}fps)")
    print(f" Refs do Instagram  : {len(data.get('references', []))} analisada(s)")
    print(f" Beats Mapeados     : {len(beats)} beat(s)")
    print(f" Candidatos B-Roll  : {total_candidates} encontrado(s)")
    print(f" B-Rolls Aprovados  : {len(approved_beats)}/{len(beats)} aprovado(s)")
    print("-" * 68)

    if not beats:
        print(" PRÓXIMO PASSO RECOMENDADO:")
        print(" 1. Edite o ROTEIRO.md ou coloque o vídeo bruto em 01_RAW/")
        print(" 2. Se a cliente mandou referência do Instagram, rode: nacci_cli.py ref-analyze --url <URL> --project .")
        print(" 3. Peça ao Agente (Antigravity/Claude): 'Quebre o ROTEIRO.md em beats e busque os B-rolls'")
    elif total_candidates == 0:
        print(" PRÓXIMO PASSO RECOMENDADO:")
        print(f" Rode a busca automática para os beats: python scripts/nacci_cli.py search --project \"{project_dir}\"")
    elif len(approved_beats) < len(beats):
        print(" PRÓXIMO PASSO RECOMENDADO (TRAVA DE REVISÃO HUMANA):")
        print(f" 1. Gere e abra o Storyboard visual: python scripts/storyboard_gen.py --project \"{project_dir}\"")
        print(f" 2. Aprove os melhores B-rolls: python scripts/nacci_cli.py approve --project \"{project_dir}\" --selections \"B01:B01_C1,...\"")
    else:
        print(" PRÓXIMO PASSO RECOMENDADO:")
        print(f" Todos os B-rolls foram aprovados! Exporte a timeline XML para Premiere/DaVinci:")
        print(f" python scripts/xml_exporter.py --project \"{project_dir}\"")
    print("=" * 68)


# ============================================================================
# 3. ANÁLISE DE REFERÊNCIAS DO INSTAGRAM / TIKTOK / SHORTS
# ============================================================================
def cmd_ref_analyze(args):
    project_dir = Path(args.project).resolve()
    data = load_project(project_dir)
    ref_dir = project_dir / "02_REFS_INSTAGRAM"
    ref_dir.mkdir(parents=True, exist_ok=True)

    url = args.url.strip()
    ref_id = f"REF_{len(data.get('references', [])) + 1:02d}"
    target_dir = ref_dir / ref_id
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] Baixando referência ({url}) via yt-dlp...")
    video_out = target_dir / f"{ref_id}.mp4"
    meta_info = {"id": ref_id, "url": url, "downloaded": False, "frames": []}

    ytdlp_bin = shutil.which("yt-dlp")
    ffmpeg_bin = shutil.which("ffmpeg")

    if ytdlp_bin:
        try:
            cmd = [
                ytdlp_bin,
                "--no-playlist",
                "-f", "mp4/best",
                "--write-info-json",
                "-o", str(video_out),
                url,
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            meta_info["downloaded"] = video_out.exists()
        except Exception as e:
            print(f"[AVISO] yt-dlp não conseguiu baixar diretamente ({e}). Registrando URL para análise contextual.")
    else:
        print("[AVISO] yt-dlp não encontrado no PATH. Instale com 'pip install yt-dlp' ou 'winget install yt-dlp' para download automático de Reels.")

    # Se o vídeo foi baixado e temos ffmpeg, detectar cenas/cortes e extrair frames para a IA ver!
    cuts_timestamps = []
    duration_sec = 0.0
    if meta_info["downloaded"] and ffmpeg_bin:
        print("[2/3] Detectando frequência de cortes (Scene Detection) e extraindo frames para análise visual da IA...")
        info_json = target_dir / f"{ref_id}.info.json"
        if info_json.exists():
            try:
                j = json.loads(info_json.read_text(encoding="utf-8", errors="ignore"))
                duration_sec = float(j.get("duration") or 0.0)
                meta_info["title"] = j.get("title", "")
                meta_info["description"] = j.get("description", "")
                meta_info["uploader"] = j.get("uploader", "")
            except Exception:
                pass

        # Scene detection
        scene_cmd = [
            ffmpeg_bin, "-i", str(video_out),
            "-vf", "select='gt(scene,0.28)',showinfo",
            "-f", "null", "-"
        ]
        res = subprocess.run(scene_cmd, capture_output=True, text=True)
        for line in res.stderr.splitlines():
            m = re.search(r"pts_time:([0-9.]+)", line)
            if m:
                cuts_timestamps.append(round(float(m.group(1)), 2))

        # Extrair até 6 frames (1 a cada N segundos) para o agente inspecionar com read_file
        frames_dir = target_dir / "frames"
        frames_dir.mkdir(exist_ok=True)
        fps_extract = "1/3" if duration_sec > 15 else "1/2"
        extract_cmd = [
            ffmpeg_bin, "-y", "-i", str(video_out),
            "-vf", f"fps={fps_extract},scale=540:-1",
            "-frames:v", "6",
            str(frames_dir / "frame_%02d.jpg")
        ]
        subprocess.run(extract_cmd, capture_output=True, text=True)
        meta_info["frames"] = [str(p.relative_to(project_dir)) for p in sorted(frames_dir.glob("*.jpg"))]

    num_cuts = len(cuts_timestamps)
    asl = round(duration_sec / (num_cuts + 1), 2) if duration_sec > 0 else 0.0
    meta_info["duration_sec"] = duration_sec
    meta_info["detected_cuts_count"] = num_cuts
    meta_info["cut_timestamps"] = cuts_timestamps
    meta_info["average_shot_length_sec"] = asl
    meta_info["notes"] = args.notes or ""

    data.setdefault("references", []).append(meta_info)
    if data.get("stage") == "setup":
        data["stage"] = "ref-analyzed"
    save_project(project_dir, data)

    # Salvar relatório Markdown da referência
    report_md = target_dir / "ANALISE_REFERENCIA.md"
    report_md.write_text(
        f"# Análise de Referência ({ref_id})\n"
        f"- **URL:** {url}\n"
        f"- **Criador:** {meta_info.get('uploader', 'N/A')}\n"
        f"- **Duração:** {duration_sec}s\n"
        f"- **Total de Cortes Detectados:** {num_cuts}\n"
        f"- **Tempo Médio por Plano (ASL):** {asl}s por corte\n"
        f"- **Timestamps dos Cortes:** {', '.join(map(str, cuts_timestamps)) if cuts_timestamps else 'N/A'}\n"
        f"- **Frames Extraídos para IA:** {', '.join(meta_info['frames']) if meta_info['frames'] else 'Nenhum'}\n"
        f"- **Notas da Cliente:** {meta_info['notes']}\n\n"
        "## Instrução para o Agente (Antigravity / Claude)\n"
        "Use a ferramenta `read_file` nos frames extraídos acima para analisar o estilo de legenda, cores, enquadramento do gancho nos primeiros 3 segundos e tipo de B-roll usado na referência.\n",
        encoding="utf-8",
    )
    print(f"[3/3] Referência {ref_id} registrada com sucesso! Relatório salvo em: {report_md}")


# ============================================================================
# 4. GERENCIAMENTO DE BEATS (BRIEFING)
# ============================================================================
def cmd_add_beat(args):
    project_dir = Path(args.project).resolve()
    data = load_project(project_dir)
    beats = data.setdefault("beats", [])

    beat_obj = {
        "id": args.id,
        "time_start": args.time_start,
        "time_end": args.time_end,
        "type": args.type,  # literal, ilustrativo, motion
        "speech": args.speech,
        "query": args.query,
        "provider_preference": args.provider or "auto",
        "notes": args.notes or "",
        "candidates": [],
        "approved_candidate": None,
    }

    # Substituir se já existir o mesmo ID
    replaced = False
    for idx, b in enumerate(beats):
        if b.get("id") == args.id:
            beat_obj["candidates"] = b.get("candidates", [])
            beat_obj["approved_candidate"] = b.get("approved_candidate")
            beats[idx] = beat_obj
            replaced = True
            break
    if not replaced:
        beats.append(beat_obj)

    data["stage"] = "briefed"
    save_project(project_dir, data)
    print(f"[OK] Beat {args.id} ({args.time_start} -> {args.time_end}) [{args.type.upper()}] salvo. Query: '{args.query}'")


# ============================================================================
# 5. PROVEDORES DE BUSCA DE B-ROLLS (7 FONTES NATIVAS GRATUITAS)
# ============================================================================
def search_wikimedia(query: str, limit: int = 3) -> list:
    """Busca vídeos e imagens no Wikimedia Commons (Domínio Público / CC - SEM API KEY)."""
    results = []
    encoded = urllib.parse.quote(f"{query} filetype:video|bitmap")
    url = (
        f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
        f"&gsrsearch={encoded}&gsrnamespace=6&gsrlimit={limit}"
        f"&prop=imageinfo&iiprop=url|extmetadata|mime|dimensions&format=json"
    )
    try:
        data = http_get_json(url)
        pages = data.get("query", {}).get("pages", {})
        for _, p in pages.items():
            ii = (p.get("imageinfo") or [{}])[0]
            ext = ii.get("extmetadata", {})
            media_url = ii.get("url", "")
            if not media_url:
                continue
            mime = ii.get("mime", "")
            media_type = "video" if ("video" in mime or media_url.endswith((".webm", ".ogv", ".mp4"))) else "image"
            artist = re.sub(r"<[^>]+>", "", ext.get("Artist", {}).get("value", "Wikimedia Contributor")).strip()
            license_name = ext.get("LicenseShortName", {}).get("value", "CC / Public Domain")
            results.append({
                "provider": "wikimedia",
                "media_type": media_type,
                "title": p.get("title", "").replace("File:", ""),
                "preview_url": media_url,
                "download_url": media_url,
                "thumbnail_url": media_url if media_type == "image" else "",
                "source_page": ii.get("descriptionurl", media_url),
                "author": artist or "Wikimedia Commons",
                "license": license_name,
                "duration": "N/A",
            })
    except Exception as e:
        print(f"  [aviso] Wikimedia search falhou para '{query}': {e}", file=sys.stderr)
    return results


def search_nasa(query: str, limit: int = 2) -> list:
    """Busca vídeos e imagens científicas/espaciais na NASA Library (Domínio Público - SEM API KEY)."""
    results = []
    encoded = urllib.parse.quote(query)
    url = f"https://images-api.nasa.gov/search?q={encoded}&page_size={limit}"
    try:
        data = http_get_json(url)
        items = data.get("collection", {}).get("items", [])[:limit]
        for item in items:
            d = (item.get("data") or [{}])[0]
            links = item.get("links") or [{}]
            thumb = links[0].get("href", "") if links else ""
            nasa_id = d.get("nasa_id", "")
            media_type = d.get("media_type", "image")
            results.append({
                "provider": "nasa",
                "media_type": media_type,
                "title": d.get("title", nasa_id),
                "preview_url": thumb,
                "download_url": thumb,
                "thumbnail_url": thumb,
                "source_page": f"https://images.nasa.gov/details/{nasa_id}",
                "author": d.get("center", "NASA"),
                "license": "Public Domain (NASA)",
                "duration": "N/A",
            })
    except Exception as e:
        print(f"  [aviso] NASA search falhou para '{query}': {e}", file=sys.stderr)
    return results


def search_openverse(query: str, limit: int = 3) -> list:
    """Busca imagens e ilustrações Creative Commons no Openverse (SEM API KEY)."""
    results = []
    encoded = urllib.parse.quote(query)
    url = f"https://api.openverse.org/v1/images/?q={encoded}&page_size={limit}"
    try:
        data = http_get_json(url)
        for item in data.get("results", [])[:limit]:
            results.append({
                "provider": "openverse",
                "media_type": "image",
                "title": item.get("title", query),
                "preview_url": item.get("url", ""),
                "download_url": item.get("url", ""),
                "thumbnail_url": item.get("thumbnail") or item.get("url", ""),
                "source_page": item.get("foreign_landing_url") or item.get("url", ""),
                "author": item.get("creator") or "Openverse Creator",
                "license": f"CC {item.get('license', 'BY').upper()}",
                "duration": "Imagem Estática",
            })
    except Exception as e:
        print(f"  [aviso] Openverse search falhou para '{query}': {e}", file=sys.stderr)
    return results


def search_pexels(query: str, limit: int = 3, orientation: str = "portrait") -> list:
    """Busca vídeos cinemáticos gratuitos no Pexels (requer PEXELS_API_KEY gratuita)."""
    api_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not api_key:
        return []
    results = []
    encoded = urllib.parse.quote(query)
    url = f"https://api.pexels.com/videos/search?query={encoded}&per_page={limit}&orientation={orientation}"
    try:
        data = http_get_json(url, headers={"Authorization": api_key})
        for v in data.get("videos", [])[:limit]:
            files = v.get("video_files", [])
            best_file = sorted(files, key=lambda x: x.get("height", 0), reverse=True)[0] if files else {}
            results.append({
                "provider": "pexels",
                "media_type": "video",
                "title": f"Pexels Video #{v.get('id')}",
                "preview_url": best_file.get("link", ""),
                "download_url": best_file.get("link", ""),
                "thumbnail_url": v.get("image", ""),
                "source_page": v.get("url", ""),
                "author": v.get("user", {}).get("name", "Pexels Creator"),
                "license": "Pexels Free License (Comercial Permitido)",
                "duration": f"{v.get('duration', '?')}s",
            })
    except Exception as e:
        print(f"  [aviso] Pexels search falhou para '{query}': {e}", file=sys.stderr)
    return results


def search_pixabay(query: str, limit: int = 3) -> list:
    """Busca vídeos gratuitos no Pixabay (requer PIXABAY_API_KEY gratuita)."""
    api_key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not api_key:
        return []
    results = []
    encoded = urllib.parse.quote(query)
    url = f"https://pixabay.com/api/videos/?key={api_key}&q={encoded}&per_page={limit}"
    try:
        data = http_get_json(url)
        for v in data.get("hits", [])[:limit]:
            vids = v.get("videos", {})
            medium = vids.get("medium") or vids.get("large") or {}
            results.append({
                "provider": "pixabay",
                "media_type": "video",
                "title": f"Pixabay: {v.get('tags', query)}",
                "preview_url": medium.get("url", ""),
                "download_url": medium.get("url", ""),
                "thumbnail_url": medium.get("thumbnail", ""),
                "source_page": v.get("pageURL", ""),
                "author": v.get("user", "Pixabay Creator"),
                "license": "Pixabay Content License (Comercial Permitido)",
                "duration": f"{v.get('duration', '?')}s",
            })
    except Exception as e:
        print(f"  [aviso] Pixabay search falhou para '{query}': {e}", file=sys.stderr)
    return results


def search_youtube_ytdlp(query: str, limit: int = 2) -> list:
    """Busca vídeos/reportagens no YouTube via yt-dlp local (SEM API KEY)."""
    ytdlp_bin = shutil.which("yt-dlp")
    if not ytdlp_bin:
        return []
    results = []
    try:
        cmd = [
            ytdlp_bin,
            f"ytsearch{limit}:{query}",
            "--dump-json",
            "--no-playlist",
            "--skip-download",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        for line in res.stdout.splitlines():
            if not line.strip():
                continue
            info = json.loads(line)
            vid_url = info.get("webpage_url") or f"https://www.youtube.com/watch?v={info.get('id')}"
            results.append({
                "provider": "youtube",
                "media_type": "video",
                "title": info.get("title", query),
                "preview_url": vid_url,
                "download_url": vid_url,
                "thumbnail_url": info.get("thumbnail", ""),
                "source_page": vid_url,
                "author": info.get("uploader") or info.get("channel", "YouTube"),
                "license": "YouTube Standard / Fair Use Editorial (Verificar Direitos)",
                "duration": f"{info.get('duration', '?')}s",
            })
    except Exception as e:
        print(f"  [aviso] YouTube yt-dlp search falhou para '{query}': {e}", file=sys.stderr)
    return results


def cmd_search(args):
    project_dir = Path(args.project).resolve()
    load_env(project_dir.parent)
    data = load_project(project_dir)
    beats = data.get("beats", [])
    if not beats:
        print("[ERRO] Nenhum beat cadastrado em project.json. Use 'add-beat' primeiro.", file=sys.stderr)
        sys.exit(1)

    orientation = "portrait" if data.get("aspect_ratio") == "9:16" else "landscape"
    target_beat_id = args.beat
    limit = args.limit or 3

    for b in beats:
        if target_beat_id and b.get("id") != target_beat_id:
            continue
        query = args.query or b.get("query")
        if not query:
            continue

        print(f"[BUSCANDO] Beat {b['id']} ({b.get('type')}): '{query}'...")
        raw_candidates = []
        prov = (args.provider or b.get("provider_preference") or "auto").lower()

        if prov in ("all", "auto", "pexels"):
            raw_candidates.extend(search_pexels(query, limit=limit, orientation=orientation))
        if prov in ("all", "auto", "pixabay"):
            raw_candidates.extend(search_pixabay(query, limit=limit))
        if prov in ("all", "auto", "wikimedia"):
            raw_candidates.extend(search_wikimedia(query, limit=limit))
        if prov in ("all", "auto", "openverse"):
            raw_candidates.extend(search_openverse(query, limit=limit))
        if prov in ("all", "nasa"):
            raw_candidates.extend(search_nasa(query, limit=2))
        if prov in ("all", "youtube") or (prov == "auto" and b.get("type") == "literal"):
            raw_candidates.extend(search_youtube_ytdlp(query, limit=2))

        # Numerar candidatos
        numbered = []
        for idx, c in enumerate(raw_candidates, start=1):
            c["candidate_id"] = f"{b['id']}_C{idx}"
            numbered.append(c)

        b["candidates"] = numbered
        print(f"  -> {len(numbered)} candidato(s) encontrado(s) para {b['id']}.")

    data["stage"] = "searched"
    save_project(project_dir, data)
    print(f"[SUCESSO] Busca concluída! Gere o Storyboard com: python scripts/storyboard_gen.py --project \"{project_dir}\"")


# ============================================================================
# 6. APROVAÇÃO HUMANA E REGISTRO EM ORIGEM.MD (TRAVA EDITORIAL)
# ============================================================================
def cmd_approve(args):
    project_dir = Path(args.project).resolve()
    data = load_project(project_dir)
    beats_by_id = {b["id"]: b for b in data.get("beats", [])}
    approved_dir = project_dir / "04_BROLLS_APPROVED"
    approved_dir.mkdir(parents=True, exist_ok=True)
    origem_path = project_dir / "ORIGEM.md"

    pairs = [p.strip() for p in args.selections.split(",") if ":" in p]
    if not pairs:
        print("[ERRO] Formato inválido em --selections. Use ex: --selections 'B01:B01_C1,B02:B02_C2'", file=sys.stderr)
        sys.exit(1)

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    ytdlp_bin = shutil.which("yt-dlp")

    for pair in pairs:
        beat_id, cand_id = [x.strip() for x in pair.split(":", 1)]
        beat = beats_by_id.get(beat_id)
        if not beat:
            print(f"[AVISO] Beat {beat_id} não encontrado.", file=sys.stderr)
            continue

        cand = next((c for c in beat.get("candidates", []) if c.get("candidate_id") == cand_id), None)
        if not cand:
            print(f"[AVISO] Candidato {cand_id} não encontrado no Beat {beat_id}.", file=sys.stderr)
            continue

        provider = cand.get("provider", "web")
        slug = slugify(cand.get("title", beat.get("query", "broll")))
        dl_url = cand.get("download_url", "")
        ext = ".mp4" if cand.get("media_type") == "video" else ".jpg"
        if dl_url.lower().endswith((".png", ".webm", ".gif", ".jpeg", ".jpg", ".mp4")):
            ext = "." + dl_url.rsplit(".", 1)[-1].split("?")[0].lower()

        local_filename = f"{beat_id}_{provider}_{slug}{ext}"
        local_path = approved_dir / local_filename

        print(f"[APROVANDO] {beat_id} -> {cand_id} ({provider}: {cand.get('title')})...")
        downloaded = False
        if not args.metadata_only and dl_url:
            try:
                if provider == "youtube" and ytdlp_bin:
                    section = f"*{args.trim_start or '00:00:00'}-{args.trim_end or '00:00:08'}"
                    cmd = [
                        ytdlp_bin, "--no-playlist", "-f", "mp4/best",
                        "--download-sections", section,
                        "-o", str(local_path), dl_url
                    ]
                    subprocess.run(cmd, check=True)
                    downloaded = local_path.exists()
                else:
                    downloaded = download_file(dl_url, local_path)
            except Exception as e:
                print(f"  [aviso] Download direto falhou ({e}). Registrando link aprovado em ORIGEM.md.")

        cand["local_file"] = f"04_BROLLS_APPROVED/{local_filename}" if downloaded else dl_url
        cand["approved_at"] = now_str
        beat["approved_candidate"] = cand

        # Registrar linha de auditoria no ORIGEM.md
        row = (
            f"| **{beat_id}** ({beat.get('time_start')}-{beat.get('time_end')}) "
            f"| `{local_filename}` "
            f"| {provider.upper()} "
            f"| {cand.get('title', '').replace('|', '-')} "
            f"| {cand.get('author', 'N/A').replace('|', '-')} "
            f"| {cand.get('license', 'N/A').replace('|', '-')} "
            f"| [Abrir Fonte]({cand.get('source_page', dl_url)}) "
            f"| {now_str} |\n"
        )
        with open(origem_path, "a", encoding="utf-8") as f:
            f.write(row)

        print(f"  [OK] Registrado em ORIGEM.md -> {local_filename}")

    data["stage"] = "approved"
    save_project(project_dir, data)
    print(f"[SUCESSO] Aprovações concluídas e auditadas em: {origem_path}")


# ============================================================================
# CLI PARSER
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="Nacci.Edit CLI - Motor de B-Rolls e Gestão de Edição para Agências")
    sub = parser.add_subparsers(dest="command", required=True)

    # setup
    p_setup = sub.add_parser("setup", help="Inicializa a estrutura de pastas de um projeto de vídeo")
    p_setup.add_argument("--project", required=True, help="Caminho da pasta do projeto")
    p_setup.add_argument("--client", default="dra-marina", help="ID do cliente (ex: dra-marina)")
    p_setup.add_argument("--title", default="", help="Título do vídeo/Reels")
    p_setup.add_argument("--aspect", default="9:16", choices=["9:16", "16:9", "1:1"], help="Proporção do vídeo")
    p_setup.add_argument("--force", action="store_true", help="Sobrescrever project.json existente")
    p_setup.set_defaults(func=cmd_setup)

    # status
    p_status = sub.add_parser("status", help="Exibe o status atual do projeto e o próximo passo recomendado")
    p_status.add_argument("--project", required=True, help="Caminho da pasta do projeto")
    p_status.set_defaults(func=cmd_status)

    # ref-analyze
    p_ref = sub.add_parser("ref-analyze", help="Baixa e disseca um Reels/TikTok de referência enviado pela cliente")
    p_ref.add_argument("--project", required=True, help="Caminho da pasta do projeto")
    p_ref.add_argument("--url", required=True, help="URL do Reels / TikTok / Shorts de referência")
    p_ref.add_argument("--notes", default="", help="Observações sobre o que a cliente gostou na referência")
    p_ref.set_defaults(func=cmd_ref_analyze)

    # add-beat
    p_beat = sub.add_parser("add-beat", help="Adiciona ou atualiza um Beat visual no briefing do vídeo")
    p_beat.add_argument("--project", required=True, help="Caminho da pasta do projeto")
    p_beat.add_argument("--id", required=True, help="ID do Beat (ex: B01, B02)")
    p_beat.add_argument("--time-start", required=True, help="Tempo inicial (ex: 00:00)")
    p_beat.add_argument("--time-end", required=True, help="Tempo final (ex: 00:04)")
    p_beat.add_argument("--type", default="ilustrativo", choices=["literal", "ilustrativo", "motion"], help="Tipo de B-roll")
    p_beat.add_argument("--speech", required=True, help="Trecho da fala correspondente no roteiro")
    p_beat.add_argument("--query", required=True, help="Termo de busca em inglês ou português para os provedores")
    p_beat.add_argument("--provider", default="auto", help="Provedor preferido (auto, pexels, pixabay, wikimedia, openverse, nasa, youtube)")
    p_beat.add_argument("--notes", default="", help="Direção visual do editor")
    p_beat.set_defaults(func=cmd_add_beat)

    # search
    p_search = sub.add_parser("search", help="Busca candidatos de B-roll nos provedores gratuitos")
    p_search.add_argument("--project", required=True, help="Caminho da pasta do projeto")
    p_search.add_argument("--beat", default="", help="Filtrar por um Beat específico (ex: B01)")
    p_search.add_argument("--provider", default="auto", help="Forçar provedor (all, auto, pexels, pixabay, wikimedia, openverse, nasa, youtube)")
    p_search.add_argument("--query", default="", help="Sobrescrever query de busca")
    p_search.add_argument("--limit", type=int, default=3, help="Limite de resultados por provedor")
    p_search.set_defaults(func=cmd_search)

    # approve
    p_app = sub.add_parser("approve", help="Aprova candidatos selecionados, baixa os cortes e registra em ORIGEM.md")
    p_app.add_argument("--project", required=True, help="Caminho da pasta do projeto")
    p_app.add_argument("--selections", required=True, help="Lista de pares BEAT:CANDIDATO (ex: 'B01:B01_C1,B02:B02_C2')")
    p_app.add_argument("--trim-start", default="", help="Início do corte para vídeos longos (ex: 00:00:05)")
    p_app.add_argument("--trim-end", default="", help="Fim do corte para vídeos longos (ex: 00:00:10)")
    p_app.add_argument("--metadata-only", action="store_true", help="Apenas registrar aprovação sem baixar o arquivo pesado agora")
    p_app.set_defaults(func=cmd_approve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
