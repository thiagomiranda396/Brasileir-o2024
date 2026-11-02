# 6. Validação

Documentos do projeto: `docs/qualidade/auditoria_fase2.md`,
`docs/qualidade/auditoria_jogadores_e_banco.md`, `docs/qualidade/relatorio_validacao_fase2.md`
(gerado), `docs/fontes_de_dados.md` (tabela de testes), `sql/05_testes.sql`,
`.github/workflows/testes.yml`.

## 6.1 Camadas de validação

| Nível | Pergunta | Exemplo no projeto |
|---|---|---|
| 1. Integridade interna | O dado é coerente consigo mesmo? | 380 partidas, 19 em casa e 19 fora por clube, 1 jogo por clube por rodada |
| 2. Entre fontes independentes | Outra fonte concorda? | openfootball × adaoduque: 380/380 jogos, 0 divergências de placar, rodada e data |
| 3. Com a fonte oficial | Bate com a CBF? | Classificação final: 160 campos (mais as 20 posições), 0 divergências |
| 4. Entre camadas | Python, SQL, JSON e DAX dão o mesmo número? | `validar_dados.py` × `classificacao_rodada`; JSON do site × CSVs; `Gols` × `Gols (conferência pelos eventos)` |
| 5. Regressão | Uma mudança quebrou o que funcionava? | 129 testes Python, 23 SQL, CI a cada push |

Uma afirmação sobre os dados só é "validada" se disser em que nível. "Conferido com o
adaoduque" não é o mesmo que "conferido com a CBF".

## 6.2 Categorias de evidência (padrão da auditoria)

| Categoria | Quem | Reproduzível? |
|---|---|---|
| A. Teste local | Agente, via scripts e testes | Sim, por comando |
| B. Consulta documental do agente | Leitura única de página pública, sem armazenar | Não; repete-se pela URL |
| C. Verificação externa | Revisor humano | Não |

Registre cada evidência com a categoria, a data e a URL ou o comando.

## 6.3 Inventário de testes

| Arquivo | Escopo |
|---|---|
| `tests/test_baixar_fontes.py` | Aquisição sem rede: hashes, procedência, falhas por fonte, `--verificar` somente leitura |
| `tests/test_conversor.py` | Leitura do Football.TXT: herança de horário, jogos adiados, linhas inválidas |
| `tests/test_integridade.py` | CSV real aprovado e 12 tipos de erro injetado detectados |
| `tests/test_classificacao.py` | Pontuação, desempate e regressão contra a tabela da CBF (`OFICIAL_CBF`) |
| `tests/test_auditoria_local.py` | Comparação jogo a jogo com o adaoduque (pula sem `data/external/`) |
| `tests/test_relatorio.py` | Regravação do relatório só quando o conteúdo muda |
| `tests/test_jogadores.py` | Gols × placares, artilharia × Wikipédia, divergências do intervalo documentadas |
| `tests/test_web.py` | JSON do site × CSVs e tabela oficial |
| `tests/test_jogo_tecnico.py` + `jogo_tecnico.mjs` | Motor da Prancheta 2024 (Node) |
| `sql/05_testes.sql` | 23 testes: contagens, integridade, constraints, não duplicação, CBF, artilharia, idempotência da carga |

## 6.4 Como reconciliar

1. **Defina a chave** de ligação e prove que ela é única nas duas fontes (ex.: mandante ×
   visitante, único no turno e returno).
2. **Compare campo a campo**, não só totais: totais iguais podem esconder erros que se
   compensam.
3. **Classifique cada divergência** (`engenharia_e_qualidade.md` §1.4) e documente a
   tolerância quando houver (ex.: 10 minutos entre horário programado e efetivo).
4. **Confira os totais dos dois lados** (ex.: a Wikipédia tinha 928 gols pró contra 929
   sofridos, uma inconsistência interna que denunciou o erro do Juventude).
5. **Registre** no relatório gerado (se for automático) ou na auditoria escrita (se for
   manual), com versão das fontes e data.
6. **Transforme em teste** sempre que a fonte puder ficar no repositório; se não puder (ex.:
   CBF), registre como evidência B.

## 6.5 Que teste criar

| Mudança | Teste |
|---|---|
| Regra de conversão ou preparo | Caso sintético em `tests/` + erro injetado que precisa ser detectado |
| Coluna ou tabela nova no `core` | Contagem e constraint em `sql/05_testes.sql`, com inserção inválida dentro de transação desfeita |
| View ou indicador novo | Valor esperado ou reconciliação com outro grão em `sql/05_testes.sql` |
| Dado novo no site | `tests/test_web.py` comparando o JSON com a origem |
| Divergência aceita | Teste que falha se aparecer **outra** divergência |
| Regra do jogo | Teste com sorteio controlado (semente fixa) |

Um teste nunca é desligado, pulado ou afrouxado para "passar". Se um teste falhar, investigue e
reporte.

## 6.6 Rodar

```powershell
py -3.14 -I -X utf8 -m unittest discover -s tests -v
py -3.14 -I scripts/baixar_fontes.py --verificar
py -3.14 -I -X utf8 scripts/validar_dados.py            # regrava o relatório só se o conteúdo mudar
& $psql -v ON_ERROR_STOP=1 -U bi_brasileirao -d brasileirao2024 -f sql/05_testes.sql
```

Ao reportar, mostre a saída real: quantos passaram, quantos foram pulados e por quê.

## 6.7 Documentar a metodologia

| O quê | Onde |
|---|---|
| Fonte, versão, licença, decisões de interpretação | `docs/fontes_de_dados.md` |
| Regras de pontuação e desempate | `docs/regras_de_classificacao.md` |
| Modelo, grãos, carga | `docs/modelagem/modelo_dados.md` |
| Resultados de validação automática | `docs/qualidade/relatorio_validacao_fase2.md` (gerado; não editar à mão) |
| Evidências manuais, investigações e pendências | `docs/qualidade/auditoria_*.md` (escritos à mão) |
| Limitações para o leitor do portfólio | `README.md`, seção "Limitações conhecidas" |

Escreva o que foi feito, com que dados, qual o resultado e o que **não** foi verificado.
