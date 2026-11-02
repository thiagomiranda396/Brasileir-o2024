"""Exporta o schema analytics do PostgreSQL para o JSON consumido pelo site (web/).

O site é estático: lê um único arquivo, web/data/brasileirao2024.json. Este script o gera a
partir das views do banco, de modo que o Power BI e o site leem os mesmos números.

Usa o psql (não há dependência Python além da biblioteca padrão). A conexão segue as
variáveis padrão do PostgreSQL (PGHOST, PGPORT, PGUSER, PGDATABASE; senha em PGPASSWORD ou
no pgpass). Padrão: usuário bi_brasileirao_leitura, banco brasileirao2024.

Uso (a partir da raiz do projeto, com o banco carregado):
    python -I scripts/exportar_web.py
    python -I scripts/exportar_web.py --psql "C:\\Program Files\\PostgreSQL\\18\\bin\\psql.exe"
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "web/data/brasileirao2024.json"

# Uma consulta por bloco do JSON. Cada uma devolve um único valor json.
CONSULTAS = {
    "clubes": """
        SELECT json_agg(json_build_object(
            'id', id_clube, 'nome', nome, 'nome_completo', nome_completo, 'uf', uf,
            'cidade', cidade, 'estadio', estadio, 'capacidade', capacidade,
            'cor1', cor_primaria, 'cor2', cor_secundaria, 'escudo', escudo_url) ORDER BY nome)
        FROM analytics.dim_clube""",
    "partidas": """
        SELECT json_agg(json_build_object(
            'id', id_partida, 'r', rodada, 'data', data_partida,
            'hora', to_char(hora_inicio, 'HH24:MI'),
            'm', id_mandante, 'v', id_visitante, 'gm', gols_mandante, 'gv', gols_visitante,
            'gm1', gols_mandante_1t, 'gv1', gols_visitante_1t, 'estadio', estadio,
            'tm', tecnico_mandante, 'tv', tecnico_visitante,
            'fm', formacao_mandante, 'fv', formacao_visitante) ORDER BY id_partida)
        FROM analytics.fato_partida""",
    # Por rodada, os clubes na ordem de exibição: [clube, pos, J, Pts, V, E, D, GP, GC].
    "classificacao": """
        SELECT json_agg(tabela ORDER BY rodada)
        FROM (SELECT rodada, json_agg(json_build_array(
                         id_clube, posicao, jogos, pontos, vitorias, empates, derrotas,
                         gols_pro, gols_contra) ORDER BY ordem_exibicao) AS tabela
              FROM analytics.classificacao_rodada GROUP BY rodada) t""",
    "destinos": """
        SELECT json_object_agg(id_clube, destino) FROM analytics.classificacao_final""",
    "gols": """
        SELECT json_agg(json_build_array(
            id_partida, id_jogador, id_clube_jogador, id_clube_beneficiado, minuto, acrescimo,
            tipo) ORDER BY id_gol)
        FROM analytics.fato_gol""",
    "cartoes": """
        SELECT json_agg(json_build_array(
            id_partida, id_jogador, id_clube, left(cartao, 1), minuto, acrescimo)
            ORDER BY id_cartao)
        FROM analytics.fato_cartao""",
    "jogadores": """
        SELECT json_agg(json_build_object(
            'id', e.id_jogador, 'nome', e.nome_exibicao, 'clube', e.id_clube,
            'pos', e.posicao, 'foto', d.foto_url, 'nome_fonte', d.nome_fonte,
            'gols', e.gols, 'pen', e.gols_penalti, 'contra', e.gols_contra,
            'ca', e.cartoes_amarelos, 'cv', e.cartoes_vermelhos,
            'ast', e.assistencias, 'jsg', e.jogos_sem_sofrer_gols,
            'selecao', e.selecao_do_campeonato) ORDER BY e.id_jogador)
        FROM analytics.jogador_estatisticas e
        JOIN analytics.dim_jogador d USING (id_jogador)""",
    "selecao": """
        SELECT json_agg(json_build_object('jogador', id_jogador, 'setor', setor)
                        ORDER BY array_position(
                            ARRAY['Goleiro','Defensor','Meio-campista','Atacante']::varchar[],
                            setor), id_jogador)
        FROM analytics.selecao_campeonato""",
    "premios": """
        SELECT json_agg(json_build_object('mes', mes, 'premio', premio, 'jogador', id_jogador)
                        ORDER BY mes, premio)
        FROM analytics.premio_mensal""",
    # Crédito de cada imagem exibida (escudos e fotos), para a página de créditos.
    "creditos": """
        SELECT coalesce(json_agg(json_build_object(
            'tipo', tipo, 'id', coalesce(id_jogador, id_clube), 'nome', nome, 'arquivo', arquivo,
            'pagina', pagina_arquivo, 'autor', autor, 'licenca', licenca, 'licenca_url', licenca_url)
            ORDER BY tipo, nome, id_jogador), '[]'::json)
        FROM analytics.credito_imagem""",
}

def consultar(psql: str, sql: str) -> object:
    ambiente = dict(os.environ)
    ambiente.setdefault("PGUSER", "bi_brasileirao_leitura")
    ambiente.setdefault("PGDATABASE", "brasileirao2024")
    ambiente["PGCLIENTENCODING"] = "UTF8"
    saida = subprocess.run([psql, "-X", "-q", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-c", sql],
                           capture_output=True, check=True, env=ambiente)
    return json.loads(saida.stdout.decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--psql", default="psql", help="caminho do executável psql")
    args = parser.parse_args(argv)

    try:
        dados = {chave: consultar(args.psql, sql) for chave, sql in CONSULTAS.items()}
    except FileNotFoundError:
        print(f"[ERRO] psql não encontrado: {args.psql} (use --psql com o caminho completo)")
        return 1
    except subprocess.CalledProcessError as erro:
        print("[ERRO] consulta falhou:\n" + erro.stderr.decode("utf-8", "replace"))
        return 1

    dados = {
        "meta": {
            "titulo": "Brasileirão Série A 2024",
            "aviso_classificacao": "Classificação por rodada reconstruída a partir dos "
                                   "resultados (rodada nominal); só a final foi conferida "
                                   "com a tabela oficial da CBF.",
            "fontes": [
                {"nome": "openfootball/south-america", "uso": "partidas", "licenca": "CC0 1.0",
                 "url": "https://github.com/openfootball/south-america"},
                {"nome": "adaoduque/Brasileirao_Dataset",
                 "uso": "gols, cartões, técnicos e estádios por partida (dados derivados)",
                 "licenca": "não declarada; arquivo bruto não redistribuído",
                 "url": "https://github.com/adaoduque/Brasileirao_Dataset"},
                {"nome": "Wikipédia (en), 2024 Campeonato Brasileiro Série A",
                 "uso": "assistências, jogos sem sofrer gols, seleção e prêmios mensais",
                 "licenca": "CC BY-SA 4.0",
                 "url": "https://en.wikipedia.org/wiki/2024_Campeonato_Brasileiro_S%C3%A9rie_A"},
                {"nome": "Wikidata", "uso": "confirmação de quem é cada jogador nas fotos",
                 "licenca": "CC0 1.0", "url": "https://www.wikidata.org/"},
                {"nome": "Wikimedia Commons", "uso": "escudos e fotos (carregados da Wikimedia)",
                 "licenca": "a de cada arquivo, na página de créditos",
                 "url": "https://commons.wikimedia.org/"},
            ],
        },
        **dados,
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    SAIDA.write_text(texto + "\n", encoding="utf-8", newline="\n")
    print(f"[OK] {SAIDA.relative_to(RAIZ)}: {len(texto) // 1024} KB; "
          f"{len(dados['partidas'])} partidas, {len(dados['gols'])} gols, "
          f"{len(dados['jogadores'])} jogadores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
