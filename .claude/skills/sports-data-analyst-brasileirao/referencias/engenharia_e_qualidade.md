# 1. Engenharia e qualidade de dados

Documentos do projeto: `docs/fontes_de_dados.md`, `docs/qualidade/`, `LICENCAS.md` e os
cabeçalhos dos scripts em `scripts/`.

## 1.1 Ciclo de vida do dado no projeto

| Pasta | O que guarda | Pode editar à mão? | No Git? |
|---|---|---|---|
| `data/raw/<fonte>/` | Arquivo bruto em versão fixada + `PROCEDENCIA.json` (URL, versão, SHA-256, bytes, `adquirido_em_utc`) | **Nunca** (bytes exatos; `.gitattributes` marca `-text`) | Sim, se a licença permitir |
| `data/external/<fonte>/` | Fontes sem licença de redistribuição (adaoduque) e o mapa de nomes local | **Nunca** | **Não** (`.gitignore`) |
| `data/reference/` | Cadastros elaborados no projeto (clubes, cores, estádios, nomes populares) e transcrições da Wikipédia | Sim, com registro do motivo e da fonte | Sim |
| `data/processed/` | Saída dos scripts (partidas, gols, cartões, jogadores, complemento) | **Não**: gere de novo pelo script | Sim |
| `web/data/`, `powerbi/dados/` | Exportações do banco | **Não**: exporte de novo | Sim |

Regra de ouro: se um número precisa mudar, muda a **regra** (script, cadastro de referência ou
SQL), e o arquivo derivado é gerado de novo. Assim a mudança fica no histórico do Git e pode
ser reproduzida.

## 1.2 Coleta

Antes de propor qualquer fonte nova, responda por escrito (e peça aprovação):

1. **Licença e termos.** Permite reutilizar e redistribuir? Se não declara licença, o projeto
   segue o padrão do adaoduque: uso local, só fatos derivados conferidos, crédito à fonte.
   Coleta automatizada em site sem autorização (ex.: CBF) está fora.
2. **Versão imutável.** Commit Git, `oldid` da Wikipédia ou arquivo com data. "Última versão"
   não serve, porque o número muda sem aviso.
3. **Hash.** O SHA-256 esperado entra em `scripts/baixar_fontes.py`. Fonte sem hash é recusada.
4. **Papel.** Fonte de **produto** (alimenta o modelo) ou de **auditoria** (só confere)?
5. **Cobertura.** O que ela tem e o que não tem para 2024 (ex.: a Wikipédia lista só o top 11
   de assistências).
6. **Ligação.** Qual chave liga a fonte ao projeto (ex.: o par mandante × visitante, único no
   turno e returno) e qual é o mapa de nomes.

## 1.3 Padronização

| Item | Padrão do projeto | Onde está |
|---|---|---|
| Clube | Sigla de 3 letras maiúsculas (`^[A-Z]{3}$`); nome de cada fonte mapeado | `data/reference/clubes.csv` (`nome_openfootball`); mapa do adaoduque em `data/external/` |
| Jogador | `id_jogador` = nome sem acento em minúsculas, com hífens, + sigla do clube (`gabriel-teixeira-bah`); `nome_fonte` (súmula) separado de `nome_exibicao` (nome popular) | `scripts/preparar_jogadores.py`, `data/reference/jogadores_destaque.csv` |
| Datas e horas | ISO 8601 (`2024-04-13`), `HH:MM`; o fuso não é informado pela fonte | `data/processed/partidas.csv` |
| Domínios | `Normal`/`Pênalti`/`Contra`; `Amarelo`/`Vermelho`; `1T`/`2T`; `Casa`/`Fora`; resultado `M`/`E`/`V` na partida e `V`/`E`/`D` no clube | `CHECK`s em `sql/02_tabelas.sql` |
| Minuto | 1 a 90 + `acrescimo` separado (acréscimo só aos 45 e aos 90) | `core.gol`, `core.cartao` |
| Arquivos | UTF-8, LF, vírgula como separador, ponto como decimal, cabeçalho na 1ª linha, booleano `0`/`1` no CSV | `.gitattributes`, `sql/03_carga.sql` |

Ao padronizar, **preserve o valor original** numa coluna própria quando ele tiver valor de
rastreio (ex.: `nome_fonte` ao lado de `nome_exibicao`; `linha_origem` em cada partida).

Ponto em aberto: estádios **não** estão padronizados (grafias diferentes entre
`clubes_visual.csv` e `partidas_complemento.csv`). Não crie um mapa sem aprovação.

## 1.4 Inconsistências: protocolo

1. **Detectar** por teste automatizado, nunca só "no olho".
2. **Quantificar**: quantos registros, quais chaves, qual diferença.
3. **Buscar evidência** em pelo menos uma fonte independente.
4. **Classificar** a causa:

   | Classe | Exemplo real do projeto | Tratamento adotado |
   |---|---|---|
   | Erro da fonte secundária | Wikipédia: Juventude com 47 gols pró; CBF e openfootball dizem 48 | Mantém a fonte principal; registra a divergência no relatório |
   | Erro da fonte secundária | adaoduque: Athletico × Internacional às 18:06; openfootball e CBF dizem 16:00 | Valor divergente citado no relatório e não usado no produto |
   | Erro provável da fonte principal | Placar do intervalo das partidas 201 e 203 igual ao final | Mantido fiel à fonte; documentado; teste falha se surgir outro caso |
   | Diferença de definição | Horário programado (openfootball) × horário efetivo (adaoduque), até 10 min | Tolerância documentada (`TOLERANCIA_MIN = 10`) |
   | Erro do projeto | Bug de conversão ou de SQL | Corrige a regra e cria teste de regressão |

5. **Decidir com o Thiago** quando o tratamento mexer em dado de fonte ou em número publicado.
6. **Proteger** com um teste que falhe se a situação mudar (ex.:
   `test_placar_do_intervalo_diverge_so_nos_casos_documentados`).
7. **Registrar** na auditoria correspondente (`docs/qualidade/`).

Como reportar uma inconsistência ao Thiago:

```
Inconsistência: <o que diverge, em uma frase>
Onde: <arquivo/view/linha/chave>
Evidência: [FATO] fonte A diz X (versão); [FATO] fonte B diz Y (versão)
Causa provável: [HIPÓTESE] ... (como confirmar)
Impacto: <números, páginas, testes ou conclusões afetados; "nenhum indicador usa" também é impacto>
Opções: 1) manter fiel à fonte e documentar  2) corrigir por regra  3) excluir da análise
Recomendação: <qual e por quê>
```

## 1.5 Duplicidades

| Tipo | Como o projeto evita | Onde |
|---|---|---|
| Mesmo jogo duas vezes | `UNIQUE (id_mandante, id_visitante)`; `UNIQUE (rodada, id_mandante)` e `(rodada, id_visitante)` | `core.partida` |
| Clube mandante e visitante na mesma rodada | Validação na carga e teste SQL (não cabe numa constraint simples) | `sql/03_carga.sql`, `sql/05_testes.sql` |
| Mesmo jogador duas vezes | `UNIQUE (nome_fonte, id_clube)` e `(nome_exibicao, id_clube)` | `core.jogador` |
| Homônimos | Grão `jogador × clube` separa "Igor Jesus" (FLA) de "Ígor Jesus" (BOT) | auditoria de jogadores |
| Transferido no meio do ano | Uma linha por clube; somar por pessoa exige uma decisão (não há id de pessoa) | `core.jogador` |
| Linha da Wikipédia sem par | A carga falha se um nome não corresponder a exatamente um jogador | `sql/03_carga.sql` |
| **Duplicação de métrica por grão** | Cada métrica só no seu grão (929 gols, não 1.858) | `sql/04_views.sql`, `powerbi/medidas.dax` |

Antes de qualquer `JOIN`, pergunte: "esta junção pode multiplicar linhas?". Se sim, agregue
antes de juntar, ou junte por uma chave que seja única do outro lado.

## 1.6 Dados ausentes

Classifique o ausente antes de tratar:

| Tipo de ausência | Exemplo | Tratamento do projeto |
|---|---|---|
| Estrutural (o valor não existe) | Placar do intervalo em jogo 0-0 (26 jogos) | Vazio, fiel à fonte; o intervalo é 0-0 por definição, mas não é gravado |
| Coberta por regra documentada da fonte | Horário omitido na linha do Football.TXT (150 jogos) | Herdado da linha anterior; `hora_explicita = 0` marca o caso |
| Fora da cobertura da fonte | Assistências fora do top 11 da Wikipédia | `NULL`, exibido em branco; **nunca zero** |
| Sem fonte | Posição de 29 jogadores | `NULL` no `core`; "Não informada" na dimensão, como rótulo |
| Inexistente para 2024 | Posse de bola, finalizações, minutos jogados | Fora do escopo (`docs/visao_produto.md`) |

Regras:
- **Zero é um valor, `NULL` é desconhecido.** `COALESCE(x, 0)` só quando a ausência
  significa "não aconteceu" e isso é garantido pela fonte (ex.: um jogador sem nenhuma linha
  em `core.gol` tem 0 gols, porque a fonte lista todos os gols).
- Se a regra de preenchimento vier de convenção da fonte, guarde uma coluna que marque o
  valor herdado.
- Conte as ausências num teste ou relatório para que um aumento inesperado apareça.
- Preenchimento por estimativa é **[ESTIMATIVA]**, só com aprovação, e nunca fica no `core`.

## 1.7 Checklist ao alterar um script de dados

- [ ] O bruto continua intocado e o hash continua batendo (`baixar_fontes.py --verificar`).
- [ ] O script falha com mensagem clara diante de uma linha inesperada (não ignora em silêncio).
- [ ] Executar duas vezes gera o mesmo arquivo, byte a byte.
- [ ] Os números de controle (SKILL.md, seção 3) continuam iguais, ou a mudança está explicada.
- [ ] Teste novo cobre a regra nova, com caso positivo e erro injetado.
- [ ] `docs/fontes_de_dados.md` ou a auditoria correspondente registra a regra.
