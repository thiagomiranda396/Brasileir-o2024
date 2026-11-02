# 4. Estatística esportiva

Documentos do projeto: `docs/regras_de_classificacao.md`, `docs/modelagem/proposta_fase3.md` §3
e §4, `sql/04_views.sql`, `powerbi/medidas.dax`.

## 4.1 Dicionário de métricas

Cada métrica tem **uma** definição, **um** grão e **uma** origem. Se precisar de outra
variante, dê outro nome.

| Métrica | Definição | Grão / origem | Observação |
|---|---|---|---|
| Jogos (J) | Partidas disputadas pelo clube | `fato_participacao` | Após a rodada N, todo clube tem N jogos |
| Pontos (Pts) | 3 por vitória, 1 por empate, 0 por derrota | `fato_participacao.pontos` | **[FATO]** confirmado indiretamente: bate com a CBF nos 20 clubes. O RGC, que define a pontuação, não foi lido |
| V, E, D | Resultado do ponto de vista do clube | `fato_participacao.resultado` | Na partida, o resultado é `M`/`E`/`V` (mandante, empate, visitante) |
| Gols pró (GP), contra (GC), saldo (SG) | Do ponto de vista do clube | `fato_participacao` | Soma do saldo da liga = 0 (teste) |
| Aproveitamento | Pontos ÷ pontos possíveis (3 × J) | ver 4.3 | **Definição pendente** |
| Gols do campeonato | Soma do placar das partidas | `fato_partida.total_gols` | 929; nunca somar em `fato_participacao` |
| Média de gols por jogo | Gols ÷ partidas | `fato_partida` | **[CÁLCULO]** 929 ÷ 380 = 2,44 |
| % vitórias do mandante, % empates, % do visitante | Partidas com cada resultado ÷ partidas | `fato_partida.resultado` | **[CÁLCULO]** 47,4% (180), 26,6% (101), 26,1% (99) |
| Jogos sem sofrer gol (clube) | Jogos do clube com GC = 0 | `fato_participacao.sem_sofrer_gols` | Métrica do **clube**, completa |
| Jogos sem sofrer gol (goleiro) | Ranking publicado pela Wikipédia | `jogador_estatisticas.jogos_sem_sofrer_gols` | Métrica do **goleiro**, só top 12. Não confundir com a do clube |
| Gols do jogador | Gols normais + pênaltis (exclui gol contra) | `fato_gol`, `jogador_estatisticas` | Gol contra conta para o clube beneficiado, não para o artilheiro |
| Gols contra | Gol em que o clube do jogador ≠ beneficiado | `fato_gol.tipo = 'Contra'` | 18 em 2024 |
| Assistências | Ranking publicado pela Wikipédia | `jogador_estatisticas.assistencias` | Só top 11; `NULL` fora dele |
| Faixa de minuto | 01-15, 16-30, 31-45+, 46-60, 61-75, 76-90+ | `fato_gol.faixa_minuto` | Acréscimo fica na faixa do fim do tempo |
| Cartões por jogo | Cartões ÷ partidas | `fato_cartao`, `fato_partida` | Cartões sem fonte independente (P6) |

**Não existem no projeto, e não devem ser inventadas:** minutos jogados (logo, nada "por 90
minutos"), finalizações, posse, xG, público, escalações completas. Sem essas fontes, não há
como falar em "merecimento" ou "eficiência de finalização".

## 4.2 Classificação

Critérios na ordem (Art. 15 do REC, adaptado): pontos → vitórias → saldo → gols pró →
confronto direto → cartões vermelhos → cartões amarelos → sorteio.

| Ponto | Regra do projeto |
|---|---|
| Confronto direto | Só com **exatamente 2** clubes empatados (§2) e os **dois** jogos entre eles já disputados até a rodada N; compara o placar agregado (180 minutos) |
| Cartões e sorteio | Não aplicados. A fonte principal não tem cartões; os cartões do adaoduque não têm conferência independente (P6); sorteio não é dado. O empate que chega a eles fica sinalizado como não resolvido. Usar os cartões no desempate seria uma decisão nova |
| Empate não resolvido | `posicao` compartilhada (`RANK`), `empate_nao_resolvido = true`, `ordem_exibicao` alfabética **só para exibição** |
| Por rodada | **Reconstrução analítica** pela rodada nominal: "após a rodada N" = todos os jogos com `rodada ≤ N`, jogados quando forem. Não é a tabela oficial publicada em cada data |
| Final | Conferida com a CBF: 20 clubes × 9 campos, 0 divergências |

Em 2024, só o critério 1 (vitórias) foi necessário na tabela final: Vitória × Atlético-MG
(47 pts) e Atlético-GO × Cuiabá (30 pts). O confronto direto não decidiu nenhuma posição.

**Aviso obrigatório** em todo gráfico ou tabela por rodada: "Classificação por rodada
reconstruída a partir dos resultados; só a final foi conferida com a tabela oficial da CBF."

## 4.3 Aproveitamento (decisão pendente)

| Definição | Fórmula | Athletico (42 pts, 38 J) | Onde aparece |
|---|---|---|---|
| CBF | `floor(100 × P / (3 × J))`, truncado | 36 | Tabela oficial (verificado nos 20 clubes) |
| View do projeto | `round(100 × P / (3 × J), 1)` | 36,8 | `classificacao_rodada`, CSVs do Power BI |
| Site | `100 × P / (3 × J)` em JS, exibido com 1 casa | 36,8% | `web/js/dados.js` e páginas |
| DAX | `DIVIDE(P, 3 × J)`, formatado com 1 casa | 36,8% | Power BI |

Enquanto o Thiago não decidir: não mude nenhuma delas; ao citar, diga qual definição está
usando; ao comparar com a CBF, use a truncada.

## 4.4 Mandante e visitante

- "Mando" é **nominal**: quem a tabela da CBF indica como mandante. O estádio pode ser outro.
  **[CÁLCULO]** O Grêmio jogou como mandante fora da Arena em 9 de 19 jogos (estádio vindo do
  adaoduque, sem conferência independente). Antes de interpretar "força em casa", confira o
  estádio, lembrando que os nomes não estão padronizados entre as fontes.
- Compare aproveitamento ou pontos por jogo, não pontos absolutos (o número de jogos em casa e
  fora é igual, 19, mas filtros por rodada mudam isso).
- **Tamanho da amostra:** com 19 jogos, uma vitória a mais muda o aproveitamento em
  5,3 pontos percentuais (3 ÷ 57). Diferenças pequenas entre clubes não sustentam conclusões.
- Vantagem de mando da liga: **[CÁLCULO]** 47,4% de vitórias do mandante contra 26,1% do
  visitante. Por que isso acontece (torcida, viagem, gramado) é **[INTERPRETAÇÃO]**: os dados
  não testam causas.

## 4.5 Gols

- Total, média por jogo e distribuição por faixa vêm de `fato_partida` e `fato_gol`.
- **[CÁLCULO]** 76-90+ é a faixa com mais gols (210, 22,6%). As faixas de fim de tempo
  incluem acréscimos, por isso não têm a mesma duração das outras: diga isso ao comparar.
- Pênaltis (76) e gols contra (18) são tipos de gol, não "gols extras".
- Placar do intervalo: 26 jogos sem valor (0-0) e 2 divergências prováveis (P4). Para "virada"
  ou "quem marcou primeiro", prefira os minutos dos gols em `fato_gol` e diga a fonte.

## 4.6 Evolução

| Pergunta | Métrica | Ordem |
|---|---|---|
| Como a tabela mudou? | Posição por rodada (`classificacao_rodada`) | Nominal, com aviso de reconstrução |
| Quem acelerou? | Pontos no turno × returno; pontos acumulados | Nominal |
| Qual a fase do time? | Média móvel de pontos (5 jogos), sequências de invencibilidade | **Cronológica** (`data_partida`) |
| Quando liderou? | Rodadas na liderança | Nominal |

Jogos adiados (enchentes no RS, rodadas 7 e 8 entre outros) fazem as duas ordens divergirem.
Diga sempre qual ordem foi usada.

## 4.7 Comparações entre clubes

- Mesmo denominador e mesmo período para todos; prefira taxas (por jogo, %) a totais.
- Mostre o valor da liga como referência (média ou mediana).
- Confronto direto: os dois jogos, placar agregado, com mando.
- Ranking com empate: mostre o empate, não o esconda com uma ordem arbitrária.
- Variação pequena com amostra pequena é ruído até prova em contrário.

## 4.8 Cuidados de interpretação

- **Correlação não é causa.** "Quem marca mais no fim ganha mais" é associação, não
  mecanismo.
- **Regressão à média.** Um início muito acima ou abaixo tende a se aproximar da média; não
  chame isso de "queda" ou "recuperação" sem mais evidência.
- **Muitas comparações.** Entre 20 clubes e muitas métricas, algum extremo aparece por acaso.
- **Índices construídos** (ex.: a força dos elencos na Prancheta 2024, derivada de pontos, gols
  e prêmios) são modelos do jogo, não estatísticas: chame-os de **[CÁLCULO]** com a fórmula e
  nunca os apresente como medida oficial de qualidade.
- Uma conclusão analítica traz os fatos e cálculos em que se apoia e a principal limitação.
