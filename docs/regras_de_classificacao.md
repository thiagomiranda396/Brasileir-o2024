# Regras de classificação: Série A 2024

## Fonte

**Regulamento Específico da Competição (REC), Campeonato Brasileiro Série A 2024**,
Diretoria de Competições da CBF, datado de "Rio de Janeiro, 29 de fevereiro de 2024". A data de
criação nos metadados do PDF é a mesma (2024-02-29 19:07 −03:00).

| Item | Situação |
|---|---|
| Cópia consultada | <https://www.srgoool.com.br/downloads.php?id_anexo=1496>, de **terceiros** |
| SHA-256 da cópia | `d40912c98dd8a05993faf8694e9a4761f9cee05162ef5acabebb78ff444cea28` |
| Cópia oficial | **Não localizada.** A página da CBF tem a aba "Documentos da competição → Regulamento", mas os links são carregados por JavaScript. O endereço antigo do armazenamento de documentos da CBF retorna 404 |
| PDF no repositório | **Não.** Os direitos sobre o documento não estão esclarecidos |

**Ressalva:** a CBF pode ter publicado versões posteriores do REC. A tabela oficial menciona uma
"REC Versão Final". O texto abaixo vem da versão de 29/02/2024 e precisa ser confirmado na versão
oficial (pendência P2 da auditoria).

## Sistema de disputa (Art. 14)

Pontos corridos, turno e returno: 19 jogos de ida e 19 de volta. É campeão o clube com mais pontos
ganhos. O mando é do clube à esquerda na tabela da Diretoria de Competições.

**Pontuação** (3 por vitória, 1 por empate, 0 por derrota): não aparece no REC; é matéria do
Regulamento Geral das Competições (RGC), que **não foi verificado**. A pontuação 3/1/0 foi
confirmada indiretamente: os pontos calculados com ela batem com a tabela oficial da CBF nos 20
clubes (auditoria, B1).

## Critérios de desempate (Art. 15)

Em caso de empate em pontos ganhos entre dois ou mais clubes ao final do campeonato:

1. Maior número de vitórias
2. Maior saldo de gols
3. Maior número de gols pró
4. Confronto direto
5. Menor número de cartões vermelhos recebidos
6. Menor número de cartões amarelos recebidos
7. Sorteio

- **§1:** para o confronto direto, considera-se o resultado dos jogos entre os clubes empatados.
  Na extração do texto do PDF, o final da frase saiu incompleto. Fontes secundárias e o REC de 2025
  falam no resultado somado dos dois jogos, o "jogo de 180 minutos"; isso precisa ser confirmado
  na versão oficial.
- **§2:** com mais de dois clubes empatados, o confronto direto não é considerado.

## Aplicação no projeto

| Critério | Dados disponíveis? | Tratamento |
|---|---|---|
| Pontos, 1 (vitórias), 2 (saldo), 3 (gols pró) | Sim, nas partidas | Implementados |
| 4 (confronto direto) | Sim, nas partidas | Implementado em `analytics.classificacao_rodada`, só para empates entre exatamente 2 clubes (§2) |
| 5 e 6 (cartões) | **Não** na fonte principal. A CBF publica os totais, mas sem licença de reutilização | Não implementados; empates que chegarem a esses critérios serão sinalizados |
| 7 (sorteio) | Não se aplica a dados | Sinalizado |

**Na classificação final de 2024, só o critério 1 foi necessário:** Vitória × Atlético-MG
(47 pts, 13 × 11 vitórias) e Atlético-GO × Cuiabá (30 pts, 7 × 6 vitórias).

**Classificações intermediárias (por rodada):** o Art. 15 trata da classificação *final*. As
classificações por rodada do projeto são uma **reconstrução analítica** pela convenção de rodada
nominal, **não** a classificação oficial publicada pela CBF em cada data. Critérios, tratamento de
jogos adiados e de confrontos diretos incompletos estão na
[proposta da Fase 3, seção 4](modelagem/proposta_fase3.md).

## Aproveitamento

O aproveitamento publicado pela CBF segue `floor(100 × pontos / (3 × jogos))`, com truncamento,
o que foi verificado nos 20 clubes (auditoria, B1). Nos indicadores do projeto, o aproveitamento é
`100 × pontos / (3 × jogos)` exibido com uma casa decimal, sem truncar: na view
`analytics.classificacao_final` (`round(..., 1)`), no site e na medida `Aproveitamento` do Power BI.
Exemplo: Athletico Paranaense, 42 pontos em 38 jogos, aparece com 36,8% (a CBF publica 36).
