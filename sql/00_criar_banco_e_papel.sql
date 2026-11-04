-- =============================================================================
-- 00_criar_banco_e_papel.sql
--
-- STATUS: testado num PostgreSQL limpo e no CI. Execute no seu servidor local
-- seguindo docs/modelagem/criacao_banco.md.
--
-- Cria os papéis do projeto e o banco dedicado brasileirao2024 no PostgreSQL 18
-- local. NÃO altera, remove nem concede nada em bancos ou papéis existentes
-- (inclusive os do TechstoreVendas).
--
-- Este arquivo contém SOMENTE SQL padrão do PostgreSQL: nenhum metacomando do
-- psql (\set, \password, \gexec...). Ele pode ser executado:
--   * pelo psql (recomendado): ver docs/modelagem/criacao_banco.md, seção 3;
--   * pelo pgAdmin, bloco a bloco: ver docs/modelagem/criacao_banco.md, seção 4.
--     ATENÇÃO: no pgAdmin, o BLOCO 3 (CREATE DATABASE) precisa ser executado
--     SOZINHO, porque CREATE DATABASE não pode rodar dentro de uma transação, e
--     o pgAdmin envia vários comandos selecionados juntos numa só transação.
--
-- Executado por um administrador (ex.: postgres), conectado ao banco "postgres".
-- Se um papel ou o banco já existir, o CREATE correspondente falha e NADA
-- existente é modificado.
--
-- Senhas NÃO ficam neste arquivo: são definidas depois, com \password no psql
-- (docs/modelagem/criacao_banco.md, seção 3, passo 3).
-- =============================================================================


-- =============================================================================
-- BLOCO 1. Pré-verificação, SOMENTE LEITURA. Confira cada resultado antes de seguir.
-- =============================================================================

-- 1a. Versão: espera-se PostgreSQL 18.x (MERGE ... WHEN NOT MATCHED BY SOURCE exige 17+).
SELECT version();

-- 1b. Nomes livres: espera-se 0 linhas em cada consulta.
SELECT rolname FROM pg_roles WHERE rolname IN ('bi_brasileirao', 'bi_brasileirao_leitura');
SELECT datname FROM pg_database WHERE datname = 'brasileirao2024';

-- 1c. ICU com pt-BR: espera-se 1 linha (sem ela, use a alternativa do BLOCO 3).
SELECT collname FROM pg_collation WHERE collprovider = 'i' AND collname = 'pt-BR-x-icu';

-- 1d. Criptografia de senha: espera-se 'scram-sha-256'.
SHOW password_encryption;

-- 1e. Quem está executando: espera-se um superusuário (rolsuper = true).
SELECT current_user, rolsuper FROM pg_roles WHERE rolname = current_user;


-- =============================================================================
-- BLOCO 2. Papéis. (No pgAdmin, os dois CREATE ROLE e os COMMENTs podem ir juntos.)
-- =============================================================================

-- Papel principal: dono do banco; executa DDL, carga e testes do projeto.
CREATE ROLE bi_brasileirao WITH
    LOGIN               -- precisa conectar para executar os scripts do projeto
    NOSUPERUSER         -- nenhum poder sobre o servidor ou sobre outros bancos
    NOCREATEDB          -- o banco é criado aqui pelo administrador; o papel não cria outros
    NOCREATEROLE        -- não cria nem altera papéis
    NOREPLICATION       -- não é usado para replicação
    NOBYPASSRLS         -- respeita políticas de segurança por linha, se houver
    INHERIT
    CONNECTION LIMIT 5; -- uso local por uma pessoa; limita conexões esquecidas abertas

COMMENT ON ROLE bi_brasileirao IS
    'Projeto Brasileirão 2024: dono do banco brasileirao2024 (DDL, carga, testes)';

-- Papel de leitura para o Power BI: privilégio mínimo.
CREATE ROLE bi_brasileirao_leitura WITH
    LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS INHERIT
    CONNECTION LIMIT 5;

COMMENT ON ROLE bi_brasileirao_leitura IS
    'Projeto Brasileirão 2024: somente leitura do schema analytics (Power BI)';


-- =============================================================================
-- BLOCO 3. Banco dedicado. NO PGADMIN, EXECUTE ESTE COMANDO SOZINHO.
--   TEMPLATE template0 : banco limpo, sem objetos herdados de template1.
--   ENCODING UTF8      : nomes com acentuação (Grêmio, São Paulo...).
--   ICU pt-BR          : ordenação correta de nomes com acento.
-- Alternativa sem ICU (se a consulta 1c não retornar linha): troque as linhas
--   LOCALE_PROVIDER = icu / ICU_LOCALE = 'pt-BR'
-- por
--   LOCALE_PROVIDER = builtin / BUILTIN_LOCALE = 'C.UTF-8'
-- (ordenação por código de caractere: acentos ordenam depois de 'z').
-- =============================================================================

CREATE DATABASE brasileirao2024 WITH
    OWNER            = bi_brasileirao
    TEMPLATE         = template0
    ENCODING         = 'UTF8'
    LOCALE_PROVIDER  = icu
    ICU_LOCALE       = 'pt-BR'
    CONNECTION LIMIT = 10;


-- =============================================================================
-- BLOCO 4. Acesso ao banco. (Executar depois do BLOCO 3, ainda conectado a "postgres".)
-- =============================================================================

COMMENT ON DATABASE brasileirao2024 IS 'Projeto de BI: Campeonato Brasileiro Série A 2024';

-- Por padrão, PUBLIC (todos os papéis do servidor) pode conectar e criar tabelas
-- temporárias em qualquer banco novo. Isto remove esse acesso: só os papéis do
-- projeto entram. O dono (bi_brasileirao) mantém todos os seus privilégios.
REVOKE ALL ON DATABASE brasileirao2024 FROM PUBLIC;

-- O papel de leitura só pode conectar: sem TEMPORARY e sem CREATE.
GRANT CONNECT ON DATABASE brasileirao2024 TO bi_brasileirao_leitura;


-- =============================================================================
-- BLOCO 5. Conferência final, SOMENTE LEITURA.
-- =============================================================================

-- Espera-se: rolsuper, rolcreatedb e rolcreaterole = false; rolcanlogin = true.
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolcanlogin, rolconnlimit,
       rolpassword IS NOT NULL AS tem_senha    -- 'tem_senha' só fica true após o \password
FROM pg_authid WHERE rolname LIKE 'bi_brasileirao%' ORDER BY rolname;

-- Espera-se: dono = bi_brasileirao, provedor 'i' (ICU), datacl sem entrada para PUBLIC ("=").
SELECT datname, pg_get_userbyid(datdba) AS dono, datlocprovider, datcollate, datacl   -- colunas presentes do PostgreSQL 15 ao 18
FROM pg_database WHERE datname = 'brasileirao2024';


-- =============================================================================
-- PRÉVIA (não faz parte deste script): privilégios DENTRO do banco, concedidos
-- em 01_schemas.sql, executado como bi_brasileirao conectado a brasileirao2024:
--
--   GRANT USAGE ON SCHEMA analytics TO bi_brasileirao_leitura;
--   GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO bi_brasileirao_leitura;
--   ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO bi_brasileirao_leitura;
--
-- Nenhum privilégio em staging ou core para o papel de leitura. As views de
-- analytics executam com os privilégios do dono (não são security_invoker).
-- =============================================================================

-- =============================================================================
-- REVERSÃO (NÃO EXECUTAR; só para referência, se você decidir desfazer).
-- Afeta somente os objetos criados por este script. No pgAdmin, um comando por vez.
--   DROP DATABASE brasileirao2024;
--   DROP ROLE bi_brasileirao_leitura;
--   DROP ROLE bi_brasileirao;
-- =============================================================================
