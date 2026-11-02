-- =============================================================================
-- 04_views.sql
--
-- Camada analytics: views de leitura, contrato com o Power BI e com o site.
-- Executado por bi_brasileirao, depois de 02_tabelas.sql:
--   psql -v ON_ERROR_STOP=1 -U bi_brasileirao -d brasileirao2024 -f sql/04_views.sql
--
-- Regra contra duplicação de métricas: cada métrica tem um grão de origem e só é
-- calculada nele.
--   fato_partida      (380)  métricas do campeonato: partidas, gols, resultados
--   fato_participacao (760)  métricas por clube: pontos, V/E/D, gols pró/contra
--   fato_gol          (929)  métricas por jogador e por minuto
--   fato_cartao      (2096)  disciplina
--
-- A classificação por rodada é uma RECONSTRUÇÃO ANALÍTICA pela rodada nominal, não
-- a classificação oficial publicada pela CBF em cada data. Só a rodada 38 foi
-- conferida com a tabela oficial.
-- =============================================================================

-- Recria tudo do zero: as views só dependem do core.
DROP VIEW IF EXISTS
    analytics.credito_imagem, analytics.premio_mensal, analytics.selecao_campeonato, analytics.jogador_estatisticas, analytics.classificacao_final,
    analytics.classificacao_rodada, analytics.fato_cartao, analytics.fato_gol,
    analytics.fato_participacao, analytics.fato_partida, analytics.dim_rodada,
    analytics.dim_jogador, analytics.dim_clube
CASCADE;


-- -----------------------------------------------------------------------------
-- Dimensões
-- -----------------------------------------------------------------------------
-- escudo_url e foto_url: miniatura na Wikimedia Commons (NULL quando não há imagem livre
-- confirmada). No Power BI, marque a coluna com a categoria de dados "URL da imagem".
CREATE VIEW analytics.dim_clube AS
SELECT c.id_clube, c.nome, c.uf, c.nome_completo, c.cidade, c.estadio, c.capacidade,
       c.cor_primaria, c.cor_secundaria, c.wiki_pt, e.url_imagem AS escudo_url
FROM core.clube c
LEFT JOIN core.escudo_clube e USING (id_clube);

CREATE VIEW analytics.dim_jogador AS
SELECT j.id_jogador, j.nome_exibicao, j.nome_fonte, j.id_clube, c.nome AS clube,
       coalesce(j.posicao, 'Não informada') AS posicao, j.wiki, f.url_imagem AS foto_url
FROM core.jogador j
JOIN core.clube c USING (id_clube)
LEFT JOIN core.foto_jogador f USING (id_jogador);

-- Grão: rodada nominal (38). Datas da primeira e da última partida da rodada,
-- inclusive jogos adiados.
CREATE VIEW analytics.dim_rodada AS
SELECT rodada,
       CASE WHEN rodada <= 19 THEN 'Turno' ELSE 'Returno' END AS turno,
       min(data_partida) AS data_inicio,
       max(data_partida) AS data_fim
FROM core.partida
GROUP BY rodada;


-- -----------------------------------------------------------------------------
-- Fatos
-- -----------------------------------------------------------------------------

-- Grão: partida (380).
CREATE VIEW analytics.fato_partida AS
SELECT p.id_partida, p.rodada, p.data_partida, p.hora_inicio, p.hora_explicita,
       p.id_mandante, p.id_visitante, p.gols_mandante, p.gols_visitante,
       p.gols_mandante_1t, p.gols_visitante_1t,
       p.gols_mandante + p.gols_visitante AS total_gols,
       p.resultado,
       CASE p.resultado WHEN 'M' THEN 'Vitória do mandante'
                        WHEN 'E' THEN 'Empate'
                        ELSE 'Vitória do visitante' END AS resultado_descricao,
       c.estadio, c.tecnico_mandante, c.tecnico_visitante,
       c.formacao_mandante, c.formacao_visitante
FROM core.partida p
JOIN core.partida_complemento c USING (id_partida);

-- Grão: clube × partida (760). Chave natural: (id_partida, id_clube).
CREATE VIEW analytics.fato_participacao AS
SELECT p.id_partida, p.rodada, p.data_partida,
       v.id_clube, v.id_adversario, v.mando,
       v.gols_pro, v.gols_contra, v.gols_pro - v.gols_contra AS saldo,
       CASE WHEN v.gols_pro > v.gols_contra THEN 'V'
            WHEN v.gols_pro = v.gols_contra THEN 'E' ELSE 'D' END AS resultado,
       CASE WHEN v.gols_pro > v.gols_contra THEN 3
            WHEN v.gols_pro = v.gols_contra THEN 1 ELSE 0 END AS pontos,
       (v.gols_contra = 0) AS sem_sofrer_gols,
       v.tecnico, v.formacao
FROM core.partida p
JOIN core.partida_complemento c USING (id_partida)
CROSS JOIN LATERAL (VALUES
    (p.id_mandante,  p.id_visitante, 'Casa', p.gols_mandante,  p.gols_visitante,
     c.tecnico_mandante, c.formacao_mandante),
    (p.id_visitante, p.id_mandante,  'Fora', p.gols_visitante, p.gols_mandante,
     c.tecnico_visitante, c.formacao_visitante)
) AS v(id_clube, id_adversario, mando, gols_pro, gols_contra, tecnico, formacao);

-- Grão: gol (929). Faixas de 15 minutos; acréscimos ficam na faixa do fim do tempo.
CREATE VIEW analytics.fato_gol AS
SELECT g.id_gol, g.id_partida, p.rodada, p.data_partida, g.id_jogador,
       g.id_clube_jogador, g.id_clube_beneficiado,
       CASE WHEN g.id_clube_beneficiado = p.id_mandante THEN 'Casa' ELSE 'Fora' END AS mando,
       g.minuto, g.acrescimo, g.periodo, g.tipo,
       CASE WHEN g.acrescimo > 0 THEN g.minuto || '+' || g.acrescimo
            ELSE g.minuto::text END AS minuto_texto,
       CASE WHEN g.minuto <= 15 THEN '01-15' WHEN g.minuto <= 30 THEN '16-30'
            WHEN g.minuto <= 45 THEN '31-45+' WHEN g.minuto <= 60 THEN '46-60'
            WHEN g.minuto <= 75 THEN '61-75' ELSE '76-90+' END AS faixa_minuto
FROM core.gol g
JOIN core.partida p USING (id_partida);

-- Grão: cartão (2.096).
CREATE VIEW analytics.fato_cartao AS
SELECT k.id_cartao, k.id_partida, p.rodada, p.data_partida, k.id_jogador, k.id_clube,
       CASE WHEN k.id_clube = p.id_mandante THEN 'Casa' ELSE 'Fora' END AS mando,
       k.cartao, k.minuto, k.acrescimo, k.periodo
FROM core.cartao k
JOIN core.partida p USING (id_partida);


-- -----------------------------------------------------------------------------
-- Classificação por rodada (reconstrução analítica) e final
-- -----------------------------------------------------------------------------
-- "Após a rodada N" = todas as partidas com rodada <= N, jogadas quando forem.
-- Ordem: pontos, vitórias, saldo, gols pró e confronto direto (só com exatamente
-- 2 clubes empatados e os dois jogos entre eles já disputados até a rodada N;
-- placar agregado). Cartões e sorteio não se aplicam. Empate não resolvido:
-- posição compartilhada (RANK) e desempate alfabético só para exibição.
CREATE VIEW analytics.classificacao_rodada AS
WITH por_rodada AS (
    SELECT id_clube, rodada, pontos,
           (resultado = 'V')::int AS v, (resultado = 'E')::int AS e, (resultado = 'D')::int AS d,
           gols_pro, gols_contra
    FROM analytics.fato_participacao
),
acumulado AS (
    SELECT id_clube, rodada,
           count(*)          OVER w AS jogos,
           sum(pontos)       OVER w AS pontos,
           sum(v)            OVER w AS vitorias,
           sum(e)            OVER w AS empates,
           sum(d)            OVER w AS derrotas,
           sum(gols_pro)     OVER w AS gols_pro,
           sum(gols_contra)  OVER w AS gols_contra
    FROM por_rodada
    WINDOW w AS (PARTITION BY id_clube ORDER BY rodada)
),
criterios AS (
    SELECT a.*, a.gols_pro - a.gols_contra AS saldo,
           count(*) OVER (PARTITION BY a.rodada, a.pontos, a.vitorias,
                                       a.gols_pro - a.gols_contra, a.gols_pro) AS tamanho_grupo
    FROM acumulado a
),
confronto AS (
    -- Para cada clube num grupo de exatamente 2: placar agregado contra o outro,
    -- só se os dois jogos entre eles já tiverem rodada <= N.
    SELECT c.id_clube, c.rodada,
           CASE WHEN count(f.id_partida) = 2 AND sum(f.gols_pro) > sum(f.gols_contra) THEN 1
                ELSE 0 END AS venceu_confronto
    FROM criterios c
    JOIN criterios o
      ON o.rodada = c.rodada AND o.id_clube <> c.id_clube AND c.tamanho_grupo = 2
     AND (o.pontos, o.vitorias, o.saldo, o.gols_pro) = (c.pontos, c.vitorias, c.saldo, c.gols_pro)
    LEFT JOIN analytics.fato_participacao f
      ON f.id_clube = c.id_clube AND f.id_adversario = o.id_clube AND f.rodada <= c.rodada
    GROUP BY c.id_clube, c.rodada
),
ordenado AS (
    SELECT cr.*, coalesce(cf.venceu_confronto, 0) AS venceu_confronto
    FROM criterios cr
    LEFT JOIN confronto cf USING (id_clube, rodada)
)
SELECT o.rodada, o.id_clube, cl.nome AS clube,
       RANK() OVER classificacao AS posicao,
       ROW_NUMBER() OVER (PARTITION BY o.rodada
                          ORDER BY o.pontos DESC, o.vitorias DESC, o.saldo DESC,
                                   o.gols_pro DESC, o.venceu_confronto DESC,
                                   cl.nome COLLATE "C") AS ordem_exibicao,
       o.jogos, o.pontos, o.vitorias, o.empates, o.derrotas,
       o.gols_pro, o.gols_contra, o.saldo,
       round(100.0 * o.pontos / (3 * o.jogos), 1) AS aproveitamento,
       (count(*) OVER (PARTITION BY o.rodada, o.pontos, o.vitorias, o.saldo, o.gols_pro,
                                    o.venceu_confronto) > 1) AS empate_nao_resolvido,
       (o.tamanho_grupo = 2 AND max(o.venceu_confronto) OVER
            (PARTITION BY o.rodada, o.pontos, o.vitorias, o.saldo, o.gols_pro) = 1)
           AS decidido_por_confronto
FROM ordenado o
JOIN core.clube cl USING (id_clube)
WINDOW classificacao AS (PARTITION BY o.rodada
                         ORDER BY o.pontos DESC, o.vitorias DESC, o.saldo DESC,
                                  o.gols_pro DESC, o.venceu_confronto DESC);

COMMENT ON VIEW analytics.classificacao_rodada IS
    'Reconstrução analítica por rodada nominal; NÃO é a classificação oficial publicada em cada data';

-- Grão: clube (20). A regra de ordenação existe só em classificacao_rodada.
-- Destino: vagas efetivas de 2024 (Wikipédia, predefinição da classificação):
-- Botafogo e Flamengo, campeões da Libertadores e da Copa do Brasil, ampliaram a
-- zona de classificação para a Libertadores até o 8º colocado.
CREATE VIEW analytics.classificacao_final AS
SELECT r.posicao, r.ordem_exibicao, r.id_clube, r.clube, r.jogos, r.pontos, r.vitorias,
       r.empates, r.derrotas, r.gols_pro, r.gols_contra, r.saldo, r.aproveitamento,
       r.empate_nao_resolvido,
       CASE WHEN r.ordem_exibicao = 1 THEN 'Campeão'
            WHEN r.ordem_exibicao <= 6  THEN 'Libertadores (fase de grupos)'
            WHEN r.ordem_exibicao <= 8  THEN 'Libertadores (2ª fase)'
            WHEN r.ordem_exibicao <= 14 THEN 'Sul-Americana'
            WHEN r.ordem_exibicao >= 17 THEN 'Rebaixado'
            ELSE 'Sem vaga' END AS destino
FROM analytics.classificacao_rodada r
WHERE r.rodada = 38;


-- -----------------------------------------------------------------------------
-- Jogadores
-- -----------------------------------------------------------------------------
-- Grão: jogador × clube. Assistências e jogos sem sofrer gols vêm dos rankings
-- parciais da Wikipédia: NULL significa "fora do ranking publicado", não zero.
CREATE VIEW analytics.jogador_estatisticas AS
SELECT j.id_jogador, j.nome_exibicao, j.id_clube, c.nome AS clube, j.posicao,
       coalesce(g.gols, 0)          AS gols,
       coalesce(g.gols_penalti, 0)  AS gols_penalti,
       coalesce(g.gols_contra, 0)   AS gols_contra,
       coalesce(k.amarelos, 0)      AS cartoes_amarelos,
       coalesce(k.vermelhos, 0)     AS cartoes_vermelhos,
       a.valor                      AS assistencias,
       s.valor                      AS jogos_sem_sofrer_gols,
       (sel.id_jogador IS NOT NULL) AS selecao_do_campeonato
FROM core.jogador j
JOIN core.clube c USING (id_clube)
LEFT JOIN (SELECT id_jogador,
                  count(*) FILTER (WHERE tipo <> 'Contra')  AS gols,
                  count(*) FILTER (WHERE tipo = 'Pênalti')  AS gols_penalti,
                  count(*) FILTER (WHERE tipo = 'Contra')   AS gols_contra
           FROM core.gol GROUP BY id_jogador) g USING (id_jogador)
LEFT JOIN (SELECT id_jogador,
                  count(*) FILTER (WHERE cartao = 'Amarelo')  AS amarelos,
                  count(*) FILTER (WHERE cartao = 'Vermelho') AS vermelhos
           FROM core.cartao GROUP BY id_jogador) k USING (id_jogador)
LEFT JOIN core.ranking_wikipedia a ON a.id_jogador = j.id_jogador AND a.metrica = 'assistencias'
LEFT JOIN core.ranking_wikipedia s ON s.id_jogador = j.id_jogador AND s.metrica = 'jogos_sem_sofrer_gols'
LEFT JOIN core.selecao_campeonato sel ON sel.id_jogador = j.id_jogador;

-- Seleção do campeonato e prêmios mensais (Wikipédia), expostos ao papel de leitura.
CREATE VIEW analytics.selecao_campeonato AS
SELECT s.id_jogador, s.setor FROM core.selecao_campeonato s;

CREATE VIEW analytics.premio_mensal AS
SELECT p.mes, p.premio, p.id_jogador FROM core.premio_mensal p;

-- Grão: imagem exibida (escudos + fotos). Crédito de cada arquivo para a página de créditos
-- do site e do Power BI: autor, licença e página do arquivo na Wikimedia Commons.
CREATE VIEW analytics.credito_imagem AS
SELECT 'Escudo'::varchar(6) AS tipo, e.id_clube, NULL::varchar(80) AS id_jogador, c.nome::varchar(80) AS nome,
       e.arquivo, e.url_imagem, e.pagina_arquivo, e.autor, e.licenca, e.licenca_url
FROM core.escudo_clube e
JOIN core.clube c USING (id_clube)
UNION ALL
SELECT 'Foto', j.id_clube, f.id_jogador, j.nome_exibicao::varchar(80),
       f.arquivo, f.url_imagem, f.pagina_arquivo, f.autor, f.licenca, f.licenca_url
FROM core.foto_jogador f
JOIN core.jogador j USING (id_jogador);


-- Privilégios do papel de leitura nas views recriadas (o DEFAULT PRIVILEGES de
-- 01_schemas.sql cobre objetos novos; isto cobre uma execução isolada deste script).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bi_brasileirao_leitura') THEN
        GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO bi_brasileirao_leitura;
    END IF;
END $$;
