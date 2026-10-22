# Brasileirão 2024: Business Intelligence

Projeto de portfólio de BI sobre o **Campeonato Brasileiro Série A 2024**, de ponta a ponta:
aquisição e auditoria de dados públicos, modelagem em PostgreSQL, indicadores em SQL, dashboard
em Power BI e, no futuro, uma aplicação web interativa.

> **Estado atual: fase de dados concluída.** O banco PostgreSQL **ainda não foi criado**, o
> dashboard Power BI **não foi implementado** e a aplicação web **não foi iniciada**. Este
> repositório contém, por enquanto, a base de partidas validada, os scripts que a reproduzem, os
> testes e a documentação de planejamento.

---

## Objetivo

Analisar a Série A 2024 com indicadores gerenciais e comparações entre clubes: classificação,
pontos, vitórias, empates e derrotas, gols, desempenho como mandante e visitante, e evolução ao
longo das rodadas. Os números são **reconstruídos a partir dos resultados das partidas** e
conferidos com referências independentes, com rastreabilidade até a fonte original.

O projeto prioriza precisão, evidências e reprodutibilidade. Limitações e pendências são
documentadas, não omitidas.

## Estado atual

| Fase | Situação |
|---|---|
| 1. Descoberta e avaliação de fontes | Concluída |
| 2. Aquisição, conversão e auditoria dos dados | **Concluída**: commit `805c9e1` (`805c9e1268fb51227d1142075f26a84b56d702b4`), "Fase 2: aquisição e validação das fontes de dados" |
| 3. Modelagem e PostgreSQL | **Proposta documentada, não executada**: nenhum banco, papel ou tabela criado |
| 4 a 8. SQL, Power BI, auditoria ponta a ponta, portfólio, publicação | Não iniciadas |

O que a Fase 2 entregou e verificou:

- **380 partidas** (38 rodadas × 10 jogos) da fonte principal, numa versão fixada por commit e
  hash SHA-256, convertidas para `data/processed/partidas.csv`.
- **Classificação final conferida com a tabela oficial da CBF:** 20 clubes × 8 campos (pontos,
  jogos, V, E, D, gols pró, gols contra, saldo) e as 20 posições, sem divergências. Campeão:
  Botafogo, com 79 pontos; 929 gols no campeonato.
- **Comparação jogo a jogo com uma fonte independente**, feita só localmente: 0 divergências de
  placar, rodada e data nas 380 partidas.
- Uma divergência encontrada na Wikipédia (gols pró do Juventude: 47 contra 48 oficiais) e uma
  na fonte secundária (horário de uma partida), ambas investigadas e documentadas.
- **70 testes automatizados** (biblioteca padrão do Python).

Detalhes: [auditoria da Fase 2](docs/qualidade/auditoria_fase2.md).

## Visão de produto

Dois produtos complementares, sobre a mesma base validada. A visão completa, com as condições
para cada recurso, está em [docs/visao_produto.md](docs/visao_produto.md).

**A. Dashboard gerencial (Power BI):** visão executiva, classificação, desempenho dos clubes,
mandantes × visitantes, gols e evolução por rodada.

**B. Aplicação web interativa:** exploração de clubes, partidas e jogadores, com prioridade
visual para cards de jogadores com foto e estatísticas; no futuro, quiz sobre o campeonato e
minijogos.

| Situação | Recursos |
|---|---|
| **Existente** | Base de partidas validada; classificação final conferida com a CBF; scripts e testes de reprodução |
| **Planejado** (dados já disponíveis) | Banco PostgreSQL e views analíticas; indicadores SQL; dashboard com classificação, desempenho, mandante × visitante, gols e evolução por rodada; exploração de clubes e partidas na aplicação web; quiz sobre clubes e partidas |
| **Depende de fontes de dados** (não avaliadas) | Fotos e estatísticas individuais de jogadores; cards de jogadores; escudos dos clubes; quiz sobre jogadores; minijogos |

Antes de implementar os recursos que dependem de fontes, será preciso avaliar procedência,
cobertura da temporada, **licenças e direitos** (dados, direito de imagem dos atletas, marcas dos
escudos), disponibilidade de dados confiáveis e requisitos técnicos. Recursos sem fonte adequada
ficam fora do produto, e a limitação é documentada.

## Tecnologias

| Ferramenta | Uso | Situação |
|---|---|---|
| Python 3 (só a biblioteca padrão) | Aquisição, conversão, validação e testes (`unittest`) | Em uso; testado com Python 3.14.8 no Windows |
| Git | Versionamento | Em uso, apenas local; sem repositório remoto |
| PostgreSQL 18 | Camadas staging, core e analytics | Previsto (Fase 3) |
| SQL (CTEs, funções de janela, `MERGE`) | Modelagem e indicadores | Previsto (Fases 3 e 4) |
| Power BI Desktop e DAX | Dashboard | Previsto (Fase 5) |
| Aplicação web | Interface interativa | **Tecnologia ainda não escolhida** |

## Fontes de dados e licenças

| Fonte | Papel | Licença | No repositório? |
|---|---|---|---|
| [openfootball/south-america](https://github.com/openfootball/south-america) | Fonte principal das partidas | CC0 1.0 | Sim |
| [Wikipédia (pt)](https://pt.wikipedia.org/w/index.php?oldid=70400733), predefinição da classificação de 2024 | Referência de validação | CC BY-SA 4.0 | Sim, com atribuição |
| [Tabela oficial da CBF](https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-a/2024) | Validação da classificação final (consulta única) | Sem licença de reutilização | Não |
| [adaoduque/Brasileirao_Dataset](https://github.com/adaoduque/Brasileirao_Dataset) | Validação independente jogo a jogo, **só local** | Não declarada | **Não** (fora do Git) |

Material original deste repositório: código sob [MIT](LICENSE) e documentação sob CC BY 4.0. A
relação completa por caminho está em [LICENCAS.md](LICENCAS.md), e a procedência das fontes em
[docs/fontes_de_dados.md](docs/fontes_de_dados.md).

## Limitações conhecidas

- A classificação **por rodada** será uma reconstrução analítica (rodada nominal, incluindo os
  jogos adiados na rodada original), **não** a classificação oficial publicada em cada data.
- Critérios de desempate por cartões (5º e 6º do regulamento) não estão disponíveis na fonte
  principal. Na classificação final de 2024, só o 1º critério (vitórias) foi necessário.
- O fuso horário das partidas não é informado pela fonte. 150 dos 380 horários são herdados da
  linha anterior pela regra do formato e ficam marcados na coluna `hora_explicita`.
- Pendências de auditoria em aberto:

  | Código | Pendência |
  |---|---|
  | P1 | URLs exatas das páginas da CBF consultadas pelo revisor externo |
  | P2 | Versão oficial do regulamento (REC) hospedada pela CBF; foi consultada uma cópia de terceiros |
  | P3 | Validação partida a partida com a CBF |
  | P4 | Validação externa do placar do intervalo (não usado nos indicadores principais) |

## Estrutura

```
.
├── data/
│   ├── raw/            # fontes brutas em versões fixadas + PROCEDENCIA.json (URL, versão, SHA-256)
│   ├── processed/      # partidas.csv: base convertida e validada
│   ├── reference/      # clubes.csv: cadastro dos 20 clubes
│   └── external/       # (fora do Git) fonte de auditoria local sem licença de redistribuição
├── docs/
│   ├── fontes_de_dados.md          # procedência, reprodução, decisões de interpretação
│   ├── regras_de_classificacao.md  # regulamento e critérios de desempate
│   ├── visao_produto.md            # visão de produto e condições por recurso
│   ├── qualidade/                  # auditoria da Fase 2 e relatório de validação gerado
│   └── modelagem/                  # proposta da Fase 3 e guia de criação do banco
├── scripts/            # baixar_fontes.py, converter_openfootball.py, validar_dados.py
├── sql/                # 00_criar_banco_e_papel.sql (proposta; NÃO executado)
├── tests/              # testes automatizados (unittest)
├── LICENSE             # MIT (código)
└── LICENCAS.md         # licenças por caminho
```

As pastas do Power BI e da aplicação web ainda não existem; serão criadas nas fases
correspondentes.

## Como executar (Windows, PowerShell)

Requisitos: Python 3 (testado com 3.14.8) e Git. Não há dependências externas a instalar.
Execute os comandos na raiz do projeto.

```powershell
# 1. Conferir os hashes dos arquivos de dados (sem acessar a rede)
py -3.14 -I scripts/baixar_fontes.py --verificar

# 2. (Opcional) Baixar de novo as fontes nas versões fixadas; falha se o conteúdo mudar
py -3.14 -I scripts/baixar_fontes.py

# 3. Gerar data/processed/partidas.csv a partir do arquivo bruto
py -3.14 -I scripts/converter_openfootball.py

# 4. Rodar os testes
py -3.14 -I -X utf8 -m unittest discover -s tests -v

# 5. Gerar o relatório de validação (docs/qualidade/relatorio_validacao_fase2.md)
py -3.14 -I -X utf8 scripts/validar_dados.py
```

Observações:

- Se o lançador `py` não estiver disponível, use o caminho completo do interpretador, por exemplo
  `& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"` no lugar de `py -3.14`.
- `-I` executa o Python em modo isolado (sem variáveis de ambiente nem pacotes do usuário).
  `-X utf8` garante a saída correta de caracteres acentuados no console do Windows.
- O passo 2 confere o hash de cada arquivo baixado e só grava o que mudou: com conteúdo idêntico
  ao versionado, nem os dados nem os `PROCEDENCIA.json` são regravados, e a saída informa
  "inalterado". A data de aquisição registrada é a da primeira obtenção validada daquela versão
  do conteúdo. Fontes sem hash esperado são recusadas, sem download.
- O passo 3 é determinístico: gera um CSV idêntico byte a byte ao versionado.
- O passo 5 só regrava o relatório versionado quando o conteúdo muda: a data de geração é
  ignorada na comparação; os hashes dos dados validados, registrados no cabeçalho, não. Sem os
  arquivos da auditoria local, uma auditoria anterior é **preservada** se os dados e os demais
  resultados não mudaram; caso contrário, o relatório é regravado com a seção 2 "NÃO
  EXECUTADA" e um aviso explícito na saída. O motivo da decisão é sempre exibido.
- **Auditoria local (opcional):** `py -3.14 -I scripts/baixar_fontes.py --auditoria` baixa a fonte
  secundária para `data/external/`. A comparação também exige um mapa de nomes local, que não é
  versionado ([detalhes](docs/fontes_de_dados.md)). Sem esses arquivos, 11 dos 70 testes são
  **pulados** de propósito, e os demais continuam executáveis.

O banco de dados **não** faz parte destes passos: os scripts SQL da Fase 3 ainda não foram
executados, e a criação do banco exige aprovação ([guia](docs/modelagem/criacao_banco.md)).

## Próximas fases

| Fase | Entrega | Dependências principais |
|---|---|---|
| 3. Modelagem e PostgreSQL | Banco `brasileirao2024`, camadas staging, core e analytics, carga com `MERGE`, testes SQL | **Autorização explícita** para criar o banco e os papéis no servidor local; proposta em [proposta_fase3.md](docs/modelagem/proposta_fase3.md) |
| 4. SQL e indicadores | Consultas, views e dicionário de indicadores | Fase 3 |
| 5. Power BI | Modelo analítico, medidas DAX e dashboard | Fases 3 e 4; escudos dependem de fonte licenciada |
| 6. Auditoria ponta a ponta | Reconciliação fonte × SQL × DAX | Fases 3 a 5 |
| 7. Documentação e portfólio | Capturas, análises e dicionário de dados | Fase 6 |
| 8. Publicação | Repositório público no GitHub | **Autorização explícita** |
| Futuro | Fontes de jogadores e imagens; aplicação web | Avaliação de fontes e licenças ([visao_produto.md](docs/visao_produto.md)) |

## Licença

Código sob [MIT](LICENSE); documentação sob CC BY 4.0; dados de terceiros sob as licenças de
origem. Ver [LICENCAS.md](LICENCAS.md).
