---
name: nacci-edit
description: >-
  Suite completa e open-source de edição de vídeos, busca inteligente de B-Rolls,
  análise de referências do Instagram/Reels, storyboard interativo com travas de aprovação,
  rastreabilidade de direitos (ORIGEM.md), cirurgia de vídeo via FFmpeg e exportação de
  timeline XML (Premiere/DaVinci/CapCut) para agências de marketing. Ative sempre que o
  usuário pedir para editar vídeos, buscar B-rolls, analisar referências de Reels, atender
  clientes da agência (como a Dra. Marina) ou executar comandos do Nacci.Edit.
---

# Nacci.Edit — AI Video Editing & B-Roll Agency Suite

Você está operando o **Nacci.Edit**, a skill open-source definitiva de engenharia e edição de vídeos para agências de marketing (compatível com **Antigravity** e **Claude Code**).

> **Localização base dos scripts e perfis desta skill:**
> Sempre que precisar rodar os scripts Python desta skill, localize a pasta onde este `SKILL.md` está instalado (ex: `~/.gemini/config/skills/nacci-edit` ou `~/.claude/skills/nacci-edit`). Na primeira vez numa máquina, rode `python "<SKILL_DIR>/scripts/nacci_cli.py" doctor` para ver o que falta instalar.

---

## 1. Filosofia Editorial e Travas Obrigatórias

O **Nacci.Edit** NUNCA joga arquivos aleatórios na timeline sem curadoria. Ele segue um fluxo editorial de 6 etapas com **trava humana obrigatória**:

1. **`setup` (Estruturação por Projeto/Cliente):** Cada vídeo tem sua própria pasta isolada com `01_RAW`, `02_REFS_INSTAGRAM`, `03_BROLLS_PREVIEW`, `04_BROLLS_APPROVED`, `05_EXPORTS`, `project.json`, `ROTEIRO.md` e `ORIGEM.md`.
2. **`ref-analyze` (Engenharia Reversa de Referências do Instagram):** Quando a cliente (ex: **Dra. Marina**) envia links de Reels/TikToks como referência, baixamos o vídeo via `yt-dlp`, detectamos a frequência exata de cortes (ASL) via `ffmpeg`, extraímos frames e usamos `read_file` nas imagens para dissecar o gancho visual, estilo de legenda e proporção de B-rolls.
3. **`brief` (Mapeamento de Beats):** Se há vídeo bruto, rode antes o `transcribe` (seção 3.G): o agente **lê** o vídeo pela transcrição com o tempo de cada palavra, e não precisa assistir quadro a quadro. Lemos o `ROTEIRO.md` (ou a transcrição do A-Roll) mais o perfil YAML do cliente (`clients/<cliente>.yaml`) e quebramos o vídeo em **Beats** cronológicos (`B01`, `B02`...), classificando cada beat como:
   - **`literal`**: Fato, estudo científico (PubMed/Nature), notícia, pessoa, produto ou diagrama anatômico real.
   - **`ilustrativo`**: Cena estética/cinemática de apoio (rotina, consultório, bem-estar, emoção).
   - **`motion`**: Card animado, manchete destacada, gráfico ou lower-third.
4. **`search` & `storyboard` (Varredura Multi-Fonte e Painel Visual):** Varremos até 6 provedores nativos gratuitos (**Pexels, Pixabay, Wikimedia Commons, Openverse, NASA e YouTube via `yt-dlp`**) e geramos o `03_BROLLS_PREVIEW/STORYBOARD.html`.
5. **`approve` (TRAVA HUMANA E DIREITOS AUTORAIS):** **NENHUM B-roll vai para a pasta final sem aprovação do usuário.** Após o usuário escolher os candidatos (no `STORYBOARD.html` ou no chat), rodamos `nacci_cli.py approve`, que baixa o corte em alta definição para `04_BROLLS_APPROVED/` e registra a auditoria completa de licença e autoria em **`ORIGEM.md`**.
6. **`edit` & `export-xml` (Cirurgia FFmpeg e Timeline Pronta):** Cortamos silêncios do bruto, normalizamos áudio a `-14 LUFS`, aplicamos B-rolls ou exportamos o arquivo `05_EXPORTS/timeline_premiere_davinci.xml` para abrir a timeline já montada no **Premiere Pro**, **DaVinci Resolve** ou **CapCut**.
7. **`check` (Autoverificação antes de entregar):** Todo arquivo final passa pelo `check` (seção 3.G) e o agente **abre a folha de contato e olha** cada quadro. Se algo falhar (resolução, volume, tela preta, legenda escondida, B-roll errado), corrige e confere de novo, no máximo 3 vezes, antes de mostrar ao usuário.

### Regras de produção (não negociáveis)

1. **O bruto é sagrado.** Nunca grave por cima do arquivo de entrada; as ferramentas recusam. Arquivo de saída existente só com `--overwrite`.
2. **Estratégia antes do corte.** Proponha o plano (beats, ritmo, B-rolls, legenda) e espere o "ok" antes de cortar ou renderizar.
3. **Corte na fala, não no meio da palavra.** Use os tempos da transcrição; os cortes de silêncio já levam 30 ms de fade no áudio para não estalar.
4. **Uma transcrição por arquivo.** Depois de `cut-silence` os tempos mudam: transcreva de novo o arquivo cortado antes de legendar ou posicionar B-roll.
5. **B-roll mudo e na palavra.** O áudio é sempre o da cliente. O B-roll entra logo depois da palavra que ele ilustra, nunca antes.
6. **Não diga "pronto" sem o `check`.**

### Como escolher B-roll (método do b-roll-finder)

1. **Entenda o vídeo inteiro antes de buscar.** Escreva a tese em uma frase.
2. **Para cada beat, escreva uma frase: "do que esta fala realmente trata?"** e busque isso, não a palavra mais próxima. Se nada ilustra com precisão, **descarte o beat**: melhor sem B-roll do que com B-roll errado.
3. **Prefira B-roll objetivo**, aquele que tem resposta certa: o paper real (PubMed/DOI) com a fonte visível, a manchete, o produto, o diagrama. Cena de banco de imagens fica para beats de emoção e rotina.
4. **Ritmo concentrado no gancho:** denso nos 3 primeiros segundos, depois espaçado e preciso.
5. **Confira cada candidato:** marca d'água, texto queimado, cara de IA, licença. O que não passa nem chega ao storyboard.
6. **O agente não faz a escolha final de gosto:** apresenta poucos candidatos bons e o usuário escolhe.

---

## 2. Perfis de Clientes da Agência (`clients/`)

Antes de planejar qualquer edição ou buscar B-rolls, **SEMPRE leia o arquivo do cliente** em `clients/<client-id>.yaml`:
- **Cliente Padrão / Primeira Cliente:** **Dra. Marina** (`clients/dra-marina.yaml` e guia detalhado em `references/dra-marina-playbook.md`).
  - Se o usuário mencionar "Dra. Marina", "vídeo da doutora", ou não especificar outro cliente, carregue automaticamente as diretrizes de `clients/dra-marina.yaml` (estética médica elegante, verde petróleo `#1E3A3A` + dourado `#D4AF37`, respeito à Resolução CFM nº 2.336/2023, sem imagens apelativas/gore).

---

## 3. Comandos e Ferramentas CLI do Nacci.Edit

Execute estes comandos via terminal (`run_command` / Bash) apontando para a pasta do `nacci-edit`:

### A. Inicializar um Projeto de Vídeo (`setup`)
```bash
python "<SKILL_DIR>/scripts/nacci_cli.py" setup --project "<PASTA_DO_PROJETO>" --client "dra-marina" --title "Titulo do Reels" --aspect "9:16"
```

### B. Checar Status e Próximo Passo (`status`)
```bash
python "<SKILL_DIR>/scripts/nacci_cli.py" status --project "<PASTA_DO_PROJETO>"
```

### C. Analisar Referência do Instagram / TikTok Enviada pela Cliente (`ref-analyze`)
```bash
python "<SKILL_DIR>/scripts/nacci_cli.py" ref-analyze --project "<PASTA_DO_PROJETO>" --url "<URL_DO_REELS>" --notes "Referência enviada pela Dra. Marina"
```
> **Ação obrigatória do Agente após rodar `ref-analyze`:** Use a ferramenta `read_file` para abrir o arquivo `02_REFS_INSTAGRAM/REF_01/ANALISE_REFERENCIA.md` e inspecionar visualmente os frames extraídos (`frame_01.jpg` a `frame_06.jpg`)! Descreva para o usuário o ritmo de cortes (ASL), o tipo de gancho nos primeiros 3s e o estilo visual da referência.

### D. Cadastrar Beats do Roteiro (`add-beat`)
Para cada trecho do `ROTEIRO.md` que pede apoio visual, cadastre o beat (prefira queries em inglês para Pexels/Wikimedia/Pixabay para obter 10x mais resultados cinemáticos, ou em português para buscas locais no YouTube):
```bash
python "<SKILL_DIR>/scripts/nacci_cli.py" add-beat \
  --project "<PASTA_DO_PROJETO>" \
  --id "B01" \
  --time-start "00:00" \
  --time-end "00:03" \
  --type "ilustrativo" \
  --speech "Você acorda cansada mesmo dormindo 8 horas por noite?" \
  --query "tired woman waking up morning cinematic vertical" \
  --notes "Gancho rápido de identificação nos primeiros 3 segundos"
```

### E. Buscar Candidatos de B-Roll e Gerar Storyboard (`search` + `storyboard_gen`)
```bash
python "<SKILL_DIR>/scripts/nacci_cli.py" search --project "<PASTA_DO_PROJETO>" --limit 3
python "<SKILL_DIR>/scripts/storyboard_gen.py" --project "<PASTA_DO_PROJETO>"
```
> **TRAVA DE REVISÃO:** Após gerar o `STORYBOARD.html`, apresente ao usuário um resumo dos candidatos encontrados para cada Beat (ou peça para ele abrir `03_BROLLS_PREVIEW/STORYBOARD.html` no navegador) e **pergunte quais candidatos ele aprova** antes de rodar o comando `approve`!

### F. Aprovar B-Rolls e Auditar Direitos em `ORIGEM.md` (`approve`)
Quando o usuário aprovar (ex: `B01:B01_C1,B02:B02_C2`), execute:
```bash
python "<SKILL_DIR>/scripts/nacci_cli.py" approve --project "<PASTA_DO_PROJETO>" --selections "B01:B01_C1,B02:B02_C2"
```

### G. Cirurgia Local de Vídeo com FFmpeg (`ffmpeg_tools.py`)
Quando o usuário tiver um arquivo de vídeo bruto em `01_RAW/`:
1. **Cortar silêncios e pausas automaticamente:**
   ```bash
   python "<SKILL_DIR>/scripts/ffmpeg_tools.py" cut-silence --input "01_RAW/bruto.mp4" --output "05_EXPORTS/01_sem_silencio.mp4"
   ```
2. **Normalizar áudio a -14 LUFS (Padrão Reels/TikTok):**
   ```bash
   python "<SKILL_DIR>/scripts/ffmpeg_tools.py" normalize-audio --input "05_EXPORTS/01_sem_silencio.mp4" --output "05_EXPORTS/02_audio_normalizado.mp4"
   ```
3. **Converter B-Roll horizontal (16:9) para vertical (9:16) com crop ou fundo desfocado:**
   ```bash
   python "<SKILL_DIR>/scripts/ffmpeg_tools.py" reframe-9x16 --input "broll.mp4" --output "broll_9x16.mp4" --mode "blur"
   ```
4. **Inserir B-Roll sobre o A-Roll mantendo a voz da cliente:**
   ```bash
   python "<SKILL_DIR>/scripts/ffmpeg_tools.py" overlay-broll --aroll "05_EXPORTS/02_audio_normalizado.mp4" --broll "04_BROLLS_APPROVED/B01_clip.mp4" --start 0.0 --end 3.0 --output "05_EXPORTS/03_com_broll.mp4"
   ```
5. **Transcrever com o tempo de cada palavra (local, faster-whisper):** gera `<arquivo>.transcricao.json` (para as ferramentas) e `<arquivo>.transcricao.md` (frases com tempo, para o agente ler). Use os tempos para os `--time-start`/`--time-end` dos beats (aceitam segundos, ex. `3.52`).
   ```bash
   python "<SKILL_DIR>/scripts/ffmpeg_tools.py" transcribe --input "05_EXPORTS/02_audio_normalizado.mp4"
   ```
6. **Legendas animadas palavra a palavra** (palavra falada na cor `secondary` do cliente, acima da área dos botões do Reels; também salva `.ass` e `.srt` para ajustar no CapCut/Premiere). Passe `--font` com a fonte do cliente se estiver instalada; `--upper` e `--words 2` para o estilo mais agressivo:
   ```bash
   python "<SKILL_DIR>/scripts/ffmpeg_tools.py" captions --input "05_EXPORTS/03_com_broll.mp4" --transcript "05_EXPORTS/02_audio_normalizado.transcricao.json" --client "dra-marina" --output "05_EXPORTS/04_legendado.mp4"
   ```
7. **Conferir o arquivo final** (resolução, fps, codec, LUFS, pico, tela preta e folha de contato). Passe em `--times` os segundos de cada corte e de cada B-roll, e **abra a imagem gerada** antes de entregar:
   ```bash
   python "<SKILL_DIR>/scripts/ffmpeg_tools.py" check --input "05_EXPORTS/04_legendado.mp4" --platform reels --times "0.5,3.2,8.0"
   ```

> Nenhuma ferramenta grava por cima do arquivo de entrada, e saída que já existe só é substituída com `--overwrite`.

### H. Exportar Timeline Pronta em XML para Premiere Pro / DaVinci Resolve / CapCut (`xml_exporter.py`)
```bash
python "<SKILL_DIR>/scripts/xml_exporter.py" --project "<PASTA_DO_PROJETO>"
```

---

## 4. Atalhos de Comandos no Chat (Comportamento do Agente)

O usuário pode acionar você com linguagem natural ou usando comandos rápidos estilo slash:
- `/nacci-edit` ou *"Nacci, inicia um vídeo novo para a Dra. Marina"* -> Rode `setup` + carregue `clients/dra-marina.yaml`.
- `/nacci-ref <url>` ou *"A Dra. Marina mandou esse Reels de referência: <url>"* -> Rode `ref-analyze`, inspecione os frames extraídos e explique a estrutura do vídeo.
- `/nacci-brief` ou *"Aqui está o roteiro da Dra. Marina, monta os beats e busca os B-rolls"* -> Salve no `ROTEIRO.md`, cadastre todos os beats com `add-beat`, rode `search` e gere o `STORYBOARD.html`.
- `/nacci-approve` ou *"Aprova o C1 pro B01 e o C2 pro B02"* -> Rode `approve`, gere o `ORIGEM.md` e exporte o XML da timeline com `xml_exporter.py`.
- `/nacci-legenda` ou *"Legenda o vídeo da Dra. Marina"* -> Rode `transcribe` no arquivo cortado, `captions` com `--client` e `check`; abra a folha de contato.
