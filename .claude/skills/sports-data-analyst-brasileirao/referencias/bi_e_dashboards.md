# 5. Business Intelligence e dashboards

Documentos do projeto: `powerbi/README.md` (modelo, medidas e layout), `powerbi/medidas.dax`,
`powerbi/tema_brasileirao.json`, `docs/visao_produto.md`, `README.md` (seção do site),
`web/js/dados.js`.

## 5.1 Definição de KPI

Nenhum KPI entra no dashboard sem esta ficha (pode ficar no comentário da medida DAX ou da view):

```
KPI: <nome exato como aparece na tela>
Pergunta que responde: <uma frase>
Fórmula: <SQL ou DAX>
Grão e origem: <view do analytics>
Filtros que respeita: <rodada, clube, mando...>
Formato: <inteiro, %, 1 casa...>
Fonte e confiabilidade: <validado contra CBF | fonte única | ranking parcial>
Limitação: <o que ele não mostra>
Teste: <onde é conferido>
```

KPIs que já existem estão em `powerbi/medidas.dax`, por pasta: campeonato, clubes,
classificação, jogadores, disciplina e calendário. Antes de criar um, procure ali.

## 5.2 Análise exploratória (antes de qualquer gráfico)

1. **Perfil:** linhas, chaves distintas, nulos por coluna, mínimo e máximo, domínios.
2. **Sanidade:** os números de controle (SKILL.md, seção 3) batem?
3. **Distribuições:** gols por jogo, por faixa de minuto, por rodada; resultados por mando.
4. **Extremos:** maior goleada, maiores sequências, rodadas atípicas. Confira cada extremo
   na fonte antes de destacá-lo: extremo é onde o erro de dado aparece.
5. **Perguntas e hipóteses:** escreva o que os dados sugerem com os rótulos
   **[CÁLCULO]**, **[HIPÓTESE]** e **[INTERPRETAÇÃO]**.
6. **Só então** escolha o visual.

## 5.3 Regras de visualização do projeto

Vêm de `powerbi/README.md` §4 e valem também para o site:

- **Uma pergunta por página**; o título da página é essa pergunta.
- Leitura de cima para baixo: números principais → um gráfico que os explica → detalhes.
- **No máximo 4 cartões e 3 gráficos** por página; detalhes em drill-through, abas ou
  "mostrar mais".
- Grade fixa (16:9, 1280 × 720, margem 24 px, espaço 16 px, 12 colunas); filtros empilhados
  na barra lateral, na mesma ordem em todas as páginas.
- Identidade inspirada no ge: faixa do título `#06AA48`, barra lateral `#0A4F29`, fundo
  `#EEF1EE`; na página do clube, as cores do clube (medida `Cor do clube`).
- **Cor com função:** azul para a série principal, laranja só para comparação, vermelho e
  verde só para resultado e zonas. A paleta do tema foi validada para daltonismo: não troque
  cores sem refazer essa validação.
- Rótulos de dados só onde importam (máximo, último valor); grade clara; sem título de eixo
  redundante.

Escolha do gráfico:

| Pergunta | Visual | Cuidado |
|---|---|---|
| Posição ao longo das rodadas | Linha com eixo Y **invertido** (1º no topo) | Poucos clubes por vez (até 3); aviso de reconstrução |
| Comparar clubes numa métrica | Barras horizontais ordenadas | Começar em zero; mostrar empates |
| Casa × fora, marcados × sofridos | Colunas agrupadas | Mesma escala; laranja só para a comparação |
| Distribuição por minuto | Colunas por faixa | Avisar que as faixas finais incluem acréscimos |
| Composição de resultados | Barra 100% ou três cartões | Evite pizza com muitas fatias |
| Ranking parcial (assistências) | Barras com nota | "Ranking parcial publicado pela Wikipédia" |

## 5.4 Power BI

- Conexão pelo PostgreSQL com `bi_brasileirao_leitura` (modo Importar) ou pela pasta
  `powerbi/dados/` (UTF-8, localidade Inglês (EUA) para os decimais com ponto).
- Modelo estrela de `modelagem.md` §2.5; relações e direções conforme o guia.
- Medidas leem a tabela do seu grão; `DIVIDE` em toda divisão; posição da classificação é
  lida da view, nunca recalculada em DAX.
- Coluna calculada só para rótulo ou ordenação (ex.: turno); regra de negócio fica no SQL.
- Página oculta de **auditoria**: `Gols` = `Gols (conferência pelos eventos)` = 929;
  `Partidas` = 380; `Jogos do clube` = 760.
- O `.pbix` é montado pelo Thiago no Power BI Desktop. Seu papel: guia, medidas, tema, revisão
  e checklist; não diga que o arquivo existe antes de ele existir.

## 5.5 Site (`web/`)

- Estático, sem dependências nem build: módulos ES, gráficos SVG próprios, tema claro e
  escuro, celular, navegação por teclado.
- Lê só `web/data/brasileirao2024.json`, gerado por `scripts/exportar_web.py` a partir das
  views. `web/js/dados.js` **não recalcula a classificação**, mas deriva participações,
  resumo por clube (casa e fora, gols, cartões, técnicos) e o resumo do campeonato a partir
  das partidas e eventos do JSON. São regras duplicadas em relação ao SQL: qualquer mudança
  numa delas exige mudar a outra e conferir com `tests/test_web.py`. Consolidar isso (por
  exemplo, exportar mais views prontas) é decisão do Thiago.
- Mudou o banco? Exporte de novo e rode `tests/test_web.py`. No CI, o JSON exportado precisa
  ser idêntico ao versionado (`git diff --exit-code`).
- Imagens: só da Wikipédia/Wikimedia Commons, com licença livre, carregadas pelo navegador e
  creditadas na página de créditos. Sem imagem: sigla nas cores do clube e iniciais do jogador.
  Carta de jogador só com foto real; nunca um rosto genérico.

## 5.6 Minijogo

- O quiz foi removido em 2026-11-01 (o Thiago o achou redundante com os rankings). Se um
  recurso parecido voltar, ele só pode usar fatos validados e regras conferíveis a partir do JSON.
- A Prancheta 2024 usa um **modelo de jogo** (força dos elencos derivada do desempenho real).
  É ficção inspirada em dados: o texto do jogo não deve apresentar resultados simulados como
  estatística de 2024. O motor tem testes próprios (`tests/jogo_tecnico.mjs`).

## 5.7 Checklist de revisão de uma página

- [ ] A página responde a uma pergunta escrita no título.
- [ ] Cada número tem ficha de KPI e bate com a view (ou com a página de auditoria).
- [ ] Avisos obrigatórios presentes (classificação reconstruída, rankings parciais).
- [ ] Nenhum dado ausente aparece como zero.
- [ ] Cores com função; contraste ok no tema claro e no escuro; legível no celular.
- [ ] Filtros na barra lateral, na ordem padrão.
- [ ] Testes do site passam e a exportação está atualizada.
