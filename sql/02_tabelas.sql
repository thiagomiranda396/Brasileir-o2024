-- =============================================================================
-- 02_tabelas.sql
--
-- Tabelas de staging (espelho dos CSVs) e do core (modelo relacional íntegro).
-- Executado por bi_brasileirao, conectado a brasileirao2024, depois de 01_schemas.sql:
--   psql -v ON_ERROR_STOP=1 -U bi_brasileirao -d brasileirao2024 -f sql/02_tabelas.sql
--
-- Idempotente (IF NOT EXISTS). Para mudar a estrutura de uma tabela já criada,
-- recrie o banco: ele é reconstruível a partir dos CSVs versionados.
--
-- Diagrama do core (setas = chaves estrangeiras):
--
--   clube ◄── partida ◄── partida_complemento
--     ▲  ▲       ▲
--     │  │       ├──── gol ────► jogador ──► clube
--     │  │       └──── cartao ─► jogador
--     │  └── jogador ◄── ranking_wikipedia, selecao_campeonato, premio_mensal, foto_jogador
--     └── escudo_clube
-- =============================================================================


-- =============================================================================
-- STAGING: tudo text, sem constraints. Falhas de arquivo aparecem aqui; falhas de
-- regra aparecem na passagem para o core.
-- =============================================================================

CREATE TABLE IF NOT EXISTS staging.clubes_csv (
    id_clube text, nome text, uf text, nome_openfootball text
);
CREATE TABLE IF NOT EXISTS staging.clubes_visual_csv (
    id_clube text, nome_completo text, cidade text, estadio text, capacidade text,
    cor_primaria text, cor_secundaria text, wiki_pt text
);
CREATE TABLE IF NOT EXISTS staging.partidas_csv (
    id_partida text, rodada text, data text, hora text, hora_explicita text,
    id_mandante text, id_visitante text, gols_mandante text, gols_visitante text,
    gols_mandante_1t text, gols_visitante_1t text, linha_origem text
);
CREATE TABLE IF NOT EXISTS staging.partidas_complemento_csv (
    id_partida text, estadio text, tecnico_mandante text, tecnico_visitante text,
    formacao_mandante text, formacao_visitante text
);
CREATE TABLE IF NOT EXISTS staging.jogadores_csv (
    id_jogador text, nome_fonte text, nome_exibicao text, id_clube text, posicao text, wiki text
);
CREATE TABLE IF NOT EXISTS staging.gols_csv (
    id_gol text, id_partida text, rodada text, id_jogador text, id_clube_jogador text,
    id_clube_beneficiado text, minuto text, acrescimo text, periodo text, tipo text
);
CREATE TABLE IF NOT EXISTS staging.cartoes_csv (
    id_cartao text, id_partida text, rodada text, id_jogador text, id_clube text, cartao text,
    minuto text, acrescimo text, periodo text, num_camisa text
);
CREATE TABLE IF NOT EXISTS staging.wiki_assistencias_csv (
    posicao text, jogador text, id_clube text, assistencias text
);
CREATE TABLE IF NOT EXISTS staging.wiki_jogos_sem_sofrer_gols_csv (
    posicao text, jogador text, id_clube text, jogos_sem_sofrer_gols text
);
CREATE TABLE IF NOT EXISTS staging.wiki_selecao_csv (
    setor text, jogador text, id_clube text
);
CREATE TABLE IF NOT EXISTS staging.wiki_premios_csv (
    mes text, premio text, jogador text, id_clube text
);
CREATE TABLE IF NOT EXISTS staging.escudos_clubes_csv (
    id_clube text, wikidata text, arquivo text, url_imagem text, pagina_arquivo text, autor text,
    licenca text, licenca_url text, origem_imagem text, consultado_em text
);
CREATE TABLE IF NOT EXISTS staging.fotos_jogadores_csv (
    id_jogador text, wikidata text, arquivo text, url_imagem text, pagina_arquivo text, autor text,
    licenca text, licenca_url text, origem_imagem text, criterio text, confirmado_por text,
    consultado_em text
);


-- =============================================================================
-- CORE
-- =============================================================================

-- Grão: clube (20).
CREATE TABLE IF NOT EXISTS core.clube (
    id_clube        char(3)     PRIMARY KEY CHECK (id_clube ~ '^[A-Z]{3}$'),
    nome            varchar(60) NOT NULL UNIQUE,
    uf              char(2)     NOT NULL CHECK (uf ~ '^[A-Z]{2}$'),
    nome_completo   varchar(80) NOT NULL,
    cidade          varchar(60) NOT NULL,
    estadio         varchar(60) NOT NULL,
    capacidade      integer     NOT NULL CHECK (capacidade > 0),
    cor_primaria    char(7)     NOT NULL CHECK (cor_primaria   ~ '^#[0-9A-F]{6}$'),
    cor_secundaria  char(7)     NOT NULL CHECK (cor_secundaria ~ '^#[0-9A-F]{6}$'),
    wiki_pt         varchar(120) NOT NULL
);
COMMENT ON TABLE core.clube IS 'Clubes da Série A 2024 (cadastro do projeto + dados do estádio principal)';

-- Grão: partida (380).
CREATE TABLE IF NOT EXISTS core.partida (
    id_partida         smallint PRIMARY KEY,
    rodada             smallint NOT NULL CHECK (rodada BETWEEN 1 AND 38),
    data_partida       date     NOT NULL CHECK (data_partida BETWEEN '2024-04-13' AND '2024-12-08'),
    hora_inicio        time,                    -- NULL se a fonte não trouxer horário
    hora_explicita     boolean  NOT NULL,       -- true = escrito na fonte; false = herdado
    id_mandante        char(3)  NOT NULL REFERENCES core.clube,
    id_visitante       char(3)  NOT NULL REFERENCES core.clube,
    gols_mandante      smallint NOT NULL CHECK (gols_mandante  >= 0),
    gols_visitante     smallint NOT NULL CHECK (gols_visitante >= 0),
    gols_mandante_1t   smallint,
    gols_visitante_1t  smallint,
    resultado          char(1)  GENERATED ALWAYS AS (
                           CASE WHEN gols_mandante > gols_visitante THEN 'M'
                                WHEN gols_mandante = gols_visitante THEN 'E'
                                ELSE 'V' END) STORED,
    linha_origem       integer  NOT NULL,       -- rastreio até data/raw/openfootball/2024_br1.txt
    CHECK (id_mandante <> id_visitante),
    CHECK ((gols_mandante_1t IS NULL) = (gols_visitante_1t IS NULL)),
    CHECK (gols_mandante_1t  <= gols_mandante),
    CHECK (gols_visitante_1t <= gols_visitante),
    CHECK (hora_inicio IS NOT NULL OR NOT hora_explicita),
    UNIQUE (id_mandante, id_visitante),   -- turno e returno: cada mando uma única vez
    UNIQUE (rodada, id_mandante),
    UNIQUE (rodada, id_visitante)
);
CREATE INDEX IF NOT EXISTS partida_visitante_idx ON core.partida (id_visitante);
COMMENT ON TABLE core.partida IS 'Partidas da Série A 2024 (fonte: openfootball, CC0)';

-- Grão: partida (380), relação 1:1 com core.partida.
CREATE TABLE IF NOT EXISTS core.partida_complemento (
    id_partida          smallint    PRIMARY KEY REFERENCES core.partida,
    estadio             varchar(80) NOT NULL,
    tecnico_mandante    varchar(60) NOT NULL,
    tecnico_visitante   varchar(60) NOT NULL,
    formacao_mandante   varchar(12),
    formacao_visitante  varchar(12)
);
COMMENT ON TABLE core.partida_complemento IS
    'Estádio, técnicos e formações de cada partida (derivado de adaoduque/Brasileirao_Dataset)';

-- Grão: jogador × clube. Homônimos de clubes diferentes são jogadores diferentes.
CREATE TABLE IF NOT EXISTS core.jogador (
    id_jogador     varchar(80) PRIMARY KEY CHECK (id_jogador ~ '^[a-z0-9-]+-[a-z]{3}$'),
    nome_fonte     varchar(80) NOT NULL,
    nome_exibicao  varchar(60) NOT NULL,
    id_clube       char(3)     NOT NULL REFERENCES core.clube,
    posicao        varchar(20),
    wiki           varchar(200),               -- candidatos de página: 'en:Título|pt:Título'
    UNIQUE (nome_fonte, id_clube),
    UNIQUE (nome_exibicao, id_clube)
);
CREATE INDEX IF NOT EXISTS jogador_clube_idx ON core.jogador (id_clube);

-- Grão: gol (929).
CREATE TABLE IF NOT EXISTS core.gol (
    id_gol                smallint    PRIMARY KEY,
    id_partida            smallint    NOT NULL REFERENCES core.partida,
    id_jogador            varchar(80) NOT NULL REFERENCES core.jogador,
    id_clube_jogador      char(3)     NOT NULL REFERENCES core.clube,
    id_clube_beneficiado  char(3)     NOT NULL REFERENCES core.clube,
    minuto                smallint    NOT NULL CHECK (minuto BETWEEN 1 AND 90),
    acrescimo             smallint    NOT NULL DEFAULT 0 CHECK (acrescimo BETWEEN 0 AND 20),
    periodo               char(2)     NOT NULL CHECK (periodo IN ('1T', '2T')),
    tipo                  varchar(8)  NOT NULL CHECK (tipo IN ('Normal', 'Pênalti', 'Contra')),
    CHECK ((periodo = '1T') = (minuto <= 45)),
    CHECK (acrescimo = 0 OR minuto IN (45, 90)),
    -- Gol contra é o único caso em que o clube do jogador não é o beneficiado.
    CHECK ((tipo = 'Contra') = (id_clube_jogador <> id_clube_beneficiado))
);
CREATE INDEX IF NOT EXISTS gol_partida_idx ON core.gol (id_partida);
CREATE INDEX IF NOT EXISTS gol_jogador_idx ON core.gol (id_jogador);

-- Grão: cartão.
CREATE TABLE IF NOT EXISTS core.cartao (
    id_cartao   smallint    PRIMARY KEY,
    id_partida  smallint    NOT NULL REFERENCES core.partida,
    id_jogador  varchar(80) NOT NULL REFERENCES core.jogador,
    id_clube    char(3)     NOT NULL REFERENCES core.clube,
    cartao      varchar(8)  NOT NULL CHECK (cartao IN ('Amarelo', 'Vermelho')),
    minuto      smallint    NOT NULL CHECK (minuto BETWEEN 1 AND 90),
    acrescimo   smallint    NOT NULL DEFAULT 0 CHECK (acrescimo BETWEEN 0 AND 20),
    periodo     char(2)     NOT NULL CHECK (periodo IN ('1T', '2T')),
    num_camisa  smallint    CHECK (num_camisa BETWEEN 0 AND 999)
);
CREATE INDEX IF NOT EXISTS cartao_partida_idx ON core.cartao (id_partida);
CREATE INDEX IF NOT EXISTS cartao_jogador_idx ON core.cartao (id_jogador);

-- Grão: jogador × métrica. Rankings publicados pela Wikipédia (só os primeiros colocados).
CREATE TABLE IF NOT EXISTS core.ranking_wikipedia (
    metrica     varchar(24) NOT NULL CHECK (metrica IN ('assistencias', 'jogos_sem_sofrer_gols')),
    id_jogador  varchar(80) NOT NULL REFERENCES core.jogador,
    posicao     smallint    NOT NULL CHECK (posicao >= 1),
    valor       smallint    NOT NULL CHECK (valor >= 0),
    PRIMARY KEY (metrica, id_jogador)
);
COMMENT ON TABLE core.ranking_wikipedia IS
    'Rankings parciais (Wikipédia em inglês, CC BY-SA 4.0): assistências e jogos sem sofrer gols';

-- Grão: jogador na seleção do campeonato (11).
CREATE TABLE IF NOT EXISTS core.selecao_campeonato (
    id_jogador  varchar(80) PRIMARY KEY REFERENCES core.jogador,
    setor       varchar(16) NOT NULL CHECK (setor IN ('Goleiro', 'Defensor', 'Meio-campista', 'Atacante'))
);

-- Grão: mês × prêmio.
CREATE TABLE IF NOT EXISTS core.premio_mensal (
    mes         smallint    NOT NULL CHECK (mes BETWEEN 4 AND 12),
    premio      varchar(20) NOT NULL CHECK (premio IN ('Craque do mês', 'Goleiro do mês', 'Revelação do mês')),
    id_jogador  varchar(80) NOT NULL REFERENCES core.jogador,
    PRIMARY KEY (mes, premio)
);

-- Imagens (Wikimedia Commons), geradas por scripts/buscar_fotos.py. Só a referência ao arquivo
-- e o crédito ficam no banco; a imagem é carregada da Wikimedia por quem a exibe. Só entram
-- licenças livres (a regra completa está no script e é conferida de novo aqui).

-- Grão: clube (até 20; clube sem escudo livre não tem linha).
CREATE TABLE IF NOT EXISTS core.escudo_clube (
    id_clube        char(3)      PRIMARY KEY REFERENCES core.clube,
    wikidata        varchar(16)  NOT NULL CHECK (wikidata ~ '^Q[0-9]+$'),
    arquivo         varchar(255) NOT NULL,
    url_imagem      varchar(600) NOT NULL CHECK (url_imagem ~ '^https://(upload|thumb)\.wikimedia\.org/'),
    pagina_arquivo  varchar(600) NOT NULL CHECK (pagina_arquivo LIKE 'https://%'),
    autor           varchar(500) NOT NULL,
    licenca         varchar(60)  NOT NULL,
    licenca_url     varchar(300),
    origem_imagem   varchar(20)  NOT NULL CHECK (origem_imagem IN ('pagina_pt', 'wikidata_p154', 'pagina_pt_uso_justo')),
    consultado_em   date         NOT NULL,
    -- Licença livre, ou o escudo da página pt marcado como uso justo (só escudos).
    CHECK (licenca ~* '^(CC0|CC BY(-SA)? [0-9]|Public domain|PD)'
           OR (licenca = 'Uso justo' AND origem_imagem = 'pagina_pt_uso_justo'))
);
COMMENT ON TABLE core.escudo_clube IS
    'Escudo de cada clube na Wikimedia Commons, com autor e licença (scripts/buscar_fotos.py)';

-- Grão: jogador × clube (só quem tem foto confirmada pela Wikidata ou pela ficha da Wikipédia).
CREATE TABLE IF NOT EXISTS core.foto_jogador (
    id_jogador      varchar(80)  PRIMARY KEY REFERENCES core.jogador,
    wikidata        varchar(16)  NOT NULL CHECK (wikidata ~ '^Q[0-9]+$'),
    arquivo         varchar(255) NOT NULL,
    url_imagem      varchar(600) NOT NULL CHECK (url_imagem ~ '^https://(upload|thumb)\.wikimedia\.org/'),
    pagina_arquivo  varchar(600) NOT NULL CHECK (pagina_arquivo LIKE 'https://%'),
    autor           varchar(500) NOT NULL,
    licenca         varchar(60)  NOT NULL CHECK (licenca ~* '^(CC0|CC BY(-SA)? [0-9]|Public domain|PD)'),
    licenca_url     varchar(300),
    origem_imagem   varchar(20)  NOT NULL CHECK (origem_imagem IN ('wikidata_p18', 'pagina_pt', 'pagina_en')),
    criterio        varchar(10)  NOT NULL CHECK (criterio IN ('curado', 'nome')),
    -- Quem confirmou o clube em 2024: o vínculo P54 da Wikidata ou a ficha da Wikipédia em inglês.
    confirmado_por  varchar(20)  NOT NULL CHECK (confirmado_por IN ('wikidata', 'wikipedia_en')),
    consultado_em   date         NOT NULL,
    -- CC BY e CC BY-SA exigem atribuição.
    CHECK (autor <> '' OR licenca ~* '^(CC0|Public domain|PD)')
);
COMMENT ON TABLE core.foto_jogador IS
    'Foto de cada jogador na Wikimedia Commons, confirmada pela Wikidata ou pela ficha da Wikipédia (scripts/buscar_fotos.py)';

-- Auditoria da carga: uma linha por tabela por carga confirmada.
CREATE TABLE IF NOT EXISTS core.carga_execucao (
    id_carga       bigint      NOT NULL,
    executado_em   timestamptz NOT NULL DEFAULT now(),
    executado_por  text        NOT NULL DEFAULT current_user,
    tabela         text        NOT NULL,
    inseridas      integer     NOT NULL,
    atualizadas    integer     NOT NULL,
    removidas      integer     NOT NULL,
    PRIMARY KEY (id_carga, tabela)
);
CREATE SEQUENCE IF NOT EXISTS core.carga_execucao_seq;
COMMENT ON TABLE core.carga_execucao IS
    'Quantas linhas cada carga inseriu, atualizou e removeu, por tabela (sem histórico de valores)';
