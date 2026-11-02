"""Gera os dados derivados de jogadores (gols, cartões, jogadores) e o complemento das partidas.

Entradas:
- data/processed/partidas.csv e data/reference/clubes.csv (base validada do projeto);
- data/external/adaoduque/ (fora do Git; baixe com `baixar_fontes.py --auditoria`):
  partidas, gols e cartões, mais o mapa local de nomes de clubes;
- data/reference/jogadores_destaque.csv (nomes de exibição e páginas da Wikipédia).

Saídas (versionadas, só fatos derivados; o arquivo bruto nunca é copiado):
- data/processed/gols.csv            um gol por linha (929 em 2024)
- data/processed/cartoes.csv         um cartão por linha
- data/processed/jogadores.csv       um jogador por clube (grão jogador × clube)
- data/processed/partidas_complemento.csv  estádio, técnicos e formações de cada partida

Regras:
- As partidas do adaoduque são ligadas às do projeto pelo par (mandante, visitante), que é
  único no turno e returno. O script falha se alguma das 380 não for encontrada.
- Em gol contra, a fonte registra o clube beneficiado; o clube do jogador é o adversário.
- Um jogador é identificado por (nome na fonte, clube). Homônimos de clubes diferentes ficam
  separados; um atleta transferido no meio do campeonato aparece uma vez por clube.
- Os gols de cada clube em cada partida precisam bater com o placar validado; o script falha
  se houver qualquer divergência.

Uso (a partir da raiz do projeto):
    python -I scripts/preparar_jogadores.py
"""

import csv
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PARTIDAS = RAIZ / "data/processed/partidas.csv"
EXTERNO = RAIZ / "data/external/adaoduque"
ADA_PARTIDAS = EXTERNO / "campeonato-brasileiro-full.csv"
ADA_GOLS = EXTERNO / "campeonato-brasileiro-gols.csv"
ADA_CARTOES = EXTERNO / "campeonato-brasileiro-cartoes.csv"
MAPA_CLUBES = EXTERNO / "mapa_nomes_adaoduque.csv"
DESTAQUES = RAIZ / "data/reference/jogadores_destaque.csv"

SAIDA_GOLS = RAIZ / "data/processed/gols.csv"
SAIDA_CARTOES = RAIZ / "data/processed/cartoes.csv"
SAIDA_JOGADORES = RAIZ / "data/processed/jogadores.csv"
SAIDA_COMPLEMENTO = RAIZ / "data/processed/partidas_complemento.csv"

COLUNAS_GOLS = ["id_gol", "id_partida", "rodada", "id_jogador", "id_clube_jogador",
                "id_clube_beneficiado", "minuto", "acrescimo", "periodo", "tipo"]
COLUNAS_CARTOES = ["id_cartao", "id_partida", "rodada", "id_jogador", "id_clube", "cartao",
                   "minuto", "acrescimo", "periodo", "num_camisa"]
COLUNAS_JOGADORES = ["id_jogador", "nome_fonte", "nome_exibicao", "id_clube", "posicao",
                     "wiki"]
COLUNAS_COMPLEMENTO = ["id_partida", "estadio", "tecnico_mandante", "tecnico_visitante",
                       "formacao_mandante", "formacao_visitante"]

TIPOS_GOL = {"": "Normal", "Penalty": "Pênalti", "Gol Contra": "Contra"}
RE_MINUTO = re.compile(r"^(\d{1,3})(?:\+(\d{1,2}))?$")


def ler_csv(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def gravar_csv(caminho: Path, colunas: list[str], linhas: list[dict]) -> None:
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas, lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


def limpar(texto: str) -> str:
    """Remove espaços (inclusive o não separável, comum na fonte) e normaliza para NFC."""
    return unicodedata.normalize("NFC", texto.replace("\xa0", " ")).strip()


def slug(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")


def id_jogador(nome: str, id_clube: str) -> str:
    return f"{slug(nome)}-{id_clube.lower()}"


def separar_minuto(texto: str) -> tuple[int, int, str]:
    """'45+4' -> (45, 4, '1T'); '67' -> (67, 0, '2T'). Minuto 45 sem acréscimo é do 1º tempo."""
    m = RE_MINUTO.match(texto.strip())
    if not m:
        raise ValueError(f"minuto inválido: {texto!r}")
    minuto, acrescimo = int(m.group(1)), int(m.group(2) or 0)
    if not 1 <= minuto <= 90:
        raise ValueError(f"minuto fora do intervalo: {texto!r}")
    return minuto, acrescimo, "1T" if minuto <= 45 else "2T"


def ligar_partidas(partidas: list[dict], ada: list[dict], mapa: dict) -> dict[str, dict]:
    """partida_id do adaoduque (só 2024) -> partida do projeto."""
    por_confronto = {(p["id_mandante"], p["id_visitante"]): p for p in partidas}
    ligacao = {}
    for r in ada:
        if not r["data"].endswith("/2024"):
            continue
        chave = (mapa[r["mandante"]], mapa[r["visitante"]])
        ligacao[r["ID"]] = por_confronto[chave]
    if len(ligacao) != len(partidas) or len({id(p) for p in ligacao.values()}) != len(partidas):
        raise SystemExit(f"[ERRO] {len(ligacao)} partidas ligadas; esperado {len(partidas)}")
    return ligacao


def preparar() -> dict[str, list[dict]]:
    partidas = ler_csv(PARTIDAS)
    mapa = {r["nome_adaoduque"]: r["id_clube"] for r in ler_csv(MAPA_CLUBES)}
    ada_partidas = ler_csv(ADA_PARTIDAS)
    ligacao = ligar_partidas(partidas, ada_partidas, mapa)

    complemento = []
    for r in ada_partidas:
        if r["ID"] in ligacao:
            complemento.append({
                "id_partida": int(ligacao[r["ID"]]["id_partida"]),
                "estadio": limpar(r["arena"]),
                "tecnico_mandante": limpar(r["tecnico_mandante"]),
                "tecnico_visitante": limpar(r["tecnico_visitante"]),
                "formacao_mandante": limpar(r["formacao_mandante"]),
                "formacao_visitante": limpar(r["formacao_visitante"]),
            })
    complemento.sort(key=lambda c: c["id_partida"])

    jogadores: dict[str, dict] = {}
    posicoes: dict[str, Counter] = defaultdict(Counter)

    def registrar(nome: str, id_clube: str) -> str:
        jid = id_jogador(nome, id_clube)
        jogadores.setdefault(jid, {"id_jogador": jid, "nome_fonte": nome,
                                   "nome_exibicao": nome, "id_clube": id_clube,
                                   "posicao": "", "wiki": ""})
        return jid

    gols = []
    for r in ler_csv(ADA_GOLS):
        if r["partida_id"] not in ligacao:
            continue
        p = ligacao[r["partida_id"]]
        beneficiado = mapa[r["clube"]]
        tipo = TIPOS_GOL[r["tipo_de_gol"]]
        adversario = p["id_visitante"] if beneficiado == p["id_mandante"] else p["id_mandante"]
        clube_jogador = adversario if tipo == "Contra" else beneficiado
        minuto, acrescimo, periodo = separar_minuto(r["minuto"])
        gols.append({
            "id_partida": int(p["id_partida"]), "rodada": int(p["rodada"]),
            "id_jogador": registrar(limpar(r["atleta"]), clube_jogador),
            "id_clube_jogador": clube_jogador, "id_clube_beneficiado": beneficiado,
            "minuto": minuto, "acrescimo": acrescimo, "periodo": periodo, "tipo": tipo,
        })

    cartoes = []
    for r in ler_csv(ADA_CARTOES):
        if r["partida_id"] not in ligacao:
            continue
        p = ligacao[r["partida_id"]]
        clube = mapa[r["clube"]]
        minuto, acrescimo, periodo = separar_minuto(r["minuto"])
        jid = registrar(limpar(r["atleta"]), clube)
        if r["posicao"]:
            posicoes[jid][r["posicao"]] += 1
        cartoes.append({
            "id_partida": int(p["id_partida"]), "rodada": int(p["rodada"]),
            "id_jogador": jid, "id_clube": clube, "cartao": r["cartao"],
            "minuto": minuto, "acrescimo": acrescimo, "periodo": periodo,
            "num_camisa": r["num_camisa"],
        })

    for jid, contagem in posicoes.items():
        jogadores[jid]["posicao"] = contagem.most_common(1)[0][0]

    # Nomes de exibição e páginas da Wikipédia; destaques sem registro na fonte (goleiros que
    # não marcaram nem levaram cartão) entram pelo nome de exibição.
    for i, d in enumerate(ler_csv(DESTAQUES), start=2):
        if None in d:  # vírgula sem aspas: a coluna wiki seria cortada em silêncio
            sys.exit(f"{DESTAQUES.name}, linha {i}: colunas a mais (título com vírgula precisa de aspas)")
        jid = registrar(d["nome_fonte"] or d["nome_exibicao"], d["id_clube"])
        jogadores[jid].update(nome_exibicao=d["nome_exibicao"], wiki=d["wiki"],
                              posicao=d["posicao"] or jogadores[jid]["posicao"])

    validar_gols(partidas, gols)

    ordem = lambda e: (e["id_partida"], e["periodo"], e["minuto"], e["acrescimo"])  # noqa: E731
    gols.sort(key=ordem)
    cartoes.sort(key=ordem)
    for i, g in enumerate(gols, start=1):
        g["id_gol"] = i
    for i, c in enumerate(cartoes, start=1):
        c["id_cartao"] = i
    return {
        "gols": gols, "cartoes": cartoes, "complemento": complemento,
        "jogadores": sorted(jogadores.values(), key=lambda j: j["id_jogador"]),
    }


def validar_gols(partidas: list[dict], gols: list[dict]) -> None:
    """Gols por clube em cada partida = placar validado. Qualquer divergência interrompe."""
    contagem = Counter((g["id_partida"], g["id_clube_beneficiado"]) for g in gols)
    divergencias = []
    for p in partidas:
        pid = int(p["id_partida"])
        for clube, placar in ((p["id_mandante"], p["gols_mandante"]),
                              (p["id_visitante"], p["gols_visitante"])):
            if contagem[(pid, clube)] != int(placar):
                divergencias.append(f"partida {pid} {clube}: {contagem[(pid, clube)]} gols "
                                    f"na fonte, placar {placar}")
    if divergencias:
        raise SystemExit("[ERRO] gols divergentes do placar:\n  " + "\n  ".join(divergencias))


def main() -> int:
    ausentes = [str(c.relative_to(RAIZ)) for c in (ADA_PARTIDAS, ADA_GOLS, ADA_CARTOES,
                                                    MAPA_CLUBES) if not c.exists()]
    if ausentes:
        print("[ERRO] arquivos externos ausentes (rode baixar_fontes.py --auditoria): "
              + ", ".join(ausentes))
        return 1
    dados = preparar()
    gravar_csv(SAIDA_GOLS, COLUNAS_GOLS, dados["gols"])
    gravar_csv(SAIDA_CARTOES, COLUNAS_CARTOES, dados["cartoes"])
    gravar_csv(SAIDA_JOGADORES, COLUNAS_JOGADORES, dados["jogadores"])
    gravar_csv(SAIDA_COMPLEMENTO, COLUNAS_COMPLEMENTO, dados["complemento"])
    print(f"[OK] {len(dados['gols'])} gols, {len(dados['cartoes'])} cartões, "
          f"{len(dados['jogadores'])} jogadores, {len(dados['complemento'])} partidas; "
          "gols conferidos com o placar das 380 partidas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
