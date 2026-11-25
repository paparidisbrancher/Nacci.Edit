# 🎬 Nacci.Edit — Open-Source AI Video Editing & Media Agency Suite

> **Suite open-source de edição de vídeos, curadoria de mídia de apoio, análise de referências e automação de timeline para agências de marketing e criadores.**  
> Compatível nativamente com **Google Antigravity** e **Claude Code**.

---

## ✨ Principais Recursos

* **Mapeamento Editorial de Beats (`literal`, `ilustrativo`, `motion`)**: Estrutura roteiros e transcrições em blocos visuais cronológicos alinhados à identidade de cada cliente.
* **Busca Multi-Fonte Nativa (6 Provedores Gratuitos)**: Integração direta com **Pexels**, **Pixabay**, **Wikimedia Commons**, **Openverse**, **NASA Media** e **YouTube (`yt-dlp`)**.
* **Storyboard HTML Interativo**: Painel visual no navegador para pré-visualizar candidatos lado a lado e aprovar cada trecho com 1 clique.
* **Trava Editorial e Auditoria de Direitos (`ORIGEM.md`)**: Nenhum arquivo entra na edição final sem aprovação humana e registro automático de fonte, autor e licença.
* **Perfis de Clientes de Agência (`clients/`)**: Configuração individual de *Brand Kit* (paleta de cores, tipografia, ritmo de cortes e regras de compliance do nicho).
* **Engenharia Reversa de Referências (Reels / TikTok / Shorts)**: Download de vídeos de referência via `yt-dlp`, detecção automática de frequência de cortes (ASL) via `ffmpeg` e extração de frames para análise visual pela IA.
* **Cirurgia Local via FFmpeg**: Corte automático de silêncios (*dead air*), normalização de áudio para `-14 LUFS`, reenquadramento `9:16` e *overlay* de vídeo.
* **Exportação de Timeline XML**: Geração de arquivo `.xml` (`xmeml`) pronto para importar a timeline montada no **Adobe Premiere Pro**, **DaVinci Resolve** ou **CapCut**.

---

## 📁 Arquitetura do Repositório

```text
nacci-edit/
├── SKILL.md                        # Instruções principais do Agente (Antigravity & Claude Code)
├── install.ps1                     # Instalador automático (Windows PowerShell)
├── .env.example                    # Configuração opcional de chaves gratuitas (Pexels/Pixabay)
├── clients/                        # Perfis de Clientes da Agência (Brand Kits & Guardrails)
│   ├── dra-marina.yaml             # Perfil completo da Dra. Marina (Medicina + Regras CFM)
│   └── _template.yaml              # Template para cadastrar novos clientes da agência
├── references/                     # Playbooks avançados carregados sob demanda pelo Agente
│   ├── dra-marina-playbook.md      # Guia de edição médica e engenharia reversa de Reels
│   └── motion-remotion-guide.md    # Guia para B-rolls animados em código (HTML/FFmpeg/Remotion)
└── scripts/                        # Motor Python (Zero dependências externas de Python!)
    ├── nacci_cli.py                # CLI principal: setup, status, ref-analyze, add-beat, search, approve
    ├── storyboard_gen.py           # Gerador do painel visual interativo STORYBOARD.html
    ├── ffmpeg_tools.py             # Cirurgia de vídeo: cut-silence, normalize-audio, reframe-9x16, overlay
    └── xml_exporter.py             # Exportador de timeline XML para Premiere Pro e DaVinci Resolve
```

---

## 🚀 Como Instalar (Passo a Passo)

### 1. Pré-requisitos Gratuitos na Máquina
O motor do **Nacci.Edit** foi escrito em **Python puro (Standard Library)** — você não precisa instalar dezenas de pacotes quebrados!  
Para destravar o download de referências do Instagram/YouTube e os cortes locais de vídeo, tenha instalados:
* **Python 3.9+**
* **FFmpeg** (No Windows, rode no terminal: `winget install Gyan.FFmpeg`)
* **yt-dlp** (No Windows, rode no terminal: `pip install yt-dlp` ou `winget install yt-dlp.yt-dlp`)

### 2. Rodar o Instalador Automático (Antigravity + Claude Code)
Abra o PowerShell na pasta do `nacci-edit` e execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Isso instala e sincroniza automaticamente a skill nos dois ambientes:
* **Antigravity:** `C:\Users\<seu-usuario>\.gemini\config\skills\nacci-edit\`
* **Claude Code:** `C:\Users\<seu-usuario>\.claude\skills\nacci-edit\`

### 3. (Opcional) Configurar Chaves Gratuitas do Pexels e Pixabay
> **Nota:** Wikimedia Commons, Openverse, NASA e YouTube (`yt-dlp`) funcionam **imediatamente sem nenhuma chave de API**!

Para adicionar milhares de vídeos verticais 9:16 de cinema do Pexels e Pixabay:
1. Copie o arquivo `.env.example` para `.env`
2. Crie uma chave gratuita em 30 segundos em [pexels.com/api](https://www.pexels.com/api/) e [pixabay.com/api/docs](https://pixabay.com/api/docs/) e cole no seu `.env`.

---

## 🩺 Como Usar na Prática (Exemplo Real: Cliente Dra. Marina)

Você pode usar o **Nacci.Edit** apenas conversando em português com o **Antigravity** ou **Claude Code**, ou rodando os comandos diretamente:

### Passo 1: Criar a Pasta do Vídeo da Dra. Marina
Peça no chat:
> *"Nacci, cria um novo projeto para a Dra. Marina chamado `reel-fadiga-cronica`."*

Ou via terminal:
```bash
python scripts/nacci_cli.py setup --project "projetos/dra-marina-fadiga" --client "dra-marina" --title "Fadiga Crônica e Cortisol"
```
O Nacci.Edit cria automaticamente:
* `01_RAW/` (Coloque aqui o vídeo bruto que a Dra. Marina gravou)
* `02_REFS_INSTAGRAM/` (Para salvar e dissecar os Reels de referência que ela mandou)
* `03_BROLLS_PREVIEW/` (Onde nasce o `STORYBOARD.html`)
* `04_BROLLS_APPROVED/` (Onde caem apenas os B-rolls aprovados por você)
* `05_EXPORTS/` (Onde saem o vídeo limpo e a timeline `.xml` para o Premiere/DaVinci)
* `ROTEIRO.md` e `ORIGEM.md`

---

### Passo 2: Analisar um Reels de Referência que a Dra. Marina Mandou no Instagram
Quando a Dra. Marina mandar um link de Reels dizendo *"Quero um vídeo nesse estilo"*, peça no chat:
> *"Analisa essa referência do Instagram que a Dra. Marina mandou: https://www.instagram.com/reel/XXXXX/"*

O Nacci.Edit roda `ref-analyze`, baixa a referência, conta quantos cortes existem via FFmpeg, calcula o **ASL (Tempo Médio por Corte)**, extrai 6 frames do vídeo e o agente analisa visualmente as imagens para replicar a estrutura de gancho e ritmo!

---

### Passo 3: Mapear os Beats do Roteiro e Buscar os B-Rolls
Cole o roteiro ou a transcrição do vídeo da Dra. Marina no chat:
> *"Aqui está o roteiro da Dra. Marina. Quebre nos beats seguindo o perfil dela e busque os B-rolls."*

O agente vai cadastrar cada Beat (`B01`, `B02`, `B03`...), varrer as fontes gratuitas e gerar o painel visual:
* Abra `03_BROLLS_PREVIEW/STORYBOARD.html` no seu navegador!

---

### Passo 4: Revisar no Storyboard Interativo e Aprovar (Trava Editorial)
No `STORYBOARD.html` aberto no navegador:
1. Assista às prévias dos candidatos lado a lado para cada frase da Dra. Marina.
2. Clique no card do seu B-roll favorito em cada Beat.
3. Clique no botão verde **"Copiar Comando de Aprovação"** na barra inferior e cole aqui no chat (ou no terminal).

O Nacci.Edit baixa os arquivos aprovados em alta resolução para `04_BROLLS_APPROVED/` e preenche automaticamente a tabela de auditoria de direitos autorais em **`ORIGEM.md`**.

---

### Passo 5: Limpar Silêncios do Bruto e Exportar Timeline XML (Premiere / DaVinci / CapCut)
Peça ao agente:
> *"Limpa os silêncios do bruto da Dra. Marina em `01_RAW/`, normaliza o áudio para -14 LUFS e exporta o XML da timeline com os B-rolls aprovados."*

Depois, basta abrir o **Premiere Pro** ou **DaVinci Resolve**, clicar em `File > Import > Timeline` e selecionar `05_EXPORTS/timeline_premiere_davinci.xml`:
* **Track V1:** Vídeo principal da Dra. Marina
* **Track V2:** Todos os B-rolls aprovados já posicionados exatamente nos segundos certos de cada fala!

---

## 🌐 Como Publicar este Repositório no seu GitHub

Esta pasta já foi inicializada com Git. Para subir para o seu GitHub como **`Nacci.Edit`**:

```bash
cd C:\Users\erick\.gemini\antigravity\scratch\nacci-edit
git add .
git commit -m "feat: initial release of Nacci.Edit open-source video editing & B-roll skill"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/Nacci.Edit.git
git push -u origin main
```
