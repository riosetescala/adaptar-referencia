#!/usr/bin/env python
"""Rastreia o rosto do apresentador no bruto (10 quadros/s) para o recorte SEGUIR o ponto focal.

Uso: <python-do-rea-video> -X utf8 -I rastrear_rosto.py BRUTO.mov rosto.json
Saída: [[t, cx, cy, h], ...] normalizados (cx pela largura; cy e h pela altura do quadro já girado).
Motivo: no reel @perfil-exemplo o apresentador sentava à direita do centro (x 0,50–0,64); recorte centrado
fixo deixava o rosto fora do ponto focal. ffmpeg aplica a rotação do .MOV (o quadro sai em pé).
"""
import json, os, subprocess, sys
import cv2
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
W, H, FPS = 540, 960, 10


def main(video, saida):
    p = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", video, "-vf", f"fps={FPS},scale={W}:{H}",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    m = os.path.expanduser("~/.cache/rea-video/models/face_detection_yunet_2023mar.onnx")
    if not os.path.exists(m):
        sys.exit("modelo yunet não encontrado em ~/.cache/rea-video/models (rode o rea-video uma vez ou peça OK para baixar)")
    det = cv2.FaceDetectorYN.create(m, "", (W, H), 0.6)
    out, i = [], 0
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        _, r = det.detect(np.frombuffer(b, np.uint8).reshape(H, W, 3))
        if r is not None and len(r):
            x, y, w, h = max(r, key=lambda z: z[3])[:4]
            out.append([round(i / FPS, 2), float((x + w / 2) / W), float((y + h / 2) / H), float(h / H)])
        i += 1
    json.dump(out, open(saida, "w"))
    hs = [o[3] for o in out]
    print(f"quadros {i}, com rosto {len(out)} ({len(out) / max(i, 1) * 100:.0f}%)")
    if hs:
        print("altura do rosto: p10 %.3f p50 %.3f p90 %.3f" % tuple(np.percentile(hs, [10, 50, 90])))
        print("centro x p5–p95: %.3f–%.3f | centro y p5–p95: %.3f–%.3f" % (
            np.percentile([o[1] for o in out], 5), np.percentile([o[1] for o in out], 95),
            np.percentile([o[2] for o in out], 5), np.percentile([o[2] for o in out], 95)))
    if len(out) < 0.8 * i:
        print("AVISO: rosto perdido em mais de 20% dos quadros; o recorte pode oscilar. Confira antes de montar.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
