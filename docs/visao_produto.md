# Visão de produto

**Status: visão aprovada; nada desta página está implementado além do que a coluna "Situação"
indica.** Este documento registra os objetivos de produto e as condições para implementá-los. O
detalhamento técnico de cada fase fica nos documentos da própria fase (ex.:
[modelagem/proposta_fase3.md](modelagem/proposta_fase3.md)).

O projeto evolui para dois produtos complementares, construídos sobre a mesma base de dados
validada (partidas e classificação da Série A 2024).

Legenda da coluna **Situação**:
- **Existente:** implementado e testado neste repositório.
- **Planejado:** previsto, com dados já disponíveis e validados no projeto.
- **Depende de fonte:** exige antes uma fonte de dados com procedência, cobertura e licença
  adequadas. Nenhuma fonte foi avaliada para esses itens.

## A. Dashboard gerencial (Power BI)

| Recurso | Situação | Observação |
|---|---|---|
| Base de partidas e classificação final validada | **Existente** | `data/processed/partidas.csv`; classificação conferida com a tabela oficial da CBF |
| Visão executiva e indicadores do campeonato | Planejado | Fases 4 e 5; métricas definidas por grão (ver proposta da Fase 3, seção 3) |
| Classificação e desempenho dos clubes | Planejado | Fases 3 a 5 |
| Mandantes × visitantes | Planejado | `analytics.fato_participacao` (proposta) |
| Gols marcados e sofridos | Planejado | Idem |
| Evolução por rodada | Planejado | Rodada nominal; reconstrução analítica, não a classificação oficial publicada em cada data |
| Escudos dos clubes | Depende de fonte | Escudos são marcas dos clubes; é preciso verificar direitos de uso e de publicação no repositório |
| Fotos e estatísticas individuais de jogadores | Depende de fonte | Ver seção C |

## B. Aplicação web interativa

| Recurso | Situação | Observação |
|---|---|---|
| Exploração de clubes e partidas | Planejado | Mesma base validada; tecnologia ainda não escolhida |
| **Cards de jogadores com foto e estatísticas** (prioridade visual inicial) | Depende de fonte | Ver seção C |
| Escudos dos clubes | Depende de fonte | Mesma condição do dashboard |
| Quiz sobre o campeonato | Depende de fonte (parcial) | Perguntas sobre clubes e partidas podem usar os dados já validados; perguntas sobre jogadores dependem da seção C. Só serão usados fatos validados |
| Minijogos interativos | Futuro, sem escopo definido | A definir depois do quiz |

A aplicação web **não foi iniciada**: não há stack escolhida, código, hospedagem nem dependências
instaladas.

## C. Condições antes de implementar recursos dependentes de fonte

Nenhum dos itens abaixo foi avaliado. Antes de implementar fotos, estatísticas de jogadores,
escudos, quiz com jogadores ou minijogos, é preciso:

1. **Fontes de dados de jogadores:** procedência, cobertura da temporada 2024 (elencos,
   participações, gols, cartões, minutos), identificadores que permitam cruzar jogador × partida
   com a base atual, e forma de aquisição reproduzível e autorizada (sem scraping de serviços que
   o proíbam).
2. **Licenças e direitos:**
   - dados: permissão de uso e de redistribuição no GitHub, e atribuição exigida;
   - **fotos de jogadores:** direito de imagem dos atletas e direito autoral do fotógrafo ou da
     agência, além da licença;
   - **escudos:** marcas registradas; definir se podem ser publicados no repositório ou apenas
     referenciados.
3. **Validação:** uma fonte independente para conferir as estatísticas individuais, nos moldes da
   auditoria da Fase 2.
4. **Requisitos técnicos:**
   - novo grão de dados (jogador; jogador × partida) e sua integração ao modelo do PostgreSQL;
   - armazenamento e otimização de imagens;
   - stack da aplicação web, hospedagem e custos;
   - acessibilidade e uso em celular.

Se não houver fonte adequada para algum item, ele fica fora do produto, e a limitação é
documentada. Não serão usados dados ou imagens sem procedência e licença verificadas.

## Ordem prevista

1. Fases 3 a 6 do plano original: PostgreSQL, indicadores SQL, Power BI, auditoria ponta a ponta.
   Elas usam apenas os dados já validados.
2. Fases 7 e 8: documentação de portfólio e preparação para publicação.
3. Avaliação de fontes de jogadores e de imagens (seção C), como uma fase de descoberta própria,
   igual à Fase 1.
4. Aplicação web e recursos visuais, conforme o resultado da avaliação.
