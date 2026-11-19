#!/usr/bin/env python
"""Monta o INVENTÁRIO DE B-ROLL da referência: um plano por linha, com a fala que o acompanha.

Uso: py -X utf8 -I inventario_broll.py perfil.json palavras.json > inventario.md
Depois: OLHE folha_broll.jpg e preencha as colunas 'Cena' e 'Layout confirmado' (E=empilhado, 1=simples).
A coluna 'Gatilho' já vem com as palavras faladas no intervalo; escolha o substantivo/verbo que a cena ilustra.
"""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")

perfil = json.load(open(sys.argv[1], encoding="utf-8"))
palavras = json.load(open(sys.argv[2], encoding="utf-8"))
B = [p for p in perfil["planos"] if p["tipo"] == "B"]
print(f'# Inventário de B-roll — {perfil["video"]}\n')
print(f'{perfil["B_n"]} planos, {perfil["B_parcela_tempo"]*100:.0f}% do tempo, média {perfil["B_media_s"]} s. '
      f'Tela dividida medida (pista): {perfil["B_empilhado_parcela"]*100:.0f}% — CONFIRMAR NA FOLHA.\n')
print("| # | Tempo | Dur | Layout (pista) | Fala no intervalo | Gatilho | Cena (olhar a folha) | Layout confirmado |")
print("|---|---|---|---|---|---|---|---|")
for p in B:
    fala = " ".join(w[2] for w in palavras if p["a"] - 0.15 <= w[0] < p["e"])
    print(f'| {p["i"]} | {p["a"]:.1f}–{p["e"]:.1f} | {p["dur"]:.1f} | {"E" if p["empilhado"] else "1"} | {fala} |  |  |  |')
