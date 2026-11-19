#!/usr/bin/env python
"""Transcreve a fala de um vídeo em português com tempo por palavra (Whisper local, sem custo).

Uso: uv run --python 3.12 --with faster-whisper python transcrever.py VIDEO.mp4 SAIDA.json
Saída: lista [[inicio, fim, palavra], ...]
Notas:
- Decodifica o áudio com ffmpeg e entrega a matriz ao Whisper. Isso evita um bug do pacote `av`
  no Windows (TypeError: open() got an unexpected keyword argument 'metadata_errors').
- Modelo 'small' (~480 MB, baixado na 1ª vez para ~/.cache/huggingface). PEDIR OK ao usuário antes
  da primeira vez. Erra números e siglas (ex.: "terceiro trimestre" saiu "T7", "zero" saiu "A0"):
  conferir de ouvido o que for virar legenda.
"""
import json, subprocess, sys, tempfile, os
import numpy as np
from faster_whisper import WhisperModel

video, saida = sys.argv[1], sys.argv[2]
wav = os.path.join(tempfile.mkdtemp(), "a.wav")
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
au = np.frombuffer(open(wav, "rb").read()[44:], dtype=np.int16).astype(np.float32) / 32768.0
segs, _ = WhisperModel("small", device="cpu", compute_type="int8").transcribe(au, language="pt", word_timestamps=True)
palavras = [[round(w.start, 2), round(w.end, 2), w.word.strip()] for s in segs for w in s.words]
json.dump(palavras, open(saida, "w", encoding="utf-8"), ensure_ascii=False)
print(len(palavras), "palavras ->", saida)
