# Relatório de validação — Fase 2

Gerado automaticamente por `scripts/validar_dados.py` em 2026-10-19T21:49:50+00:00 (UTC).
Não edite à mão; execute o script novamente.

Dados validados: `data/processed/partidas.csv` sha256 `6f7fa8000d411247f2e9c75dab96ed2df1c548ef038faca220af3805a88ddfee`; `data/reference/clubes.csv` sha256 `72408ad0acb164f769875a82b323ee2a7759672d09b2dbb3a7493d5616b6df39`

## 1. Integridade interna (`data/processed/partidas.csv`)

| Teste | Resultado | Detalhe |
|---|---|---|
| 380 partidas | APROVADO | 380 encontradas |
| id_partida único | APROVADO |  |
| 20 clubes, todos no cadastro | APROVADO | 20 usados; fora do cadastro: nenhum |
| mandante diferente do visitante | APROVADO |  |
| cada confronto mandante×visitante ocorre uma única vez (turno e returno) | APROVADO | 380 pares distintos de 380 possíveis |
| cada clube: 19 jogos em casa e 19 fora | APROVADO |  |
| rodadas 1 a 38 com 10 jogos cada | APROVADO |  |
| cada clube joga exatamente uma vez por rodada | APROVADO |  |
| datas entre 13/04/2024 e 08/12/2024 | APROVADO | 2024-04-13 a 2024-12-08 |
| horário preenchido (HH:MM) | APROVADO |  |
| hora_explicita é 0 ou 1 | APROVADO | 230 explícitos, 150 herdados da linha anterior |
| placar final preenchido e não negativo | APROVADO |  |
| placar do intervalo ausente somente em jogos 0-0 | APROVADO | 26 jogos sem placar do intervalo |
| gols do intervalo ≤ gols finais | APROVADO |  |

## 2. Comparação jogo a jogo com adaoduque/Brasileirao_Dataset

Chave de comparação: (mandante, visitante), única em turno e returno.

- Partidas 2024 com clubes não mapeados: nenhuma
- Partidas presentes nas duas fontes: **380**
- Somente no openfootball: 0 
- Somente no adaoduque: 0 

| Atributo | Divergências |
|---|---|
| placar | 0 |
| rodada | 0 |
| data | 0 |
| hora | 211 |

Horários **herdados** (sem horário escrito na linha do openfootball): 150. Desses, 150 coincidem com o adaoduque em até 10 minutos e 0 divergem mais que isso.

Divergências de hora com até 10 minutos de diferença: **210**. Hipótese (não documentada pelas fontes): o adaoduque registra o horário efetivo de início, poucos minutos após o horário programado registrado pelo openfootball. Essas diferenças não são tratadas como erro e não são listadas.
Divergências de hora acima de 10 minutos: **1**.

### Divergências de hora

| Mandante × Visitante | openfootball (fonte principal) | adaoduque (fonte secundária, valor divergente) |
|---|---|---|
| ATP × INT | 16:00 | 18:06 |

Os valores da coluna adaoduque são atribuídos à fonte secundária e divergem da fonte principal; não são usados no produto. Investigação em `docs/qualidade/auditoria_fase2.md`, seção D.

## 3. Classificação recalculada × Wikipédia (revisão 70400733)

Ordenação: pontos, vitórias, saldo de gols, gols pró.

| Pos | Clube | Pts | J | V | E | D | GP | GC | SG | Wikipédia |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | BOT | 79 | 38 | 23 | 10 | 5 | 59 | 29 | 30 | confere |
| 2 | PAL | 73 | 38 | 22 | 7 | 9 | 60 | 33 | 27 | confere |
| 3 | FLA | 70 | 38 | 20 | 10 | 8 | 61 | 42 | 19 | confere |
| 4 | FOR | 68 | 38 | 19 | 11 | 8 | 53 | 39 | 14 | confere |
| 5 | INT | 65 | 38 | 18 | 11 | 9 | 53 | 36 | 17 | confere |
| 6 | SPA | 59 | 38 | 17 | 8 | 13 | 53 | 43 | 10 | confere |
| 7 | COR | 56 | 38 | 15 | 11 | 12 | 54 | 45 | 9 | confere |
| 8 | BAH | 53 | 38 | 15 | 8 | 15 | 49 | 49 | 0 | confere |
| 9 | CRU | 52 | 38 | 14 | 10 | 14 | 43 | 41 | 2 | confere |
| 10 | VAS | 50 | 38 | 14 | 8 | 16 | 43 | 56 | -13 | confere |
| 11 | VIT | 47 | 38 | 13 | 8 | 17 | 45 | 52 | -7 | confere |
| 12 | ATM | 47 | 38 | 11 | 14 | 13 | 47 | 54 | -7 | confere |
| 13 | FLU | 46 | 38 | 12 | 10 | 16 | 33 | 39 | -6 | confere |
| 14 | GRE | 45 | 38 | 12 | 9 | 17 | 44 | 50 | -6 | confere |
| 15 | JUV | 45 | 38 | 11 | 12 | 15 | 48 | 59 | -11 | DIVERGE (GP: 47; SG: -12) |
| 16 | RBB | 44 | 38 | 10 | 14 | 14 | 44 | 48 | -4 | confere |
| 17 | ATP | 42 | 38 | 11 | 9 | 18 | 40 | 46 | -6 | confere |
| 18 | CRI | 38 | 38 | 9 | 11 | 18 | 42 | 61 | -19 | confere |
| 19 | ATG | 30 | 38 | 7 | 9 | 22 | 29 | 58 | -29 | confere |
| 20 | CUI | 30 | 38 | 6 | 12 | 20 | 29 | 49 | -20 | confere |

### Verificações de totais

- openfootball: gols pró = 929, gols sofridos = 929 → consistente
- Wikipédia: gols pró = 928, gols sofridos = 929 → INCONSISTENTE
- Empates não resolvidos pelos critérios 1–3: nenhum
- Clubes com divergência em relação à Wikipédia: 1
