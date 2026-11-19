# adaptar-referencia

Skill do Claude Code: edita o vídeo bruto do usuário no estilo de um vídeo de referência, com engenharia reversa medida da referência e portão de fidelidade antes de entregar. Complementa a skill `rea-video`.

## Instalação

```bash
git clone https://github.com/riosetescala/adaptar-referencia ~/.claude/skills/adaptar-referencia
```

Uso: `/adaptar-referencia` (ou peça "edite meu bruto no estilo desta referência"). Fluxo completo em `SKILL.md`.

## Requisitos
- Python com OpenCV, YuNet e rapidocr (o ambiente da skill `rea-video` já serve); ffmpeg; faster-whisper para transcrição.
- Ajuste o caminho do Python em `SKILL.md` (`<python-do-rea-video>`).
- Tolerâncias do portão são provisórias (1 referência). Use `scripts/calibrar.py` com 3 ou mais referências do mesmo estilo.
