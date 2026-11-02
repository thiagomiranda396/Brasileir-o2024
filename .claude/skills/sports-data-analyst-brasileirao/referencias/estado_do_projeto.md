# Estado do projeto (retrato de 2026-11-01)

Retrato feito na criação desta Skill, a partir de `README.md`, `docs/`, `sql/`, `scripts/`,
`tests/`, `powerbi/`, `web/` e do histórico Git da pasta `C:\Projetos\Brasileirão2024`.
**Confira antes de usar** (seção 6): o projeto continua mudando.

## 1. Objetivo e produtos

Portfólio de BI sobre o Campeonato Brasileiro Série A 2024, a ser publicado no GitHub:
dados públicos auditados → modelo relacional no PostgreSQL → camada analítica em SQL →
dashboard no Power BI e site interativo (estatísticas, escudos, fotos e minijogo).

| Produto | Situação |
|---|---|
| Dados validados (`data/`) | Pronto. Partidas, gols, cartões e jogadores conferidos (ver seção 4) |
| Banco PostgreSQL (`sql/`) | Pronto. 23 testes SQL passam |
| Site (`web/`) | Pronto. Visão geral, Classificação, Clubes, Jogadores, Partidas, Minijogos (Prancheta 2024), Créditos (o quiz foi removido em 2026-11-01 a pedido do Thiago) |
| Power BI (`powerbi/`) | **Guia pronto**: medidas DAX, tema, CSVs e layout. O `.pbix` ainda não foi montado |
| Publicação no GitHub | **Pendente** (seção 5) |

## 2. Arquitetura e tecnologias

| Camada | Tecnologia | Onde | Observação |
|---|---|---|---|
| Aquisição | Python 3.11+ (só biblioteca padrão; o README usa `py -3.14`) | `scripts/baixar_fontes.py` | Versões fixadas (commit/revisão) e SHA-256 |
| Conversão e preparo | Python | `scripts/converter_openfootball.py`, `scripts/preparar_jogadores.py` | Falham em vez de "adivinhar" |
| Validação | Python | `scripts/validar_dados.py` → `docs/qualidade/relatorio_validacao_fase2.md` | Relatório gerado; não editar à mão |
| Banco | PostgreSQL 15+ (README: testado no 16 e no 18), `psql` | `sql/00` a `sql/06`, `sql/executar_tudo.sql` | Banco `brasileirao2024`, collation ICU `pt-BR` |
| Camadas | `staging` (tudo `text`) → `core` (PK, FK, CHECK) → `analytics` (views) | `sql/01`, `02`, `04` | `analytics` é o contrato com Power BI e site |
| Carga | `\copy` + views tipadas + `MERGE`, numa transação | `sql/03_carga.sql` | Idempotente; auditoria em `core.carga_execucao` |
| Papéis | `bi_brasileirao` (dono), `bi_brasileirao_leitura` (só `analytics`) | `sql/00_criar_banco_e_papel.sql` | Senhas por `\password`, nunca em arquivo |
| Power BI | Power BI Desktop, modelo estrela, DAX | `powerbi/README.md`, `medidas.dax`, `tema_brasileirao.json`, `dados/*.csv` | CSVs exportados por `sql/06_exportar_csv.sql` |
| Site | HTML, CSS e JS puros (módulos ES), gráficos SVG próprios | `web/` | Lê `web/data/brasileirao2024.json` (gerado por `scripts/exportar_web.py`). A classificação vem pronta da view; participações, casa e fora, sequências e aproveitamento são derivados de novo em JS (`web/js/dados.js` e páginas) |
| Imagens | `scripts/buscar_fotos.py` (Wikidata ou, na falta do vínculo, a ficha da Wikipédia em inglês confirma o jogador; Commons dá arquivo, autor e licença) → `core.escudo_clube`, `core.foto_jogador` → `analytics.credito_imagem` | `data/reference/escudos_clubes.csv`, `fotos_jogadores.csv` | Só licenças livres; nenhuma imagem no repositório; o site só lê as URLs do JSON |
| Testes | `unittest` (101), Node para o motor do jogo, SQL (21) | `tests/`, `sql/05_testes.sql` | 11 testes pulam sem `data/external/` |
| CI | GitHub Actions | `.github/workflows/testes.yml`, `pages.yml` | Recria o banco a cada push e confere o JSON do site |

## 3. Decisões já aprovadas (não reabrir sem motivo novo)

| Decisão | Registrada em |
|---|---|
| openfootball (CC0) é a fonte principal das partidas | `docs/fontes_de_dados.md` |
| adaoduque (sem licença) fica fora do Git; só fatos derivados conferidos são publicados | `docs/fontes_de_dados.md`, `LICENCAS.md` |
| Wikipédia (CC BY-SA 4.0) para assistências, jogos sem sofrer gol, seleção e prêmios, com atribuição | `data/reference/wikipedia_en/PROCEDENCIA.md` |
| CBF consultada manualmente para validar a classificação final; sem coleta automatizada | `docs/qualidade/auditoria_fase2.md` (B1) |
| Clube identificado pela sigla de 3 letras (BOT, PAL...) | `docs/fontes_de_dados.md` |
| Rodada **nominal** é a perspectiva principal; data real preservada para análise cronológica | `docs/modelagem/proposta_fase3.md` §4 |
| Classificação por rodada é **reconstrução analítica**, com aviso obrigatório; só a final foi conferida | `proposta_fase3.md` §4, `sql/04_views.sql` |
| Desempate: pontos, vitórias, saldo, gols pró, confronto direto (só 2 empatados e os 2 jogos já disputados, placar agregado); cartões e sorteio não se aplicam | `docs/regras_de_classificacao.md` |
| Empate não resolvido: posição compartilhada (`RANK`) e ordem alfabética só para exibição | `proposta_fase3.md` §4.3 |
| Horário sem valor na fonte herda o da linha anterior, marcado por `hora_explicita` | `docs/fontes_de_dados.md`, auditoria seção E |
| Placar do intervalo vazio (jogos 0-0) fica vazio, fiel à fonte | `docs/fontes_de_dados.md` |
| `TRUNCATE` só na `staging`; `core` sincronizado por `MERGE`; sem papel de carga separado | `proposta_fase3.md` §5 e §6 |
| Cada métrica é calculada no seu grão (`fato_partida` para o campeonato, `fato_participacao` para clubes) | `proposta_fase3.md` §3 |
| Uma fonte da verdade: Power BI e site leem as mesmas views | `README.md` |
| Jogador = `jogador × clube`; homônimos de clubes diferentes ficam separados | `docs/qualidade/auditoria_jogadores_e_banco.md` |
| Assistências fora do ranking da Wikipédia = `NULL` (nunca zero) | `sql/04_views.sql`, auditoria de jogadores |
| Destino 2024: Libertadores até o 8º (vagas ampliadas), Sul-Americana até o 14º, rebaixados do 17º ao 20º | `sql/04_views.sql` |
| Identidade visual inspirada no ge; uma pergunta por página; até 4 cartões e 3 gráficos | `powerbi/README.md` §4 |
| Carta de jogador só com foto real; sem foto livre, mostra a camisa do clube e as iniciais | Conversa de 2026-10-30, `README.md` |
| Licenças: código MIT; documentação CC BY 4.0; dados de terceiros nas licenças de origem | `LICENCAS.md` |
| Foto só com confirmação da Wikidata (nome + vínculo com o clube em 2024) e licença livre com autor; crédito no banco (`core.foto_jogador`, `analytics.credito_imagem`); o site não busca imagens sozinho | Decisão do Thiago em 2026-11-01, `scripts/buscar_fotos.py`, `docs/fontes_de_dados.md` |
| Quiz removido do site (redundante com os rankings) | Pedido do Thiago em 2026-11-01 |

## 4. Etapas concluídas

| Etapa | Entregas | Evidência |
|---|---|---|
| Fase 1: avaliação de fontes | Fontes escolhidas e descartadas, com motivo | `docs/fontes_de_dados.md` |
| Fase 2: aquisição e validação das partidas | 380 partidas; classificação final = CBF (160 campos); comparação jogo a jogo com o adaoduque | `docs/qualidade/auditoria_fase2.md` |
| Fase 3: modelagem e PostgreSQL | 3 schemas, 10 tabelas no `core`, carga idempotente, 21 testes SQL | `docs/modelagem/modelo_dados.md` |
| Jogadores | 929 gols conferidos com os placares; artilharia = Wikipédia; cartões; seleção e prêmios | `docs/qualidade/auditoria_jogadores_e_banco.md` |
| Camada analítica | Dimensões, fatos, classificação por rodada e final, estatísticas de jogador | `sql/04_views.sql` |
| Site | 8 páginas, tema claro e escuro, celular, créditos das imagens | `web/`, `tests/test_web.py` |
| Minijogo | Prancheta 2024 (jogo de técnico) | `web/js/tecnico/`, `tests/jogo_tecnico.mjs` |
| Power BI (guia) | Medidas DAX, tema, layout de 5 páginas, CSVs | `powerbi/` |

## 5. Pendências

### 5.1 Dados (herdadas das auditorias)

| Código | Pendência | Impacto |
|---|---|---|
| P1 | URLs exatas da verificação feita pelo revisor na CBF | Evidência C da auditoria fica sem link |
| P2 | Versão oficial do regulamento (REC); a cópia consultada é de terceiros e o §1 (confronto direto) está truncado | Regra do confronto direto apoiada em fontes secundárias. Não decidiu nenhuma posição em 2024 |
| P3 | Validação jogo a jogo com a CBF | Partidas validadas só contra fonte independente não oficial |
| P4 | Placar do intervalo: 2 divergências prováveis no openfootball (partidas 201 e 203) | Não usado em indicadores; protegido por teste |
| P6 | Cartões sem fonte independente | Apresentados como dado da fonte, sem a garantia dos gols |
| P7 | Assistências só do top 11 da Wikipédia; jogos sem sofrer gol de goleiros só do top 12 | Rankings parciais; `NULL` fora deles |

### 5.2 Decisões em aberto

| Decisão | Situação | Por que importa |
|---|---|---|
| Definição do aproveitamento | `docs/regras_de_classificacao.md` diz "será decidida na Fase 4"; não há registro da decisão. Hoje: CBF `floor(100 × P / (3 × J))` (ex.: Athletico 36); view `round(..., 1)` (36,8); site recalcula em JS `100 × P / (3 × J)` e exibe com 1 casa (36,8%); DAX `DIVIDE` sem arredondar, formatado com 1 casa | O site e o Power BI mostram 36,8; a CBF, 36. Três implementações da mesma regra |
| Repositório no GitHub | Nome do repositório vazio ainda não informado; a pasta local não tem remoto. Último commit em 2026-10-22 (Fase 2); Fase 3, site e Power BI não estão commitados | Sem isso, não há portfólio publicado nem CI rodando |
| Montagem do `.pbix` e capturas `docs/img/powerbi-*.png` | Depende do Power BI Desktop do Thiago | O README aponta para imagens que ainda não existem |
| Estádios | Não existe entidade estádio. Os nomes vêm de duas fontes com grafias diferentes ("Nilton Santos" em `clubes_visual.csv`, "Estádio Nilton Santos" nas partidas) e há jogos em outros estádios (ex.: o Grêmio foi mandante fora da Arena em 9 dos 19 jogos; a causa provável são as enchentes no RS, ainda não verificada jogo a jogo). O estádio de cada partida vem do adaoduque, sem conferência independente | Qualquer análise de "fator casa real" exige um mapa de estádios, que é decisão de modelagem |

### 5.3 Arrumação e documentação (encontradas na criação da Skill, nada foi alterado)

| Item | Evidência | Impacto |
|---|---|---|
| Pasta `.github/` ausente em `C:\Projetos\Brasileirão2024` | Existe na cópia de trabalho do projeto, não na pasta local | Sem ela, o CI e a publicação do site não sobem para o GitHub |
| `_backup_versao_local/` fora do `.gitignore` | Pasta na raiz do projeto local | Pode ir para o repositório público por engano |
| `sql/00_criar_banco_e_papel.sql`, BLOCO 5 | A consulta final usa `datlocale`, que só existe a partir do PostgreSQL 17; no 16 ela falha depois de criar papéis e banco (verificado num banco de teste) | O README diz "testado no 16"; no 15 e no 16 o script termina com erro, embora tudo tenha sido criado |
| README: "101 testes" nos destaques e "100 testes" na estrutura | `README.md` | Contagem atual: 101 |
| `docs/regras_de_classificacao.md` diz que o confronto direto "será implementado" | Já está implementado em `analytics.classificacao_rodada` | Documento desatualizado |
| `docs/modelagem/criacao_banco.md`: pré-requisito "o agente ainda não verificou" | O mesmo documento diz "Status: testado" | Documento desatualizado |

## 6. Como reconferir este retrato

```powershell
git status --short                       # o que mudou e não foi commitado
git log --oneline -n 10                  # últimos commits
git remote -v                            # se já existe repositório remoto
py -3.14 -I -X utf8 -m unittest discover -s tests   # estado dos testes
```

E releia: `README.md` (destaques e limitações), `docs/visao_produto.md` (situação de cada
recurso) e as seções "Pendências" das auditorias em `docs/qualidade/`.
