# 7. Rastreabilidade

Documentos do projeto: `docs/fontes_de_dados.md`, `LICENCAS.md`, os `PROCEDENCIA.json` e
`PROCEDENCIA.md` em `data/`, `docs/qualidade/` e a seção "Limitações conhecidas" do `README.md`.

## 7.1 A cadeia que precisa continuar inteira

```
Fonte (URL + commit/oldid + SHA-256 + licença)        data/raw/<fonte>/PROCEDENCIA.json
  → script versionado (commit Git)                     scripts/*.py
  → arquivo processado, com rastreio até a linha        data/processed/*.csv (linha_origem, ids)
  → staging (cópia fiel, tudo text)                     staging.*_csv
  → core (tipado, validado; contagens da carga)         core.*, core.carga_execucao
  → analytics (views, uma regra por métrica)            analytics.*
  → Power BI (medidas) e site (JSON exportado)          powerbi/, web/data/
```

Pergunta de controle: "dado um número na tela, consigo chegar à linha do arquivo bruto que o
originou?". Se a resposta for não, a rastreabilidade quebrou.

| Elemento de rastreio | O que guarda |
|---|---|
| `PROCEDENCIA.json` | URL, versão, licença, SHA-256, bytes, `adquirido_em_utc` (primeira obtenção daquela versão) |
| `linha_origem` | Linha de `data/raw/openfootball/2024_br1.txt` de cada partida |
| `hora_explicita` | Horário escrito na fonte (1) ou herdado pela regra do formato (0) |
| `nome_fonte` × `nome_exibicao` | Nome na súmula × nome popular (com a página da Wikipédia usada) |
| `core.carga_execucao` | Quem carregou, quando e quantas linhas foram inseridas, atualizadas e removidas |
| Cabeçalho do relatório de validação | SHA-256 dos arquivos validados |
| Git | Histórico do conteúdo de todos os arquivos derivados |

## 7.2 Registro de tratamento

Toda regra que muda, exclui, herda, mapeia ou padroniza um dado é registrada assim (no
documento da fonte ou na auditoria correspondente):

```
Data: AAAA-MM-DD
Item: <tabela/coluna/registros afetados, com quantidade>
Fonte: <fonte e versão>
Situação encontrada: <o que estava no dado>
Evidência: <fontes consultadas, categoria A/B/C>
Tratamento: <manter fiel | corrigir por regra | excluir | herdar | mapear>
Regra implementada em: <script/SQL e teste que a protege>
Aprovado por: <Thiago, data> (obrigatório se mexer em dado de fonte ou número publicado)
Impacto: <números e telas afetados>
```

## 7.3 Premissas em vigor

| Premissa | Base | Onde está registrada |
|---|---|---|
| Pontuação 3/1/0 | Bate com a CBF nos 20 clubes; o RGC não foi lido | `docs/regras_de_classificacao.md` |
| Confronto direto pelo placar agregado de 180 minutos | REC 2025 e fontes secundárias; o §1 do REC 2024 consultado está truncado | idem |
| Horário herdado da linha anterior quando omitido | Parser oficial do openfootball; 150/150 coincidem com o adaoduque em até 10 min | `docs/fontes_de_dados.md` |
| Horário no fuso de Brasília | Prévias da imprensa; não verificado jogo a jogo | idem |
| Diferenças de até 10 min = horário programado × efetivo | Hipótese, não documentada pelas fontes | relatório de validação |
| Mesmo nome + mesmo clube = mesmo jogador | Grão `jogador × clube` | auditoria de jogadores |
| Destino das vagas de 2024 | Predefinição da Wikipédia (vagas ampliadas pelos títulos de BOT e FLA) | `sql/04_views.sql` |

Uma premissa nova só entra com a base e o lugar de registro. Se for usada num número
publicado, precisa de aprovação.

## 7.4 Limitações para o leitor

Estas limitações aparecem para quem vê o portfólio (README, notas do Power BI, site). Ao criar
uma tela ou análise que dependa delas, repita o aviso no próprio visual:

- Classificação por rodada é reconstrução analítica; só a final foi conferida.
- Assistências e jogos sem sofrer gol (goleiros) são rankings parciais da Wikipédia.
- Cartões sem fonte independente para conferência jogo a jogo.
- Placar do intervalo: 2 divergências prováveis no openfootball (rodada 22).
- Fotos só de jogadores com página e foto livre na Wikipédia.
- Sem minutos jogados, finalizações, posse ou xG.
- Estádio por partida vem de fonte sem licença declarada e sem conferência independente; nomes
  não padronizados.

Modelo de nota curta para um visual:

```
Fonte: <fonte(s)>. <Cálculo em uma frase>. <Limitação principal>.
Ex.: "Fonte: openfootball (CC0). Classificação reconstruída rodada a rodada a partir dos
resultados; só a tabela final foi conferida com a CBF."
```

## 7.5 Licenças e o que pode ser publicado

| Situação | Pode publicar? |
|---|---|
| Dado CC0 (openfootball) e derivados | Sim |
| Dado CC BY-SA (Wikipédia) | Sim, com atribuição; continua sob CC BY-SA |
| Fonte sem licença (adaoduque) | Só fatos derivados conferidos, com crédito; o bruto nunca |
| Tabela da CBF, regulamento de terceiros | Não; só consulta e citação do resultado da conferência |
| Imagens | Só por link para a Wikimedia, com licença livre e crédito; nenhuma no repositório |

Antes de publicar um arquivo novo, confira o `.gitignore` e acrescente a linha
correspondente em `LICENCAS.md` (com aprovação).
