# Proposta: Fase 3 (modelagem e PostgreSQL)

**Status: PROPOSTA, revisão 3 (2026-10-19).** Nenhum banco, papel, schema ou tabela foi criado.
Os trechos SQL deste documento são rascunhos para revisão e **não foram executados**.

Decisões já aprovadas, incorporadas aqui:
- evolução por **rodada nominal** como perspectiva principal, preservando a data real da partida;
- classificação intermediária documentada como **reconstrução analítica**, não como classificação
  oficial histórica da CBF;
- o adaoduque fica fora do Git e do produto analítico.

---

## 1. Visão geral das camadas

```
data/processed/partidas.csv ─┐            ┌─> core.partida (380) ─┐
data/reference/clubes.csv  ──┼─> staging ─┤                       ├─> analytics.* (views) ─> Power BI
                             │            └─> core.clube (20) ────┘
data/external/ (adaoduque) ──X  nunca é lido pela carga
```

| Schema | Papel | Objetos | Grão de cada objeto |
|---|---|---|---|
| `staging` | Espelho fiel dos CSVs, tudo como `text` e sem constraints | `staging.clubes_csv` | 1 linha por linha de `clubes.csv` (20) |
| | | `staging.partidas_csv` | 1 linha por linha de `partidas.csv` (380) |
| `core` | Dados tipados e íntegros (PK, FK, CHECK, UNIQUE); fonte da verdade | `core.clube` | 1 linha por clube (20) |
| | | `core.partida` | 1 linha por partida (380) |
| `analytics` | Views de leitura; contrato com o Power BI | `analytics.dim_clube` | 1 linha por clube (20) |
| | | `analytics.fato_partida` | 1 linha por partida (380) |
| | | `analytics.fato_participacao` | 1 linha por clube por partida (760) |
| | | `analytics.classificacao_rodada` | 1 linha por clube por rodada nominal (20 × 38 = 760) |
| | | `analytics.classificacao_final` | 1 linha por clube (20); filtro da anterior na rodada 38 |

**Por que staging separada:** falhas de carga (arquivo, codificação, número de colunas) aparecem
na staging; violações de regra aparecem na passagem para o `core`. As contagens CSV = staging =
core viram testes.

**Por que views, e não tabelas, no `analytics`:** são 760 linhas no máximo; as views garantem que
nenhum número fique desatualizado em relação ao `core`. Se houver necessidade de desempenho,
podem virar *materialized views* sem mudar o contrato.

---

## 2. Camada `core`

### `core.clube` (grão: clube)

```sql
CREATE TABLE core.clube (
    id_clube  char(3)     PRIMARY KEY CHECK (id_clube ~ '^[A-Z]{3}$'),
    nome      varchar(60) NOT NULL UNIQUE,
    uf        char(2)     NOT NULL CHECK (uf ~ '^[A-Z]{2}$')
);
```

`nome_openfootball` existe só para a conversão do arquivo-fonte e não sobe para o `core`. O mapa
de nomes do adaoduque fica em `data/external/adaoduque/`, fora do Git, e a carga nunca o lê.

### `core.partida` (grão: partida)

```sql
CREATE TABLE core.partida (
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
    CHECK (hora_inicio IS NOT NULL OR NOT hora_explicita),  -- horário "explícito" exige valor
    UNIQUE (id_mandante, id_visitante),   -- turno e returno: cada mando uma única vez
    UNIQUE (rodada, id_mandante),
    UNIQUE (rodada, id_visitante)
);
```

Notas:
- **Rastreabilidade do horário.** `hora_inicio` + `hora_explicita` preservam exatamente o que está
  no CSV: horário escrito na fonte, horário herdado pela regra do formato ou ausente (`NULL`, com
  `hora_explicita = false`). Nada é preenchido no banco. A única combinação proibida é um horário
  marcado como explícito sem valor.
- "Um jogo por clube por rodada" exige que o clube não seja mandante *e* visitante na mesma rodada.
  Isso não cabe numa constraint simples e fica num teste SQL (seção 7).
- A carga converte o placar do intervalo vazio (`''`) para `NULL` (`NULLIF(..., '')::smallint`).

---

## 3. Camada `analytics` e o problema da duplicação de métricas

Uma partida gera **duas** linhas de participação (mandante e visitante). Somar ou contar sem
cuidado nesse grão dobra as métricas do campeonato. A regra do projeto: **cada métrica tem um
grão de origem, e só é calculada nele.**

### `analytics.fato_partida` (grão: partida; 380 linhas)

Expõe `core.partida` mais `total_gols = gols_mandante + gols_visitante`. É a origem das métricas
**do campeonato**: número de partidas, total e média de gols por jogo, distribuição de resultados
(mandante, empate, visitante).

### `analytics.fato_participacao` (grão: clube × partida; 760 linhas)

```sql
CREATE VIEW analytics.fato_participacao AS
SELECT p.id_partida, p.rodada, p.data_partida, p.hora_inicio, p.hora_explicita,
       v.id_clube, v.id_adversario, v.mando,
       v.gols_pro, v.gols_contra, v.gols_pro - v.gols_contra AS saldo,
       CASE WHEN v.gols_pro > v.gols_contra THEN 'V'
            WHEN v.gols_pro = v.gols_contra THEN 'E' ELSE 'D' END AS resultado,
       CASE WHEN v.gols_pro > v.gols_contra THEN 3
            WHEN v.gols_pro = v.gols_contra THEN 1 ELSE 0 END AS pontos
FROM core.partida p
CROSS JOIN LATERAL (VALUES
    (p.id_mandante,  p.id_visitante, 'Casa', p.gols_mandante,  p.gols_visitante),
    (p.id_visitante, p.id_mandante,  'Fora', p.gols_visitante, p.gols_mandante)
) AS v(id_clube, id_adversario, mando, gols_pro, gols_contra);
```

Chave natural: `(id_partida, id_clube)`. É a origem das métricas **por clube**: pontos, V/E/D,
gols pró e contra, saldo, aproveitamento, casa e fora.

### Regras contra a duplicação

| Métrica | Grão correto | Cálculo correto | Erro evitado |
|---|---|---|---|
| Nº de partidas do campeonato | partida | `COUNT(*)` em `fato_partida` | `COUNT(*)` em participação dá 760 |
| Total de gols do campeonato | partida | `SUM(total_gols)` em `fato_partida` | `SUM(gols_pro + gols_contra)` em participação dá 1.858 |
| Empates no campeonato | partida | `COUNT(*) FILTER (WHERE resultado = 'E')` em `fato_partida` | contar `'E'` em participação dobra |
| Pontos, V/E/D, gols de um clube | participação | soma filtrada pelo clube | — |
| Jogos de um clube | participação | `COUNT(*)` filtrado pelo clube | — |
| Saldo somado de todos os clubes | participação | Deve ser 0; serve como **teste**, não como métrica | — |

No Power BI, `fato_partida` e `fato_participacao` serão duas tabelas fato ligadas às dimensões. As
medidas do campeonato são definidas sobre `fato_partida`; as de clube, sobre `fato_participacao`.
O detalhamento fica para a Fase 5.

`desempenho por mando` não será uma view própria: é a mesma `fato_participacao` agrupada por
`mando`. Isso evita uma segunda definição das mesmas métricas.

---

## 4. Classificação por rodada (reconstrução analítica)

> **Aviso obrigatório na documentação e no dashboard:** a classificação por rodada é uma
> **reconstrução analítica a partir dos resultados**, pela convenção de rodada nominal. **Não** é a
> classificação oficial publicada pela CBF em cada data. Só a classificação final (rodada 38) foi
> validada contra a tabela oficial.

### 4.1 Definição de "classificação após a rodada N"

Considera **todas as partidas com `rodada ≤ N`**, independentemente da data em que foram jogadas.

### 4.2 Jogos adiados

Um jogo da rodada 7 disputado em julho entra na classificação "após a rodada 7". Consequências:
- todo clube tem exatamente N jogos após a rodada N, o que torna a comparação justa;
- a tabela "após a rodada 7" **não** é a tabela que existia na data da rodada 7; essa diferença
  é intencional e documentada;
- a **análise cronológica** continua possível: `fato_participacao` preserva `data_partida`, e
  uma tabela calendário no Power BI permite acumular por data. Ela não faz parte da v1.

### 4.3 Critérios de ordenação

Aplicados em sequência, adaptados do Art. 15 do REC (que trata da classificação **final**):

| # | Critério | Aplicação nas rodadas intermediárias |
|---|---|---|
| — | Pontos | Sempre |
| 1 | Vitórias | Sempre |
| 2 | Saldo de gols | Sempre |
| 3 | Gols pró | Sempre |
| 4 | Confronto direto | Só se **exatamente 2** clubes estiverem empatados (§2) **e** os **dois** confrontos entre eles (ida e volta) tiverem `rodada ≤ N`. Compara o placar agregado dos 180 minutos |
| 5–6 | Cartões | **Não aplicáveis**: sem dados licenciados |
| 7 | Sorteio | Não aplicável |

**Confronto direto incompleto:** se os dois clubes ainda não se enfrentaram duas vezes até a
rodada N (0 ou 1 jogo), o critério 4 **não** é aplicado. Usar meio confronto anteciparia uma regra
pensada para o jogo de 180 minutos.

**Empate não resolvido** (após os critérios aplicáveis):
- `posicao` = posição compartilhada (estilo `RANK()`: dois clubes em 5º, o próximo em 7º);
- `empate_nao_resolvido` = `true`;
- `ordem_exibicao` = desempate alfabético por nome, **só para exibição**, nunca apresentado como
  posição oficial.

**Ressalva sobre o §1 do Art. 15:** o texto do REC sobre como somar o confronto direto ficou
truncado na cópia de terceiros consultada; o placar agregado vem de fontes secundárias e do REC
2025. A cópia consultada **não é a versão oficial hospedada pela CBF** (pendência P2 da
auditoria).

### 4.4 Objetos

- `analytics.classificacao_rodada`: CTE com acumulados (`SUM(...) OVER (PARTITION BY id_clube ORDER BY rodada)`) sobre um produto clube × rodada; o confronto direto é calculado só para os pares empatados elegíveis; as posições saem de `RANK()`.
- `analytics.classificacao_final`: `SELECT … FROM analytics.classificacao_rodada WHERE rodada = 38`. A regra de ordenação existe **num só lugar**.

---

## 5. Carga e recarga sem `TRUNCATE` no `core`

### Alternativas avaliadas

| Opção | Como funciona | Avaliação |
|---|---|---|
| A. `TRUNCATE` em staging e core + reinserção | Esvazia tudo e insere de novo | Simples, mas é uma remoção em massa no `core`; com FKs, exige `CASCADE`, e um erro de alvo apaga mais do que devia |
| B. `DELETE` + `INSERT` numa transação | Igual a A, sem precisar do privilégio `TRUNCATE` | Mesmo efeito em massa; só troca o privilégio |
| C. **`MERGE` (PostgreSQL 17+)** | Compara staging × core: insere novas, atualiza alteradas, remove as que saíram da fonte (`WHEN NOT MATCHED BY SOURCE`) | Idempotente; só mexe no que mudou. **Recomendada para o `core`.** O `MERGE` **não guarda histórico**: depois dele, o estado anterior não fica registrado em lugar nenhum. A auditoria da carga é um mecanismo próprio (seção 5.2) |
| D. Staging em tabelas `TEMP` | Staging recriada a cada sessão | Dispensa até o `TRUNCATE` da staging, mas perde a staging persistente para inspeção |

### 5.1 Decisão aprovada

- **Staging:** `TRUNCATE staging.clubes_csv, staging.partidas_csv` no início da carga. São só
  cópias dos CSVs versionados, e o comando é restrito a esse schema. Não há outro `TRUNCATE` em
  nenhum script.
- **Core:** `MERGE`, sem `TRUNCATE` nem `DELETE` em massa.
- **Sem papel de carga separado** nesta etapa (`bi_brasileirao` é dono e executa a carga).

### 5.2 Transação, validações, rollback e auditoria da carga

O script `03_carga.sql` é executado **somente pelo psql**, porque `\copy` é um comando do psql e
não existe no pgAdmin:

```
psql -v ON_ERROR_STOP=1 -U bi_brasileirao -d brasileirao2024 -f sql/03_carga.sql
```

| Etapa | Mecanismo | Em caso de falha |
|---|---|---|
| 1. Abrir transação | `BEGIN;` | — |
| 2. Validar a staging antes de tocar no core | Bloco `DO` com `RAISE EXCEPTION` se: contagens ≠ 20 e 380; valores não convertíveis (datas, inteiros, horas); `id_clube` duplicado na staging | Exceção → psql para (`ON_ERROR_STOP`) → a transação é **desfeita** ao encerrar a conexão; core intacto |
| 3. Registrar o que vai mudar | Contagens calculadas **antes** do `MERGE`, comparando staging × core: linhas a inserir, a atualizar (alguma coluna diferente) e a remover, por tabela. Gravadas em `core.carga_execucao` (ver abaixo) | Mesma regra: nada fica gravado se a transação for desfeita |
| 4. Aplicar | `MERGE` em `core.clube` (insere e atualiza), `MERGE` em `core.partida` (insere, atualiza e remove), remoção de clubes órfãos | Violação de constraint ou FK → exceção → rollback |
| 5. Validar o resultado | Bloco `DO`: contagens do core = staging; ausência de clube como mandante e visitante na mesma rodada; soma de gols de `fato_participacao` = de `fato_partida`. A comparação com a classificação oficial fica em `05_testes.sql` | Exceção → rollback de **tudo**, inclusive do registro da etapa 3 |
| 6. Confirmar | `COMMIT;` | — |

**Tabela de auditoria** (`core.carga_execucao`, grão: uma linha por carga confirmada):

| Coluna | Conteúdo |
|---|---|
| `id_carga` | `bigint GENERATED ALWAYS AS IDENTITY`, PK |
| `executado_em` | `timestamptz NOT NULL DEFAULT now()` |
| `executado_por` | `text NOT NULL DEFAULT current_user` |
| `clubes_inseridos`, `clubes_atualizados`, `clubes_removidos` | Contagens da etapa 3 |
| `partidas_inseridas`, `partidas_atualizadas`, `partidas_removidas` | Contagens da etapa 3 |

Limites do mecanismo, assumidos explicitamente:
- Registra **quantas** linhas mudaram em cada carga, **não quais valores** existiam antes. Não há
  histórico linha a linha (SCD) nem *trigger* de auditoria.
- O histórico do conteúdo dos dados fica no **Git**: cada versão de `partidas.csv` é rastreável
  até o commit e o hash da fonte (`PROCEDENCIA.json`). O banco é sempre recriável a partir disso.
- Uma carga **desfeita** não deixa registro no banco (é desfeita junto com a transação); a falha
  aparece na saída do psql.
- `RETURNING merge_action()` pode ser usado para **exibir** na saída do psql as linhas afetadas,
  mas essa saída não é persistida e não é considerada mecanismo de auditoria.

Esboço:

```sql
-- executado com: psql -v ON_ERROR_STOP=1 ... -f sql/03_carga.sql
BEGIN;
TRUNCATE staging.clubes_csv, staging.partidas_csv;
\copy staging.clubes_csv   FROM 'data/reference/clubes.csv'   WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.partidas_csv FROM 'data/processed/partidas.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

MERGE INTO core.clube AS c
USING (SELECT id_clube, nome, uf FROM staging.clubes_csv) AS s ON c.id_clube = s.id_clube
WHEN MATCHED AND (c.nome, c.uf) IS DISTINCT FROM (s.nome, s.uf) THEN UPDATE SET nome = s.nome, uf = s.uf
WHEN NOT MATCHED THEN INSERT (id_clube, nome, uf) VALUES (s.id_clube, s.nome, s.uf);

MERGE INTO core.partida AS p USING (/* conversão de tipos da staging */) AS s ON p.id_partida = s.id_partida
WHEN MATCHED AND (/* alguma coluna diferente */) THEN UPDATE SET …
WHEN NOT MATCHED THEN INSERT …
WHEN NOT MATCHED BY SOURCE THEN DELETE;

-- Clubes que saíram da fonte: só depois das partidas, para respeitar a FK.
DELETE FROM core.clube c WHERE NOT EXISTS (SELECT 1 FROM staging.clubes_csv s WHERE s.id_clube = c.id_clube);

DO $$ BEGIN /* validações da etapa 5; RAISE EXCEPTION em qualquer falha */ END $$;
COMMIT;
```

---

## 6. Banco, papéis e privilégios

Os comandos SQL estão em [`sql/00_criar_banco_e_papel.sql`](../../sql/00_criar_banco_e_papel.sql);
os pré-requisitos, os passos específicos do psql (senhas) e a execução pelo pgAdmin estão em
[criacao_banco.md](criacao_banco.md). **Nada foi executado.** Resumo:

| Papel | Atributos | Privilégios | Justificativa |
|---|---|---|---|
| `bi_brasileirao` | `LOGIN`, sem superusuário, sem `CREATEDB`/`CREATEROLE`/replicação/`BYPASSRLS`, limite de 5 conexões | **Dono** do banco `brasileirao2024` e de todos os objetos dentro dele | Executa DDL, carga e testes do projeto. Ser dono do banco dá controle total **só** sobre ele, sem nenhum poder no servidor ou nos outros bancos |
| `bi_brasileirao_leitura` (opcional, recomendado) | `LOGIN`, sem nenhum atributo especial | `CONNECT` no banco; `USAGE` + `SELECT` apenas no schema `analytics` | Conexão do Power BI com privilégio mínimo: não enxerga staging nem core e não pode alterar nada. As views do `analytics` rodam com os privilégios do dono, então a leitura do `core` acontece só através delas |
| `PUBLIC` | — | `REVOKE ALL ON DATABASE brasileirao2024` (remove `CONNECT` e `TEMP`) | Nenhum outro usuário do servidor, inclusive os do TechstoreVendas, se conecta a este banco por padrão |

**Sobre `TRUNCATE`:** como dono, `bi_brasileirao` tem implicitamente todos os privilégios sobre
suas tabelas, inclusive `TRUNCATE`. Um `REVOKE` não remove direitos do dono de forma efetiva,
porque o dono pode se conceder de volta. Só um papel de carga separado e **não dono** permitiria
restringir `TRUNCATE` de verdade. Para um projeto local, de uma pessoa, isso adiciona um terceiro
papel sem ganho proporcional. A proteção proposta é outra:
1. o banco é dedicado e recriável a partir dos CSVs versionados;
2. o `core` só é alterado por `MERGE` (seção 5);
3. `TRUNCATE` aparece só no script de carga e só sobre o schema `staging`.

**Decisão aprovada:** nenhum papel de carga separado nesta etapa. A separação dono/carga (dono
`NOLOGIN` + papel de carga com `INSERT`/`UPDATE`/`DELETE` e `TRUNCATE` só na staging) fica
registrada apenas como alternativa futura.

**Senha:** nunca em arquivo do repositório. Ela é definida interativamente com `\password` no
`psql`. Para conexões sem digitar a senha, use `%APPDATA%\postgresql\pgpass.conf`, configurado por
você, fora do repositório.

**Agrupamento (collation):** ICU `pt-BR`, para que nomes com acento ordenem como em português:
"São Paulo" antes de "Santos", enquanto a ordem por código de caractere coloca "ã" depois de
todas as letras sem acento e inverte os dois. O script começa com uma consulta somente leitura que confirma
se o ICU está disponível. A alternativa sem ICU (`builtin`/`C.UTF-8`) também está no arquivo.

---

## 7. Testes previstos para a Fase 3 (`sql/05_testes.sql`)

- **Contagens:** CSV = staging = core (20 clubes, 380 partidas); 760 participações.
- **Integridade:** nenhum clube como mandante e visitante na mesma rodada; 19 jogos em casa e 19
  fora por clube; constraints rejeitando inserções inválidas, dentro de transações desfeitas com
  `ROLLBACK`.
- **Não duplicação:** `COUNT(DISTINCT id_partida)` em participação = 380;
  `SUM(gols_pro)` em participação = `SUM(total_gols)` em partida = 929; `SUM(saldo)` = 0;
  `SUM(pontos)` = 3 × (partidas com vencedor) + 2 × (empates).
- **Classificação:** `classificacao_final` igual à tabela oficial da CBF (160 campos e 20
  posições, mesmos valores de `tests/test_classificacao.py`); pontos acumulados na rodada 38 =
  pontos finais; após cada rodada N, todo clube com exatamente N jogos.
- **Rastreabilidade:** 230 partidas com `hora_explicita = true` e 150 com `false`, como no CSV.
- **Reconciliação Python × SQL:** a classificação calculada por `scripts/validar_dados.py` e pela
  view devem coincidir.

## 8. Organização prevista dos scripts

```
sql/
  00_criar_banco_e_papel.sql   # papéis e banco; SQL puro, executado uma vez por um administrador (aguarda aprovação)
  01_schemas.sql               # staging, core, analytics + privilégios do papel de leitura
  02_tabelas.sql               # staging, core e core.carga_execucao
  03_carga.sql                 # somente psql: \copy → staging → validação → MERGE no core → validação
  04_views.sql                 # analytics.*
  05_testes.sql                # testes da seção 7
```

## 9. Pendências que afetam a Fase 3

- **P2.** Versão oficial do REC hospedada pela CBF. A cópia consultada é de terceiros, e o §1
  (confronto direto) está incompleto nela.
- **P3.** Validação jogo a jogo com a CBF continua pendente. Só a classificação final foi
  confrontada com a tabela oficial.
