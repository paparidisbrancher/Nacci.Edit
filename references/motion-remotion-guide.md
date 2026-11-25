# Guia de B-Rolls em Motion Graphics & Remotion (Nacci.Edit)

Quando um Beat do roteiro for classificado como `--type motion` (ex: destacar a manchete de um artigo científico citado pela Dra. Marina, mostrar 3 sintomas na tela, ou animar um número/estatística), o agente pode gerar o insert visual diretamente em código!

## Opção 1: Card Editorial / Artigo Científico via HTML + FFmpeg (Ultra Rápido)

Se você não quiser subir um projeto React/Remotion pesado para um insert de 4 segundos:
1. Gere um arquivo HTML/CSS (1080x1920) com a paleta da cliente (ex: fundo `#1E3A3A`, destaque dourado `#D4AF37`, fonte `Playfair Display` + `Inter`).
2. Capture ou renderize em vídeo `.mp4` com zoom suave (*Ken Burns effect*) via FFmpeg:
   ```bash
   ffmpeg -y -loop 1 -i card_estudo.png -vf "scale=1200:-1,zoompan=z='min(zoom+0.0008,1.12)':d=120:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30" -t 4 -c:v libx264 -pix_fmt yuv420p 04_BROLLS_APPROVED/B02_motion_estudo.mp4
   ```

## Opção 2: Composição Remotion (React + TypeScript)

Para animações mais complexas (gráficos animados, cursores clicando, texto cinético):
- Use `useCurrentFrame()` e `spring({ frame, fps, config: { damping: 14, stiffness: 120 } })` para movimentos suaves e naturais.
- Salve a renderização final diretamente em `04_BROLLS_APPROVED/<BEAT_ID>_motion_<slug>.mp4` e registre no `ORIGEM.md` como `MOTION_INTERNO (Nacci.Edit)`.
