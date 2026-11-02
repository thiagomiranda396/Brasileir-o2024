# 3. SQL analítico

Documentos do projeto: `sql/04_views.sql` (os padrões já usados), `sql/05_testes.sql` (como
testar) e `docs/modelagem/proposta_fase3.md` §3 (regras contra duplicação).

Todos os exemplos abaixo foram executados contra o modelo do projeto (PostgreSQL 16, papel
`bi_brasileirao_leitura`) em 2026-11-01. Os resultados citados são **[CÁLCULO]** sobre os dados
validados.

## 3.1 Convenções

- Nomes em português, `snake_case`, sem acento nos identificadores.
- Cabeçalho com o propósito, o grão e o comando de execução; comentário curto antes de cada
  bloco não óbvio.
- `psql -v ON_ERROR_STOP=1`, executado da raiz do projeto (os caminhos são relativos).
- Exploração com o papel de leitura, só no `analytics`. Nada de `UPDATE`, `DELETE` ou DDL
  "de teste" no banco do projeto; para testar, use uma transação com `ROLLBACK`, como em
  `sql/05_testes.sql`.
- View nova: `COMMENT ON VIEW` quando houver ressalva (ex.: reconstrução analítica).

## 3.2 Padrões que o projeto já usa

| Padrão | Para quê | Exemplo no projeto |
|---|---|---|
| `CROSS JOIN LATERAL (VALUES ...)` | Transformar 1 partida em 2 participações (mandante e visitante) | `analytics.fato_participacao` |
| `SUM(...) OVER (PARTITION BY id_clube ORDER BY rodada)` | Acumulado por rodada | `analytics.classificacao_rodada` (CTE `acumulado`) |
| `RANK()` × `ROW_NUMBER()` | Posição com empate compartilhado × ordem única de exibição | `classificacao_rodada` |
| `COUNT(*) OVER (PARTITION BY ...)` | Tamanho do grupo empatado | CTE `criterios` |
| `COUNT(*) FILTER (WHERE ...)` | Várias contagens numa passada | `jogador_estatisticas` |
| `IS DISTINCT FROM` | Comparar com `NULL` sem surpresa | `staging.mesclar` (MERGE) |
| Agregar antes de juntar | Evitar multiplicar linhas | Subconsultas de gols e cartões em `jogador_estatisticas` |

## 3.3 Exemplos conferidos

**Casa × fora por clube (CTE + `FILTER`).** Use os denominadores reais (`count(*)`), não 19
fixo.

```sql
WITH por_mando AS (
    SELECT id_clube,
           round(100.0 * sum(pontos) FILTER (WHERE mando = 'Casa')
                       / (3 * count(*) FILTER (WHERE mando = 'Casa')), 1) AS aprov_casa,
           round(100.0 * sum(pontos) FILTER (WHERE mando = 'Fora')
                       / (3 * count(*) FILTER (WHERE mando = 'Fora')), 1) AS aprov_fora
    FROM analytics.fato_participacao
    GROUP BY id_clube
)
SELECT id_clube, aprov_casa, aprov_fora, aprov_casa - aprov_fora AS vantagem_casa_pp
FROM por_mando
ORDER BY vantagem_casa_pp DESC;
-- Fortaleza no topo: 82,5% em casa × 36,8% fora (45,7 pontos percentuais).
```

Lição: no PostgreSQL, `ORDER BY aprov_casa - aprov_fora` direto no mesmo `SELECT` falha
(um alias de saída não entra numa expressão do `ORDER BY`). A CTE resolve e deixa a consulta
mais legível.

**Maior sequência invicta (ilhas e lacunas).** Sequência é **cronológica**: ordene por
`data_partida`, não pela rodada nominal (jogos adiados mudariam a ordem).

```sql
WITH jogos AS (
    SELECT id_clube, resultado,
           row_number() OVER (PARTITION BY id_clube ORDER BY data_partida, id_partida) AS n
    FROM analytics.fato_participacao
),
ilhas AS (
    SELECT id_clube, n - row_number() OVER (PARTITION BY id_clube ORDER BY n) AS grupo
    FROM jogos
    WHERE resultado <> 'D'
)
SELECT id_clube, max(tamanho) AS maior_invencibilidade
FROM (SELECT id_clube, grupo, count(*) AS tamanho FROM ilhas GROUP BY id_clube, grupo) s
GROUP BY id_clube
ORDER BY maior_invencibilidade DESC;
-- Internacional e Botafogo: 16 jogos.
```

**Variação de posição (`LAG`).**

```sql
SELECT rodada, posicao,
       lag(posicao) OVER (ORDER BY rodada) - posicao AS variacao   -- positivo = subiu
FROM analytics.classificacao_rodada
WHERE id_clube = 'BOT'
ORDER BY rodada;
```

**Participação percentual (janela sobre agregado).**

```sql
SELECT faixa_minuto, count(*) AS gols,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct
FROM analytics.fato_gol
GROUP BY faixa_minuto
ORDER BY faixa_minuto;
-- 76-90+: 210 gols (22,6%), a faixa com mais gols.
```

**Turno × returno.**

```sql
SELECT id_clube,
       sum(pontos) FILTER (WHERE rodada <= 19) AS pontos_turno,
       sum(pontos) FILTER (WHERE rodada >= 20) AS pontos_returno
FROM analytics.fato_participacao
GROUP BY id_clube
ORDER BY sum(pontos) FILTER (WHERE rodada >= 20) - sum(pontos) FILTER (WHERE rodada <= 19) DESC;
-- Corinthians: 19 → 37 pontos.
```

Atenção: turno e returno aqui são **nominais** (rodada ≤ 19). Um jogo adiado da rodada 7 conta
no turno mesmo que tenha sido disputado em julho.

**Forma recente (média móvel de 5 jogos, cronológica).**

```sql
SELECT id_clube, data_partida, pontos,
       round(avg(pontos) OVER (PARTITION BY id_clube ORDER BY data_partida, id_partida
                               ROWS BETWEEN 4 PRECEDING AND CURRENT ROW), 2) AS media_ultimos_5
FROM analytics.fato_participacao;
```

Use `ROWS`, não `RANGE`: a janela é de 5 jogos, não de 5 datas. Os 4 primeiros jogos de cada
clube têm janela menor; marque ou filtre esses pontos num gráfico.

**Aproveitamento: as três definições em jogo** (decisão pendente; ver
`estatistica_esportiva.md`).

```sql
SELECT clube, pontos, jogos,
       floor(100.0 * pontos / (3 * jogos))    AS aprov_cbf_truncado,   -- Athletico: 36
       round(100.0 * pontos / (3 * jogos), 1) AS aprov_projeto,        -- Athletico: 36.8
       aproveitamento                          AS aprov_view            -- igual ao do projeto
FROM analytics.classificacao_final
ORDER BY ordem_exibicao;
```

**Reconciliação entre grãos** (padrão de teste: o esperado é zero linha).

```sql
SELECT p.id_partida, p.total_gols, count(g.id_gol) AS eventos
FROM analytics.fato_partida p
LEFT JOIN analytics.fato_gol g USING (id_partida)
GROUP BY p.id_partida, p.total_gols
HAVING count(g.id_gol) <> p.total_gols;
```

## 3.4 Armadilhas

| Armadilha | Sintoma | Como evitar |
|---|---|---|
| Somar no grão errado | 1.858 gols em vez de 929 | Métrica do campeonato em `fato_partida`; do clube em `fato_participacao` |
| `JOIN` que multiplica | Totais inflados após juntar gols com participações | Agregue antes; confira `count(*)` antes e depois do `JOIN` |
| Divisão inteira | `100 * pontos / (3 * jogos)` entre inteiros trunca sem avisar | Use `100.0 * ...` e escolha explicitamente `round` ou `floor` |
| Média de médias | Média dos aproveitamentos dos clubes ≠ aproveitamento geral | Some numeradores e denominadores, depois divida |
| `NULL` em agregação | `avg(assistencias)` ignora quem está fora do ranking e parece "média da liga" | Diga sobre qual população a métrica vale; não use `COALESCE(..., 0)` em ranking parcial |
| `NOT IN` com `NULL` | Subconsulta com um `NULL` faz o `NOT IN` não devolver nada | Prefira `NOT EXISTS` |
| Alias no `ORDER BY` com expressão | `column "x" does not exist` | CTE ou repetir a expressão |
| Ordem nominal × cronológica | Sequências e "forma" erradas por causa de jogos adiados | Sequências por `data_partida`; tabela por `rodada` |
| Empate na ordenação | Top N instável entre execuções | Critério de desempate explícito (`ordem_exibicao`, nome) |
| Ordenação de texto | "São Paulo" depois de "Santos" com collation `C` | O banco usa ICU `pt-BR`. Atenção: o desempate de `ordem_exibicao` usa `COLLATE "C"` (código de caractere); só afeta empates não resolvidos, que não ocorrem na tabela final |
| Comparar textos de fontes diferentes | 19 de 19 jogos do Botafogo "fora do estádio" só por grafia | Padronize (com aprovação) antes de comparar nomes |
| Horário sem fuso | Conclusões sobre "jogos à noite" | A fonte não informa o fuso; trate como horário local declarado, com ressalva |

## 3.5 Checklist de uma view ou indicador novo

- [ ] Grão escrito no comentário e conferido com `count(*)` e `count(DISTINCT chave)`.
- [ ] Lê só do `core` ou de outras views do `analytics`; nenhuma regra duplicada.
- [ ] Teste em `sql/05_testes.sql` com o valor esperado ou uma reconciliação.
- [ ] Privilégio do papel de leitura (o bloco `DO` no fim de `04_views.sql` cobre).
- [ ] Se o Power BI ou o site consomem: `sql/06_exportar_csv.sql`, `scripts/exportar_web.py`,
      `powerbi/medidas.dax`, `web/js/` e `tests/test_web.py`.
- [ ] `docs/modelagem/modelo_dados.md` atualizado.
