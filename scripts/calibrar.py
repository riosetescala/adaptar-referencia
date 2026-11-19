#!/usr/bin/env python
"""CALIBRA as tolerâncias do portão a partir de VÁRIAS referências do mesmo estilo.

Uso: py -X utf8 -I calibrar.py perfil_ref1.json perfil_ref2.json perfil_ref3.json [--saida tolerancias.json]
Mostra, por métrica, o mínimo, o máximo e a dispersão entre as referências. Com --saida, grava as tolerâncias
(o qa_fidelidade.py lê ./tolerancias.json da pasta dos scripts, se existir).

Regra: tolerância = a maior entre o padrão e 60% da dispersão observada entre as referências.
Com menos de 3 referências o portão continua PROVISÓRIO (o qa_fidelidade.py avisa).
Só junte referências do MESMO estilo (talking head com B-roll); misturar estilos infla as tolerâncias e o portão deixa de reprovar.
"""
import json, statistics, sys

sys.stdout.reconfigure(encoding="utf-8")
PADRAO = {"tol_cortes": 0.30, "tol_A": 0.35, "tol_B_parcela_pp": 0.08, "tol_B_empilhado_pp": 0.30, "tol_B_media": 0.40}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    saida = sys.argv[sys.argv.index("--saida") + 1] if "--saida" in sys.argv else None
    if saida in args:
        args.remove(saida)
    P = [json.load(open(a, encoding="utf-8")) for a in args]
    n = len(P)
    met = [("cortes_por_min", "cortes/min", "rel", "tol_cortes"), ("A_media_s", "plano do apresentador (s)", "rel", "tol_A"),
           ("B_parcela_tempo", "B-roll parcela do tempo", "abs", "tol_B_parcela_pp"), ("B_media_s", "duração média do B-roll (s)", "rel", "tol_B_media"),
           ("B_empilhado_parcela", "B-roll em tela dividida (pista)", "abs", "tol_B_empilhado_pp")]
    tol = dict(PADRAO)
    print(f"{n} referência(s)\n{'métrica':36} {'mín':>8} {'máx':>8} {'média':>8} {'dispersão':>10}")
    for chave, nome, tipo, tk in met:
        v = [p[chave] for p in P if p.get(chave) is not None]
        if len(v) < 2:
            print(f"{nome:36} {'(menos de 2 valores)':>38}"); continue
        mn, mx, md = min(v), max(v), statistics.mean(v)
        disp = (mx - mn) / md if tipo == "rel" else (mx - mn)
        tol[tk] = round(max(PADRAO[tk], 0.6 * disp), 3)
        print(f"{nome:36} {mn:8.2f} {mx:8.2f} {md:8.2f} {disp*100:9.0f}{'%' if tipo=='rel' else ' p.p.'}")
    tol["n_refs"] = n
    print("\ntolerâncias resultantes:", json.dumps(tol, ensure_ascii=False))
    if n < 3:
        print("AVISO: menos de 3 referências, o portão segue PROVISÓRIO.")
    if saida:
        json.dump(tol, open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("gravado em", saida)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main()
