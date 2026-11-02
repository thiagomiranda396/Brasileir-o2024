-- =============================================================================
-- 05_testes.sql
--
-- Testes do banco. Cada teste é um bloco que lança exceção se falhar; com
-- ON_ERROR_STOP o psql para no primeiro erro. Nada é gravado: tudo roda numa
-- transação desfeita no fim (ROLLBACK).
--   psql -v ON_ERROR_STOP=1 -U bi_brasileirao -d brasileirao2024 -f sql/05_testes.sql
-- Saída esperada: uma linha "OK" por teste e, no fim, "TODOS OS TESTES PASSARAM".
-- =============================================================================

\set ON_ERROR_STOP 1
\pset tuples_only on
\pset format unaligned
BEGIN;

CREATE TEMP TABLE resultado_teste (ordem serial, teste text) ON COMMIT DROP;

-- Auxiliar: falha se a condição não for verdadeira; senão imprime "OK  <teste>".
CREATE FUNCTION pg_temp.afirmar(condicao boolean, teste text)
RETURNS text LANGUAGE plpgsql AS $$
BEGIN
    IF condicao IS NOT TRUE THEN
        RAISE EXCEPTION 'FALHOU: %', teste;
    END IF;
    INSERT INTO resultado_teste (teste) VALUES (teste);
    RETURN 'OK  ' || teste;
END $$;


-- 1. Contagens --------------------------------------------------------------
SELECT pg_temp.afirmar((SELECT count(*) FROM core.clube) = 20, 'contagem: 20 clubes');
SELECT pg_temp.afirmar((SELECT count(*) FROM core.partida) = 380, 'contagem: 380 partidas');
SELECT pg_temp.afirmar((SELECT count(*) FROM analytics.fato_participacao) = 760,
                       'contagem: 760 participações');
SELECT pg_temp.afirmar((SELECT count(*) FROM core.gol) = 929, 'contagem: 929 gols');
SELECT pg_temp.afirmar((SELECT count(*) FROM core.cartao) = 2096, 'contagem: 2.096 cartões');
SELECT pg_temp.afirmar((SELECT count(*) FROM analytics.classificacao_rodada) = 760,
                       'contagem: 20 clubes × 38 rodadas na classificação');

-- 2. Integridade ------------------------------------------------------------
SELECT pg_temp.afirmar(NOT EXISTS (
    SELECT 1 FROM core.partida a JOIN core.partida b
      ON a.rodada = b.rodada AND a.id_mandante = b.id_visitante),
    'integridade: nenhum clube como mandante e visitante na mesma rodada');

SELECT pg_temp.afirmar(NOT EXISTS (
    SELECT id_clube FROM analytics.fato_participacao GROUP BY id_clube
    HAVING count(*) FILTER (WHERE mando = 'Casa') <> 19
        OR count(*) FILTER (WHERE mando = 'Fora') <> 19),
    'integridade: 19 jogos em casa e 19 fora por clube');

SELECT pg_temp.afirmar(NOT EXISTS (
    SELECT 1 FROM analytics.classificacao_rodada WHERE jogos <> rodada),
    'integridade: após a rodada N, todo clube tem N jogos');

SELECT pg_temp.afirmar(
    (SELECT count(*) FILTER (WHERE hora_explicita) = 230
        AND count(*) FILTER (WHERE NOT hora_explicita) = 150 FROM core.partida),
    'rastreabilidade: 230 horários explícitos e 150 herdados');

-- 3. Constraints rejeitam dados inválidos (cada tentativa é desfeita) -------
DO $$
DECLARE
    rejeitou boolean;
BEGIN
    BEGIN
        INSERT INTO core.partida (id_partida, rodada, data_partida, hora_explicita, id_mandante,
                                  id_visitante, gols_mandante, gols_visitante, linha_origem)
        VALUES (999, 1, '2024-05-01', false, 'BOT', 'BOT', 1, 0, 1);
        rejeitou := false;
    EXCEPTION WHEN check_violation THEN rejeitou := true;
    END;
    IF NOT rejeitou THEN RAISE EXCEPTION 'FALHOU: partida de um clube contra ele mesmo'; END IF;

    BEGIN
        INSERT INTO core.partida (id_partida, rodada, data_partida, hora_explicita, id_mandante,
                                  id_visitante, gols_mandante, gols_visitante, linha_origem)
        VALUES (999, 1, '2024-05-01', false, 'XXX', 'YYY', 1, 0, 1);
        rejeitou := false;
    EXCEPTION WHEN foreign_key_violation THEN rejeitou := true;
    END;
    IF NOT rejeitou THEN RAISE EXCEPTION 'FALHOU: partida com clube inexistente'; END IF;

    BEGIN
        UPDATE core.gol SET tipo = 'Contra' WHERE id_gol = 1;  -- mesmo clube: não pode ser contra
        rejeitou := false;
    EXCEPTION WHEN check_violation THEN rejeitou := true;
    END;
    IF NOT rejeitou THEN RAISE EXCEPTION 'FALHOU: gol contra creditado ao próprio clube'; END IF;
END $$;
SELECT pg_temp.afirmar(true, 'constraints: rejeitam auto-confronto, FK inválida e gol contra incoerente');

-- 4. Não duplicação das métricas -------------------------------------------
SELECT pg_temp.afirmar(
    (SELECT count(DISTINCT id_partida) FROM analytics.fato_participacao) = 380,
    'grão: participação cobre 380 partidas distintas');
SELECT pg_temp.afirmar(
    (SELECT sum(gols_pro) FROM analytics.fato_participacao)
        = (SELECT sum(total_gols) FROM analytics.fato_partida)
    AND (SELECT sum(total_gols) FROM analytics.fato_partida) = 929,
    'grão: gols da participação = gols das partidas = 929');
SELECT pg_temp.afirmar((SELECT sum(saldo) FROM analytics.fato_participacao) = 0,
                       'grão: soma dos saldos = 0');
SELECT pg_temp.afirmar(
    (SELECT sum(pontos) FROM analytics.fato_participacao) =
    (SELECT 3 * count(*) FILTER (WHERE resultado <> 'E') + 2 * count(*) FILTER (WHERE resultado = 'E')
     FROM analytics.fato_partida),
    'grão: pontos = 3 × partidas com vencedor + 2 × empates');
SELECT pg_temp.afirmar(
    (SELECT sum(gols) + sum(gols_contra) FROM analytics.jogador_estatisticas) = 929,
    'grão: gols dos jogadores + gols contra = 929');
SELECT pg_temp.afirmar(
    (SELECT count(*) FROM analytics.fato_gol) = 929
    AND (SELECT count(*) FROM analytics.fato_cartao) = 2096,
    'grão: views de gols e cartões não duplicam linhas');

-- 5. Classificação final = tabela oficial da CBF ----------------------------
SELECT pg_temp.afirmar((
WITH oficial(id_clube, posicao, pontos, jogos, vitorias, empates, derrotas, gols_pro, gols_contra) AS (
    VALUES ('BOT', 1, 79, 38, 23, 10,  5, 59, 29), ('PAL',  2, 73, 38, 22,  7,  9, 60, 33),
           ('FLA', 3, 70, 38, 20, 10,  8, 61, 42), ('FOR',  4, 68, 38, 19, 11,  8, 53, 39),
           ('INT', 5, 65, 38, 18, 11,  9, 53, 36), ('SPA',  6, 59, 38, 17,  8, 13, 53, 43),
           ('COR', 7, 56, 38, 15, 11, 12, 54, 45), ('BAH',  8, 53, 38, 15,  8, 15, 49, 49),
           ('CRU', 9, 52, 38, 14, 10, 14, 43, 41), ('VAS', 10, 50, 38, 14,  8, 16, 43, 56),
           ('VIT',11, 47, 38, 13,  8, 17, 45, 52), ('ATM', 12, 47, 38, 11, 14, 13, 47, 54),
           ('FLU',13, 46, 38, 12, 10, 16, 33, 39), ('GRE', 14, 45, 38, 12,  9, 17, 44, 50),
           ('JUV',15, 45, 38, 11, 12, 15, 48, 59), ('RBB', 16, 44, 38, 10, 14, 14, 44, 48),
           ('ATP',17, 42, 38, 11,  9, 18, 40, 46), ('CRI', 18, 38, 38,  9, 11, 18, 42, 61),
           ('ATG',19, 30, 38,  7,  9, 22, 29, 58), ('CUI', 20, 30, 38,  6, 12, 20, 29, 49)
)
SELECT NOT EXISTS (
        SELECT id_clube, posicao, pontos, jogos, vitorias, empates, derrotas, gols_pro, gols_contra
        FROM oficial
        EXCEPT
        SELECT id_clube::text, posicao::int, pontos::int, jogos::int, vitorias::int, empates::int,
               derrotas::int, gols_pro::int, gols_contra::int
        FROM analytics.classificacao_final)
    AND (SELECT count(*) FROM analytics.classificacao_final) = 20
    AND NOT EXISTS (SELECT 1 FROM analytics.classificacao_final WHERE empate_nao_resolvido)),
    'classificação final igual à da CBF (20 clubes × 9 campos), sem empate não resolvido');

SELECT pg_temp.afirmar(
    (SELECT string_agg(id_clube, ',' ORDER BY ordem_exibicao) FROM analytics.classificacao_final
     WHERE destino = 'Rebaixado') = 'ATP,CRI,ATG,CUI',
    'classificação final: rebaixados ATP, CRI, ATG e CUI');

-- 6. Artilharia = Wikipédia (12 primeiros) ---------------------------------
SELECT pg_temp.afirmar((
WITH wiki(nome, id_clube, gols) AS (
    VALUES ('Yuri Alberto', 'COR', 15), ('Alerrandro', 'VIT', 15), ('Estêvão', 'PAL', 13),
           ('Pablo Vegetti', 'VAS', 12), ('Pedro', 'FLA', 11), ('Wesley', 'INT', 11),
           ('Raphael Veiga', 'PAL', 11), ('Luciano', 'SPA', 11), ('Hulk', 'ATM', 10),
           ('Rodrigo Garro', 'COR', 10), ('Flaco López', 'PAL', 10), ('Lucas Moura', 'SPA', 10)
)
SELECT (SELECT count(*) FROM wiki w JOIN analytics.jogador_estatisticas j
       ON j.nome_exibicao = w.nome AND j.id_clube = w.id_clube AND j.gols = w.gols) = 12
    AND (SELECT count(*) FROM analytics.jogador_estatisticas WHERE gols >= 10) = 12),
    'artilharia igual à da Wikipédia (12 jogadores com 10 gols ou mais)');

-- 7. Imagens (escudos e fotos) ----------------------------------------------
SELECT pg_temp.afirmar(
    (SELECT count(*) FROM analytics.dim_clube) = 20
    AND (SELECT count(*) FROM analytics.dim_jogador) = (SELECT count(*) FROM core.jogador)
    AND (SELECT count(*) FROM analytics.credito_imagem)
        = (SELECT count(*) FROM core.escudo_clube) + (SELECT count(*) FROM core.foto_jogador)
    AND NOT EXISTS (SELECT 1 FROM analytics.credito_imagem
                    WHERE url_imagem !~ '^https://(upload|thumb)\.wikimedia\.org/'
                       OR url_imagem LIKE '%utm\_%'
                       OR (licenca !~* '^(CC0|CC BY(-SA)? [0-9]|Public domain|PD)'
                           AND NOT (tipo = 'Escudo' AND licenca = 'Uso justo'))
                       OR (autor = '' AND licenca !~* '^(CC0|Public domain|PD)')),
    'imagens: cada imagem tem crédito, licença livre e URL da Wikimedia, sem duplicar as dimensões');

SELECT pg_temp.afirmar(NOT EXISTS (
    SELECT 1 FROM core.foto_jogador f JOIN core.jogador j USING (id_jogador)
    GROUP BY f.wikidata, j.id_clube HAVING count(*) > 1),
    'imagens: nenhuma pessoa da Wikidata é a foto de dois jogadores do mesmo clube');

-- 8. Carga idempotente ------------------------------------------------------
SELECT pg_temp.afirmar(
    NOT EXISTS (SELECT 1 FROM core.carga_execucao
                WHERE id_carga = (SELECT max(id_carga) FROM core.carga_execucao)
                  AND (inseridas, atualizadas, removidas) <> (0, 0, 0))
    OR (SELECT count(DISTINCT id_carga) FROM core.carga_execucao) = 1,
    'carga: a última recarga não alterou nada (ou houve só a carga inicial)');

-- Resultado -----------------------------------------------------------------
SELECT 'TODOS OS TESTES PASSARAM (' || count(*) || ')' FROM resultado_teste;
ROLLBACK;
