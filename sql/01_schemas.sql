-- =============================================================================
-- 01_schemas.sql
--
-- Cria os três schemas do projeto e os privilégios do papel de leitura.
-- Executado por bi_brasileirao, conectado ao banco brasileirao2024:
--   psql -v ON_ERROR_STOP=1 -U bi_brasileirao -d brasileirao2024 -f sql/01_schemas.sql
--
-- Idempotente: pode ser executado de novo sem efeito colateral.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS analytics;

COMMENT ON SCHEMA staging   IS 'Espelho fiel dos CSVs (tudo text, sem constraints) e funções de carga';
COMMENT ON SCHEMA core      IS 'Dados tipados e íntegros (PK, FK, CHECK, UNIQUE); fonte da verdade';
COMMENT ON SCHEMA analytics IS 'Views de leitura: contrato com o Power BI e com o site';

-- O schema public não é usado pelo projeto.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- Papel de leitura (Power BI): só o schema analytics, só SELECT.
-- Ignorado em silêncio se o papel opcional não tiver sido criado.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bi_brasileirao_leitura') THEN
        GRANT USAGE ON SCHEMA analytics TO bi_brasileirao_leitura;
        GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO bi_brasileirao_leitura;
        ALTER DEFAULT PRIVILEGES IN SCHEMA analytics
            GRANT SELECT ON TABLES TO bi_brasileirao_leitura;
    END IF;
END $$;
