---
name: adaptar-referencia
description: Edita o vídeo bruto do usuário no estilo de um vídeo de referência (reel, vídeo viral), com engenharia reversa MEDIDA da referência e portão de fidelidade antes de entregar. Use quando o usuário der uma referência de edição + material bruto próprio e pedir "fazer algo parecido", "editar nesse estilo", "modelar essa edição". Cobre ritmo, A-roll x B-roll, tela dividida, zoom/ponto focal, legenda, e lista as cenas acessórias que faltam no bruto. Complementa a skill rea-video (que só disseca). Trigger: /adaptar-referencia
---

# Adaptar referência → material do usuário

Origem: reel @perfil-exemplo. A edição saiu com planos de 3,4 s (referência: 1,65 s), quase sem B-roll (referência: 24% do tempo, em tela dividida) e com zoom fora do rosto. O erro tinha três causas, e esta skill fecha as três:

1. **Prompt:** pedia "qual trecho do bruto entra em cada plano da referência", o que supõe que todo plano da referência é o apresentador. Falso: 1 em cada 4 planos é cena acessória que o bruto não tem.
2. **Skill rea-video:** disseca para RECRIAR o mesmo vídeo; não compara a estrutura da referência com o material que o usuário tem, e só descreve B-roll se o fluxo `decompose` + `review` completo rodar.
3. **Execução:** o `decompose` quebrou e segui por atalho (respondi lotes de etapas por padrão, não olhei o B-roll, confiei em heurística sem conferir, não comparei o resultado com a referência).

## Regras duras

- **Nenhuma etapa de análise pode ser respondida em lote por padrão.** Se uma ferramenta pedir julgamento visual, olhe as imagens. Se a ferramenta quebrar, PARE e diga o que ficou sem análise; não siga como se estivesse completa.
- **Número automático de layout (tela dividida) é pista, não verdade.** Confirme olhando `folha_broll.jpg`.
- **Não entregue sem passar no portão de fidelidade** (`qa_fidelidade.py`), ou declare cada desvio ao usuário com o motivo.
- **A sugestão das cenas acessórias é SUA**, derivada da referência. O usuário não deve ter que pensar nela.
- **Download de qualquer arquivo (clipe, modelo) exige OK do usuário:** diga fonte, nome e tamanho. Evite pessoas identificáveis e marcas visíveis em stock usado para vender serviço.
- Fidelidade de formato: mapeie beat → cena antes de montar.

## Fluxo

Scripts em `~/.claude/skills/adaptar-referencia/scripts/`. Python com cv2 (do rea-video): `<python-do-rea-video> -X utf8 -I`.

1. **Medir a referência** — `perfil_video.py ref.mp4 perfil_ref`. Produz `perfil.json` (cortes/min, secos x graduais, A-roll x B-roll, parcela de B-roll, duração média, tela dividida [pista], escala e posição do rosto) e `folha_broll.jpg` (um quadro por B-roll, numerado, com E = empilhado e 1 = simples).
2. **Transcrever a referência** — `transcrever.py` (precisa OK do usuário na 1ª vez: baixa modelo de ~480 MB).
3. **Inventário de B-roll** — `inventario_broll.py perfil.json palavras.json`. **Olhe a folha** e preencha: cena, layout confirmado, e o **gatilho** (o substantivo ou verbo da fala que a cena ilustra). Registre a regra observada (na referência: cada B-roll ilustra literalmente a palavra; pessoas citadas, lugares, objetos, ações; ~1,1 s; em rajadas nos substantivos fortes; dois clipes empilhados com a legenda na emenda).
4. **Transcrever o bruto** e escolher o que entra (limites de palavra, sem comer sílaba). Marcar pausas como pontos de corte.
5. **Pedido de insumos** — `necessidades.py perfil_ref.json --alvo <s> --bruto-s <s> --b-empilhado <confirmado> --manifesto insumos.json`. Imprime, para o tamanho do vídeo pedido, quanto a referência exige (cortes, planos do apresentador, planos de B-roll, tela dividida x cheia, clipes distintos, música), quanto já temos e **quantos faltam**, em dois cenários: fidelidade total e mínimo viável. Entregue essa tabela ao usuário antes de qualquer montagem.
5b. **Lista de cenas necessárias** — aplique a regra do passo 3 ao roteiro do bruto: para cada substantivo-chave, a cena que ilustra, com a parcela de B-roll da referência como meta. Compare com o que o usuário tem. **Entregue a lista do que falta ANTES de montar**, com sugestões de onde obter (material próprio do cliente primeiro; stock como reserva, com aprovação de download).
6. **Montar** — `rastrear_rosto.py bruto.mov rosto.json` (o recorte segue o rosto) e depois `montar.py config.json --planejar` (confira planos, B-roll em % e tempos) e `montar.py config.json` (renderiza). Copie `scripts/config_exemplo.json` (é o config real do reel de exemplo v2): tempos em segundos do bruto, janelas de B-roll amarradas à palavra-gatilho, topo = clipe e base = `"T"` (apresentador) ou outro clipe. A escala do rosto sai sozinha da faixa p10–p90 do `perfil_ref`. **Antes de montar, rode `texto_em_broll.py` em cada clipe baixado** (marca, modelo, inscrição). Reprova texto grande; texto pequeno é só aviso e você decide olhando.
7. **Portão** — `perfil_video.py saida.mp4 perfil_saida`, `qa_fidelidade.py perfil_ref/perfil.json perfil_saida/perfil.json --plano plano_pecas.json --b-empilhado-ref <valor confirmado>` (`--plano` usa o B-roll EXATO do `montar.py`; sem ele o medidor por aparência subestima telas divididas mistas) e `texto_em_broll.py saida.mp4 --regiao 0:0.45` (só metades de B-roll). Se REPROVADO, corrija e repita. Mostre as tabelas ao usuário. O portão mede **estrutura**; relevância do B-roll e legenda você confere à vista.
8. **Olhar o resultado** em quadros lado a lado com a referência antes de entregar.

## Prompt padrão (se o usuário não pedir tudo isso, a skill pede por ele)

> Referência de edição: <arquivo>. Bruto: <arquivo>. Objetivo: <onde vai ser publicado>.
> Meça a referência (ritmo, cortes, A-roll x B-roll, tela dividida, zoom e ponto focal, legenda, trilha). Faça o inventário de B-roll com a fala de cada cena. Liste as cenas acessórias que o meu bruto não tem e sugira de onde tirar. Só monte depois disso e só entregue se passar no portão de fidelidade. Nada pago nem download sem meu OK.

## Calibração (referência de 118 s, talking head com B-roll)

78 cortes, todos secos (1 quadro). 39,5 cortes/min. Apresentador: média 1,69 s por plano (0,4–4,75). B-roll: 26 planos, 24% do tempo, 1,1 s, ~91% em tela dividida (olhando; a pista automática dá 77%). Rosto: altura p10–p90 = 0,227–0,343 do quadro, centro horizontal 0,40–0,56.

## Limites conhecidos

- A pista de tela dividida erra planos com costura suave ou coberta pela legenda.
- A classificação A-roll x B-roll assume um apresentador dominante em uma ou poucas aparências; vídeos sem apresentador exigem ajuste manual.
- Legenda (fonte, caixa, posição) não é medida: confira visualmente (na referência: caixa amarela, texto preto serifado, 1–3 palavras, na altura da emenda).
- Transição gradual (fade/dissolve) não é detectada; só corte seco.

## Relação com a skill rea-video

- `rea-video` responde **"de que este vídeo é feito?"** (tipo de cada plano: real, IA, 3D; camadas de texto; separação de voz/música/efeitos; plano de recriação). Serve para qualquer vídeo, sem material próprio.
- `adaptar-referencia` responde **"como faço o MEU vídeo parecer com este?"**. É a skill do trabalho; a `rea-video` é uma ferramenta de apoio dela.
- Ordem: comece SEMPRE por `adaptar-referencia`. Chame `rea-video` dentro do passo 1 só se precisar de camada que a medição própria não tem (BPM e estilo da música, separação de áudio, plano de recriação com IA). Se a `rea-video` falhar, siga com as medições próprias e declare o que ficou sem análise.

## Estrutura interna

```
adaptar-referencia/
  SKILL.md                    regras duras + fluxo de 8 passos + calibração
  scripts/
    perfil_video.py           MEDE um vídeo (referência ou resultado)  -> perfil.json + folha_broll.jpg
    rastrear_rosto.py         segue o rosto no bruto (10 quadros/s)  -> rosto.json (ponto focal)
    montar.py + config.json   MONTA: apresentador com recorte no rosto + B-roll em tela dividida + legenda
    texto_em_broll.py         OCR: texto grande (marca/modelo) reprova; pequeno avisa
    calibrar.py               N perfis de referência  -> tolerancias.json (o portão lê sozinho)
    transcrever.py            fala com tempo por palavra (Whisper local)  -> palavras.json
    inventario_broll.py       perfil.json + palavras.json  -> tabela de B-roll com a fala de cada cena
    necessidades.py           perfil da referência + alvo + o que temos  -> quanto precisa / temos / FALTA
    qa_fidelidade.py          perfil da referência x perfil do resultado  -> APROVADO / REPROVADO (portão)
```

Fluxo de dados: referência -> `perfil_video` -> `inventario_broll` (olhar a folha) -> `necessidades` (o que falta) -> conseguir material (com OK) -> montar -> `perfil_video` do resultado -> `qa_fidelidade`.

## Status de validação (o que foi testado e o que NÃO foi)

- `perfil_video.py`, `qa_fidelidade.py`, `necessidades.py`: testados em 1 referência e em 3 edições do reel @perfil-exemplo.
- `montar.py` e o fluxo inteiro: rodados do zero (rastrear rosto, transcrever, perfil, planejar, renderizar, medir, portão), sem erro. Usei a própria referência como clipe-substituto, então a **qualidade do B-roll** não foi testada, só o código.
- **Lição do teste:** o medidor por aparência leu 27% de B-roll na v2 entregue; o plano exato dá **36%** (referência: 24%). A v2 passou no portão por causa dessa medição, não por estar dentro da meta. Por isso `--plano` existe. Ao entregar, compare também `montar.py --planejar` com a meta.
- `texto_em_broll.py`: caminhos reprova/aviso/ok validados com vídeos sintéticos. **Limite real:** em vídeo de verdade ele achou só texto pequeno e **não leu a inscrição inclinada** que vi a olho. É auxiliar, não substitui olhar. O limite de 2% da altura ("grande") ainda não foi validado com um caso real.
- **Tolerâncias do portão: PROVISÓRIAS** (calibradas com 1 referência). Para torná-las firmes: reúna 3 ou mais referências do mesmo estilo, gere `perfil.json` de cada e rode `calibrar.py ... --saida tolerancias.json` (na pasta dos scripts). Não há referências extras no computador hoje.
- Ainda **sem**: medição da música e dos efeitos sonoros da referência, escolha e mix de trilha, checklist de autorização do cliente, e vídeos sem apresentador.
