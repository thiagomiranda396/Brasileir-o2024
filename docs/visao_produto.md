# Visão de produto

**Status (2026-11-04):** os dois produtos estão implementados sobre a mesma base validada. Esta
página registra o que existe, de onde vêm os dados de cada recurso e o que ficou de fora.

Legenda da coluna **Situação**:
- **Existente:** implementado e testado neste repositório.
- **Pronto:** arquivo do aplicativo no repositório, pronto para abrir e publicar.
- **Limitado:** existe, com a limitação descrita.

## A. Dashboard gerencial (Power BI)

| Recurso | Situação | Observação |
|---|---|---|
| Modelo estrela sobre o schema `analytics` | Pronto | [powerbi/README.md](../powerbi/README.md): conexão, relações, páginas |
| Medidas DAX (campeonato, clubes, classificação, jogadores, disciplina) | Existente | [powerbi/medidas.dax](../powerbi/medidas.dax) |
| Tema de cores | Existente | [powerbi/tema_brasileirao.json](../powerbi/tema_brasileirao.json) |
| Projeto do Power BI (PBIP: modelo TMDL + relatório PBIR) | Pronto | [powerbi/Brasileirao2024.pbip](../powerbi/Brasileirao2024.pbip), abre no Desktop e publica no Service |

## B. Aplicação web interativa (`web/`)

| Recurso | Situação | Fonte dos dados |
|---|---|---|
| Visão geral, destaques e gráficos | Existente | partidas (openfootball) e gols |
| Classificação rodada a rodada, casa e fora, evolução de posições | Existente | `analytics.classificacao_rodada` (reconstrução analítica; final conferida com a CBF) |
| Página de cada clube | Existente | partidas, gols, cartões, técnicos e estádios |
| Partidas com gols minuto a minuto e expulsões | Existente | partidas + gols e cartões (adaoduque, derivados) |
| Rankings de jogadores e página de cada jogador | Existente | gols e cartões (adaoduque); assistências e goleiros: **limitado** ao ranking da Wikipédia |
| Seleção do campeonato e prêmios mensais | Existente | Wikipédia (CC BY-SA 4.0) |
| Escudos dos clubes | Existente | Wikimedia Commons, registrados por `scripts/buscar_fotos.py`; sem imagem ou sem rede, sigla nas cores do clube |
| Fotos de jogadores | **Limitado** | Wikimedia Commons, só quando a Wikidata ou a ficha da Wikipédia em inglês confirma o jogador (nome e clube em 2024) e o arquivo tem licença livre; demais com a camisa do clube. Cobertura em `docs/qualidade/fotos_jogadores.md` |
| Minijogos: Prancheta 2024, jogo de técnico com mata-mata das quartas à final | Existente | Mesmos dados (força dos elencos derivada da tabela final, gols e prêmios) |
| Créditos das imagens (autor e licença de cada arquivo) | Existente | `analytics.credito_imagem` (metadados do Commons gravados no banco) |

## Decisões sobre imagens e direitos

- **Nenhuma imagem fica no repositório.** O script `scripts/buscar_fotos.py` registra, para cada
  escudo e foto, o arquivo da Wikimedia Commons, a URL da miniatura, o autor e a licença
  (`data/reference/escudos_clubes.csv` e `fotos_jogadores.csv` → `core.escudo_clube` e
  `core.foto_jogador`). O site carrega a imagem da Wikimedia pela URL e mostra os créditos
  (`analytics.credito_imagem`). O Power BI não usa imagens externas: o clube aparece num selo
  com a sigla nas cores dele e o jogador, pelo nome.
- **Escudos** são marcas dos clubes, usados só para identificá-los, como nas páginas da própria
  Wikipédia.
- **Fotos** de atletas seguem a licença do autor na Wikimedia Commons (só CC0, domínio público,
  CC BY e CC BY-SA). A foto só entra quando a Wikidata confirma que a pessoa teve vínculo com o
  clube em 2024 e tem o mesmo nome; antes, o site buscava pelo nome e podia trazer um homônimo
  (decisão do Thiago em 2026-11-01). Como a Wikidata não registra o clube de 2024 de muitos
  jogadores, a ficha da página em inglês (clube num período que inclui 2024) vale como segunda
  confirmação. Sem confirmação, a carta mostra a camisa do clube.

## Fora do escopo

- Assistências e minutos jogados de todos os jogadores: não há fonte aberta com licença clara.
- Estatísticas de jogo (posse, finalizações): a fonte disponível não tem esses dados para 2024.
- Classificação oficial publicada em cada data: o projeto reconstrói a tabela pela rodada nominal.
