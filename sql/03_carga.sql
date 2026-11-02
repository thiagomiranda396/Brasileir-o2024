-- =============================================================================
-- 03_carga.sql
--
-- Carrega os CSVs versionados no core, numa única transação:
--   CSV --\copy--> staging (text) --views tipadas--> validação --MERGE--> core --> validação
--
-- SOMENTE PSQL (\copy é um comando do psql). Execute a partir da RAIZ do projeto,
-- porque os caminhos dos CSVs são relativos:
--   psql -v ON_ERROR_STOP=1 -U bi_brasileirao -d brasileirao2024 -f sql/03_carga.sql
--
-- Idempotente: uma segunda execução com os mesmos CSVs não altera nenhuma linha do
-- core e registra 0 inserções, 0 atualizações e 0 remoções.
--
-- Em qualquer erro (arquivo, conversão de tipo, constraint, validação), o psql
-- para (ON_ERROR_STOP) e a transação inteira é desfeita: o core fica intacto e
-- nenhum registro de carga é gravado.
--
-- Compatível com PostgreSQL 15+ (MERGE). A remoção das linhas que saíram da fonte
-- é um DELETE separado e restrito a elas, em vez de WHEN NOT MATCHED BY SOURCE
-- (17+), para que o mesmo script rode em versões anteriores.
-- =============================================================================

\set ON_ERROR_STOP 1
BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Staging: espelho dos CSVs. O único TRUNCATE do projeto, restrito à staging.
-- -----------------------------------------------------------------------------
TRUNCATE staging.clubes_csv, staging.clubes_visual_csv, staging.partidas_csv,
         staging.partidas_complemento_csv, staging.jogadores_csv, staging.gols_csv,
         staging.cartoes_csv, staging.wiki_assistencias_csv,
         staging.wiki_jogos_sem_sofrer_gols_csv, staging.wiki_selecao_csv,
         staging.wiki_premios_csv, staging.escudos_clubes_csv, staging.fotos_jogadores_csv;

\copy staging.clubes_csv               FROM 'data/reference/clubes.csv'                                WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.clubes_visual_csv        FROM 'data/reference/clubes_visual.csv'                         WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.partidas_csv             FROM 'data/processed/partidas.csv'                              WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.partidas_complemento_csv FROM 'data/processed/partidas_complemento.csv'                  WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.jogadores_csv            FROM 'data/processed/jogadores.csv'                             WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.gols_csv                 FROM 'data/processed/gols.csv'                                  WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.cartoes_csv              FROM 'data/processed/cartoes.csv'                               WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.wiki_assistencias_csv    FROM 'data/reference/wikipedia_en/assistencias.csv'             WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.wiki_jogos_sem_sofrer_gols_csv FROM 'data/reference/wikipedia_en/jogos_sem_sofrer_gols.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.wiki_selecao_csv         FROM 'data/reference/wikipedia_en/selecao_do_campeonato.csv'    WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.wiki_premios_csv         FROM 'data/reference/wikipedia_en/premios_mensais.csv'          WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.escudos_clubes_csv       FROM 'data/reference/escudos_clubes.csv'                        WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.fotos_jogadores_csv      FROM 'data/reference/fotos_jogadores.csv'                       WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')


-- -----------------------------------------------------------------------------
-- 2. Views tipadas da staging: mesmas colunas e tipos do core. Um valor que não
--    converte (data, inteiro, hora) gera erro aqui e desfaz a carga.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW staging.v_clube AS
SELECT c.id_clube::char(3) AS id_clube, c.nome::varchar(60) AS nome, c.uf::char(2) AS uf,
       v.nome_completo::varchar(80) AS nome_completo, v.cidade::varchar(60) AS cidade,
       v.estadio::varchar(60) AS estadio, v.capacidade::integer AS capacidade,
       v.cor_primaria::char(7) AS cor_primaria, v.cor_secundaria::char(7) AS cor_secundaria,
       v.wiki_pt::varchar(120) AS wiki_pt
FROM staging.clubes_csv c
JOIN staging.clubes_visual_csv v USING (id_clube);

CREATE OR REPLACE VIEW staging.v_partida AS
SELECT id_partida::smallint AS id_partida, rodada::smallint AS rodada,
       data::date AS data_partida, NULLIF(hora, '')::time AS hora_inicio,
       (hora_explicita = '1') AS hora_explicita,
       id_mandante::char(3) AS id_mandante, id_visitante::char(3) AS id_visitante,
       gols_mandante::smallint AS gols_mandante, gols_visitante::smallint AS gols_visitante,
       NULLIF(gols_mandante_1t, '')::smallint AS gols_mandante_1t,
       NULLIF(gols_visitante_1t, '')::smallint AS gols_visitante_1t,
       linha_origem::integer AS linha_origem
FROM staging.partidas_csv;

CREATE OR REPLACE VIEW staging.v_partida_complemento AS
SELECT id_partida::smallint AS id_partida, estadio::varchar(80) AS estadio,
       tecnico_mandante::varchar(60) AS tecnico_mandante,
       tecnico_visitante::varchar(60) AS tecnico_visitante,
       NULLIF(formacao_mandante, '')::varchar(12) AS formacao_mandante,
       NULLIF(formacao_visitante, '')::varchar(12) AS formacao_visitante
FROM staging.partidas_complemento_csv;

CREATE OR REPLACE VIEW staging.v_jogador AS
SELECT id_jogador::varchar(80) AS id_jogador, nome_fonte::varchar(80) AS nome_fonte,
       nome_exibicao::varchar(60) AS nome_exibicao, id_clube::char(3) AS id_clube,
       NULLIF(posicao, '')::varchar(20) AS posicao, NULLIF(wiki, '')::varchar(200) AS wiki
FROM staging.jogadores_csv;

CREATE OR REPLACE VIEW staging.v_gol AS
SELECT id_gol::smallint AS id_gol, id_partida::smallint AS id_partida,
       id_jogador::varchar(80) AS id_jogador, id_clube_jogador::char(3) AS id_clube_jogador,
       id_clube_beneficiado::char(3) AS id_clube_beneficiado, minuto::smallint AS minuto,
       acrescimo::smallint AS acrescimo, periodo::char(2) AS periodo, tipo::varchar(8) AS tipo
FROM staging.gols_csv;

CREATE OR REPLACE VIEW staging.v_cartao AS
SELECT id_cartao::smallint AS id_cartao, id_partida::smallint AS id_partida,
       id_jogador::varchar(80) AS id_jogador, id_clube::char(3) AS id_clube,
       cartao::varchar(8) AS cartao, minuto::smallint AS minuto,
       acrescimo::smallint AS acrescimo, periodo::char(2) AS periodo,
       NULLIF(num_camisa, '')::smallint AS num_camisa
FROM staging.cartoes_csv;

-- Os arquivos da Wikipédia trazem o nome de exibição; a ligação com o jogador é por
-- (nome_exibicao, clube), que é UNIQUE no core.
CREATE OR REPLACE VIEW staging.v_ranking_wikipedia AS
SELECT 'assistencias'::varchar(24) AS metrica, j.id_jogador,
       w.posicao::smallint AS posicao, w.assistencias::smallint AS valor
FROM staging.wiki_assistencias_csv w
JOIN staging.v_jogador j ON j.nome_exibicao = w.jogador AND j.id_clube = w.id_clube
UNION ALL
SELECT 'jogos_sem_sofrer_gols', j.id_jogador, w.posicao::smallint, w.jogos_sem_sofrer_gols::smallint
FROM staging.wiki_jogos_sem_sofrer_gols_csv w
JOIN staging.v_jogador j ON j.nome_exibicao = w.jogador AND j.id_clube = w.id_clube;

CREATE OR REPLACE VIEW staging.v_selecao_campeonato AS
SELECT j.id_jogador, w.setor::varchar(16) AS setor
FROM staging.wiki_selecao_csv w
JOIN staging.v_jogador j ON j.nome_exibicao = w.jogador AND j.id_clube = w.id_clube;

CREATE OR REPLACE VIEW staging.v_premio_mensal AS
SELECT w.mes::smallint AS mes, w.premio::varchar(20) AS premio, j.id_jogador
FROM staging.wiki_premios_csv w
JOIN staging.v_jogador j ON j.nome_exibicao = w.jogador AND j.id_clube = w.id_clube;

CREATE OR REPLACE VIEW staging.v_escudo_clube AS
SELECT id_clube::char(3) AS id_clube, wikidata::varchar(16) AS wikidata,
       arquivo::varchar(255) AS arquivo, url_imagem::varchar(600) AS url_imagem,
       pagina_arquivo::varchar(600) AS pagina_arquivo, coalesce(autor, '')::varchar(500) AS autor,
       licenca::varchar(60) AS licenca, NULLIF(licenca_url, '')::varchar(300) AS licenca_url,
       origem_imagem::varchar(20) AS origem_imagem, consultado_em::date AS consultado_em
FROM staging.escudos_clubes_csv;

CREATE OR REPLACE VIEW staging.v_foto_jogador AS
SELECT id_jogador::varchar(80) AS id_jogador, wikidata::varchar(16) AS wikidata,
       arquivo::varchar(255) AS arquivo, url_imagem::varchar(600) AS url_imagem,
       pagina_arquivo::varchar(600) AS pagina_arquivo, coalesce(autor, '')::varchar(500) AS autor,
       licenca::varchar(60) AS licenca, NULLIF(licenca_url, '')::varchar(300) AS licenca_url,
       origem_imagem::varchar(20) AS origem_imagem, criterio::varchar(10) AS criterio,
       confirmado_por::varchar(20) AS confirmado_por, consultado_em::date AS consultado_em
FROM staging.fotos_jogadores_csv;


-- -----------------------------------------------------------------------------
-- 3. Funções de sincronização (genéricas, por catálogo). Comparam a view tipada
--    com a tabela do core pelas colunas da view e mexem só no que mudou.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION staging.colunas(origem regclass) RETURNS text[]
LANGUAGE sql STABLE AS $$
    SELECT array_agg(attname::text ORDER BY attnum)
    FROM pg_attribute WHERE attrelid = origem AND attnum > 0 AND NOT attisdropped
$$;

-- Insere as linhas novas e atualiza as alteradas; devolve as contagens calculadas
-- ANTES do MERGE (o MERGE não guarda histórico).
CREATE OR REPLACE FUNCTION staging.mesclar(alvo regclass, origem regclass, chave text[],
                                           OUT inseridas integer, OUT atualizadas integer)
LANGUAGE plpgsql AS $$
DECLARE
    cols    text[] := staging.colunas(origem);
    nao_chave text[] := ARRAY(SELECT c FROM unnest(cols) c WHERE c <> ALL (chave));
    junta   text := (SELECT string_agg(format('t.%1$I = s.%1$I', c), ' AND ') FROM unnest(chave) c);
    lista_t text := (SELECT string_agg(format('t.%I', c), ', ') FROM unnest(nao_chave) c);
    lista_s text := (SELECT string_agg(format('s.%I', c), ', ') FROM unnest(nao_chave) c);
    difere  text := format('ROW(%s) IS DISTINCT FROM ROW(%s)', lista_t, lista_s);
BEGIN
    EXECUTE format('SELECT count(*) FROM %s s WHERE NOT EXISTS (SELECT 1 FROM %s t WHERE %s)',
                   origem, alvo, junta) INTO inseridas;
    EXECUTE format('SELECT count(*) FROM %s s JOIN %s t ON %s WHERE %s',
                   origem, alvo, junta, difere) INTO atualizadas;
    EXECUTE format(
        'MERGE INTO %1$s AS t USING %2$s AS s ON %3$s '
        'WHEN MATCHED AND %4$s THEN UPDATE SET %5$s '
        'WHEN NOT MATCHED THEN INSERT (%6$s) VALUES (%7$s)',
        alvo, origem, junta, difere,
        (SELECT string_agg(format('%1$I = s.%1$I', c), ', ') FROM unnest(nao_chave) c),
        (SELECT string_agg(format('%I', c), ', ') FROM unnest(cols) c),
        (SELECT string_agg(format('s.%I', c), ', ') FROM unnest(cols) c));
END $$;

-- Remove do core só as linhas cuja chave não existe mais na fonte.
CREATE OR REPLACE FUNCTION staging.remover_ausentes(alvo regclass, origem regclass, chave text[])
RETURNS integer LANGUAGE plpgsql AS $$
DECLARE
    junta text := (SELECT string_agg(format('t.%1$I = s.%1$I', c), ' AND ') FROM unnest(chave) c);
    n integer;
BEGIN
    EXECUTE format('DELETE FROM %s t WHERE NOT EXISTS (SELECT 1 FROM %s s WHERE %s)',
                   alvo, origem, junta);
    GET DIAGNOSTICS n = ROW_COUNT;
    RETURN n;
END $$;


-- -----------------------------------------------------------------------------
-- 4. Validação da staging, antes de tocar no core.
-- -----------------------------------------------------------------------------
DO $$
DECLARE
    esperado record;
BEGIN
    FOR esperado IN
        SELECT * FROM (VALUES
            ('staging.clubes_csv',        20, (SELECT count(*) FROM staging.clubes_csv)),
            ('staging.v_clube',           20, (SELECT count(*) FROM staging.v_clube)),
            ('staging.partidas_csv',     380, (SELECT count(*) FROM staging.partidas_csv)),
            ('staging.v_partida_complemento', 380, (SELECT count(*) FROM staging.v_partida_complemento))
        ) AS t(objeto, esperado, obtido)
    LOOP
        IF esperado.obtido <> esperado.esperado THEN
            RAISE EXCEPTION 'staging: % tem % linhas; esperado %',
                esperado.objeto, esperado.obtido, esperado.esperado;
        END IF;
    END LOOP;

    IF (SELECT count(*) FROM staging.v_partida) <> 380 THEN  -- força a conversão de tipos
        RAISE EXCEPTION 'staging: conversão de partidas falhou';
    END IF;
    IF EXISTS (SELECT id_clube FROM staging.clubes_csv GROUP BY id_clube HAVING count(*) > 1) THEN
        RAISE EXCEPTION 'staging: id_clube duplicado';
    END IF;
    -- Cada linha da Wikipédia precisa corresponder a exatamente um jogador.
    IF (SELECT count(*) FROM staging.v_ranking_wikipedia) <>
       (SELECT count(*) FROM staging.wiki_assistencias_csv) +
       (SELECT count(*) FROM staging.wiki_jogos_sem_sofrer_gols_csv)
       OR (SELECT count(*) FROM staging.v_selecao_campeonato) <> (SELECT count(*) FROM staging.wiki_selecao_csv)
       OR (SELECT count(*) FROM staging.v_premio_mensal) <> (SELECT count(*) FROM staging.wiki_premios_csv) THEN
        RAISE EXCEPTION 'staging: jogador da Wikipédia sem correspondência em jogadores.csv';
    END IF;
END $$;


-- -----------------------------------------------------------------------------
-- 5. Sincronização: inserções e atualizações dos pais para os filhos; remoções dos
--    filhos para os pais (respeitando as FKs). Contagens em core.carga_execucao.
-- -----------------------------------------------------------------------------
CREATE TEMP TABLE carga_tabelas (ordem int, alvo regclass, origem regclass, chave text[])
    ON COMMIT DROP;
INSERT INTO carga_tabelas VALUES
    (1, 'core.clube',               'staging.v_clube',               '{id_clube}'),
    (2, 'core.partida',             'staging.v_partida',             '{id_partida}'),
    (3, 'core.partida_complemento', 'staging.v_partida_complemento', '{id_partida}'),
    (4, 'core.jogador',             'staging.v_jogador',             '{id_jogador}'),
    (5, 'core.gol',                 'staging.v_gol',                 '{id_gol}'),
    (6, 'core.cartao',              'staging.v_cartao',              '{id_cartao}'),
    (7, 'core.ranking_wikipedia',   'staging.v_ranking_wikipedia',   '{metrica,id_jogador}'),
    (8, 'core.selecao_campeonato',  'staging.v_selecao_campeonato',  '{id_jogador}'),
    (9, 'core.premio_mensal',       'staging.v_premio_mensal',       '{mes,premio}'),
    (10, 'core.escudo_clube',       'staging.v_escudo_clube',        '{id_clube}'),
    (11, 'core.foto_jogador',       'staging.v_foto_jogador',        '{id_jogador}');

CREATE TEMP TABLE carga_resultado (tabela text, inseridas int, atualizadas int, removidas int)
    ON COMMIT DROP;

DO $$
DECLARE
    t record;
    r record;
    n integer;
BEGIN
    FOR t IN SELECT * FROM carga_tabelas ORDER BY ordem DESC LOOP
        n := staging.remover_ausentes(t.alvo, t.origem, t.chave);
        INSERT INTO carga_resultado VALUES (t.alvo::text, 0, 0, n);
    END LOOP;
    FOR t IN SELECT * FROM carga_tabelas ORDER BY ordem LOOP
        r := staging.mesclar(t.alvo, t.origem, t.chave);
        UPDATE carga_resultado SET inseridas = r.inseridas, atualizadas = r.atualizadas
        WHERE tabela = t.alvo::text;
    END LOOP;
END $$;


-- -----------------------------------------------------------------------------
-- 6. Validação do resultado. Qualquer falha desfaz tudo, inclusive a etapa 5.
-- -----------------------------------------------------------------------------
DO $$
DECLARE
    t record;
    n_core bigint;
    n_origem bigint;
BEGIN
    FOR t IN SELECT * FROM carga_tabelas LOOP
        EXECUTE format('SELECT count(*) FROM %s', t.alvo) INTO n_core;
        EXECUTE format('SELECT count(*) FROM %s', t.origem) INTO n_origem;
        IF n_core <> n_origem THEN
            RAISE EXCEPTION 'core: % tem % linhas; a fonte tem %', t.alvo, n_core, n_origem;
        END IF;
    END LOOP;

    IF EXISTS (SELECT 1 FROM core.partida a JOIN core.partida b
               ON a.rodada = b.rodada AND a.id_mandante = b.id_visitante) THEN
        RAISE EXCEPTION 'core: clube como mandante e visitante na mesma rodada';
    END IF;

    -- Gols de cada clube em cada partida = placar validado.
    IF EXISTS (
        SELECT 1
        FROM core.partida p
        CROSS JOIN LATERAL (VALUES (p.id_mandante, p.gols_mandante),
                                   (p.id_visitante, p.gols_visitante)) AS v(id_clube, placar)
        LEFT JOIN (SELECT id_partida, id_clube_beneficiado, count(*) AS gols
                   FROM core.gol GROUP BY 1, 2) g
               ON g.id_partida = p.id_partida AND g.id_clube_beneficiado = v.id_clube
        WHERE coalesce(g.gols, 0) <> v.placar) THEN
        RAISE EXCEPTION 'core: gols por partida divergem do placar';
    END IF;

    -- Clube do gol/cartão precisa ser um dos dois clubes da partida.
    IF EXISTS (SELECT 1 FROM core.gol g JOIN core.partida p USING (id_partida)
               WHERE g.id_clube_beneficiado NOT IN (p.id_mandante, p.id_visitante)
                  OR g.id_clube_jogador NOT IN (p.id_mandante, p.id_visitante))
       OR EXISTS (SELECT 1 FROM core.cartao c JOIN core.partida p USING (id_partida)
                  WHERE c.id_clube NOT IN (p.id_mandante, p.id_visitante)) THEN
        RAISE EXCEPTION 'core: gol ou cartão de clube que não jogou a partida';
    END IF;
END $$;


-- -----------------------------------------------------------------------------
-- 7. Registro da carga e confirmação.
-- -----------------------------------------------------------------------------
WITH id AS (SELECT nextval('core.carga_execucao_seq') AS id_carga)
INSERT INTO core.carga_execucao (id_carga, tabela, inseridas, atualizadas, removidas)
SELECT id.id_carga, r.tabela, r.inseridas, r.atualizadas, r.removidas
FROM carga_resultado r CROSS JOIN id;

SELECT tabela, inseridas, atualizadas, removidas
FROM carga_resultado JOIN carga_tabelas ON tabela = alvo::text
ORDER BY ordem;

COMMIT;
