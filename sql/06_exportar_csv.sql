-- =============================================================================
-- 06_exportar_csv.sql
--
-- Exporta as views do schema analytics para powerbi/dados/*.csv (UTF-8, com
-- cabeçalho). Serve para abrir o modelo do Power BI sem um PostgreSQL local
-- (modo "pasta de CSVs"); com o banco, conecte direto nas views.
-- SOMENTE PSQL; executar a partir da raiz do projeto:
--   psql -v ON_ERROR_STOP=1 -U bi_brasileirao_leitura -d brasileirao2024 -f sql/06_exportar_csv.sql
-- =============================================================================

\set ON_ERROR_STOP 1
\copy (SELECT * FROM analytics.dim_clube ORDER BY id_clube)                     TO 'powerbi/dados/dim_clube.csv'            WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy (SELECT * FROM analytics.dim_jogador ORDER BY id_jogador)                 TO 'powerbi/dados/dim_jogador.csv'          WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy (SELECT * FROM analytics.dim_rodada ORDER BY rodada)                      TO 'powerbi/dados/dim_rodada.csv'           WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy (SELECT * FROM analytics.fato_partida ORDER BY id_partida)                TO 'powerbi/dados/fato_partida.csv'         WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy (SELECT * FROM analytics.fato_participacao ORDER BY id_partida, mando)    TO 'powerbi/dados/fato_participacao.csv'    WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy (SELECT * FROM analytics.fato_gol ORDER BY id_gol)                        TO 'powerbi/dados/fato_gol.csv'             WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy (SELECT * FROM analytics.fato_cartao ORDER BY id_cartao)                  TO 'powerbi/dados/fato_cartao.csv'          WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy (SELECT * FROM analytics.classificacao_rodada ORDER BY rodada, ordem_exibicao) TO 'powerbi/dados/classificacao_rodada.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy (SELECT * FROM analytics.classificacao_final ORDER BY ordem_exibicao)     TO 'powerbi/dados/classificacao_final.csv'  WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy (SELECT * FROM analytics.jogador_estatisticas ORDER BY id_jogador)        TO 'powerbi/dados/jogador_estatisticas.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy (SELECT * FROM analytics.credito_imagem ORDER BY tipo, nome, id_jogador)  TO 'powerbi/dados/credito_imagem.csv'       WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
