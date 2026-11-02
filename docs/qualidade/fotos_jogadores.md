# Fotos dos jogadores e escudos: relatório da busca

Gerado por `scripts/buscar_fotos.py` em 2026-11-02. Não edite à mão: rode o script de novo.

A foto só entra quando a Wikidata ou a ficha da Wikipédia em inglês confirma a pessoa (mesmo
nome e o clube em 2024) e o arquivo tem licença livre com autor. As regras completas estão
no início do script.

## Cobertura

| Item | Quantidade |
|---|---|
| Escudos com imagem | 20 de 20 |
| Jogadores (jogador × clube) | 587 |
| Com foto | 333 |
| Sem imagem livre | 193 |
| Licença recusada | 0 |
| Ambíguo | 0 |
| Sem correspondência | 61 |
| Curado sem vínculo | 0 |
| Curado sem item | 0 |

Das 333 fotos, 45 vêm de páginas curadas e 288 da correspondência pelo nome. A Wikidata confirmou 85; a ficha da Wikipédia em inglês confirmou 248 que a Wikidata não registrava no clube.

## Destaques sem foto

Jogadores de `data/reference/jogadores_destaque.csv` (artilharia, assistências, goleiros,
seleção e prêmios) que ficaram sem foto, e o motivo.

| Jogador | Clube | Motivo |
|---|---|---|
| Agustín Rossi | FLA | sem imagem livre |
| Alexandro Bernabei | INT | sem imagem livre |
| Alisson Santana | ATM | sem imagem livre |
| Cauly | BAH | sem imagem livre |
| Everaldo | BAH | sem imagem livre |
| Kaio Jorge | CRU | sem imagem livre |
| Lucas Arcanjo | VIT | sem imagem livre |
| Marcos Felipe | BAH | sem imagem livre |
| Mateus Carvalho | VAS | sem imagem livre |
| Rafael | SPA | sem imagem livre |
| Wesley França | FLA | sem imagem livre |

## Casos ambíguos (ficaram sem foto)

Nenhum.

## Como incluir um jogador que ficou de fora

1. Ache a página dele na Wikipédia e confira que é a mesma pessoa (clube em 2024).
2. Preencha a coluna `wiki` em `data/reference/jogadores_destaque.csv`
   (`pt:Título` ou `en:Título`; título com vírgula vai entre aspas).
3. Rode `preparar_jogadores.py`, este script, a carga do banco e a exportação.
   Se nem a Wikidata nem a ficha da página em inglês mostrarem o clube em 2024, a foto
   continua de fora.
