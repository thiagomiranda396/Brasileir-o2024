# Licenças

Este repositório reúne material original do projeto e dados de terceiros. Cada parte mantém a
sua licença.

## Material original do projeto

| Caminho | Licença | Titular |
|---|---|---|
| `scripts/`, `tests/`, `sql/` | [MIT](LICENSE) | Thiago Miranda, 2026 |
| `README.md`, `docs/`, `LICENCAS.md` | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt_BR) | Thiago Miranda, 2026 |
| `data/reference/clubes.csv` (cadastro elaborado no projeto: siglas, nomes, UF, grafia na fonte) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt_BR) | Thiago Miranda, 2026 |

Atribuição sugerida para a documentação: "Projeto Brasileirão 2024 — BI, de Thiago Miranda,
licenciado sob CC BY 4.0".

## Dados de terceiros

| Caminho | Origem | Licença da origem | Condições |
|---|---|---|---|
| `data/raw/openfootball/2024_br1.txt` | [openfootball/south-america](https://github.com/openfootball/south-america), commit `119fa17` | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (domínio público) | Nenhuma; a atribuição é feita por cortesia |
| `data/processed/partidas.csv` | Derivado exclusivamente do arquivo acima por `scripts/converter_openfootball.py` | CC0 1.0 (mantida) | Nenhuma |
| `data/raw/wikipedia/tabela_serie_a_2024.wikitext` | Wikipédia em português, "Predefinição:Tabela do Campeonato Brasileiro da Série A - 2024", [revisão 70400733](https://pt.wikipedia.org/w/index.php?oldid=70400733), colaboradores da Wikipédia | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.pt_BR) | Atribuição obrigatória; redistribuições e adaptações desse arquivo continuam sob CC BY-SA 4.0. A licença **não** se estende ao resto do repositório, que apenas o utiliza como referência de validação |
| `data/raw/*/PROCEDENCIA.json` | Gerados por `scripts/baixar_fontes.py` (metadados: URL, versão, hash) | CC BY 4.0 (material original) | — |

## Material de terceiros que NÃO está no repositório

| Material | Motivo | Como obter |
|---|---|---|
| Dataset [adaoduque/Brasileirao_Dataset](https://github.com/adaoduque/Brasileirao_Dataset) e o mapa de nomes usado para cruzá-lo | Sem licença declarada (todos os direitos reservados). Usado só na auditoria local; fica em `data/external/`, ignorado pelo Git | `python -I scripts/baixar_fontes.py --auditoria` (dataset); o mapa de nomes é um arquivo local, descrito em `docs/fontes_de_dados.md` |
| Tabela oficial da CBF | Sem licença de reutilização; consultada uma única vez para validação | [cbf.com.br](https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-a/2024) |
| REC Série A 2024 (cópia de terceiros) | Direitos não esclarecidos | Ver `docs/regras_de_classificacao.md` |

Nomes e marcas de clubes e competições pertencem aos respectivos titulares e são citados só para
identificação.
