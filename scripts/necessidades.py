#!/usr/bin/env python
"""PEDIDO DE INSUMOS: quanto material a referência exige para um vídeo de X segundos, quanto já temos e quanto falta.

Uso:
  py -X utf8 -I necessidades.py perfil_ref.json --alvo 54 --bruto-s 86.6 \
      [--manifesto insumos.json] [--b-empilhado 0.91] [--max-usos 3]

manifesto (insumos.json), o que existe HOJE em disco ou foi aprovado:
  {"clipes": [{"arquivo": "carro.mp4", "duracao": 31.3}], "musica": 0}

Premissas explícitas (aparecem no relatório):
- Cada clipe de B-roll rende no máximo --max-usos trechos distintos (padrão 3) de ~1 s cada, para não repetir imagem.
- Plano de B-roll em tela dividida precisa de 2 clipes ao mesmo tempo; plano simples, de 1.
- --b-empilhado: parcela de B-roll em tela dividida CONFIRMADA olhando a folha (a medição automática é só pista).
"""
import json, math, sys
sys.stdout.reconfigure(encoding="utf-8")


def arg(nome, padrao=None, tipo=float):
    a = sys.argv
    return tipo(a[a.index(nome) + 1]) if nome in a else padrao


def main():
    R = json.load(open(sys.argv[1], encoding="utf-8"))
    T = arg("--alvo")
    bruto = arg("--bruto-s", 0.0)
    emp = arg("--b-empilhado", R["B_empilhado_parcela"] or 0.0)
    max_usos = int(arg("--max-usos", 3))
    man = {"clipes": [], "musica": 0}
    if "--manifesto" in sys.argv:
        man = json.load(open(sys.argv[sys.argv.index("--manifesto") + 1], encoding="utf-8"))
    D = R["duracao"]
    esc = T / D

    cortes = round(R["cortes_por_min"] * T / 60)
    a_planos = round(R["A_n"] * esc)
    b_planos = round(R["B_n"] * esc)
    b_tempo = R["B_parcela_tempo"] * T
    b_emp = round(b_planos * emp)
    b_simp = b_planos - b_emp
    slots_total = 2 * b_emp + b_simp          # fidelidade total: cada metade é um clipe distinto
    slots_min = b_emp + b_simp                # mínimo viável: uma metade da tela dividida é o apresentador
    fala_precisa = T - b_tempo                # segundos de A-roll necessários

    usos = lambda d: max(1, min(max_usos, int(d // (R["B_media_s"] or 1.1))))
    tenho_clipes = len(man["clipes"])
    tenho_slots = sum(usos(c["duracao"]) for c in man["clipes"])

    L = []
    L.append(f"# Pedido de insumos — referência {R['video']} → vídeo de {T:.0f} s\n")
    L.append(f"Referência: {D:.0f} s, {R['cortes_por_min']} cortes/min, plano do apresentador {R['A_media_s']} s, "
             f"B-roll {R['B_parcela_tempo']*100:.0f}% do tempo ({R['B_n']} planos de {R['B_media_s']} s), "
             f"tela dividida {emp*100:.0f}% dos B-rolls.\n")
    L.append("| Insumo | Referência (proporcional) | Meta p/ o vídeo | Temos hoje | Faltam |")
    L.append("|---|---|---|---|---|")
    ok = lambda f: "0" if f <= 0 else f"**{f}**"
    L.append(f"| Cortes totais | {R['cortes_por_min']}/min | {cortes} | — | — |")
    L.append(f"| Planos do apresentador (jump cuts) | {R['A_n']} em {D:.0f} s | {a_planos} | bruto de {bruto:.0f} s | 0 (sobra material) |")
    L.append(f"| Fala útil do apresentador | {(1-R['B_parcela_tempo'])*100:.0f}% do tempo | {fala_precisa:.0f} s | {bruto:.0f} s | {ok(math.ceil(fala_precisa - bruto))} |")
    L.append(f"| Planos de B-roll (≈{R['B_media_s']} s cada) | {R['B_n']} | {b_planos} ({b_tempo:.0f} s) | {tenho_slots} trechos aproveitáveis | — |")
    L.append(f"|   dos quais em tela dividida | {emp*100:.0f}% | {b_emp} | — | — |")
    L.append(f"|   dos quais tela cheia | {(1-emp)*100:.0f}% | {b_simp} | — | — |")
    L.append(f"| **Clipes distintos — fidelidade total** (2 por tela dividida + 1 por simples) | — | **{slots_total} trechos** | {tenho_slots} | {ok(max(0, slots_total - tenho_slots))} |")
    L.append(f"| **Clipes distintos — mínimo viável** (apresentador em uma metade) | — | **{slots_min} trechos** | {tenho_slots} | {ok(max(0, slots_min - tenho_slots))} |")
    L.append(f"| Clipes-fonte necessários (≤{max_usos} trechos cada) | — | {math.ceil(slots_total / max_usos)} (total) / {math.ceil(slots_min / max_usos)} (mínimo) | {tenho_clipes} | {ok(max(0, math.ceil(slots_total / max_usos) - tenho_clipes))} / {ok(max(0, math.ceil(slots_min / max_usos) - tenho_clipes))} |")
    L.append(f"| Música (cama baixa, ~-39 dB na referência) | 1 faixa | 1 | {man.get('musica', 0)} | {ok(1 - man.get('musica', 0))} |")
    L.append("| Efeitos sonoros | não medidos na referência | indeterminado | — | — |")
    L.append("\n**Premissas:** cada clipe rende no máximo %d trechos distintos; tela dividida usa 2 clipes ao mesmo tempo. "
             "A parcela de tela dividida (%.0f%%) é a confirmada olhando a folha, não a medida automática." % (max_usos, emp * 100))
    L.append("**Próximo passo:** o agente lista, para cada substantivo-chave do roteiro do bruto, a cena que o ilustra, até cobrir os planos faltantes.")
    print("\n".join(L))


if __name__ == "__main__":
    if len(sys.argv) < 3 or "--alvo" not in sys.argv:
        sys.exit(__doc__)
    main()
