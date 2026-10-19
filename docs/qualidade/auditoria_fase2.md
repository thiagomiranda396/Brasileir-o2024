# Auditoria da Fase 2: dados das partidas

Situação em 2026-10-19 (evidências coletadas em 2026-10-18 e 2026-10-19). Este documento é
escrito à mão e consolida as evidências.
Os resultados dos testes automatizados ficam em
[relatorio_validacao_fase2.md](relatorio_validacao_fase2.md), gerado por `scripts/validar_dados.py`.

As evidências estão separadas em três categorias, conforme quem verificou e se a verificação
pode ser repetida automaticamente.

| Categoria | Quem executou | Reproduzível por script? |
|---|---|---|
| **A. Testes locais** | Agente, via `scripts/` | Sim |
| **B. Consulta documental do agente** | Agente: leitura única de uma página pública, sem armazenar o conteúdo | Não; repete-se manualmente pela URL |
| **C. Verificação externa** | Revisor humano independente | Não |

---

## A. Testes locais (reproduzíveis)

| Teste | Resultado | Evidência |
|---|---|---|
| Hash SHA-256 das fontes fixadas | Aprovado (3/3) | `scripts/baixar_fontes.py --verificar` |
| Integridade interna do CSV | Aprovado (14/14) | Seção 1 do relatório gerado |
| Mesmos jogos no adaoduque | 380/380 | Seção 2 do relatório gerado |
| Placar, rodada e data contra o adaoduque | 0 divergências | Seção 2 do relatório gerado |
| Horário contra o adaoduque | 210 diferenças de até 10 min; 1 acima (ATP × INT, ver seção D) | Seção 2 do relatório gerado |
| Horários herdados contra o adaoduque | 150/150 coincidem em até 10 min | Seção 2 do relatório gerado |
| Classificação contra a Wikipédia (rev. 70400733) | 19/20 iguais; Juventude diverge (GP 47 na Wikipédia) | Seção 3 do relatório gerado |
| Reprodutibilidade da conversão | CSV idêntico byte a byte numa segunda execução | Executado em 2026-10-18 |
| Testes automatizados permanentes (`tests/`) | 41/41 aprovados com a auditoria local; 33 aprovados e 8 pulados sem os arquivos de `data/external/` | `python -I -X utf8 -m unittest discover -s tests -v`, executado em 2026-10-19 |

## B. Consulta documental do agente

**B1. Classificação final oficial da CBF.** Consulta em 2026-10-18 à página
<https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-a/2024>.
Os valores da classificação estão embutidos no HTML da página. Foram comparados em memória com a
classificação calculada a partir de `data/processed/partidas.csv`:

- 20 clubes × 8 campos (Pts, J, V, E, D, GP, GC, SG) = **160 campos, 0 divergências**;
- posições 1 a 20 **iguais** às calculadas;
- Juventude na CBF: GP **48**, GC 59, SG −11. Isso confirma que a Wikipédia está errada (GP 47);
- totais da CBF: 929 gols pró = 929 gols sofridos;
- a CBF também publica cartões amarelos e vermelhos por clube e o aproveitamento. O
  aproveitamento publicado é **truncado**, não arredondado: `floor(100 × Pts / 114)`, o que vale
  para os 20 clubes. Exemplo: Athletico, 42/114 = 36,84% → publicado 36.

A página não foi armazenada nem entra no pipeline automatizado. Os termos de uso da CBF para
coleta automatizada não estão esclarecidos (ver Fase 1).

**B2. Horário de Athletico-PR × Internacional (21/04/2024).** Ver seção D.

**B3. Regulamento (REC).** Ver [../regras_de_classificacao.md](../regras_de_classificacao.md).

## C. Verificação externa (revisor independente)

Informada pelo usuário em 2026-10-18, a partir das páginas oficiais da CBF:

| Item verificado | Resultado | URL informada |
|---|---|---|
| Gols pró do Juventude | 48 | **Pendente**: o revisor não informou a URL exata. Provavelmente a página da tabela citada em B1 |
| Horário programado de Athletico-PR × Internacional, 21/04/2024 | 16h | **Pendente**: URL da página da partida não informada |

## D. Investigação: Athletico-PR × Internacional (18:06 no adaoduque)

**Fatos verificados**

1. O openfootball registra **16:00 explícito**: linha 46 do arquivo bruto, sem herança.
2. O valor 18:06 **já está no JSON de origem** do adaoduque
   (`data/brasileirao-2024.json`, commit `15f027c`, rodada 3: `"hour": "18:06"`). Não é erro de
   conversão para CSV. O repositório não informa de onde vêm esses dados.
3. A legenda do adaoduque define o campo como "Horário que ocorreu a partida". Os outros jogos do
   mesmo dia aparecem nessa fonte com no máximo 2 minutos de diferença do horário programado
   pelo openfootball; só este jogo tem diferença de horas.
4. A matéria do Correio Braziliense com o **resultado final** da partida foi publicada em
   **21/04/2024 às 18:25**
   ([link](https://www.correiobraziliense.com.br/esportes/2024/04/6842449-internacional-perde-para-o-athletico-pr-na-ligga-arena.html)).
   Um jogo iniciado às 18:06 não poderia ter terminado antes de ~19:55.
5. As prévias da imprensa indicam 16h, horário de Brasília
   ([Trivela](https://trivela.com.br/onde-assistir/athletico-pr-x-internacional-onde-assistir-palpites-e-escalacoes-campeonato-brasileiro-21-04-2024/)),
   e o revisor confirmou 16h na CBF (seção C).

**Conclusão.** O 18:06 é um valor **divergente**, atribuído à fonte secundária (adaoduque), e não é
usado no produto; a causa exata do erro não pode ser
determinada sem conhecer a fonte dele. O horário 16:00 do openfootball é o correto.
**Nenhuma alteração foi feita** em `data/processed/partidas.csv`, porque o dado da fonte principal
já está correto.

## E. Regra de herança de horários

No Football.TXT, 150 das 380 linhas de jogo não têm horário escrito. O conversor atribui a elas o
horário da linha anterior na mesma data. A regra se apoia em três evidências:

1. **Semântica do formato pelo próprio mantenedor.** A exportação oficial
   [openfootball/football.json](https://github.com/openfootball/football.json)
   (`2025/br.1.json`, commit `0d15b452ab561042631ae2f9f94ea7a5eaa0ef4a`) atribui horário às linhas
   sem horário. Exemplo: Cruzeiro × Mirassol, 29/03/2025, aparece com `"time": "18:30"`, herdado de
   São Paulo × Sport. Não há exportação JSON de 2024; a evidência vem do arquivo de 2025, que usa o
   mesmo formato e o mesmo parser.
2. **Fonte independente.** Os 150 horários herdados coincidem com o adaoduque em até 10 minutos.
3. **Rastreabilidade.** A coluna `hora_explicita` (1 = escrito na linha; 0 = herdado) permite
   excluir ou tratar à parte os horários herdados em qualquer análise.

Nenhum horário foi presumido sem evidência: a fonte não tem nenhum jogo sem horário que não possa
ser herdado (o teste "horário preenchido" foi aprovado).

## F. O que está validado e o que não está

| Item | Situação |
|---|---|
| Classificação final (Pts, J, V, E, D, GP, GC, SG, posição) | **Validada** contra a CBF (B1) e contra uma fonte independente (A) |
| Placar, rodada e data das 380 partidas | **Validados** contra uma fonte independente (A). Não comparados jogo a jogo com a CBF |
| Placar do intervalo | **Não validado** externamente; só testes de coerência interna |
| Horário das partidas | Coerente com o adaoduque. Só ATP × INT foi conferido contra a CBF (pelo revisor) |
| Critérios de desempate | Fonte do REC é uma cópia de terceiros (ver regras_de_classificacao.md) |

## Pendências

- **P1.** URLs exatas consultadas pelo revisor (seção C).
- **P2.** Versão oficial do REC hospedada pela CBF (aba "Documentos da competição → Regulamento").
  **A cópia consultada é de terceiros, não a versão oficial.**
- **P3.** **Validação jogo a jogo com a CBF: pendente.** As 380 partidas só foram comparadas com
  uma fonte independente não oficial (adaoduque). A comparação com a CBF exigiria coleta automatizada
  não autorizada ou conferência manual.
- **P4.** Validação externa do placar do intervalo. Ele não é usado no núcleo obrigatório.
- ~~P5. Testes com erros injetados num script permanente~~ → **resolvida** em 2026-10-19 (`tests/`).
