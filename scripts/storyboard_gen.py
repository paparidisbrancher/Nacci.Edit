#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nacci.Edit Storyboard Generator - Painel Visual Interativo de Revisão e Aprovação de B-Rolls
Gera um arquivo STORYBOARD.html interativo onde o editor ou cliente visualiza os candidatos
lado a lado, escolhe o melhor clipe para cada Beat e copia o comando de aprovação com 1 clique.
"""

import argparse
import html
import json
import sys
import webbrowser
from pathlib import Path


def generate_html(project_dir: Path, data: dict) -> str:
    title = html.escape(data.get("title", "Projeto Nacci.Edit"))
    client = html.escape(data.get("client_id", "dra-marina"))
    aspect = html.escape(data.get("aspect_ratio", "9:16"))
    beats = data.get("beats", [])
    proj_path_js = str(project_dir).replace("\\", "\\\\")

    beats_html = []
    for b in beats:
        bid = html.escape(b.get("id", "B00"))
        t_start = html.escape(b.get("time_start", "00:00"))
        t_end = html.escape(b.get("time_end", "00:04"))
        btype = html.escape(b.get("type", "ilustrativo")).upper()
        speech = html.escape(b.get("speech", ""))
        query = html.escape(b.get("query", ""))
        notes = html.escape(b.get("notes", ""))
        approved = b.get("approved_candidate") or {}
        approved_id = approved.get("candidate_id", "")

        candidates_cards = []
        for idx, c in enumerate(b.get("candidates", []), start=1):
            cid = html.escape(c.get("candidate_id", f"{bid}_C{idx}"))
            prov = html.escape(c.get("provider", "web")).upper()
            ctitle = html.escape(c.get("title", "Sem título"))
            author = html.escape(c.get("author", "N/A"))
            lic = html.escape(c.get("license", "N/A"))
            mtype = c.get("media_type", "image")
            preview_url = html.escape(c.get("preview_url", ""))
            thumb_url = html.escape(c.get("thumbnail_url") or c.get("preview_url", ""))
            source_page = html.escape(c.get("source_page", preview_url))
            is_selected = (cid == approved_id) or (not approved_id and idx == 1)
            sel_class = "selected" if is_selected else ""

            if mtype == "video" and preview_url.endswith((".mp4", ".webm", ".ogv")):
                media_tag = f'<video src="{preview_url}" poster="{thumb_url}" controls muted loop preload="metadata"></video>'
            elif thumb_url:
                media_tag = f'<img src="{thumb_url}" alt="{ctitle}" loading="lazy" />'
            else:
                media_tag = f'<div class="no-preview">Prévia externa ({prov})</div>'

            candidates_cards.append(f"""
            <div class="cand-card {sel_class}" data-beat="{bid}" data-cand="{cid}" onclick="selectCandidate('{bid}', '{cid}', this)">
              <div class="cand-header">
                <span class="badge-provider">{prov}</span>
                <span class="cand-id">{cid}</span>
              </div>
              <div class="media-box">
                {media_tag}
              </div>
              <div class="cand-body">
                <div class="cand-title" title="{ctitle}">{ctitle}</div>
                <div class="cand-meta">Autor: {author}</div>
                <div class="cand-license">Licença: {lic}</div>
                <div class="cand-actions">
                  <a href="{source_page}" target="_blank" onclick="event.stopPropagation()">Abrir Fonte ↗</a>
                  <button type="button" class="btn-pick">Selecionar</button>
                </div>
              </div>
            </div>
            """)

        if not candidates_cards:
            candidates_cards.append('<div class="empty-cand">Nenhum candidato buscado ainda para este Beat. Rode <code>nacci_cli.py search</code>.</div>')

        beats_html.append(f"""
        <section class="beat-block" id="beat-{bid}">
          <div class="beat-info">
            <div class="beat-top">
              <span class="beat-id">{bid}</span>
              <span class="beat-time">{t_start} → {t_end}</span>
              <span class="badge-type type-{btype.lower()}">{btype}</span>
            </div>
            <blockquote class="beat-speech">“{speech}”</blockquote>
            <div class="beat-details">
              <span><strong>Busca:</strong> <code>{query}</code></span>
              {f'<span><strong>Direção Visual:</strong> {notes}</span>' if notes else ''}
            </div>
          </div>
          <div class="candidates-grid">
            {''.join(candidates_cards)}
          </div>
        </section>
        """)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Storyboard Nacci.Edit — {title}</title>
  <style>
    :root {{
      --bg: #0f1115;
      --panel: #181b22;
      --card: #1f242d;
      --border: #2e3646;
      --accent: #d4af37;
      --accent-green: #10b981;
      --text: #f3f4f6;
      --muted: #9ca3af;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg);
      color: var(--text);
      padding: 28px 24px 120px;
      line-height: 1.5;
    }}
    header {{
      max-width: 1280px;
      margin: 0 auto 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 18px;
    }}
    .brand {{ display: flex; align-items: center; gap: 12px; }}
    .brand-logo {{
      background: linear-gradient(135deg, #d4af37, #b48a1e);
      color: #000;
      font-weight: 800;
      padding: 6px 12px;
      border-radius: 8px;
      letter-spacing: 0.5px;
    }}
    .meta-pills span {{
      background: var(--panel);
      border: 1px solid var(--border);
      padding: 6px 12px;
      border-radius: 999px;
      font-size: 0.85rem;
      margin-left: 8px;
    }}
    main {{ max-width: 1280px; margin: 0 auto; display: flex; flex-direction: column; gap: 28px; }}
    .beat-block {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 20px;
    }}
    .beat-top {{ display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }}
    .beat-id {{
      background: var(--accent);
      color: #000;
      font-weight: 800;
      padding: 3px 10px;
      border-radius: 6px;
    }}
    .beat-time {{ font-family: monospace; color: var(--muted); font-size: 0.95rem; }}
    .badge-type {{
      font-size: 0.75rem;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      background: #2d3748;
    }}
    .type-literal {{ background: #1e3a8a; color: #93c5fd; }}
    .type-ilustrativo {{ background: #064e3b; color: #6ee7b7; }}
    .type-motion {{ background: #581c87; color: #d8b4fe; }}
    .beat-speech {{
      font-size: 1.1rem;
      font-style: italic;
      color: #fff;
      border-left: 3px solid var(--accent);
      padding-left: 12px;
      margin: 10px 0;
    }}
    .beat-details {{ font-size: 0.88rem; color: var(--muted); display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 16px; }}
    .candidates-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
      gap: 16px;
    }}
    .cand-card {{
      background: var(--card);
      border: 2px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      cursor: pointer;
      transition: all 0.18s ease;
      display: flex;
      flex-direction: column;
    }}
    .cand-card:hover {{ border-color: #6b7280; transform: translateY(-2px); }}
    .cand-card.selected {{
      border-color: var(--accent-green);
      box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.25);
    }}
    .cand-header {{
      display: flex;
      justify-content: space-between;
      padding: 8px 12px;
      background: rgba(0,0,0,0.25);
      font-size: 0.78rem;
      font-weight: 700;
    }}
    .badge-provider {{ color: var(--accent); }}
    .media-box {{
      width: 100%;
      height: 190px;
      background: #000;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }}
    .media-box video, .media-box img {{ width: 100%; height: 100%; object-fit: cover; }}
    .cand-body {{ padding: 12px; display: flex; flex-direction: column; gap: 6px; flex: 1; }}
    .cand-title {{ font-weight: 600; font-size: 0.92rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .cand-meta, .cand-license {{ font-size: 0.78rem; color: var(--muted); }}
    .cand-actions {{
      margin-top: auto;
      padding-top: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .cand-actions a {{ color: #60a5fa; text-decoration: none; font-size: 0.82rem; }}
    .btn-pick {{
      background: var(--border);
      color: var(--text);
      border: none;
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
    }}
    .cand-card.selected .btn-pick {{ background: var(--accent-green); color: #000; }}
    .approval-bar {{
      position: fixed;
      bottom: 0; left: 0; right: 0;
      background: rgba(24, 27, 34, 0.96);
      backdrop-filter: blur(10px);
      border-top: 1px solid var(--border);
      padding: 16px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      z-index: 100;
    }}
    .cmd-box {{
      flex: 1;
      background: #090b0e;
      border: 1px solid var(--border);
      padding: 10px 14px;
      border-radius: 8px;
      font-family: monospace;
      font-size: 0.85rem;
      color: #6ee7b7;
      overflow-x: auto;
      white-space: nowrap;
    }}
    .btn-approve {{
      background: var(--accent-green);
      color: #000;
      font-weight: 800;
      border: none;
      padding: 12px 22px;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.92rem;
    }}
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span class="brand-logo">NACCI.EDIT</span>
      <div>
        <h1>{title}</h1>
        <p style="color: var(--muted); font-size: 0.9rem;">Painel de Revisão Humana e Trava Editorial de B-Rolls</p>
      </div>
    </div>
    <div class="meta-pills">
      <span>Cliente: <strong>{client}</strong></span>
      <span>Formato: <strong>{aspect}</strong></span>
      <span>Beats: <strong>{len(beats)}</strong></span>
    </div>
  </header>

  <main>
    {''.join(beats_html)}
  </main>

  <div class="approval-bar">
    <div class="cmd-box" id="cmdOutput">Selecione os B-rolls acima...</div>
    <button class="btn-approve" onclick="copyCommand()">Copiar Comando de Aprovação</button>
  </div>

  <script>
    const selections = {{}};
    const projectPath = "{proj_path_js}";

    function initSelections() {{
      document.querySelectorAll('.cand-card.selected').forEach(card => {{
        selections[card.dataset.beat] = card.dataset.cand;
      }});
      updateCommand();
    }}

    function selectCandidate(beatId, candId, el) {{
      document.querySelectorAll(`.cand-card[data-beat="${{beatId}}"]`).forEach(c => c.classList.remove('selected'));
      el.classList.add('selected');
      selections[beatId] = candId;
      updateCommand();
    }}

    function updateCommand() {{
      const pairs = Object.entries(selections).map(([b, c]) => `${{b}}:${{c}}`).join(',');
      const cmd = `python scripts/nacci_cli.py approve --project "${{projectPath}}" --selections "${{pairs}}"`;
      document.getElementById('cmdOutput').textContent = cmd;
    }}

    function copyCommand() {{
      const text = document.getElementById('cmdOutput').textContent;
      navigator.clipboard.writeText(text);
      const btn = document.querySelector('.btn-approve');
      btn.textContent = "Copiado! Cole no Antigravity / Claude";
      setTimeout(() => btn.textContent = "Copiar Comando de Aprovação", 2500);
    }}

    initSelections();
  </script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Gera o Storyboard HTML interativo do projeto Nacci.Edit")
    parser.add_argument("--project", required=True, help="Caminho da pasta do projeto")
    parser.add_argument("--open", action="store_true", help="Abrir automaticamente no navegador padrão")
    args = parser.parse_args()

    project_dir = Path(args.project).resolve()
    pfile = project_dir / "project.json"
    if not pfile.exists():
        print(f"[ERRO] project.json não encontrado em {project_dir}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(pfile.read_text(encoding="utf-8"))
    out_file = project_dir / "03_BROLLS_PREVIEW" / "STORYBOARD.html"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(generate_html(project_dir, data), encoding="utf-8")

    data["stage"] = "storyboard-ready"
    pfile.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[SUCESSO] Storyboard interativo gerado em: {out_file}")
    if args.open:
        webbrowser.open(out_file.as_uri())


if __name__ == "__main__":
    main()
