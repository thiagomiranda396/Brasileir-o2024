# Licenças

Este repositório reúne material original do projeto e dados de terceiros. Cada parte mantém a
sua licença.

## Material original do projeto

| Caminho | Licença | Titular |
|---|---|---|
| `scripts/`, `tests/`, `sql/`, `web/` (exceto `web/data/`), `.github/`, `powerbi/medidas.dax`, `powerbi/tema_brasileirao.json` | [MIT](LICENSE) | Thiago Miranda, 2026 |
| `README.md`, `docs/`, `LICENCAS.md`, `powerbi/README.md` | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt_BR) | Thiago Miranda, 2026 |
| `data/reference/clubes.csv` (cadastro elaborado no projeto: siglas, nomes, UF, grafia na fonte) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt_BR) | Thiago Miranda, 2026 |
| `data/reference/clubes_visual.csv` (cores, cidade, estádio e capacidade, página da Wikipédia) e `data/reference/jogadores_destaque.csv` (nomes populares e páginas da Wikipédia) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt_BR); estádios e capacidades são fatos consultados na Wikipédia | Thiago Miranda, 2026 |

Atribuição sugerida para a documentação: "Projeto Brasileirão 2024 — BI, de Thiago Miranda,
licenciado sob CC BY 4.0".

## Dados de terceiros

| Caminho | Origem | Licença da origem | Condições |
|---|---|---|---|
| `data/raw/openfootball/2024_br1.txt` | [openfootball/south-america](https://github.com/openfootball/south-america), commit `119fa17` | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (domínio público) | Nenhuma; a atribuição é feita por cortesia |
| `data/processed/partidas.csv` | Derivado exclusivamente do arquivo acima por `scripts/converter_openfootball.py` | CC0 1.0 (mantida) | Nenhuma |
| `data/raw/wikipedia/tabela_serie_a_2024.wikitext` | Wikipédia em português, "Predefinição:Tabela do Campeonato Brasileiro da Série A - 2024", [revisão 70400733](https://pt.wikipedia.org/w/index.php?oldid=70400733), colaboradores da Wikipédia | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.pt_BR) | Atribuição obrigatória; redistribuições e adaptações desse arquivo continuam sob CC BY-SA 4.0. A licença **não** se estende ao resto do repositório, que apenas o utiliza como referência de validação |
| `data/raw/*/PROCEDENCIA.json` | Gerados por `scripts/baixar_fontes.py` (metadados: URL, versão, hash) | CC BY 4.0 (material original) | — |
| `data/processed/gols.csv`, `cartoes.csv`, `jogadores.csv`, `partidas_complemento.csv` | Derivados por `scripts/preparar_jogadores.py` de [adaoduque/Brasileirao_Dataset](https://github.com/adaoduque/Brasileirao_Dataset), commit `15f027c` | A fonte não declara licença | Contêm só fatos esportivos (quem marcou, minuto, cartões, técnico, estádio), reorganizados e conferidos pelo projeto; o arquivo bruto **não** é redistribuído. Crédito à fonte no README, no site e aqui. Se o autor da fonte pedir, estes arquivos são removidos |
| `data/reference/escudos_clubes.csv`, `data/reference/fotos_jogadores.csv` | Gerados por `scripts/buscar_fotos.py`: referência a arquivos da [Wikimedia Commons](https://commons.wikimedia.org/) (nome, URL da miniatura, página), com o **autor e a licença de cada arquivo** lidos dos metadados do Commons, e o item da [Wikidata](https://www.wikidata.org/) do jogador, com a fonte que confirmou o clube em 2024 (Wikidata ou a ficha da página na Wikipédia em inglês; nenhum texto da Wikipédia é copiado) | Os metadados da Wikidata são [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/); cada imagem segue a licença registrada na sua linha (só CC0, domínio público, CC BY e CC BY-SA são aceitas) | As imagens **não** estão no repositório. Quem exibe uma imagem (site, Power BI) dá o crédito da linha correspondente: no site, na página "Créditos das imagens"; no Power BI, pela tabela `credito_imagem` |
| `data/reference/wikipedia_en/*.csv` | Wikipédia em inglês, [2024 Campeonato Brasileiro Série A](https://en.wikipedia.org/wiki/2024_Campeonato_Brasileiro_S%C3%A9rie_A), colaboradores da Wikipédia, consultado em 2026-10-29 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.pt_BR) | Atribuição obrigatória; adaptações desses arquivos continuam sob CC BY-SA 4.0 |
| `web/data/brasileirao2024.json`, `powerbi/dados/*.csv` | Exportados do banco: combinam as fontes acima | As de cada parte | As partes vindas da Wikipédia (assistências, jogos sem sofrer gol, seleção, prêmios) continuam sob CC BY-SA 4.0 |

## Material de terceiros que NÃO está no repositório

| Material | Motivo | Como obter |
|---|---|---|
| Arquivos brutos do dataset [adaoduque/Brasileirao_Dataset](https://github.com/adaoduque/Brasileirao_Dataset) (partidas, gols, cartões) e o mapa de nomes usado para cruzá-los | Sem licença declarada. Ficam em `data/external/`, ignorado pelo Git; o repositório publica só os fatos derivados listados acima | `python -I scripts/baixar_fontes.py --auditoria`; o mapa de nomes é um arquivo local, descrito em `docs/fontes_de_dados.md` |
| Escudos dos clubes e fotos de jogadores (os arquivos de imagem) | Carregados da Wikimedia Commons por quem os exibe, sob as licenças dos autores. O repositório guarda só a referência e o crédito de cada arquivo (`data/reference/escudos_clubes.csv` e `fotos_jogadores.csv`, acima) | Pela URL de cada linha; autor e licença na mesma linha |
| Tabela oficial da CBF | Sem licença de reutilização; consultada uma única vez para validação | [cbf.com.br](https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-a/2024) |
| REC Série A 2024 (cópia de terceiros) | Direitos não esclarecidos | Ver `docs/regras_de_classificacao.md` |

Nomes e marcas de clubes e competições pertencem aos respectivos titulares e são citados só para
identificação.
