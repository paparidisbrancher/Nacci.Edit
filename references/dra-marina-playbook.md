# Playbook de Edição da Agência: Dra. Marina (`dra-marina`)

Este guia define o padrão ouro da agência para editar os Reels, Shorts e vídeos educativos da **Dra. Marina**.

---

## 1. Como Usar as Referências do Instagram que a Dra. Marina Envia

A Dra. Marina costuma mandar links de Reels do Instagram que ela gostou. Sempre que ela mandar um link:

1. **Rode o analisador de referências do Nacci.Edit:**
   ```bash
   python scripts/nacci_cli.py ref-analyze --project "<PASTA_DO_PROJETO>" --url "<LINK_DO_REELS>" --notes "Referência enviada pela Dra. Marina"
   ```
2. **Inspecione os 6 frames extraídos (`frame_01.jpg` a `frame_06.jpg`):**
   - **O Gancho (0s a 3s):** Como o vídeo de referência prende a atenção? É um B-roll curioso, uma manchete de artigo científico no topo, ou um zoom rápido no rosto?
   - **Frequência de Cortes (ASL):** Veja no `ANALISE_REFERENCIA.md` quantos segundos dura cada plano em média. Replique essa mesma cadência nos Beats do roteiro da Dra. Marina!
   - **Posicionamento de Texto:** Onde ficam as legendas e os *lower-thirds* para não serem cobertos pelos botões do Instagram Reels?

---

## 2. Fórmulas de B-Roll para Vídeos Médicos (Alto Engajamento + Sobriedade)

Para posicionar a Dra. Marina como autoridade máxima sem parecer comercial barato:

| Momento do Vídeo | Tempo | Tipo de Beat | O que buscar no Nacci.Edit |
| :--- | :--- | :--- | :--- |
| **1. Gancho (Hook)** | `00:00 - 00:03` | `ilustrativo` ou `literal` | Cena altamente identificável da dor/sintoma (ex: `woman waking up tired morning cinematic`) em corte dinâmico, OU manchete real de estudo científico. |
| **2. Explicação / Mecanismo** | `00:03 - 00:15` | `literal` | Ilustração anatômica limpa, célula, molécula ou diagrama médico no **Wikimedia Commons** ou **Openverse** (ex: `human brain illustration clean`, `cortisol hormone diagram`). |
| **3. Prova Científica** | `00:15 - 00:25` | `literal` / `motion` | Print ou recorte de paper do PubMed / Nature / Lancet destacando o título do estudo com marca-texto dourado (`#D4AF37`). |
| **4. Humanização / Solução** | `00:25 - 00:40` | `ilustrativo` | Cenas estéticas de hábitos saudáveis, rotina matinal elegante, preparo de alimentos, sono reparador ou ambiente de consultório minimalista no **Pexels** / **Pixabay**. |
| **5. Fechamento / CTA** | Últimos 5s | `A-Roll Puro` | Voltar 100% para o rosto da Dra. Marina (olho no olho) gerando conexão e confiança, apenas com *lower-third* discreto contendo nome e CRM/RQE. |

---

## 3. Checklist de Compliance Médico (Resolução CFM nº 2.336/2023)

Antes de aprovar qualquer B-roll ou texto para a Dra. Marina, verifique:
- [x] **Sem sensacionalismo ou pânico:** Evitar B-rolls de cirurgias abertas com sangue, expressões exageradas de dor extrema ou imagens chocantes.
- [x] **Caráter educativo:** Todo B-roll literal de estudo científico deve ter a fonte registrada no `ORIGEM.md`.
- [x] **Identificação profissional:** Garantir espaço limpo no vídeo para o lower-third com `Dra. Marina | CRM-XX 00000 | RQE 00000`.
