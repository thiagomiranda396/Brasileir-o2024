-- =============================================================================
-- executar_tudo.sql
--
-- Cria a estrutura, carrega os dados, cria as views e roda os testes, em ordem.
-- Pré-requisito: banco e papéis criados por 00_criar_banco_e_papel.sql.
-- Executar a partir da RAIZ do projeto (os caminhos dos CSVs são relativos):
--   psql -v ON_ERROR_STOP=1 -U bi_brasileirao -d brasileirao2024 -f sql/executar_tudo.sql
-- =============================================================================

\set ON_ERROR_STOP 1
\ir 01_schemas.sql
\ir 02_tabelas.sql
\ir 03_carga.sql
\ir 04_views.sql
\ir 05_testes.sql
