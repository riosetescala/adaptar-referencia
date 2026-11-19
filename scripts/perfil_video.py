#!/usr/bin/env python
"""Mede o PERFIL DE EDIÇÃO de um vídeo (referência ou resultado).

Uso:  python perfil_video.py VIDEO.mp4 PASTA_SAIDA
Saída: PASTA_SAIDA/perfil.json   (métricas + lista de planos)
       PASTA_SAIDA/folha_broll.jpg (um quadro por plano B-roll, numerado, para OLHAR)

Mede: cortes (secos x graduais), A-roll x B-roll, tela dividida (empilhado),
escala e posição do rosto do apresentador (zoom e ponto focal).
Roda no Python do rea-video (tem cv2 e numpy):
  <python-do-rea-video> -I perfil_video.py ...
"""
import json, os, sys
import cv2
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np


def hist(f):
    h = cv2.calcHist([cv2.resize(f, (64, 114))], [0, 1, 2], None, [6, 6, 6], [0, 256] * 3)
    return cv2.normalize(h, h).flatten()


def diffs(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    d, prev = [0.0], None
    while True:
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(cv2.resize(f, (90, 160)), cv2.COLOR_BGR2GRAY).astype(np.float32)
        if prev is not None:
            d.append(float(np.abs(g - prev).mean()))
        prev = g
    return fps, np.array(d)


def achar_cortes(d):
    idx = []
    for i in range(1, len(d) - 1):
        viz = np.r_[d[max(0, i - 6):i], d[i + 1:i + 7]]
        if d[i] > 18 and d[i] >= d[i - 1] and d[i] >= d[i + 1] and d[i] > 3 * (viz.mean() + 1e-3):
            if not idx or i - idx[-1] >= 3:
                idx.append(i)
    return idx


def frame_em(cap, t):
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, f = cap.read()
    return f if ok else None


def empilhado(f):
    """PISTA de tela dividida (costura horizontal no centro + metades diferentes).
    Acerta ~77% na referência de calibração (~91% visual). NUNCA usar sozinho: confirmar olhando folha_broll.jpg."""
    g = cv2.cvtColor(cv2.resize(f, (216, 384)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    p = np.abs(np.diff(g, axis=0)).mean(axis=1)
    centro = p[184:200]
    faixa = p[120:264]
    base = np.percentile(p, 90) + 1e-3
    h2 = f.shape[0] // 2
    dif = cv2.compareHist(hist(f[:h2]), hist(f[h2:]), cv2.HISTCMP_CORREL)
    return bool(centro.max() >= faixa.max() * 0.999 and centro.max() > 2.0 * base and dif < 0.85)


def detector_rosto():
    m = os.path.expanduser("~/.cache/rea-video/models/face_detection_yunet_2023mar.onnx")
    if os.path.exists(m):
        det = cv2.FaceDetectorYN.create(m, "", (320, 320), 0.6)

        def f(img):
            h, w = img.shape[:2]
            det.setInputSize((w, h))
            _, r = det.detect(img)
            return [] if r is None else [tuple(map(float, x[:4])) for x in r]
        return f
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    def f(img):
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return [tuple(map(float, r)) for r in casc.detectMultiScale(g, 1.1, 5, minSize=(60, 60))]
    return f


def niveis(vals, gap=0.045):
    if not vals:
        return []
    v = sorted(vals)
    grupos, cur = [], [v[0]]
    for x in v[1:]:
        if x - cur[-1] > gap:
            grupos.append(cur); cur = [x]
        else:
            cur.append(x)
    grupos.append(cur)
    return [{"altura_rosto": round(float(np.mean(g)), 3), "planos": len(g)} for g in grupos if len(g) >= 2]


def main(video, saida):
    os.makedirs(saida, exist_ok=True)
    fps, d = diffs(video)
    n = len(d)
    idx = achar_cortes(d)
    b = [0] + idx + [n]
    planos = [{"i": k, "a": b[k] / fps, "e": b[k + 1] / fps} for k in range(len(b) - 1)]
    dur = n / fps
    cap = cv2.VideoCapture(video)
    H = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    hs = []
    for p in planos:
        f = frame_em(cap, (p["a"] + p["e"]) / 2)
        p["_f"] = f
        hs.append(hist(f) if f is not None else None)
        p["dur"] = p["e"] - p["a"]
    # A-roll = grupo(s) de aparência que cobre(m) mais tempo (apresentador falando). Cobertura gulosa, até 3 sementes.
    cobertos = set()
    sementes = []
    for _ in range(3):
        melhor, ganho = None, 0
        for j, hj in enumerate(hs):
            if hj is None or j in sementes:
                continue
            g = sum(planos[k]["dur"] for k, hk in enumerate(hs)
                    if hk is not None and k not in cobertos and cv2.compareHist(hj, hk, cv2.HISTCMP_CORREL) > 0.8)
            if g > ganho:
                melhor, ganho = j, g
        if melhor is None or ganho < 0.10 * dur:
            break
        sementes.append(melhor)
        for k, hk in enumerate(hs):
            if hk is not None and cv2.compareHist(hs[melhor], hk, cv2.HISTCMP_CORREL) > 0.8:
                cobertos.add(k)
    for k, p in enumerate(planos):
        p["tipo"] = "A" if k in cobertos else "B"
    # tela dividida + rosto
    achar_rosto = detector_rosto()
    for p in planos:
        f = p.pop("_f")
        if f is None:
            p["empilhado"] = False
            continue
        p["empilhado"] = empilhado(f)
        if p["tipo"] == "A":
            rs = [r for r in achar_rosto(f) if r[3] / H > 0.15]
            if rs:
                x, y, w, h = max(rs, key=lambda r: r[3])
                p["rosto"] = {"h": round(h / H, 3), "cx": round((x + w / 2) / f.shape[1], 3), "cy": round((y + h / 2) / H, 3)}
    A = [p for p in planos if p["tipo"] == "A"]
    B = [p for p in planos if p["tipo"] == "B"]
    rostos = [p["rosto"] for p in A if "rosto" in p]
    perfil = {
        "video": os.path.basename(video), "duracao": round(dur, 2), "fps": round(fps, 3),
        "n_planos": len(planos), "n_cortes": len(idx), "cortes_por_min": round(len(idx) / dur * 60, 1),
        "cortes_secos": len(idx),  # só detectamos corte de 1 quadro; transição gradual não vira corte
        "A_n": len(A), "A_media_s": round(float(np.mean([p["dur"] for p in A])), 2) if A else None,
        "A_min_s": round(min(p["dur"] for p in A), 2) if A else None,
        "A_max_s": round(max(p["dur"] for p in A), 2) if A else None,
        "B_n": len(B), "B_media_s": round(float(np.mean([p["dur"] for p in B])), 2) if B else None,
        "B_parcela_tempo": round(sum(p["dur"] for p in B) / dur, 3),
        "B_empilhado_parcela": round(sum(p["empilhado"] for p in B) / len(B), 3) if B else None,
        "rosto_h_p10_p50_p90": [round(float(np.percentile([r["h"] for r in rostos], q)), 3) for q in (10, 50, 90)] if rostos else None,
        "rosto_cx_p5_p95": [round(float(np.percentile([r["cx"] for r in rostos], 5)), 3), round(float(np.percentile([r["cx"] for r in rostos], 95)), 3)] if rostos else None,
        "rosto_cy_p5_p95": [round(float(np.percentile([r["cy"] for r in rostos], 5)), 3), round(float(np.percentile([r["cy"] for r in rostos], 95)), 3)] if rostos else None,
        "planos": [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in p.items()} for p in planos],
    }
    json.dump(perfil, open(os.path.join(saida, "perfil.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # folha de B-roll numerada, para OLHAR (nunca confiar só no número)
    tiles = []
    for p in B:
        f = frame_em(cap, (p["a"] + p["e"]) / 2)
        if f is None:
            continue
        t = cv2.resize(f, (216, 384))
        cv2.rectangle(t, (0, 0), (110, 22), (0, 0, 0), -1)
        cv2.putText(t, f'#{p["i"]} {"E" if p["empilhado"] else "1"}', (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        tiles.append(t)
    if tiles:
        while len(tiles) % 8:
            tiles.append(np.zeros_like(tiles[0]))
        rows = [np.hstack(tiles[i:i + 8]) for i in range(0, len(tiles), 8)]
        cv2.imwrite(os.path.join(saida, "folha_broll.jpg"), np.vstack(rows[:2]))
        if len(rows) > 2:
            cv2.imwrite(os.path.join(saida, "folha_broll_2.jpg"), np.vstack(rows[2:4]))
    resumo = {k: v for k, v in perfil.items() if k != "planos"}
    print(json.dumps(resumo, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
