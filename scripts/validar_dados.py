"""Valida as partidas convertidas e as compara com fontes independentes.

1. Integridade interna de data/processed/partidas.csv (falha => código de saída 1).
2. Comparação jogo a jogo com o dataset adaoduque (data/external, apenas local).
3. Classificação recalculada versus a predefinição da Wikipédia.

Gera o relatório docs/qualidade/relatorio_validacao_fase2.md.
"""

import csv
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PARTIDAS = RAIZ / "data/processed/partidas.csv"
CLUBES = RAIZ / "data/reference/clubes.csv"
ADAODUQUE = RAIZ / "data/external/adaoduque/campeonato-brasileiro-full.csv"
# Mapa de nomes usado só pela auditoria local; fica fora do Git, junto do dataset.
MAPA_ADAODUQUE = RAIZ / "data/external/adaoduque/mapa_nomes_adaoduque.csv"
ARQUIVOS_AUDITORIA = (ADAODUQUE, MAPA_ADAODUQUE)
WIKIPEDIA = RAIZ / "data/raw/wikipedia/tabela_serie_a_2024.wikitext"
RELATORIO = RAIZ / "docs/qualidade/relatorio_validacao_fase2.md"

INICIO, FIM = date(2024, 4, 13), date(2024, 12, 8)
TOLERANCIA_MIN = 10  # diferença de horário aceita entre horário programado e efetivo


def minutos(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def ler_csv(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------
# 1. Integridade interna
# --------------------------------------------------------------------------

def testes_integridade(partidas: list[dict], clubes: set[str]) -> list[tuple[str, bool, str]]:
    r = []

    def teste(nome, ok, detalhe=""):
        r.append((nome, bool(ok), detalhe))

    teste("380 partidas", len(partidas) == 380, f"{len(partidas)} encontradas")

    ids = [p["id_partida"] for p in partidas]
    teste("id_partida único", len(ids) == len(set(ids)))

    usados = {p["id_mandante"] for p in partidas} | {p["id_visitante"] for p in partidas}
    teste("20 clubes, todos no cadastro", usados == clubes and len(usados) == 20,
          f"{len(usados)} usados; fora do cadastro: {sorted(usados - clubes) or 'nenhum'}")

    teste("mandante diferente do visitante",
          all(p["id_mandante"] != p["id_visitante"] for p in partidas))

    pares = Counter((p["id_mandante"], p["id_visitante"]) for p in partidas)
    teste("cada confronto mandante×visitante ocorre uma única vez (turno e returno)",
          len(pares) == 380 and max(pares.values()) == 1,
          f"{len(pares)} pares distintos de 380 possíveis")

    casa = Counter(p["id_mandante"] for p in partidas)
    fora = Counter(p["id_visitante"] for p in partidas)
    teste("cada clube: 19 jogos em casa e 19 fora",
          all(casa[c] == 19 and fora[c] == 19 for c in clubes))

    por_rodada = Counter(int(p["rodada"]) for p in partidas)
    teste("rodadas 1 a 38 com 10 jogos cada",
          sorted(por_rodada) == list(range(1, 39)) and set(por_rodada.values()) == {10})

    clube_rodada = Counter((int(p["rodada"]), c) for p in partidas
                           for c in (p["id_mandante"], p["id_visitante"]))
    teste("cada clube joga exatamente uma vez por rodada",
          len(clube_rodada) == 38 * 20 and max(clube_rodada.values()) == 1)

    datas = [date.fromisoformat(p["data"]) for p in partidas]
    teste("datas entre 13/04/2024 e 08/12/2024",
          all(INICIO <= d <= FIM for d in datas), f"{min(datas)} a {max(datas)}")

    teste("horário preenchido (HH:MM)",
          all(re.fullmatch(r"\d{2}:\d{2}", p["hora"]) for p in partidas))

    herdados = sum(p["hora_explicita"] == "0" for p in partidas)
    teste("hora_explicita é 0 ou 1", all(p["hora_explicita"] in ("0", "1") for p in partidas),
          f"{len(partidas) - herdados} explícitos, {herdados} herdados da linha anterior")

    gols_ok = all(p["gols_mandante"].isdigit() and p["gols_visitante"].isdigit()
                  for p in partidas)
    teste("placar final preenchido e não negativo", gols_ok)

    sem_1t = [p for p in partidas if p["gols_mandante_1t"] == ""]
    teste("placar do intervalo ausente somente em jogos 0-0",
          all(p["gols_mandante"] == "0" and p["gols_visitante"] == "0" for p in sem_1t),
          f"{len(sem_1t)} jogos sem placar do intervalo")

    com_1t = [p for p in partidas if p["gols_mandante_1t"] != ""]
    teste("gols do intervalo ≤ gols finais",
          all(int(p["gols_mandante_1t"]) <= int(p["gols_mandante"]) and
              int(p["gols_visitante_1t"]) <= int(p["gols_visitante"]) for p in com_1t))
    return r


# --------------------------------------------------------------------------
# 2. Comparação com adaoduque
# --------------------------------------------------------------------------

def auditoria_ausente() -> list[str]:
    """Arquivos da auditoria local que não existem (lista vazia = auditoria possível)."""
    return [str(p.relative_to(RAIZ)).replace("\\", "/") for p in ARQUIVOS_AUDITORIA if not p.exists()]


def carregar_mapa_adaoduque() -> dict:
    """Nome do clube no adaoduque -> id_clube (arquivo usado só pela auditoria local)."""
    return {c["nome_adaoduque"]: c["id_clube"] for c in ler_csv(MAPA_ADAODUQUE)}


def carregar_adaoduque(mapa: dict) -> tuple[dict, list[str]]:
    jogos, sem_mapa = {}, set()
    for linha in ler_csv(ADAODUQUE):
        if not linha["data"].endswith("/2024"):
            continue
        m, v = linha["mandante"], linha["visitante"]
        if m not in mapa or v not in mapa:
            sem_mapa.update(n for n in (m, v) if n not in mapa)
            continue
        dia, mes, ano = linha["data"].split("/")
        chave = (mapa[m], mapa[v])
        if chave in jogos:
            raise ValueError(f"adaoduque: confronto duplicado {chave}")
        jogos[chave] = {
            "id_origem": linha["ID"],
            "rodada": int(linha["rodata"]),
            "data": f"{ano}-{mes}-{dia}",
            "hora": linha["hora"],
            "gols_mandante": int(linha["mandante_Placar"]),
            "gols_visitante": int(linha["visitante_Placar"]),
        }
    return jogos, sorted(sem_mapa)


def comparar_adaoduque(partidas: list[dict], ada: dict) -> dict:
    nossos = {(p["id_mandante"], p["id_visitante"]): p for p in partidas}
    res = {"so_openfootball": sorted(set(nossos) - set(ada)),
           "so_adaoduque": sorted(set(ada) - set(nossos)),
           "comuns": 0, "placar": [], "rodada": [], "data": [], "hora": [],
           "herdados": {"total": 0, "ate_tolerancia": 0}}
    for chave in sorted(set(nossos) & set(ada)):
        p, a = nossos[chave], ada[chave]
        res["comuns"] += 1
        placar_p = (int(p["gols_mandante"]), int(p["gols_visitante"]))
        placar_a = (a["gols_mandante"], a["gols_visitante"])
        if placar_p != placar_a:
            res["placar"].append((chave, placar_p, placar_a))
        if int(p["rodada"]) != a["rodada"]:
            res["rodada"].append((chave, p["rodada"], a["rodada"]))
        if p["data"] != a["data"]:
            res["data"].append((chave, p["data"], a["data"]))
        if p["hora"] != a["hora"]:
            res["hora"].append((chave, p["hora"], a["hora"]))
        if p["hora_explicita"] == "0":
            res["herdados"]["total"] += 1
            if abs(minutos(p["hora"]) - minutos(a["hora"])) <= TOLERANCIA_MIN:
                res["herdados"]["ate_tolerancia"] += 1
    return res


# --------------------------------------------------------------------------
# 3. Classificação
# --------------------------------------------------------------------------

def calcular_classificacao(partidas: list[dict]) -> list[dict]:
    t = defaultdict(lambda: dict(J=0, V=0, E=0, D=0, GP=0, GC=0))
    for p in partidas:
        m, v = p["id_mandante"], p["id_visitante"]
        gm, gv = int(p["gols_mandante"]), int(p["gols_visitante"])
        for clube, gp, gc in ((m, gm, gv), (v, gv, gm)):
            s = t[clube]
            s["J"] += 1
            s["GP"] += gp
            s["GC"] += gc
            s["V" if gp > gc else "E" if gp == gc else "D"] += 1
    linhas = []
    for clube, s in t.items():
        s.update(clube=clube, Pts=3 * s["V"] + s["E"], SG=s["GP"] - s["GC"])
        linhas.append(s)

    # Critérios 1-3 do regulamento após pontos: vitórias, saldo, gols pró.
    linhas.sort(key=lambda s: (-s["Pts"], -s["V"], -s["SG"], -s["GP"]))
    for pos, s in enumerate(linhas, start=1):
        s["pos"] = pos
    return linhas


def empates_nao_resolvidos(tabela: list[dict]) -> list[list[str]]:
    """Grupos ainda empatados após pontos, vitórias, saldo e gols pró."""
    grupos = defaultdict(list)
    for s in tabela:
        grupos[(s["Pts"], s["V"], s["SG"], s["GP"])].append(s["clube"])
    return [g for g in grupos.values() if len(g) > 1]


def carregar_wikipedia() -> dict:
    texto = WIKIPEDIA.read_text(encoding="utf-8")
    ordem = dict((cod, int(n)) for n, cod in re.findall(r"\|team(\d+)=(\w+)", texto))
    valores = dict(((campo, cod), int(v)) for campo, cod, v in
                   re.findall(r"\|(win|draw|loss|gf|ga)_(\w+)=\s*(-?\d+)", texto))
    ajustes = dict(re.findall(r"\|adjust_points_(\w+)=\s*(-?\d+)", texto))
    tabela = {}
    for cod, pos in ordem.items():
        v, e, d = (valores[(c, cod)] for c in ("win", "draw", "loss"))
        gp, gc = valores[("gf", cod)], valores[("ga", cod)]
        tabela[cod] = dict(pos=pos, J=v + e + d, V=v, E=e, D=d, GP=gp, GC=gc,
                           SG=gp - gc, Pts=3 * v + e + int(ajustes.get(cod, 0)))
    return tabela


# --------------------------------------------------------------------------
# Relatório
# --------------------------------------------------------------------------

def gerar_relatorio(integ, sem_mapa, comp, tabela, empates, wiki) -> str:
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    L = ["# Relatório de validação — Fase 2", "",
         f"Gerado automaticamente por `scripts/validar_dados.py` em {agora} (UTC).",
         "Não edite à mão; execute o script novamente.", "",
         "## 1. Integridade interna (`data/processed/partidas.csv`)", "",
         "| Teste | Resultado | Detalhe |", "|---|---|---|"]
    for nome, ok, det in integ:
        L.append(f"| {nome} | {'APROVADO' if ok else 'REPROVADO'} | {det} |")

    L += ["", "## 2. Comparação jogo a jogo com adaoduque/Brasileirao_Dataset", ""]
    if comp is None:
        L += ["**NÃO EXECUTADA:** arquivos da auditoria local ausentes: "
              + ", ".join(f"`{a}`" for a in auditoria_ausente()) + ". O dataset não tem licença "
              "e, assim como o mapa de nomes, fica fora do Git (ver docs/fontes_de_dados.md)."]
    else:
        L += secao_adaoduque(sem_mapa, comp)

    L += secao_wikipedia(tabela, empates, wiki)
    return "\n".join(L) + "\n"


def secao_adaoduque(sem_mapa, comp) -> list[str]:
    L = ["Chave de comparação: (mandante, visitante), única em turno e returno.", "",
          f"- Partidas 2024 com clubes não mapeados: {sem_mapa or 'nenhuma'}",
          f"- Partidas presentes nas duas fontes: **{comp['comuns']}**",
          f"- Somente no openfootball: {len(comp['so_openfootball'])} {comp['so_openfootball'] or ''}",
          f"- Somente no adaoduque: {len(comp['so_adaoduque'])} {comp['so_adaoduque'] or ''}",
          "", "| Atributo | Divergências |", "|---|---|"]
    for campo in ("placar", "rodada", "data", "hora"):
        L.append(f"| {campo} | {len(comp[campo])} |")

    hora_pequena = [d for d in comp["hora"] if abs(minutos(d[1]) - minutos(d[2])) <= TOLERANCIA_MIN]
    hora_relevante = [d for d in comp["hora"] if d not in hora_pequena]
    h = comp["herdados"]
    L += ["", f"Horários **herdados** (sem horário escrito na linha do openfootball): {h['total']}. "
          f"Desses, {h['ate_tolerancia']} coincidem com o adaoduque em até {TOLERANCIA_MIN} minutos "
          f"e {h['total'] - h['ate_tolerancia']} divergem mais que isso."]
    L += ["", f"Divergências de hora com até {TOLERANCIA_MIN} minutos de diferença: "
          f"**{len(hora_pequena)}**. Hipótese (não documentada pelas fontes): o adaoduque "
          "registra o horário efetivo de início, poucos minutos após o horário programado "
          "registrado pelo openfootball. Essas diferenças não são tratadas como erro e não são listadas.",
          f"Divergências de hora acima de {TOLERANCIA_MIN} minutos: **{len(hora_relevante)}**."]
    comp = dict(comp, hora=hora_relevante)
    for campo in ("placar", "rodada", "data", "hora"):
        if comp[campo]:
            L += ["", f"### Divergências de {campo}", "",
                  "| Mandante × Visitante | openfootball (fonte principal) "
                  "| adaoduque (fonte secundária, valor divergente) |", "|---|---|---|"]
            for (m, v), a, b in comp[campo]:
                L.append(f"| {m} × {v} | {a} | {b} |")
            L += ["", "Os valores da coluna adaoduque são atribuídos à fonte secundária e "
                  "divergem da fonte principal; não são usados no produto. Investigação em "
                  "`docs/qualidade/auditoria_fase2.md`, seção D."]
    return L


def secao_wikipedia(tabela, empates, wiki) -> list[str]:
    L = ["", "## 3. Classificação recalculada × Wikipédia (revisão 70400733)", "",
          "Ordenação: pontos, vitórias, saldo de gols, gols pró.", "",
          "| Pos | Clube | Pts | J | V | E | D | GP | GC | SG | Wikipédia |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    divergencias_wiki = []
    for s in tabela:
        w = wiki.get(s["clube"])
        campos = ("pos", "Pts", "J", "V", "E", "D", "GP", "GC", "SG")
        difs = [f"{c}: {w[c]}" for c in campos if w and w[c] != s[c]]
        if w is None:
            difs = ["ausente"]
        if difs:
            divergencias_wiki.append((s["clube"], difs))
        L.append(f"| {s['pos']} | {s['clube']} | {s['Pts']} | {s['J']} | {s['V']} | {s['E']} | "
                 f"{s['D']} | {s['GP']} | {s['GC']} | {s['SG']} | "
                 f"{'confere' if not difs else 'DIVERGE (' + '; '.join(difs) + ')'} |")

    total_gp = sum(s["GP"] for s in tabela)
    total_gc = sum(s["GC"] for s in tabela)
    wiki_gp = sum(w["GP"] for w in wiki.values())
    wiki_gc = sum(w["GC"] for w in wiki.values())
    L += ["", "### Verificações de totais", "",
          f"- openfootball: gols pró = {total_gp}, gols sofridos = {total_gc} "
          f"→ {'consistente' if total_gp == total_gc else 'INCONSISTENTE'}",
          f"- Wikipédia: gols pró = {wiki_gp}, gols sofridos = {wiki_gc} "
          f"→ {'consistente' if wiki_gp == wiki_gc else 'INCONSISTENTE'}",
          f"- Empates não resolvidos pelos critérios 1–3: {empates or 'nenhum'}",
          f"- Clubes com divergência em relação à Wikipédia: {len(divergencias_wiki)}"]
    return L


def main() -> int:
    partidas = ler_csv(PARTIDAS)
    clubes_ref = ler_csv(CLUBES)
    ids_clubes = {c["id_clube"] for c in clubes_ref}

    integ = testes_integridade(partidas, ids_clubes)
    comp, sem_mapa = None, []
    if not auditoria_ausente():
        ada, sem_mapa = carregar_adaoduque(carregar_mapa_adaoduque())
        comp = comparar_adaoduque(partidas, ada)
    tabela = calcular_classificacao(partidas)
    empates = empates_nao_resolvidos(tabela)
    wiki = carregar_wikipedia()

    RELATORIO.parent.mkdir(parents=True, exist_ok=True)
    RELATORIO.write_text(gerar_relatorio(integ, sem_mapa, comp, tabela, empates, wiki),
                         encoding="utf-8", newline="\n")

    reprovados = [n for n, ok, _ in integ if not ok]
    print(f"Integridade: {len(integ) - len(reprovados)}/{len(integ)} aprovados")
    if comp is None:
        print("adaoduque: comparação NÃO executada; ausentes: " + ", ".join(auditoria_ausente()))
    else:
        hora_relevante = sum(abs(minutos(a) - minutos(b)) > TOLERANCIA_MIN
                             for _, a, b in comp["hora"])
        print(f"adaoduque: {comp['comuns']} em comum; divergências "
              + ", ".join(f"{c}={len(comp[c])}" for c in ("placar", "rodada", "data", "hora"))
              + f" (hora > {TOLERANCIA_MIN} min: {hora_relevante})")
    print(f"Relatório: {RELATORIO.relative_to(RAIZ)}")
    return 1 if reprovados else 0


if __name__ == "__main__":
    sys.exit(main())
