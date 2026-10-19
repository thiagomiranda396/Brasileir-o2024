"""Converte o arquivo Football.TXT do openfootball em CSV de partidas.

Entrada : data/raw/openfootball/2024_br1.txt
Mapeamento: data/reference/clubes.csv (nome_openfootball -> id_clube)
Saída   : data/processed/partidas.csv

Regras de interpretação do formato (verificadas no arquivo de 2024):
- "▪ Matchday N" abre a rodada N. Jogos adiados aparecem sob a rodada
  original, em blocos posteriores com a data real em que foram disputados.
- Linha de data: "Sat Apr 13 2024" ou "Sun Apr 14" (sem ano herda o anterior).
  O dia da semana informado é conferido com a data calculada.
- Linha de jogo: "[HH:MM]  Mandante  v  Visitante  G-G [(G-G)]".
  Jogo sem horário herda o horário da linha anterior na mesma data. Essa é a
  semântica do formato aplicada pelo próprio parser do openfootball (ver a
  exportação oficial football.json, documentada em docs/fontes_de_dados.md).
  A coluna hora_explicita distingue horário escrito na linha (1) de herdado (0).
  O placar entre parênteses é o do intervalo; 0-0 vem sem ele.

Qualquer linha não reconhecida interrompe a conversão com erro.
"""

import csv
import re
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "data/raw/openfootball/2024_br1.txt"
CLUBES = RAIZ / "data/reference/clubes.csv"
SAIDA = RAIZ / "data/processed/partidas.csv"

MESES = {m: i for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), start=1)}
DIAS = "Mon Tue Wed Thu Fri Sat Sun".split()

RE_TITULO = re.compile(r"^= .+$")
RE_COMENTARIO = re.compile(r"^#")
RE_RODADA = re.compile(r"^▪ Matchday (\d+)$")
RE_DATA = re.compile(r"^\s+(Mon|Tue|Wed|Thu|Fri|Sat|Sun) ([A-Z][a-z]{2}) (\d{1,2})(?: (\d{4}))?$")
RE_JOGO = re.compile(
    r"^\s+(?:(\d{2}:\d{2})\s+)?(\S.*?)\s+v\s+(\S.*?)\s+(\d+)-(\d+)(?:\s+\((\d+)-(\d+)\))?$")

COLUNAS = ["id_partida", "rodada", "data", "hora", "hora_explicita", "id_mandante", "id_visitante",
           "gols_mandante", "gols_visitante", "gols_mandante_1t", "gols_visitante_1t",
           "linha_origem"]


def carregar_mapa_clubes() -> dict:
    with CLUBES.open(encoding="utf-8", newline="") as f:
        return {r["nome_openfootball"]: r["id_clube"] for r in csv.DictReader(f)}


def converter() -> list[dict]:
    linhas = ENTRADA.read_text(encoding="utf-8").splitlines()
    return converter_linhas(linhas, carregar_mapa_clubes())


def converter_linhas(linhas: list[str], mapa: dict) -> list[dict]:
    """Interpreta as linhas do Football.TXT; mapa: nome na fonte -> id_clube.

    Um jogo sem horário logo após uma linha de data (nada a herdar) fica com
    hora vazia e hora_explicita = 0: nenhum horário é presumido.
    """
    partidas = []
    rodada = data_atual = hora_atual = None
    ano = None

    for num, linha in enumerate(linhas, start=1):
        if not linha.strip() or RE_TITULO.match(linha) or RE_COMENTARIO.match(linha):
            continue

        if m := RE_RODADA.match(linha):
            rodada = int(m.group(1))
            continue

        if m := RE_DATA.match(linha):
            dia_semana, mes, dia, ano_txt = m.groups()
            if ano_txt:
                ano = int(ano_txt)
            if ano is None:
                raise ValueError(f"linha {num}: data sem ano e sem ano anterior")
            data_atual = date(ano, MESES[mes], int(dia))
            if DIAS[data_atual.weekday()] != dia_semana:
                raise ValueError(f"linha {num}: {dia_semana} não confere com {data_atual}")
            hora_atual = None
            continue

        if m := RE_JOGO.match(linha):
            hora, mandante, visitante, gm, gv, gm1, gv1 = m.groups()
            if rodada is None or data_atual is None:
                raise ValueError(f"linha {num}: jogo antes de rodada/data")
            for nome in (mandante, visitante):
                if nome not in mapa:
                    raise ValueError(f"linha {num}: clube sem mapeamento: {nome!r}")
            if hora:
                hora_atual = hora
            partidas.append({
                "id_partida": len(partidas) + 1,
                "rodada": rodada,
                "data": data_atual.isoformat(),
                "hora": hora_atual or "",
                "hora_explicita": 1 if hora else 0,
                "id_mandante": mapa[mandante],
                "id_visitante": mapa[visitante],
                "gols_mandante": int(gm),
                "gols_visitante": int(gv),
                "gols_mandante_1t": "" if gm1 is None else int(gm1),
                "gols_visitante_1t": "" if gv1 is None else int(gv1),
                "linha_origem": num,
            })
            continue

        raise ValueError(f"linha {num}: formato não reconhecido: {linha!r}")

    return partidas


def main() -> int:
    partidas = converter()
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with SAIDA.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(partidas)
    print(f"{len(partidas)} partidas gravadas em {SAIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
