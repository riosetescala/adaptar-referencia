#!/usr/bin/env python
"""PORTÃO DE FIDELIDADE: compara o perfil do vídeo produzido com o perfil da referência.

Uso:  python qa_fidelidade.py perfil_ref.json perfil_saida.json [--b-empilhado-ref 0.91]
Sai com código 1 se algo estiver fora da tolerância. Só entregue se passar, ou se você declarar
cada desvio ao usuário com o motivo. (O gate existe porque o primeiro erro foi entregar um
corte com planos de 3,4 s contra 1,65 s da referência, sem B-roll e com zoom fora do rosto.)

--plano plano_pecas.json: usa o B-roll EXATO do montar.py (parcela, nº e duração) em vez da medição por aparência.
--b-empilhado-ref: parcela de B-roll em tela dividida CONFIRMADA olhando a folha (a medição
automática é só pista). Se dada, substitui o valor medido da referência.
"""
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8")


def rel(ref, out, tol):
    return abs(out - ref) <= tol * ref


def main():
    a = sys.argv[1:]
    manual = None
    if "--b-empilhado-ref" in a:
        i = a.index("--b-empilhado-ref"); manual = float(a[i + 1]); del a[i:i + 2]
    plano = None
    if "--plano" in a:
        i = a.index("--plano"); plano = json.load(open(a[i + 1], encoding="utf-8")); del a[i:i + 2]
    R = json.load(open(a[0], encoding="utf-8")); S = json.load(open(a[1], encoding="utf-8"))
    if plano:  # plano_pecas.json do montar.py: B-roll EXATO (o medidor por aparência subestima telas divididas mistas)
        tot = sum(p["d"] for p in plano); B = [p for p in plano if p["modo"] == "pilha"]
        S["B_parcela_tempo"] = round(sum(p["d"] for p in B) / tot, 3)
        S["B_n"] = len(B); S["B_media_s"] = round(sum(p["d"] for p in B) / max(len(B), 1), 2)
        S["B_empilhado_parcela"] = 1.0
        print(f"(B-roll tomado do plano exato: {S['B_parcela_tempo']*100:.0f}% do tempo, {len(B)} planos)")
    tol = {"tol_cortes": 0.30, "tol_A": 0.35, "tol_B_parcela_pp": 0.08, "tol_B_empilhado_pp": 0.30, "tol_B_media": 0.40, "n_refs": 1}
    arq = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tolerancias.json")
    if os.path.exists(arq):
        tol.update(json.load(open(arq, encoding="utf-8")))
    linhas = []

    def chk(nome, ref, out, ok, regra):
        linhas.append((nome, ref, out, "OK" if ok else "FALHA", regra))

    chk("cortes por minuto", R["cortes_por_min"], S["cortes_por_min"],
        rel(R["cortes_por_min"], S["cortes_por_min"], tol["tol_cortes"]), f"±{tol['tol_cortes']*100:.0f}%")
    if R["A_media_s"] and S["A_media_s"]:
        chk("plano médio do apresentador (s)", R["A_media_s"], S["A_media_s"],
            rel(R["A_media_s"], S["A_media_s"], tol["tol_A"]), f"±{tol['tol_A']*100:.0f}%")
    chk("B-roll: parcela do tempo", R["B_parcela_tempo"], S["B_parcela_tempo"],
        abs(R["B_parcela_tempo"] - S["B_parcela_tempo"]) <= tol["tol_B_parcela_pp"], f"±{tol['tol_B_parcela_pp']*100:.0f} p.p.")
    if R["B_n"] and R["B_n"] >= 5:
        refe = manual if manual is not None else R["B_empilhado_parcela"]
        out = S["B_empilhado_parcela"] if S["B_empilhado_parcela"] is not None else 0.0
        chk("B-roll em tela dividida (parcela)", refe, out, abs(refe - out) <= tol["tol_B_empilhado_pp"], f"±{tol['tol_B_empilhado_pp']*100:.0f} p.p. (pista; confirme na folha)")
    if R["B_media_s"] and S["B_media_s"]:
        chk("duração média do B-roll (s)", R["B_media_s"], S["B_media_s"],
            rel(R["B_media_s"], S["B_media_s"], tol["tol_B_media"]), f"±{tol['tol_B_media']*100:.0f}%")
    if R.get("rosto_cx_p5_p95") and S.get("rosto_cx_p5_p95"):
        lo, hi = R["rosto_cx_p5_p95"]
        ok = S["rosto_cx_p5_p95"][0] >= lo - 0.06 and S["rosto_cx_p5_p95"][1] <= hi + 0.06
        chk("rosto: posição horizontal p5–p95", f"{lo}–{hi}", f'{S["rosto_cx_p5_p95"][0]}–{S["rosto_cx_p5_p95"][1]}', ok, "dentro da faixa ±0,06 (ponto focal)")
    if R.get("rosto_h_p10_p50_p90") and S.get("rosto_h_p10_p50_p90"):
        r10, _, r90 = R["rosto_h_p10_p50_p90"]; s10, _, s90 = S["rosto_h_p10_p50_p90"]
        ok = s10 >= r10 * 0.85 and s90 <= r90 * 1.15
        chk("rosto: escala (zoom) p10–p90", f"{r10}–{r90}", f"{s10}–{s90}", ok, "não passar da amplitude de zoom da referência ±15%")

    print(f'{"critério":42} {"referência":>14} {"saída":>14}  resultado   regra')
    falhas = 0
    for n, r, o, res, reg in linhas:
        print(f"{n:42} {str(r):>14} {str(o):>14}  {res:9}   {reg}")
        falhas += res == "FALHA"
    print(f"\n{'APROVADO' if not falhas else 'REPROVADO'}: {falhas} critério(s) fora da tolerância.")
    if tol.get("n_refs", 1) < 3:
        print(f"PROVISÓRIO: tolerâncias calibradas com {tol.get('n_refs', 1)} referência(s). Rode calibrar.py com 3 ou mais do mesmo estilo.")
    print("LEMBRETE: o portão mede ESTRUTURA. Confira à vista: B-roll combina com a palavra, legenda correta, e rode texto_em_broll.py nos clipes.")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main()
