# Fontes de dados e procedência

## Fontes utilizadas

| Fonte | Papel | Versão fixada | Licença | No repositório? |
|---|---|---|---|---|
| [openfootball/south-america](https://github.com/openfootball/south-america) — `brazil/2024_br1.txt` | **Fonte principal** das partidas | commit `119fa1724b2079a1072a0cb0ca0ccac26d92fd34` | CC0 1.0 (domínio público) | Sim — `data/raw/openfootball/` |
| [Wikipédia — Predefinição: Tabela do Campeonato Brasileiro da Série A - 2024](https://pt.wikipedia.org/w/index.php?oldid=70400733) | Referência da classificação final | revisão `70400733` (2025-07-04) | CC BY-SA 4.0 | Sim — `data/raw/wikipedia/` (com atribuição) |
| [adaoduque/Brasileirao_Dataset](https://github.com/adaoduque/Brasileirao_Dataset) — `campeonato-brasileiro-full.csv` | Validação independente, jogo a jogo | commit `15f027c3be337bb130d6ae94436b5cdca737377c` | **Não declarada** | **Não** — `data/external/` está no `.gitignore` |

A URL, a versão, o hash SHA-256, o tamanho e a data de aquisição de cada arquivo ficam
registrados em `PROCEDENCIA.json`, na mesma pasta do arquivo baixado.

**`adquirido_em_utc`** é o momento da **primeira obtenção e validação bem-sucedida daquela
versão do conteúdo**, identificada pelo SHA-256. Um novo download idêntico não altera a data, e
nem o arquivo de dados nem o registro são regravados. Se só os metadados descritivos mudarem
(descrição, licença etc.), o registro é atualizado e a data é preservada. A data atual só é
usada quando uma nova versão do conteúdo é validada, quando o arquivo existe sem registro, ou
quando a data registrada está ausente ou é inválida (só vale texto ISO 8601 com fuso UTC,
deslocamento zero). Nesses casos a data original não é conhecida, e a saída informa a
substituição. O registro só é criado ou atualizado depois de validar o download pelo hash
esperado.

**Atribuição (Wikipédia):** "Predefinição:Tabela do Campeonato Brasileiro da Série A - 2024",
colaboradores da Wikipédia em português, licença
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

**adaoduque:** sem licença declarada, os dados não são redistribuídos. São usados apenas
localmente, para conferência. Qualquer pessoa pode obtê-los executando o script de aquisição.

## Como reproduzir

Requisito: Python 3.10+ (só a biblioteca padrão). A partir da raiz do projeto:

```bash
python -I scripts/baixar_fontes.py                 # baixa as fontes de produto e confere o SHA-256
python -I scripts/converter_openfootball.py        # gera data/processed/partidas.csv
python -I -X utf8 -m unittest discover -s tests -v # testes automatizados
python -I -X utf8 scripts/validar_dados.py         # gera docs/qualidade/relatorio_validacao_fase2.md
```

- `baixar_fontes.py --verificar` só confere os hashes dos arquivos locais, sem acessar a rede e
  sem gravar nem criar nenhum arquivo ou pasta.
  Se uma fonte mudar o conteúdo publicado na URL fixada, o script falha em vez de sobrescrever.
- Fontes sem hash SHA-256 esperado são **recusadas** sempre que são processadas, inclusive em
  `--verificar`: não são baixadas, verificadas nem registradas, e o script termina com código 1.
  (Uma fonte de auditoria não solicitada, sem `--auditoria`, é apenas ignorada.)
- **Auditoria local (opcional):** `baixar_fontes.py --auditoria` também baixa o adaoduque para
  `data/external/adaoduque/`. A comparação também precisa do mapa de nomes local
  `data/external/adaoduque/mapa_nomes_adaoduque.csv`, que não é versionado. Se **qualquer um**
  dos dois faltar, 11 testes são **pulados** (8 em `tests/test_auditoria_local.py` e 3 em
  `tests/test_relatorio.py`; o motivo informa o arquivo ausente). Nesse caso, o relatório
  versionado mantém a auditoria anterior se os dados validados (identificados pelo SHA-256 no
  cabeçalho) e os demais resultados não mudaram; se mudaram, a seção 2 é regravada como "NÃO
  EXECUTADA", com aviso. Os demais testes não dependem desses arquivos. O adaoduque nunca
  alimenta o produto analítico: nenhum script de carga ou modelagem lê `data/external/`.

### Testes automatizados (`tests/`)

| Arquivo | Escopo | Depende do adaoduque? |
|---|---|---|
| `test_baixar_fontes.py` | Aquisição sem rede (downloads simulados): gravação só do que mudou, preservação de `adquirido_em_utc` (só quando a data é válida), nova versão, hash divergente, recusa de fonte sem hash, `--verificar` somente leitura, `--auditoria` | Não |
| `test_conversor.py` | Interpretação do Football.TXT com entradas sintéticas: herança e marcação de horários, jogos adiados, rejeição de linhas inválidas | Não |
| `test_integridade.py` | CSV real aprovado + 12 tipos de erro injetado detectados | Não |
| `test_classificacao.py` | Regras de pontuação e desempate; regressão contra a tabela oficial da CBF | Não |
| `test_auditoria_local.py` | Detecção dos arquivos de auditoria (sempre executada) + comparação jogo a jogo e detecção de divergências injetadas | Comparação: **sim** (pulada se o dataset ou o mapa estiverem ausentes) |
| `test_relatorio.py` | Regravação do relatório só quando o conteúdo muda: regra de decisão (textos sintéticos) e execução real em diretório temporário, incluindo preservação e invalidação da auditoria anterior | 3 dos 16 testes: **sim** (pulados se ausentes) |

Os erros são injetados em cópias em memória; nenhum arquivo é alterado pelos testes.

## Decisões de interpretação

1. **Identificador dos clubes:** siglas de 3 letras da predefinição da Wikipédia (BOT, PAL...),
   mapeadas para os nomes de cada fonte em `data/reference/clubes.csv`.
2. **Jogos adiados:** o openfootball mantém cada jogo na **rodada original** e registra a **data
   real**. As enchentes no RS adiaram, entre outros, jogos das rodadas 7 e 8. O CSV preserva as
   duas informações. Decisão: a evolução por **rodada nominal** é a perspectiva principal, e a
   data real fica disponível para análises cronológicas (ver
   [proposta da Fase 3, seção 4](modelagem/proposta_fase3.md)).
3. **Horário:** jogo sem horário no Football.TXT herda o horário da linha anterior na mesma data,
   que é a semântica aplicada pelo parser oficial do openfootball. A coluna `hora_explicita`
   distingue horário escrito (1) de herdado (0); os 150 horários herdados coincidem com o
   adaoduque em até 10 minutos. Evidências completas na
   [auditoria, seção E](qualidade/auditoria_fase2.md). O fuso não é informado pela fonte; as
   prévias da imprensa usam horário de Brasília, mas isso não foi verificado jogo a jogo.
4. **Placar do intervalo:** ausente somente em jogos 0-0, nos quais é necessariamente 0-0.
   O CSV mantém o campo vazio, fiel à fonte.
5. **id_partida:** número sequencial na ordem do arquivo de origem. `linha_origem` aponta a linha
   do arquivo bruto, para rastrear cada registro.

## Referências consultadas (não armazenadas no repositório)

| Referência | Uso | Por que não está no repositório |
|---|---|---|
| [Tabela oficial da CBF, Série A 2024](https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-a/2024) | Validação da classificação final (consulta única) | Sem licença de reutilização; coleta automatizada não autorizada |
| REC Série A 2024 (cópia de terceiros) | Critérios de classificação | Direitos não esclarecidos; ver [regras_de_classificacao.md](regras_de_classificacao.md) |
| [openfootball/football.json](https://github.com/openfootball/football.json), `2025/br.1.json` | Evidência da semântica de horários do formato | Não é necessário; basta o link e o commit |

## Revisão de licenças e do que é publicado

| Arquivo ou pasta | Origem | Licença | Publicável? |
|---|---|---|---|
| `data/raw/openfootball/` | openfootball | CC0 1.0 | Sim |
| `data/raw/wikipedia/` | Wikipédia | CC BY-SA 4.0 | Sim, com a atribuição acima; o arquivo continua sob CC BY-SA |
| `data/processed/partidas.csv` | Derivado só do openfootball | CC0 na origem | Sim |
| `data/reference/clubes.csv` | Elaborado no projeto (sigla, nome, UF, grafia no openfootball). **É o cadastro carregado no produto** | CC BY 4.0 (material original; ver [LICENCAS.md](../LICENCAS.md)) | Sim |
| `data/external/adaoduque/mapa_nomes_adaoduque.csv` | Elaborado no projeto: grafia dos nomes no adaoduque (colunas `id_clube`, `nome_adaoduque`; 20 linhas), usada **só** pela auditoria local | — | **Não**; fica fora do Git junto com o dataset e nunca é lido pela carga do banco. Para refazer a auditoria num clone, recrie este arquivo localmente |
| `data/external/` | adaoduque | Não declarada | **Não**; está no `.gitignore` (verificado com `git check-ignore`) |
| `docs/qualidade/relatorio_validacao_fase2.md` | Gerado; contém **contagens agregadas** da comparação com o adaoduque e **um único valor** da fonte secundária (o horário 18:06 de ATP × INT), identificado como divergente; e valores da Wikipédia para comparação | CC BY 4.0 (material original) | Sim; nenhum registro do dataset do adaoduque é reproduzido além dessa citação |

Licenças do material original do projeto (MIT para o código, CC BY 4.0 para a documentação) e
a relação completa por caminho estão em [LICENCAS.md](../LICENCAS.md).

## Fontes avaliadas e não utilizadas

Detalhes no relatório da Fase 1: CBF (sem licença de dados nem API documentada; é consultada
manualmente como referência oficial), football-data.org (acesso gratuito à temporada 2024 não
confirmado), Base dos Dados/Transfermarkt, API-Football e FBref (termos não verificados ou
restritivos).
