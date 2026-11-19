#!/usr/bin/env python
"""Acha TEXTO LEGÍVEL (marca, modelo, placa, logotipo escrito) em clipes de B-roll ou no vídeo final.

Uso:
  rea-python -X utf8 -I texto_em_broll.py VIDEO [--passo 0.5] [--regiao 0:0.45] [--min-conf 0.6] [--min-letras 3]
  --grande P      texto com altura >= P% do quadro reprova (padrão 2,0); abaixo disso é só aviso
  --regiao Y0:Y1  fração da altura a analisar (ex.: 0:0.45 = metade de cima da tela dividida, longe da legenda)
Sai com código 1 se encontrar texto. Use:
  1) em cada clipe baixado, ANTES de montar (região inteira);
  2) no vídeo final, só nas metades de B-roll (--regiao 0:0.45), porque a legenda fica na emenda e no peito.
Origem: no reel @perfil-exemplo apareceram "E-TENSE" e "DS AUTOMOBILES" legíveis em clipes de carro; só peguei olhando.
Limite: OCR perde texto pequeno/borrado e acusa letreiro genérico (placa, monitor): confirme cada achado olhando o quadro.
"""
import re, sys
import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

sys.stdout.reconfigure(encoding="utf-8")


def arg(nome, padrao, tipo=float):
    a = sys.argv
    return tipo(a[a.index(nome) + 1]) if nome in a else padrao


def main():
    video = sys.argv[1]
    passo = arg("--passo", 0.5)
    y0, y1 = [float(x) for x in (sys.argv[sys.argv.index("--regiao") + 1] if "--regiao" in sys.argv else "0:1").split(":")]
    min_conf = arg("--min-conf", 0.6)
    min_letras = int(arg("--min-letras", 3))
    ocr = RapidOCR()
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    dur = n / fps
    achados = []
    t = 0.0
    while t < dur:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = cap.read()
        if not ok:
            break
        h = f.shape[0]
        reg = f[int(h * y0):int(h * y1)]
        if reg.shape[1] > 1000:  # acelera: no máx. ~1000 px de largura
            reg = cv2.resize(reg, (1000, int(reg.shape[0] * 1000 / reg.shape[1])))
        res, _ = ocr(reg)
        for caixa, txt, conf in (res or []):
            if float(conf) >= min_conf and len(re.findall(r"[A-Za-zÀ-ÿ]", txt)) >= min_letras:
                ys = [p[1] for p in caixa]
                alt = (max(ys) - min(ys)) / reg.shape[0] * (y1 - y0)   # altura do texto, fração do quadro inteiro
                achados.append((round(t, 1), txt, round(float(conf), 2), round(alt * 100, 1)))
        t += passo
    grande = arg("--grande", 2.0)  # % da altura do quadro a partir da qual o texto é "grande"
    print(f"{video}: {len(achados)} texto(s) detectado(s) em {dur:.1f} s (a cada {passo} s, região {y0}–{y1})")
    for tt, txt, c, alt in achados:
        print(f"  {tt:6.1f}s  {txt!r}  conf {c}  altura {alt}%  {'GRANDE' if alt >= grande else 'pequeno'}")
    gr = [a for a in achados if a[3] >= grande]
    if gr:
        print(f"REPROVADO: {len(gr)} texto(s) GRANDE(S) (>= {grande}% da altura). Troque o trecho do clipe se for marca/modelo.")
    elif achados:
        print("AVISO: só texto pequeno/incidental. Olhe os quadros e decida (selo, banner, valor em outra moeda).")
    else:
        print("OK: nenhum texto detectado (OCR perde texto muito pequeno ou borrado; confirme visualmente).")
    sys.exit(1 if gr else 0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main()
