#!/usr/bin/env python
"""MONTAGEM reutilizável: bruto + B-roll em tela dividida + legenda, guiada por um config JSON.

Uso:  py -X utf8 -I montar.py config.json [--planejar]
  --planejar: só imprime o plano (planos, tempos, B-roll) sem renderizar. Use antes de renderizar.
  SKIP=1 (variável de ambiente): reaproveita peças já renderizadas em p/ (para ajustes locais).

O que faz (regras vindas da referência medida):
- Apresentador: planos de ~ritmo.alvo_a_s (ex. 1,65 s), cortados em limite de palavra, com RECORTE QUE SEGUE O ROSTO
  (rosto.json de rastrear_rosto.py) e escala do rosto dentro da faixa p10–p90 medida na referência (perfil_ref).
- B-roll em tela dividida 1080x960 + 1080x960: topo = clipe, base = apresentador ("T") ou outro clipe.
- Legenda branca, sem caixa, 1–3 palavras por cartão, na altura da emenda nas telas divididas.
- Áudio sempre do bruto (a fala segue contínua); fades de 20–30 ms nas junções.
Ver config_exemplo.json. Python do sistema (sem cv2); usa ffmpeg/ffprobe.
"""
import json, os, statistics, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
BS = chr(92)


def carregar(cfg_path):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(cfg_path))
    cfg["_base"] = base
    return cfg


def resolver(base, p):
    return p if os.path.isabs(p) else os.path.join(base, p)


def main():
    cfg = carregar(sys.argv[1])
    planejar = "--planejar" in sys.argv
    base = cfg["_base"]; os.chdir(base)
    W, H = 1080, 1920
    SRC_W, SRC_H = cfg.get("fonte_wh", [2160, 3840])
    RAW = cfg["bruto"]
    WORDS = json.load(open(resolver(base, cfg["palavras"]), encoding="utf-8"))
    ROSTO = json.load(open(resolver(base, cfg["rosto"])))
    CL = {k: resolver(base, v) for k, v in cfg.get("clips", {}).items()}
    probe = lambda f, e: subprocess.run(["ffprobe", "-v", "error"] + e + ["-of", "csv=p=0:s=x", f], capture_output=True, text=True).stdout.strip()
    DUR = {k: float(probe(v, ["-show_entries", "format=duration"])) for k, v in CL.items()}
    DIM = {k: [int(x) for x in probe(v, ["-select_streams", "v", "-show_entries", "stream=width,height"]).split("x")] for k, v in CL.items()}
    YB = cfg.get("clips_vies_vertical", {})
    leg = cfg.get("legenda", {})
    FIX = leg.get("corrige", {})
    ritmo_a = cfg.get("ritmo", {}).get("alvo_a_s", 1.65)
    ac = cfg.get("apresentador", {})
    a_cy = ac.get("cy", 0.36)
    base_f, base_cy = ac.get("base_T", {}).get("f", 0.45), ac.get("base_T", {}).get("cy", 0.45)

    # escala do rosto: ciclo dentro da faixa p10–p90 da referência (medido/alvo ~0,97 na calibração)
    if "f_alvo" in ac:
        F_ALVO = ac["f_alvo"]
    else:
        pr = json.load(open(resolver(base, cfg["perfil_ref"]), encoding="utf-8"))
        r10, _, r90 = pr["rosto_h_p10_p50_p90"]
        lo, hi = r10 * 1.08, r90 * 0.97
        F_ALVO = [round(lo + (hi - lo) * f, 3) for f in (0.1, 0.9, 0.0, 0.75, 0.4)]

    def snap(t):  # início de palavra mais próximo, menos 30 ms (não comer sílaba)
        return min((w[0] for w in WORDS), key=lambda x: abs(x - t)) - 0.03

    def cortes_em(a, b, alvo):
        n = max(1, round((b - a) / alvo))
        cand = [w[0] - 0.03 for w in WORDS if a + 0.5 < w[0] < b - 0.5]
        if not cand:
            return [(a, b)]
        pts = [a] + sorted(set(min(cand, key=lambda x: abs(x - (a + (b - a) * j / n))) for j in range(1, n))) + [b]
        return list(zip(pts[:-1], pts[1:]))

    def clip_de(spec, k=0):
        """spec: 'T' (apresentador) ou {'clip': id, 'offs': [..]} / {'clip': id, 't': x}"""
        if spec == "T":
            return "T"
        offs = spec.get("offs") or [spec.get("t", 0.0)]
        return (spec["clip"], offs[k % len(offs)])

    PIECES = []
    for seg in cfg["segmentos"]:
        a, b = seg["a"], seg["b"]
        if seg["tipo"] == "pilha":
            for j, (x, y) in enumerate(cortes_em(a, b, seg.get("alvo_s", 1.25))):
                PIECES.append(dict(a=x, b=y, modo="pilha", topo=clip_de(seg["topo"], j), base=clip_de(seg.get("base", "T"), j)))
            continue
        cur = a
        for j in sorted([j for j in cfg.get("janelas", []) if a <= j["a"] < b], key=lambda j: j["a"]):
            ja, jb = max(snap(j["a"]), cur), min(snap(j["b"]), b)
            if ja - cur > 0.3:
                for (x, y) in cortes_em(cur, ja, ritmo_a):
                    PIECES.append(dict(a=x, b=y, modo="a"))
            PIECES.append(dict(a=ja, b=jb, modo="pilha", topo=clip_de(j["topo"]), base=clip_de(j.get("base", "T")), gatilho=j.get("gatilho", "")))
            cur = jb
        if b - cur > 0.3:
            for (x, y) in cortes_em(cur, b, ritmo_a):
                PIECES.append(dict(a=x, b=y, modo="a"))
    for p in PIECES:  # duração em quadros inteiros (evita deriva de sincronia)
        p["b"] = p["a"] + round((p["b"] - p["a"]) * 30) / 30
        p["d"] = p["b"] - p["a"]

    tot = sum(p["d"] for p in PIECES); bt = sum(p["d"] for p in PIECES if p["modo"] == "pilha")
    nb = sum(1 for p in PIECES if p["modo"] == "pilha")
    print(f"PLANO: {len(PIECES)} planos, {tot:.1f} s, {len(PIECES)/tot*60:.1f} cortes/min | B-roll {nb} planos, {bt:.1f} s ({bt/tot*100:.0f}%), média {bt/max(nb,1):.2f} s")
    if planejar:
        t = 0
        for i, p in enumerate(PIECES):
            desc = "apresentador" if p["modo"] == "a" else f"pilha {p['topo']} | {p['base']} {p.get('gatilho','')}"
            print(f"{i:02d} saída {t:5.1f}s  bruto {p['a']:6.2f}–{p['b']:6.2f} ({p['d']:.2f}s)  {desc}")
            t += p["d"]
        return

    def rosto_em(a, b):
        r = [x for x in ROSTO if a <= x[0] <= b] or [min(ROSTO, key=lambda x: abs(x[0] - (a + b) / 2))]
        return (statistics.median(x[1] for x in r) * SRC_W, statistics.median(x[2] for x in r) * SRC_H, statistics.median(x[3] for x in r) * SRC_H)

    clamp = lambda v, lo, hi: max(lo, min(hi, v))

    def crop_apresentador(a, b, f, razao, cy):
        xf, yf, hf = rosto_em(a, b)
        ch = hf / f; cw = ch * razao
        if cw > SRC_W:
            cw = SRC_W; ch = cw / razao
        x0 = clamp(xf - 0.5 * cw, 0, SRC_W - cw); y0 = clamp(yf - cy * ch, 0, SRC_H - ch)
        return f"crop={cw:.0f}:{ch:.0f}:{x0:.0f}:{y0:.0f}"

    def cobrir(k, razao=1.125):
        w, h = DIM[k]
        cw, ch = (h * razao, h) if w / h > razao else (w, w / razao)
        return f"crop={cw:.0f}:{ch:.0f}:{(w - cw) / 2:.0f}:{(h - ch) * YB.get(k, 0.5):.0f},scale={W}:960:flags=lanczos"

    def run(cmd):
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(r.stderr[-1500:]); sys.exit(1)

    os.makedirs("p", exist_ok=True)
    kf = 0
    for i, p in enumerate(PIECES):
        out = f"p/p{i:02d}.mov"; p["out"] = out; a, d = p["a"], p["d"]
        af = f"afade=t=in:d=0.02,afade=t=out:st={d-0.03:.3f}:d=0.03,aresample=48000"
        if p["modo"] == "a":
            f = F_ALVO[kf % len(F_ALVO)]; kf += 1; p["f"] = f
            vf = f"{crop_apresentador(a, a + d, f, 9 / 16, a_cy)},scale={W}:{H}:flags=lanczos,fps=30,format=yuv420p"
            cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{a}", "-t", f"{d}", "-i", RAW, "-vf", vf, "-af", af]
        else:
            (kt, tt) = p["topo"]
            tt = min(tt, max(0, DUR[kt] - d - 0.1))
            ins = ["-ss", f"{a}", "-t", f"{d}", "-i", RAW, "-ss", f"{tt}", "-t", f"{d}", "-i", CL[kt]]
            fc = f"[1:v]{cobrir(kt)}[t];"
            if p["base"] == "T":
                fc += f"[0:v]{crop_apresentador(a, a + d, base_f, 1.125, base_cy)},scale={W}:960:flags=lanczos[u];"
            else:
                kb, tb = p["base"]; tb = min(tb, max(0, DUR[kb] - d - 0.1))
                ins += ["-ss", f"{tb}", "-t", f"{d}", "-i", CL[kb]]
                fc += f"[2:v]{cobrir(kb)}[u];"
            fc += "[t][u]vstack,fps=30,format=yuv420p[v]"
            cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + ins + ["-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-af", af]
        cmd += ["-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "pcm_s16le", "-ar", "48000", out]
        if not (os.environ.get("SKIP") and os.path.exists(out)):
            run(cmd)
        print("peca", i, round(a, 2), round(d, 2), p["modo"])

    # legendas
    destaque = leg.get("destaque", [])
    y_a, y_p = leg.get("y_a", 1240), leg.get("y_pilha", 960)
    off = 0.0; caps = []
    for p in PIECES:
        y = y_p if p["modo"] == "pilha" else y_a
        ws = [w for w in WORDS if w[0] >= p["a"] - 0.03 and w[0] < p["b"] - 0.05]
        chunk = []
        def flush():
            nonlocal chunk
            if chunk:
                t = " ".join(FIX.get(c[2].strip(",.").strip(), c[2].strip(",.")) for c in chunk)
                caps.append((off + chunk[0][0] - p["a"], off + min(chunk[-1][1], p["b"]) - p["a"], t, y)); chunk = []
        for w in ws:
            if destaque and w[2].strip(",.") == destaque[0].split()[0]:
                flush()
            chunk.append(w)
            if len(chunk) >= 3 or w[2].strip().endswith((",", ".")):
                flush()
        flush(); off += p["d"]
    print("duracao", round(off, 2), "planos", len(PIECES), "legendas", len(caps))
    ts = lambda t: f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
    ass = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "", "[V4+ Styles]",
           "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
           f"Style: Cap,{leg.get('fonte', 'Times New Roman')},{leg.get('tamanho', 72)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,5,40,40,0,1",
           "", "[Events]", "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"]
    for k, (a, b, t, y) in enumerate(caps):
        nxt = caps[k + 1][0] if k + 1 < len(caps) else 1e9
        b = min(b + 0.08, nxt - 0.01)
        big = "{" + BS + f"fs{leg.get('destaque_tamanho', 110)}" + "}" if any(x in t for x in destaque) else ""
        ass.append(f"Dialogue: 0,{ts(a)},{ts(b)},Cap,,0,0,0,,{{{BS}pos(540,{y})}}{big}{t}")
    open("legenda.ass", "w", encoding="utf-8").write("\n".join(ass))

    inp, tr = [], ""
    for i, p in enumerate(PIECES):
        inp += ["-i", p["out"]]
        tr += f"[{i}:v]trim=duration={round(p['d'],4)},setpts=PTS-STARTPTS[v{i}];[{i}:a]atrim=duration={round(p['d'],4)},asetpts=PTS-STARTPTS[a{i}];"
    fc = tr + "".join(f"[v{i}][a{i}]" for i in range(len(PIECES))) + f"concat=n={len(PIECES)}:v=1:a=1[v][a];[v]ass=legenda.ass[vo]"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + inp + ["-filter_complex", fc, "-map", "[vo]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "19", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", cfg.get("saida", "reel.mp4")])
    json.dump([{k: v for k, v in p.items() if k != "out"} for p in PIECES], open("plano_pecas.json", "w"), ensure_ascii=False)
    print("ok ->", cfg.get("saida", "reel.mp4"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main()
