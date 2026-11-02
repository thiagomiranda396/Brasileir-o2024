# Procedência: Wikipédia em inglês

| Item | Valor |
|---|---|
| Artigo | [2024 Campeonato Brasileiro Série A](https://en.wikipedia.org/wiki/2024_Campeonato_Brasileiro_S%C3%A9rie_A) |
| Autoria | Colaboradores da Wikipédia |
| Licença | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.pt_BR) |
| Consultado em | 2026-10-29 (versão do artigo vigente nessa data) |
| Seções transcritas | Top goalscorers, Top assists, Clean sheets, Monthly awards, Team of the Year |

Os arquivos desta pasta são transcrições manuais dessas seções, com os nomes de clubes trocados
pelas siglas de `data/reference/clubes.csv`. Ficam sob CC BY-SA 4.0, com atribuição aos
colaboradores da Wikipédia; a licença não se estende ao resto do repositório.

`artilheiros.csv` serve só de referência de validação: a artilharia publicada pelo projeto é
calculada a partir dos gols de cada partida (`data/processed/gols.csv`), e o teste
`tests/test_jogadores.py` confere que ela coincide com esta lista.

Limitação: o artigo lista só os primeiros colocados de assistências (11 jogadores) e de jogos
sem sofrer gols (12 goleiros). Não há fonte aberta com as assistências de todos os jogadores.
