# 2. Modelagem

Documentos do projeto: `docs/modelagem/modelo_dados.md` (o que existe),
`docs/modelagem/proposta_fase3.md` (por que é assim), `sql/02_tabelas.sql`, `sql/04_views.sql`
e `powerbi/README.md` §2 (modelo estrela).

## 2.1 Princípio: o grão primeiro

Toda tabela, view e medida começa com a frase "uma linha por ___". Sem essa frase, não há
modelo. O cabeçalho de cada objeto SQL do projeto diz o grão; mantenha esse padrão.

## 2.2 Entidades do `core`

| Entidade | Grão | Chave | Relações e regras principais |
|---|---|---|---|
| `clube` | clube (20) | `id_clube` (sigla) | Nome único; cores em hexadecimal; estádio, cidade e capacidade do cadastro |
| `partida` | partida (380) | `id_partida` (ordem do arquivo-fonte) | FK mandante e visitante → `clube`; `resultado` é coluna gerada; `linha_origem` aponta o bruto |
| `partida_complemento` | partida (1:1) | `id_partida` | Estádio, técnicos e formações (adaoduque, derivado) |
| `jogador` | jogador × clube (587) | `id_jogador` (slug + sigla) | FK → `clube`; `nome_fonte` e `nome_exibicao` únicos por clube |
| `gol` | gol (929) | `id_gol` | FK → partida, jogador e dois clubes (do jogador e beneficiado); gol contra ⇔ clubes diferentes |
| `cartao` | cartão (2.096) | `id_cartao` | FK → partida, jogador, clube |
| `ranking_wikipedia` | jogador × métrica (23) | `(metrica, id_jogador)` | Assistências e jogos sem sofrer gol; rankings **parciais** |
| `selecao_campeonato` | jogador (11) | `id_jogador` | Setor: goleiro, defensor, meio-campista, atacante |
| `premio_mensal` | mês × prêmio (21) | `(mes, premio)` | Craque, goleiro e revelação do mês |
| `carga_execucao` | carga × tabela | `(id_carga, tabela)` | Inseridas, atualizadas e removidas por carga |

**Estatísticas não são tabelas.** Pontos, saldo, aproveitamento, artilharia e classificação
são **derivados** em views do `analytics`, para nunca ficarem desatualizados em relação ao
`core`. A exceção são dados externos que o projeto não consegue derivar (rankings da Wikipédia),
guardados como fatos da fonte.

## 2.3 E a temporada?

O escopo é **uma temporada (2024)**. Ela está implícita: o `CHECK` de `data_partida` limita as
datas a 13/04/2024–08/12/2024, `rodada` vai de 1 a 38 e `dim_rodada` é a dimensão de tempo
nominal. Não existe `dim_temporada`.

Para várias temporadas seria preciso, no mínimo: `id_temporada` em `partida` (e nas chaves
`UNIQUE` de rodada e de confronto), jogador por temporada, cadastro de clubes por temporada
(quem subiu e quem caiu), regras de classificação e destinos por temporada e novas fontes. Isso
muda o grão de quase tudo: **é decisão do Thiago**. Não acrescente colunas "preparando o
futuro" sem pedido.

## 2.4 Camada `analytics` (contrato com Power BI e site)

| View | Grão | Para que serve |
|---|---|---|
| `dim_clube`, `dim_jogador`, `dim_rodada` | clube, jogador × clube, rodada | Filtros e rótulos |
| `fato_partida` | partida (380) | Métricas **do campeonato** |
| `fato_participacao` | clube × partida (760) | Métricas **por clube**, casa e fora |
| `fato_gol` | gol (929) | Artilharia, faixas de minuto |
| `fato_cartao` | cartão (2.096) | Disciplina |
| `classificacao_rodada` | clube × rodada (760) | Tabela após cada rodada (reconstrução analítica) |
| `classificacao_final` | clube (20) | Tabela final e destino; filtro da anterior na rodada 38 |
| `jogador_estatisticas` | jogador × clube (587) | Gols, pênaltis, cartões, assistências |
| `selecao_campeonato`, `premio_mensal` | listas | Wikipédia |

Regras:
- **Uma regra num só lugar.** A ordenação da classificação existe só em
  `classificacao_rodada`; `classificacao_final` apenas filtra. O DAX e o JavaScript só leem a
  posição pronta.
- `desempenho por mando` não tem view própria: é `fato_participacao` agrupada por `mando`.
  Não crie uma segunda definição das mesmas métricas.
- Mudar uma coluna do `analytics` quebra o contrato: confira `scripts/exportar_web.py`,
  `web/js/dados.js`, `sql/06_exportar_csv.sql`, `powerbi/medidas.dax` e os testes.

## 2.5 Modelo estrela no Power BI

- `dim_rodada` filtra todos os fatos; `dim_clube` filtra `fato_participacao[id_clube]`,
  `fato_gol[id_clube_beneficiado]`, `fato_cartao`, `classificacao_*`.
- `dim_clube → fato_participacao[id_adversario]` existe **inativa** (use `USERELATIONSHIP`).
- **Não** relacione `dim_jogador` com `dim_clube` (dois caminhos até `fato_gol`) nem
  `fato_partida` com `dim_clube` (dois clubes por partida).
- `dim_calendario` é tabela calculada em DAX, ligada a `fato_partida[data_partida]`.

## 2.6 Padrões de chave e constraint

- Chave natural quando ela é estável e legível (sigla do clube); sequencial quando a fonte
  não tem identificador (`id_partida`, `id_gol`), sempre com uma coluna de rastreio até a origem.
- Regra de negócio simples vira `CHECK` (placar não negativo, período coerente com o minuto,
  acréscimo só aos 45 e aos 90). Regra entre linhas vira validação na carga **e** teste SQL.
- Coluna derivada de outra da mesma linha pode ser `GENERATED ALWAYS AS ... STORED`
  (`partida.resultado`).
- Sem `ON DELETE CASCADE`: remoções são explícitas, dos filhos para os pais.

## 2.7 Checklist para mudar o modelo (sempre com aprovação)

1. Escreva uma proposta curta no estilo de `proposta_fase3.md`: problema, grão, colunas,
   chaves, alternativas avaliadas, impacto em views, Power BI, site e testes.
2. Depois da aprovação: `sql/02_tabelas.sql` (usa `IF NOT EXISTS`; mudar uma tabela existente
   exige recriar o banco, que é reconstruível a partir dos CSVs).
3. View tipada e sincronização em `sql/03_carga.sql`; validações da carga.
4. Views em `sql/04_views.sql`; privilégios do papel de leitura.
5. Testes em `sql/05_testes.sql` e, se o dado vier de CSV, em `tests/`.
6. Exportações (`sql/06_exportar_csv.sql`, `scripts/exportar_web.py`) e consumidores
   (`powerbi/`, `web/js/`).
7. `docs/modelagem/modelo_dados.md` e, se mudar um grão, a seção 3 do `SKILL.md`.
