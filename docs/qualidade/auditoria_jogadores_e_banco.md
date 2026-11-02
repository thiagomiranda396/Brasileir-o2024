# Auditoria: dados de jogadores, banco e site

Complementa a [auditoria da Fase 2](auditoria_fase2.md), que validou as partidas. Aqui estão as
verificações dos dados de jogadores (gols, cartões, assistências), do banco PostgreSQL e do JSON
publicado no site. Todas são reproduzíveis pelos testes (`tests/` e `sql/05_testes.sql`).

## 1. Gols (fonte: adaoduque/Brasileirao_Dataset, commit `15f027c`)

| Verificação | Resultado |
|---|---|
| Ligação das partidas da fonte com as 380 do projeto, pelo par (mandante, visitante) | 380 de 380 |
| Total de gols | 929, igual ao total do campeonato |
| Gols de cada clube em cada partida = placar validado (760 comparações) | **0 divergências** |
| Artilharia (12 jogadores com 10 gols ou mais) = Wikipédia em inglês | Igual nos 12, e ninguém fora da lista com 10 ou mais |
| Gols do 1º tempo (minuto ≤ 45, acréscimos inclusos) = placar do intervalo do openfootball, nas 354 partidas que o têm | 352 iguais, **2 divergentes** (ver abaixo) |

**Divergências do intervalo (pendência P4 da Fase 2, agora parcialmente resolvida).** Nas
partidas 201 (Corinthians 1 x 1 Bragantino) e 203 (Vasco 2 x 0 Fluminense), ambas da rodada 22,
o openfootball registra o placar do intervalo igual ao placar final, enquanto os minutos dos gols
na fonte de jogadores indicam 0 x 1 e 1 x 0. O empate do Corinthians aos 90+4 torna improvável um
1 x 1 no intervalo. Conclusão provável: erro de digitação no openfootball. O placar do intervalo
não é usado em nenhum indicador; a divergência fica documentada e o teste
`test_placar_do_intervalo_diverge_so_nos_casos_documentados` falha se aparecer qualquer outra.

**Gols contra.** A fonte registra o clube beneficiado; o projeto deriva o clube do jogador (o
adversário). Os 18 gols contra são coerentes com isso (constraint `CHECK` em `core.gol`).

## 2. Cartões

2.096 cartões (1.968 amarelos e 128 vermelhos). Cada cartão pertence a um dos dois clubes da
partida (validado na carga). **Não há fonte independente** para conferir os cartões jogo a jogo;
eles são apresentados como dado da fonte, sem a mesma garantia dos gols.

## 3. Jogadores

- Grão `jogador × clube`, identificado pelo nome como aparece na súmula da fonte. Homônimos de
  clubes diferentes ficam separados (ex.: "Igor Jesus" do Flamengo, meia da base, e "Ígor Jesus"
  do Botafogo, atacante). Um atleta transferido no meio do campeonato aparece uma vez por clube.
- `data/reference/jogadores_destaque.csv` dá o nome popular de 69 jogadores (ex.: "Alerrandro"
  para "Alerrandro Barra Mansa Realino de Souza") e as páginas da Wikipédia usadas nas fotos.
  Os demais aparecem com o nome da fonte.

## 4. Assistências, goleiros, seleção e prêmios (Wikipédia em inglês, CC BY-SA 4.0)

Transcrição manual das seções do artigo, consultado em 2026-10-29
([procedência](../../data/reference/wikipedia_en/PROCEDENCIA.md)). **Limitação:** o artigo lista
só os primeiros colocados (11 em assistências, 12 em jogos sem sofrer gol). No banco e no site,
quem está fora do ranking aparece com assistências em branco, nunca como zero. A carga falha se
algum nome da Wikipédia não corresponder a exatamente um jogador.

## 5. Banco PostgreSQL

`sql/05_testes.sql` (23 testes) roda dentro de uma transação desfeita:

- contagens (20 clubes, 380 partidas, 760 participações, 929 gols, 2.096 cartões, 760 linhas de
  classificação);
- integridade (19 jogos em casa e 19 fora por clube; N jogos após a rodada N; horários
  explícitos e herdados);
- constraints rejeitando dados inválidos (auto-confronto, FK inexistente, gol contra incoerente);
- não duplicação de métricas entre os grãos (gols, saldo, pontos);
- classificação final igual à da CBF (20 clubes × 9 campos) e rebaixados;
- artilharia igual à da Wikipédia;
- carga idempotente (a recarga não altera nenhuma linha).

O papel `bi_brasileirao_leitura` exporta o site e alimenta o Power BI, e recebe
`permission denied` ao tentar ler o schema `core` (verificado).

**Confronto direto (critério 4):** implementado na view `classificacao_rodada`, mas não decidiu
nenhuma posição em 2024: os únicos empates após os critérios 1 a 3 aconteceram nas rodadas 1 a 3,
entre clubes que ainda não tinham se enfrentado duas vezes.

## 6. Site

`tests/test_web.py` confere o JSON publicado (`web/data/brasileirao2024.json`) contra os CSVs:
partidas, classificação final (CBF), 38 rodadas com N jogos, gols e cartões, referências entre
tabelas e gols por jogador. No CI, o JSON é exportado de novo do banco e precisa ser idêntico ao
versionado.

## Pendências

| Código | Pendência |
|---|---|
| P1 a P3 | Herdadas da Fase 2 (URLs da CBF, REC oficial, validação jogo a jogo com a CBF) |
| P4 | Placar do intervalo: 352 de 354 conferidos; 2 divergências prováveis no openfootball |
| P6 | Cartões sem fonte independente |
| P7 | Assistências completas: não há fonte aberta com licença clara |
