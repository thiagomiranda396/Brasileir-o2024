"""Busca, confere e registra as imagens livres do site e do Power BI: os escudos dos clubes e
as fotos dos jogadores (Wikimedia Commons).

Por que existe: antes, o navegador procurava a foto pelo nome do jogador na Wikipédia e
aceitava o primeiro resultado descrito como futebolista, o que pode trazer um homônimo. Aqui
a foto só entra quando a Wikidata (ou, na falta do vínculo lá, a ficha da Wikipédia em inglês)
confirma que a pessoa jogou naquele clube em 2024 e tem o mesmo nome; autor e licença de cada
arquivo ficam registrados.

Regras:
1. Clube: o item da Wikidata vem da página da Wikipédia em português (wiki_pt em
   data/reference/clubes_visual.csv). Escudo = imagem principal dessa página (a mesma que o
   site usava) ou, se ela faltar ou tiver a licença recusada, o logotipo (P154) do item. O
   escudo precisa ser SVG ou PNG: um JPG costuma ser uma foto (a P154 do Corinthians, por
   exemplo, é uma foto recortada), e uma foto não serve de escudo. Sem escudo livre, vale o
   escudo da página pt mesmo marcado como uso justo (decisão do Thiago em 2026-11-02), com a
   licença registrada como "Uso justo"; isso nunca vale para fotos de jogadores.
2. Candidatos de um clube: pessoas (P31 = Q5) com vínculo P54 ao clube que não terminou antes
   de 2024 nem começou depois de 2024, nascidas a partir de 1975 ou sem data de nascimento.
3. Jogador do projeto (grão jogador × clube) e candidato correspondem quando o nome na súmula
   ou o nome de exibição é igual a um rótulo, apelido, nome de nascimento (P1477) ou alcunha
   (P1449) do candidato, ignorando acentos, maiúsculas, pontuação e as partículas de/da/do.
   - Página curada (coluna wiki de jogadores.csv): vale o item da página, mas só se ele
     estiver entre os candidatos do clube.
   - Mais de um candidato: fica o que tem o vínculo com datas; se ainda sobrar mais de um, o
     jogador fica sem foto (ambíguo).
   - Um candidato que corresponde a dois jogadores do mesmo clube não é usado (os dois ficam
     sem foto), salvo quando um deles é curado: o curado fica com ele.
3b. Segunda confirmação, pela ficha da Wikipédia em inglês (Infobox football biography): a
   Wikidata não registra o clube de 2024 de muitos jogadores. Para quem ficou sem item na
   regra 3 (sem correspondência ou curado sem vínculo/sem item):
   - Curado: vale o item da página curada se ele é uma pessoa e a ficha dessa página lista o
     clube num período que inclui 2024 (sem o filtro de nascimento: a pessoa foi escolhida à
     mão). Se não se confirmar, o jogador passa pela busca por nome, como os demais.
   - Busca por nome: a busca da Wikidata traz futebolistas (P106 = Q937857) com o nome; ficam
     as pessoas nascidas a partir de 1975 com rótulo ou apelido igual ao nome (como na regra
     3) e cuja ficha em inglês lista o clube num período que inclui 2024. Período sem fim
     ("2019–") não vale se depois dele vier outro clube que não seja empréstimo. Dois itens
     confirmados para o mesmo jogador: ambíguo, sem foto.
   O clube da ficha é o destino do link, conferido pelo item da Wikidata (com redirecionamentos).
   A coluna confirmado_por registra a fonte: wikidata ou wikipedia_en.
4. Imagem: na ordem, a imagem principal da página da pessoa na Wikipédia em português, a da
   página em inglês (as páginas costumam ter a foto mais recente) e a P18 do item (Commons).
   Fica a primeira com licença aceita.
5. Licença: só CC0, domínio público, CC BY e CC BY-SA, lidas dos metadados do arquivo. CC BY e
   CC BY-SA sem autor nos metadados são recusadas. A miniatura precisa vir dos servidores da
   Wikimedia (upload.wikimedia.org ou thumb.wikimedia.org); os parâmetros utm_ são retirados.

Nada é inventado: sem correspondência confirmada, o jogador fica sem foto e o site mostra a
camisa do clube.

Saídas:
- data/reference/escudos_clubes.csv
- data/reference/fotos_jogadores.csv
- docs/qualidade/fotos_jogadores.md   relatório gerado (cobertura, ambíguos, destaques sem foto)

Precisa de internet (APIs da Wikipédia, da Wikidata e do Commons). Uso, na raiz do projeto:
    py -3.14 -I scripts/buscar_fotos.py
"""

import argparse
import csv
import html
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
JOGADORES = RAIZ / "data/processed/jogadores.csv"
DESTAQUES = RAIZ / "data/reference/jogadores_destaque.csv"
CLUBES_VISUAL = RAIZ / "data/reference/clubes_visual.csv"
SAIDA_ESCUDOS = RAIZ / "data/reference/escudos_clubes.csv"
SAIDA_FOTOS = RAIZ / "data/reference/fotos_jogadores.csv"
SAIDA_RELATORIO = RAIZ / "docs/qualidade/fotos_jogadores.md"

COLUNAS_ESCUDOS = ["id_clube", "wikidata", "arquivo", "url_imagem", "pagina_arquivo", "autor",
                   "licenca", "licenca_url", "origem_imagem", "consultado_em"]
COLUNAS_FOTOS = ["id_jogador", "wikidata", "arquivo", "url_imagem", "pagina_arquivo", "autor",
                 "licenca", "licenca_url", "origem_imagem", "criterio", "confirmado_por", "consultado_em"]

LARGURA_FOTO = 330      # tamanhos-padrão de miniatura da Wikimedia
LARGURA_ESCUDO = 250
ANO = 2024
NASCIDOS_DESDE = 1975
AGENTE = ("Brasileirao2024-portfolio/1.0 "
          "(https://github.com/thiagomiranda396/Brasileir-o2024; scripts/buscar_fotos.py)")
PARTICULAS = {"de", "da", "do", "das", "dos", "e", "d"}
# "PDM-owner": o próprio autor marcou o arquivo como domínio público (Public Domain Mark).
LICENCA_LIVRE = re.compile(r"^(cc0\b|cc by(-sa)? \d|public domain|pdm?\b|pdm?-)", re.IGNORECASE)
LICENCA_SEM_AUTOR_OK = re.compile(r"^(cc0\b|public domain|pdm?\b|pdm?-)", re.IGNORECASE)
HOST_IMAGEM = re.compile(r"^https://(upload|thumb)\.wikimedia\.org/")
FORMATO_ESCUDO = re.compile(r"\.(svg|png)$", re.IGNORECASE)
LOTE_SPARQL = 100       # itens por consulta com VALUES
FUTEBOLISTA = "Q937857"
LINGUAS_NOME = {"pt", "pt-br", "en", "es", "mul"}


# --- Texto --------------------------------------------------------------------------------

def chave_nome(nome: str) -> str:
    """Nome comparável: sem acentos, minúsculo, só letras e números, sem de/da/do."""
    base = unicodedata.normalize("NFKD", nome or "")
    base = "".join(c for c in base if not unicodedata.combining(c)).lower()
    palavras = re.sub(r"[^a-z0-9]+", " ", base).split()
    return " ".join(p for p in palavras if p not in PARTICULAS)


class _Texto(HTMLParser):
    def __init__(self):
        super().__init__()
        self.partes = []

    def handle_data(self, data):
        self.partes.append(data)


def texto_puro(trecho_html: str) -> str:
    """Texto visível de um trecho HTML dos metadados do Commons (autor, crédito)."""
    p = _Texto()
    p.feed(trecho_html or "")
    return re.sub(r"\s+", " ", html.unescape("".join(p.partes))).strip()


def licenca_livre(nome: str) -> bool:
    return bool(LICENCA_LIVRE.match((nome or "").strip()))


PREFIXO_ARQUIVO = re.compile(r"^(file|ficheiro|arquivo|imagem|image)\s*:\s*", re.IGNORECASE)


def nome_arquivo(valor: str) -> str:
    """'File:A_b.jpg', 'Ficheiro:A b.jpg' ou a URL Special:FilePath/A%20b.jpg -> 'A b.jpg'."""
    valor = urllib.parse.unquote(valor or "")
    if "Special:FilePath/" in valor:
        valor = valor.split("Special:FilePath/", 1)[1]
    valor = PREFIXO_ARQUIVO.sub("", valor.replace("_", " ").strip())
    return re.sub(r"\s+", " ", valor)


def titulo_de_url(url: str) -> str:
    """'https://pt.wikipedia.org/wiki/Pedro_(futebolista)' -> 'Pedro (futebolista)'."""
    return urllib.parse.unquote(url.rsplit("/wiki/", 1)[1]).replace("_", " ")


def limpar_url(url: str) -> str:
    """Tira da URL da miniatura os parâmetros de rastreio utm_ que a API acrescenta."""
    partes = urllib.parse.urlsplit(url or "")
    resto = [(k, v) for k, v in urllib.parse.parse_qsl(partes.query, keep_blank_values=True)
             if not k.lower().startswith("utm_")]
    return urllib.parse.urlunsplit(partes._replace(query=urllib.parse.urlencode(resto)))


def qid_de(linha: dict) -> str:
    """Linha do SPARQL -> 'Q123' (a variável ?p é sempre o item da pessoa)."""
    return linha["p"]["value"].rsplit("/", 1)[1]


# --- Acesso às APIs -----------------------------------------------------------------------

class Cliente:
    """Pedidos com User-Agent identificado, pausa entre eles e novas tentativas em 429/5xx."""

    def __init__(self, pausa: float = 0.2, tentativas: int = 5):
        self.pausa = pausa
        self.tentativas = tentativas
        self.pedidos = 0

    def json(self, url: str, params: dict, aceitar: str = "application/json", post: bool = False) -> dict:
        corpo = urllib.parse.urlencode(params)
        endereco, dados = (url, corpo.encode("utf-8")) if post else (f"{url}?{corpo}", None)
        espera = 2.0
        for tentativa in range(1, self.tentativas + 1):
            time.sleep(self.pausa)
            pedido = urllib.request.Request(endereco, data=dados,
                                            headers={"User-Agent": AGENTE, "Accept": aceitar})
            try:
                with urllib.request.urlopen(pedido, timeout=90) as r:
                    self.pedidos += 1
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504) or tentativa == self.tentativas:
                    detalhe = e.read().decode("utf-8", "replace")[:500]
                    raise RuntimeError(f"HTTP {e.code} em {url}: {detalhe}") from e
                espera = float(e.headers.get("Retry-After") or espera)
            except urllib.error.URLError:
                if tentativa == self.tentativas:
                    raise
            time.sleep(espera)
            espera *= 2
        raise RuntimeError("inalcançável")

    def wiki(self, host: str, **params) -> dict:
        base = {"action": "query", "format": "json", "formatversion": "2"}
        return self.json(f"https://{host}/w/api.php", {**base, **params})

    def sparql(self, consulta: str) -> list[dict]:
        # POST: as consultas com VALUES ficam longas demais para a URL de um GET.
        r = self.json("https://query.wikidata.org/sparql", {"query": consulta, "format": "json"},
                      "application/sparql-results+json", post=True)
        return r["results"]["bindings"]


def lotes(itens: list, n: int = 50):
    for i in range(0, len(itens), n):
        yield itens[i:i + n]


def resolver_titulos(resposta: dict, pedidos: list[str]) -> dict[str, dict]:
    """Liga cada título pedido à página final (normalização e redirecionamento)."""
    q = resposta.get("query", {})
    passo = {n["from"]: n["to"] for n in q.get("normalized", [])}
    passo.update({r["from"]: r["to"] for r in q.get("redirects", [])})
    paginas = {p["title"]: p for p in q.get("pages", []) if not p.get("missing") and not p.get("invalid")}
    resultado = {}
    for t in pedidos:
        final = t
        for _ in range(4):
            if final not in passo:
                break
            final = passo[final]
        if final in paginas:
            resultado[t] = paginas[final]
    return resultado


def paginas(cli: Cliente, host: str, titulos: list[str]) -> dict[str, dict]:
    """Título pedido -> {'titulo', 'qid', 'imagem'} (imagem principal livre da página)."""
    saida = {}
    for lote in lotes(sorted(set(titulos))):
        r = cli.wiki(host, titles="|".join(lote), redirects="1", prop="pageprops|pageimages",
                     ppprop="wikibase_item", piprop="name", pilimit="50")
        for pedido, p in resolver_titulos(r, lote).items():
            imagem = p.get("pageimage")
            saida[pedido] = {"titulo": p["title"], "qid": p.get("pageprops", {}).get("wikibase_item"),
                             "imagem": nome_arquivo(imagem) if imagem else None}
    return saida


# --- Candidatos da Wikidata ---------------------------------------------------------------

# Consultas curtas e sem UNION: o Wikidata Query Service recusa (erro 500) ou estoura o tempo
# (504) com a versão que juntava vínculos, nomes e imagens numa consulta só.
CONSULTA_VINCULOS = """
SELECT DISTINCT ?p ?inicio ?fim WHERE {
  ?p p:P54 ?vinculo .
  ?vinculo ps:P54 wd:%(clube)s .
  ?p wdt:P31 wd:Q5 .
  OPTIONAL { ?vinculo pq:P580 ?inicio }
  OPTIONAL { ?vinculo pq:P582 ?fim }
  FILTER(!BOUND(?inicio) || YEAR(?inicio) <= %(ano)d)
  FILTER(!BOUND(?fim) || YEAR(?fim) >= %(ano)d)
  FILTER NOT EXISTS { ?p wdt:P569 ?nasc . FILTER(YEAR(?nasc) < %(nascidos)d) }
}"""

# Rótulos e apelidos nas línguas que interessam; nome de nascimento e alcunha em qualquer língua.
CONSULTA_ROTULOS = """
SELECT ?p ?nome WHERE {
  VALUES ?p { %(itens)s }
  ?p rdfs:label|skos:altLabel ?nome .
  FILTER(LANG(?nome) IN ("pt", "pt-br", "en", "es", "mul"))
}"""

CONSULTA_NOMES_PROPRIOS = """
SELECT ?p ?nome WHERE {
  VALUES ?p { %(itens)s }
  ?p wdt:P1477|wdt:P1449 ?nome .
}"""

CONSULTA_IMAGENS = """
SELECT ?p ?img ?ptwiki ?enwiki WHERE {
  VALUES ?p { %(itens)s }
  OPTIONAL { ?p wdt:P18 ?img }
  OPTIONAL { ?ptwiki schema:about ?p ; schema:isPartOf <https://pt.wikipedia.org/> }
  OPTIONAL { ?enwiki schema:about ?p ; schema:isPartOf <https://en.wikipedia.org/> }
}"""


def por_item(cli: Cliente, consulta: str, qids, cache: dict) -> list[dict]:
    """Roda a consulta com VALUES em lotes, só para os itens ainda não consultados.

    cache: qid -> linhas já recebidas (um jogador que mudou de clube aparece em dois clubes).
    """
    faltam = sorted(set(qids) - cache.keys())
    for lote in lotes(faltam, LOTE_SPARQL):
        for q in lote:
            cache[q] = []
        for b in cli.sparql(consulta % {"itens": " ".join(f"wd:{q}" for q in lote)}):
            cache.setdefault(qid_de(b), []).append(b)
    return [b for q in sorted(set(qids)) for b in cache[q]]


@dataclass
class Candidato:
    qid: str
    nomes: set = field(default_factory=set)       # chaves de nome
    datado: bool = False                          # vínculo com início ou fim informado
    imagens: set = field(default_factory=set)     # P18
    ptwiki: str | None = None
    enwiki: str | None = None


def agrupar_candidatos(linhas: list[dict]) -> dict[str, Candidato]:
    """Junta as linhas do SPARQL (vínculos, nomes e imagens) em um candidato por item."""
    cands: dict[str, Candidato] = {}
    for b in linhas:
        qid = qid_de(b)
        c = cands.setdefault(qid, Candidato(qid))
        if "nome" in b:
            chave = chave_nome(b["nome"]["value"])
            if chave:
                c.nomes.add(chave)
        if "inicio" in b or "fim" in b:
            c.datado = True
        if "img" in b:
            c.imagens.add(nome_arquivo(b["img"]["value"]))
        if "ptwiki" in b:
            c.ptwiki = titulo_de_url(b["ptwiki"]["value"])
        if "enwiki" in b:
            c.enwiki = titulo_de_url(b["enwiki"]["value"])
    return cands


@dataclass
class Escolha:
    qid: str | None
    criterio: str             # curado | nome | (motivo de não ter foto)
    detalhe: str = ""
    confirmado_por: str = "wikidata"     # wikidata | wikipedia_en


def escolher(jogadores: list[dict], cands: dict[str, Candidato],
             curados: dict[str, str | None]) -> dict[str, Escolha]:
    """Escolhe o item da Wikidata de cada jogador de UM clube.

    jogadores: linhas de jogadores.csv do clube; curados: id_jogador -> qid da página curada
    (None se a página curada não tem item).
    """
    escolha: dict[str, Escolha] = {}
    reservados = {}
    for j in jogadores:
        jid = j["id_jogador"]
        if jid not in curados:
            continue
        qid = curados[jid]
        if qid and qid in cands:
            escolha[jid] = Escolha(qid, "curado")
            reservados[qid] = jid
        elif qid:
            escolha[jid] = Escolha(None, "curado sem vínculo",
                                   f"{qid} não tem vínculo P54 com o clube em {ANO} na Wikidata")
        else:
            escolha[jid] = Escolha(None, "curado sem item", "a página curada não tem item na Wikidata")

    por_nome = defaultdict(set)
    for c in cands.values():
        for n in c.nomes:
            por_nome[n].add(c.qid)

    for j in jogadores:
        jid = j["id_jogador"]
        if jid in escolha and escolha[jid].qid:
            continue
        chaves = {chave_nome(j["nome_fonte"]), chave_nome(j["nome_exibicao"])} - {""}
        achados = set().union(*(por_nome.get(k, set()) for k in chaves)) - set(reservados)
        if len(achados) > 1:
            datados = {q for q in achados if cands[q].datado}
            if len(datados) == 1:
                achados = datados
        if not achados:
            escolha.setdefault(jid, Escolha(None, "sem correspondência"))
        elif len(achados) > 1:
            escolha[jid] = Escolha(None, "ambíguo", ", ".join(sorted(achados)))
        else:
            escolha[jid] = Escolha(achados.pop(), "nome")

    # Um item casando com dois jogadores do mesmo clube: nenhum dos dois o usa.
    usos = defaultdict(list)
    for jid, e in escolha.items():
        if e.qid and e.criterio == "nome":
            usos[e.qid].append(jid)
    for qid, jids in usos.items():
        if len(jids) > 1:
            for jid in jids:
                escolha[jid] = Escolha(None, "ambíguo", f"{qid} corresponde a {', '.join(sorted(jids))}")
    return escolha


# --- Ficha da Wikipédia em inglês (segunda confirmação) -----------------------------------

INFOBOX = re.compile(r"\{\{\s*Infobox[ _]+football[ _]+biography", re.IGNORECASE)
FAIXA_ANOS = re.compile(r"(\d{4})\s*(?:([–—-])\s*(\d{4}|\d{2}(?!\d))?)?")
EMPRESTIMO = re.compile(r"→|&rarr;|\(\s*loan\s*\)|\{\{\s*loan", re.IGNORECASE)
LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def bloco_infobox(texto: str) -> str | None:
    """Conteúdo da predefinição Infobox football biography (sem as chaves de fora), ou None."""
    texto = re.sub(r"<!--.*?-->", "", texto or "", flags=re.DOTALL)
    texto = re.sub(r"<ref[^>/]*/>|<ref[^>]*>.*?</ref>", "", texto, flags=re.DOTALL | re.IGNORECASE)
    m = INFOBOX.search(texto)
    if not m:
        return None
    nivel, i = 0, m.start()
    while i < len(texto):
        if texto.startswith("{{", i):
            nivel, i = nivel + 1, i + 2
        elif texto.startswith("}}", i):
            nivel, i = nivel - 1, i + 2
            if nivel == 0:
                return texto[m.start() + 2:i - 2]
        else:
            i += 1
    return None


def parametros(bloco: str) -> dict[str, str]:
    """'Infobox x | years1 = 2019– | clubs1 = [[A|B]]' -> {'years1': '2019–', 'clubs1': '[[A|B]]'}."""
    partes, atual, nivel, i = [], [], 0, 0
    while i < len(bloco):
        dois = bloco[i:i + 2]
        if dois in ("{{", "[["):
            nivel += 1
            atual.append(dois)
            i += 2
        elif dois in ("}}", "]]"):
            nivel -= 1
            atual.append(dois)
            i += 2
        elif bloco[i] == "|" and nivel == 0:
            partes.append("".join(atual))
            atual, i = [], i + 1
        else:
            atual.append(bloco[i])
            i += 1
    partes.append("".join(atual))
    saida = {}
    for parte in partes[1:]:
        if "=" in parte:
            chave, valor = parte.split("=", 1)
            saida[chave.strip().lower()] = valor.strip()
    return saida


def faixa(anos: str) -> tuple[int, int, bool] | None:
    """'2019–2021' -> (2019, 2021, False); '2023–' -> (2023, 9999, True); '2019–20' -> (2019, 2020, False)."""
    texto = re.sub(r"\{\{0\|[^}]*\}\}", "", anos or "")      # {{0|0000}} só alinha a coluna
    m = FAIXA_ANOS.search(texto)
    if not m:
        return None
    inicio = int(m[1])
    if m[3]:
        fim = int(m[3]) if len(m[3]) == 4 else inicio // 100 * 100 + int(m[3])
        return inicio, fim + (100 if fim < inicio else 0), False
    if m[2]:
        return inicio, 9999, True
    return inicio, inicio, False


def clubes_no_ano(texto: str, ano: int) -> set[str]:
    """Destinos dos links dos clubes (clubsN) cujo período (yearsN) inclui o ano.

    Período sem fim só vale se nenhum clube depois dele na ficha for uma transferência: um
    "2015–" esquecido antes de outro clube é ficha desatualizada. Empréstimos ("→ Clube (loan)")
    não encerram o vínculo com o clube dono do passe.
    """
    bloco = bloco_infobox(texto)
    if not bloco:
        return set()
    p = parametros(bloco)
    numeros = sorted(int(k[5:]) for k in p if re.fullmatch(r"years\d+", k))
    transferencias = [n for n in numeros if not EMPRESTIMO.search(p.get(f"clubs{n}", ""))]
    saida = set()
    for n in numeros:
        f = faixa(p[f"years{n}"])
        link = LINK.search(p.get(f"clubs{n}", ""))
        if not f or not link:
            continue
        inicio, fim, aberto = f
        if inicio <= ano <= fim and not (aberto and any(m > n for m in transferencias)):
            saida.add(link[1].strip().replace("_", " "))
    return saida


def textos(cli, host: str, titulos) -> dict[str, str]:
    """Título pedido -> wikitext da página (seguindo redirecionamentos)."""
    saida = {}
    for lote in lotes(sorted(set(titulos)), 20):      # lotes menores: o texto inteiro vem junto
        r = cli.wiki(host, titles="|".join(lote), redirects="1", prop="revisions",
                     rvprop="content", rvslots="main")
        for pedido, pag in resolver_titulos(r, lote).items():
            rev = (pag.get("revisions") or [{}])[0]
            saida[pedido] = rev.get("slots", {}).get("main", {}).get("content", "")
    return saida


def buscar_futebolistas(cli, nome: str, cache: dict) -> list[str]:
    """Itens de futebolistas cujo rótulo ou apelido contém o nome, pela busca da Wikidata."""
    termo = nome.replace('"', "").strip()
    if termo and termo not in cache:
        r = cli.wiki("www.wikidata.org", list="search", srnamespace="0", srlimit="50", srprop="",
                     srsearch=f'"{termo}" haswbstatement:P106={FUTEBOLISTA}')
        cache[termo] = [b["title"] for b in r.get("query", {}).get("search", [])
                        if re.fullmatch(r"Q\d+", b["title"])]
    return cache.get(termo, [])


def entidades(cli, qids, props: str) -> dict[str, dict]:
    """Itens da Wikidata com as partes pedidas (labels|aliases|sitelinks ou claims)."""
    saida = {}
    for lote in lotes(sorted(set(qids))):
        r = cli.json("https://www.wikidata.org/w/api.php", {
            "action": "wbgetentities", "format": "json", "ids": "|".join(lote), "props": props,
            "sitefilter": "enwiki"})
        for q in lote:
            saida[q] = r.get("entities", {}).get(q, {})
    return saida


def nomes_do_item(ent: dict) -> set[str]:
    """Chaves dos rótulos e apelidos do item nas línguas usadas na regra 3."""
    nomes = [r["value"] for lang, r in ent.get("labels", {}).items() if lang in LINGUAS_NOME]
    nomes += [a["value"] for lang, lista in ent.get("aliases", {}).items() if lang in LINGUAS_NOME for a in lista]
    return {k for k in map(chave_nome, nomes) if k}


def pessoa_recente(ent: dict, checar_nascimento: bool = True) -> bool:
    """Regra 2 sem o vínculo: o item é uma pessoa (P31 = Q5) sem nascimento antes de 1975.

    Página curada não passa pelo filtro de nascimento: a pessoa foi escolhida à mão e o filtro
    só serve para separar homônimos (há itens com uma segunda data de nascimento errada).
    """
    afirmacoes = ent.get("claims", {})

    def valores(prop):
        return [a["mainsnak"]["datavalue"]["value"] for a in afirmacoes.get(prop, [])
                if a.get("mainsnak", {}).get("snaktype") == "value" and "datavalue" in a["mainsnak"]]

    if not any(isinstance(v, dict) and v.get("id") == "Q5" for v in valores("P31")):
        return False
    for v in valores("P569") if checar_nascimento else []:
        m = re.match(r"^\+?(\d{4})-", v.get("time", "") if isinstance(v, dict) else "")
        if m and int(m[1]) < NASCIDOS_DESDE:
            return False
    return True


def confirmar_pela_ficha(cli, jogadores: list[dict], escolhas: dict, curados: dict,
                         qids_clube: dict, log) -> None:
    """Regra 3b: confirma pela ficha da Wikipédia em inglês quem a Wikidata não confirmou.

    Curado: primeiro o item da página curada; se ele não se confirmar, a busca por nome.
    """
    pendentes = [j for j in jogadores if escolhas[j["id_jogador"]].criterio in
                 ("sem correspondência", "curado sem vínculo", "curado sem item")]
    if not pendentes:
        return
    buscas, por_nome, curado_de = {}, {}, {}
    for j in pendentes:
        jid = j["id_jogador"]
        if curados.get(jid):
            curado_de[jid] = curados[jid]
        nomes = sorted({j["nome_fonte"], j["nome_exibicao"]} - {""})
        por_nome[jid] = {q for n in nomes for q in buscar_futebolistas(cli, n, buscas)}
    basicos = entidades(cli, {q for qs in por_nome.values() for q in qs} | set(curado_de.values()),
                        "labels|aliases|sitelinks")
    enwiki = {q: e.get("sitelinks", {}).get("enwiki", {}).get("title") for q, e in basicos.items()}
    for j in pendentes:
        chaves = {chave_nome(j["nome_fonte"]), chave_nome(j["nome_exibicao"])} - {""}
        por_nome[j["id_jogador"]] = {q for q in por_nome[j["id_jogador"]]
                                     if enwiki.get(q) and nomes_do_item(basicos[q]) & chaves}
    restantes = {q for qs in por_nome.values() for q in qs} | {q for q in curado_de.values() if enwiki.get(q)}
    afirmacoes = entidades(cli, restantes, "claims")
    recentes = {q for q, e in afirmacoes.items() if pessoa_recente(e)}
    pessoas = {q for q, e in afirmacoes.items() if pessoa_recente(e, checar_nascimento=False)}
    fichas = textos(cli, "en.wikipedia.org", {enwiki[q] for q in pessoas})
    clubes = {q: clubes_no_ano(fichas.get(enwiki[q], ""), ANO) for q in pessoas}
    destinos = paginas(cli, "en.wikipedia.org", {t for ts in clubes.values() for t in ts})
    clube_ok = {q: {destinos[t]["qid"] for t in ts if t in destinos} for q, ts in clubes.items()}

    usados = defaultdict(set)          # clube -> itens já escolhidos pela Wikidata
    for j in jogadores:
        if escolhas[j["id_jogador"]].qid:
            usados[j["id_clube"]].add(escolhas[j["id_jogador"]].qid)
    for j in pendentes:
        jid, cid = j["id_jogador"], j["id_clube"]
        q = curado_de.get(jid)
        if q and q in pessoas and qids_clube[cid] in clube_ok[q] and q not in usados[cid]:
            escolhas[jid] = Escolha(q, "curado", confirmado_por="wikipedia_en")
            continue
        ok = {c for c in por_nome[jid] & recentes if qids_clube[cid] in clube_ok[c]} - usados[cid]
        if len(ok) == 1:
            escolhas[jid] = Escolha(ok.pop(), "nome", confirmado_por="wikipedia_en")
        elif len(ok) > 1:
            escolhas[jid] = Escolha(None, "ambíguo", "pela ficha: " + ", ".join(sorted(ok)))
        elif q:
            if not enwiki.get(q):
                motivo = "o item da página curada não tem página em inglês"
            elif q not in pessoas:
                motivo = "o item da página curada não é uma pessoa (página de desambiguação?)"
            else:
                motivo = f"a ficha em inglês não lista o clube em {ANO}"
            escolhas[jid].detalhe += f"; ficha da Wikipédia: {motivo}; a busca por nome também não confirmou"

    # O mesmo item para dois jogadores do mesmo clube: nenhum o usa, salvo um único curado.
    usos = defaultdict(list)
    for j in jogadores:
        e = escolhas[j["id_jogador"]]
        if e.qid and e.confirmado_por == "wikipedia_en":
            usos[(j["id_clube"], e.qid)].append(j["id_jogador"])
    for (_, qid), jids in usos.items():
        if len(jids) > 1:
            curados_ = [jid for jid in jids if escolhas[jid].criterio == "curado"]
            for jid in jids:
                if not (len(curados_) == 1 and jid in curados_):
                    escolhas[jid] = Escolha(None, "ambíguo", f"{qid} corresponde a {', '.join(sorted(jids))}")
    novos = sum(1 for j in pendentes if escolhas[j["id_jogador"]].qid)
    log(f"  Ficha da Wikipédia (en): mais {novos} jogadores confirmados ({len(buscas)} buscas por nome)")


# --- Arquivos e licenças ------------------------------------------------------------------

def ler_imageinfo(resposta: dict, pedidos: list[str]) -> dict[str, dict]:
    """Nome do arquivo pedido -> metadados (miniatura, página, autor, licença)."""
    q = resposta.get("query", {})
    passo = {nome_arquivo(n["from"]): nome_arquivo(n["to"]) for n in q.get("normalized", [])}
    paginas_ = {nome_arquivo(p["title"]): p for p in q.get("pages", [])}
    saida = {}
    for pedido in pedidos:
        chave = nome_arquivo(pedido)
        p = paginas_.get(passo.get(chave, chave))
        info = (p or {}).get("imageinfo")
        if not info:
            continue
        info = info[0]
        meta = info.get("extmetadata", {})
        valor = lambda k: (meta.get(k) or {}).get("value", "")  # noqa: E731
        saida[pedido] = {
            "url_imagem": limpar_url(info.get("thumburl") or info.get("url", "")),
            "pagina_arquivo": info.get("descriptionurl", ""),
            "autor": texto_puro(valor("Artist")),
            "licenca": texto_puro(valor("LicenseShortName")),
            "licenca_url": valor("LicenseUrl").strip(),
            "nao_livre": str(valor("NonFree")).strip().lower() in ("true", "1"),
        }
    return saida


def metadados(cli: Cliente, host: str, arquivos: list[str], largura: int) -> dict[str, dict]:
    saida = {}
    for lote in lotes(sorted(set(arquivos))):
        r = cli.wiki(host, titles="|".join(f"File:{a}" for a in lote), prop="imageinfo",
                     iiprop="url|extmetadata", iiurlwidth=str(largura),
                     iiextmetadatafilter="Artist|LicenseShortName|LicenseUrl|NonFree")
        saida.update(ler_imageinfo(r, lote))
    return saida


def recusa_licenca(m: dict) -> str | None:
    """Motivo para recusar o arquivo, ou None se ele pode ser usado."""
    if m["nao_livre"] or not licenca_livre(m["licenca"]):
        return f"licença não aceita: {m['licenca'] or 'sem licença nos metadados'}"
    if not m["autor"] and not LICENCA_SEM_AUTOR_OK.match(m["licenca"]):
        return f"{m['licenca']} sem autor nos metadados"
    if not HOST_IMAGEM.match(m["url_imagem"]):
        return "miniatura fora dos servidores da Wikimedia"
    return None


def metadados_por_host(cli: Cliente, fontes: list[tuple], largura: int) -> dict[str, dict]:
    """fontes: (host, arquivo, origem) -> {host: {arquivo: metadados}}."""
    por_host = defaultdict(set)
    for host, arquivo, _ in fontes:
        por_host[host].add(arquivo)
    return {host: metadados(cli, host, sorted(arqs), largura) for host, arqs in sorted(por_host.items())}


def primeira_aceita(fontes: list[tuple], meta: dict) -> tuple[tuple | None, list[str]]:
    """A primeira imagem com licença aceita, na ordem de preferência, e os motivos das recusadas.

    fontes: [(host, arquivo, origem)]; meta: saída de metadados_por_host.
    Devolve ((arquivo, origem, metadados) ou None, ["arquivo: motivo", ...]).
    """
    motivos, vistos = [], set()
    for host, arquivo, origem in fontes:
        if arquivo in vistos:
            continue
        vistos.add(arquivo)
        m = meta.get(host, {}).get(arquivo)
        motivo = "sem metadados do arquivo" if not m else recusa_licenca(m)
        if not motivo:
            return (arquivo, origem, m), motivos
        motivos.append(f"{arquivo}: {motivo}")
    return None, motivos


# --- Execução -----------------------------------------------------------------------------

def ler_csv(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    for i, linha in enumerate(linhas, start=2):
        if None in linha:
            raise SystemExit(f"{caminho.name}, linha {i}: colunas a mais (vírgula sem aspas?)")
    return linhas


def gravar_csv(caminho: Path, colunas: list[str], linhas: list[dict]) -> None:
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas, lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


def candidatos_curados(wiki: str) -> list[tuple[str, str]]:
    """'en:Título|pt:Título' -> [('en.wikipedia.org', 'Título'), ...]."""
    saida = []
    for parte in (wiki or "").split("|"):
        if ":" in parte:
            lang, titulo = parte.split(":", 1)
            saida.append((f"{lang.strip()}.wikipedia.org", titulo.strip()))
    return saida


def escudo_uso_justo(fontes: list[tuple], meta: dict) -> tuple | None:
    """Último recurso (decisão do Thiago): o escudo da página pt mesmo sem licença livre.

    Só escudo, nunca foto: a imagem identifica o clube, como nos outros. A licença fica
    registrada como "Uso justo" e a página de créditos avisa.
    """
    for host, arquivo, origem in fontes:
        m = meta.get(host, {}).get(arquivo)
        if origem == "pagina_pt" and m and HOST_IMAGEM.match(m["url_imagem"]):
            return arquivo, "pagina_pt_uso_justo", {**m, "licenca": "Uso justo", "licenca_url": ""}
    return None


def buscar_escudos(cli: Cliente, clubes: list[dict], hoje: str, log) -> tuple[list[dict], dict, list]:
    pags = paginas(cli, "pt.wikipedia.org", [c["wiki_pt"] for c in clubes])
    qids, origem, problemas = {}, {}, []
    for c in clubes:
        p = pags.get(c["wiki_pt"])
        if not p or not p["qid"]:
            raise SystemExit(f"Clube {c['id_clube']}: página '{c['wiki_pt']}' sem item na Wikidata")
        qids[c["id_clube"]] = p["qid"]
        if p["imagem"]:
            origem[c["id_clube"]] = [("pt.wikipedia.org", p["imagem"], "pagina_pt")]
    # Logotipos (P154) de todos os clubes: entram quando a imagem da página falta ou é recusada.
    r = cli.json("https://www.wikidata.org/w/api.php", {"action": "wbgetentities", "format": "json",
                 "ids": "|".join(sorted(set(qids.values()))), "props": "claims"})
    for c in clubes:
        ent = r.get("entities", {}).get(qids[c["id_clube"]], {})
        logos = [s["mainsnak"].get("datavalue", {}).get("value")
                 for s in ent.get("claims", {}).get("P154", [])]
        origem.setdefault(c["id_clube"], []).extend(
            ("pt.wikipedia.org", nome_arquivo(v), "wikidata_p154") for v in logos if isinstance(v, str))
    fora_do_formato = defaultdict(list)
    for cid, fontes in origem.items():
        fora_do_formato[cid] = [f"{a}: escudo precisa ser SVG ou PNG" for _, a, _ in fontes
                                if not FORMATO_ESCUDO.search(a)]
        origem[cid] = [f for f in fontes if FORMATO_ESCUDO.search(f[1])]
    meta = metadados_por_host(cli, [f for fs in origem.values() for f in fs], LARGURA_ESCUDO)
    linhas = []
    for c in clubes:
        cid = c["id_clube"]
        aceita, motivos = primeira_aceita(origem.get(cid, []), meta)
        if not aceita:
            aceita = escudo_uso_justo(origem.get(cid, []), meta)
        if not aceita:
            motivos = fora_do_formato[cid] + motivos
            problemas.append((cid, "; ".join(motivos) or "sem imagem na página nem logotipo na Wikidata"))
            continue
        arquivo, de_onde, m = aceita
        linhas.append({"id_clube": cid, "wikidata": qids[cid], "arquivo": arquivo,
                       **{k: m[k] for k in ("url_imagem", "pagina_arquivo", "autor", "licenca", "licenca_url")},
                       "origem_imagem": de_onde, "consultado_em": hoje})
    log(f"Escudos: {len(linhas)} de {len(clubes)}")
    return linhas, qids, problemas


def buscar_fotos(cli: Cliente, jogadores: list[dict], qids_clube: dict, hoje: str, log):
    # 1. Itens das páginas curadas.
    pedidos = defaultdict(list)
    for j in jogadores:
        for host, titulo in candidatos_curados(j["wiki"]):
            pedidos[host].append(titulo)
    resolvidas = {host: paginas(cli, host, titulos) for host, titulos in pedidos.items()}
    curados = {}
    for j in jogadores:
        alvos = candidatos_curados(j["wiki"])
        if alvos:
            qid = next((resolvidas[h].get(t, {}).get("qid") for h, t in alvos
                        if resolvidas[h].get(t, {}).get("qid")), None)
            curados[j["id_jogador"]] = qid

    # 2. Candidatos de cada clube e escolha.
    por_clube = defaultdict(list)
    for j in jogadores:
        por_clube[j["id_clube"]].append(j)
    escolhas = {}
    cache_rotulos, cache_proprios = {}, {}
    for cid in sorted(por_clube):
        vinculos = cli.sparql(CONSULTA_VINCULOS % {"clube": qids_clube[cid], "ano": ANO,
                                                   "nascidos": NASCIDOS_DESDE})
        qids = {qid_de(b) for b in vinculos}
        cands = agrupar_candidatos(vinculos + por_item(cli, CONSULTA_ROTULOS, qids, cache_rotulos)
                                   + por_item(cli, CONSULTA_NOMES_PROPRIOS, qids, cache_proprios))
        escolhas.update(escolher(por_clube[cid], cands, curados))
        log(f"  {cid}: {len(cands)} candidatos na Wikidata, "
            f"{sum(1 for j in por_clube[cid] if escolhas[j['id_jogador']].qid)} de {len(por_clube[cid])} jogadores identificados")

    # 2b. Segunda confirmação pela ficha da Wikipédia em inglês.
    confirmar_pela_ficha(cli, jogadores, escolhas, curados, qids_clube, log)

    # 3. Imagens possíveis de cada pessoa, na ordem: P18, página pt, página en.
    escolhidos = {e.qid for e in escolhas.values() if e.qid}
    imagens = agrupar_candidatos(por_item(cli, CONSULTA_IMAGENS, escolhidos, {}))
    titulos = defaultdict(set)
    for c in imagens.values():
        for host, titulo in (("pt.wikipedia.org", c.ptwiki), ("en.wikipedia.org", c.enwiki)):
            if titulo:
                titulos[host].add(titulo)
    pags = {host: paginas(cli, host, sorted(ts)) for host, ts in titulos.items()}
    origem = {}
    for j in jogadores:
        e = escolhas[j["id_jogador"]]
        c = imagens.get(e.qid) if e.qid else None
        if not c:
            continue
        # A imagem principal da página costuma ser a mais recente; a P18 fica como reserva.
        fontes = []
        for host, titulo in (("pt.wikipedia.org", c.ptwiki), ("en.wikipedia.org", c.enwiki)):
            imagem = pags.get(host, {}).get(titulo, {}).get("imagem") if titulo else None
            if imagem:
                fontes.append((host, imagem, "pagina_" + host[:2]))
        fontes += [("commons.wikimedia.org", img, "wikidata_p18") for img in sorted(c.imagens)]
        if fontes:
            origem[j["id_jogador"]] = fontes

    # 4. Metadados e licença: fica a primeira imagem aceita.
    meta = metadados_por_host(cli, [f for fs in origem.values() for f in fs], LARGURA_FOTO)
    linhas, recusadas = [], []
    for j in jogadores:
        jid = j["id_jogador"]
        e = escolhas[jid]
        if jid not in origem:
            if e.qid:
                escolhas[jid] = Escolha(e.qid, "sem imagem livre")
            continue
        aceita, motivos = primeira_aceita(origem[jid], meta)
        recusadas += [(jid, m) for m in motivos]
        if not aceita:
            escolhas[jid] = Escolha(e.qid, "licença recusada", "; ".join(motivos))
            continue
        arquivo, de_onde, m = aceita
        linhas.append({"id_jogador": jid, "wikidata": e.qid, "arquivo": arquivo,
                       **{k: m[k] for k in ("url_imagem", "pagina_arquivo", "autor", "licenca", "licenca_url")},
                       "origem_imagem": de_onde, "criterio": e.criterio,
                       "confirmado_por": e.confirmado_por, "consultado_em": hoje})
    return linhas, escolhas, recusadas


def relatorio(jogadores, destaques, escolhas, fotos, escudos, problemas_escudos, hoje) -> str:
    com_foto = {f["id_jogador"] for f in fotos}
    nomes = {j["id_jogador"]: (j["nome_exibicao"], j["id_clube"]) for j in jogadores}
    contagem = defaultdict(int)
    for jid, e in escolhas.items():
        contagem["com foto" if jid in com_foto else e.criterio] += 1
    linhas = [
        "# Fotos dos jogadores e escudos: relatório da busca",
        "",
        f"Gerado por `scripts/buscar_fotos.py` em {hoje}. Não edite à mão: rode o script de novo.",
        "",
        "A foto só entra quando a Wikidata ou a ficha da Wikipédia em inglês confirma a pessoa (mesmo",
        f"nome e o clube em {ANO}) e o arquivo tem licença livre com autor. As regras completas estão",
        "no início do script.",
        "",
        "## Cobertura",
        "",
        "| Item | Quantidade |",
        "|---|---|",
        f"| Escudos com imagem | {len(escudos)} de 20 |",
        f"| Jogadores (jogador × clube) | {len(jogadores)} |",
    ]
    for chave in ("com foto", "sem imagem livre", "licença recusada", "ambíguo", "sem correspondência",
                  "curado sem vínculo", "curado sem item"):
        linhas.append(f"| {chave.capitalize()} | {contagem.get(chave, 0)} |")
    por_criterio = defaultdict(int)
    for f in fotos:
        por_criterio[f["criterio"]] += 1
        por_criterio[f["confirmado_por"]] += 1
    linhas += ["", f"Das {len(fotos)} fotos, {por_criterio['curado']} vêm de páginas curadas e "
               f"{por_criterio['nome']} da correspondência pelo nome. A Wikidata confirmou "
               f"{por_criterio['wikidata']}; a ficha da Wikipédia em inglês confirmou "
               f"{por_criterio['wikipedia_en']} que a Wikidata não registrava no clube.", ""]
    if problemas_escudos:
        linhas += ["## Clubes sem escudo", ""] + [f"- {c}: {m}" for c, m in problemas_escudos] + [""]
    ids_destaque = {j["id_jogador"] for j in jogadores
                    if any(d["nome_exibicao"] == j["nome_exibicao"] and d["id_clube"] == j["id_clube"] for d in destaques)}
    faltam = sorted(ids_destaque - com_foto)
    linhas += ["## Destaques sem foto", "",
               "Jogadores de `data/reference/jogadores_destaque.csv` (artilharia, assistências, goleiros,",
               "seleção e prêmios) que ficaram sem foto, e o motivo.", ""]
    if faltam:
        linhas += ["| Jogador | Clube | Motivo |", "|---|---|---|"]
        for jid in faltam:
            e = escolhas[jid]
            motivo = e.criterio + (f" ({e.detalhe})" if e.detalhe else "")
            linhas.append(f"| {nomes[jid][0]} | {nomes[jid][1]} | {motivo} |")
    else:
        linhas.append("Nenhum.")
    ambiguos = sorted(jid for jid, e in escolhas.items() if e.criterio == "ambíguo")
    linhas += ["", "## Casos ambíguos (ficaram sem foto)", ""]
    linhas += [f"- {nomes[j][0]} ({nomes[j][1]}): {escolhas[j].detalhe}" for j in ambiguos] or ["Nenhum."]
    linhas += ["", "## Como incluir um jogador que ficou de fora", "",
               "1. Ache a página dele na Wikipédia e confira que é a mesma pessoa (clube em 2024).",
               "2. Preencha a coluna `wiki` em `data/reference/jogadores_destaque.csv`",
               "   (`pt:Título` ou `en:Título`; título com vírgula vai entre aspas).",
               "3. Rode `preparar_jogadores.py`, este script, a carga do banco e a exportação.",
               "   Se nem a Wikidata nem a ficha da página em inglês mostrarem o clube em 2024, a foto",
               "   continua de fora.", ""]
    return "\n".join(linhas)


def main(argv=None) -> int:
    argparse.ArgumentParser(description=__doc__.split("\n\n")[0]).parse_args(argv)
    hoje = datetime.now(timezone.utc).date().isoformat()
    log = lambda m: print(m, flush=True)  # noqa: E731
    jogadores = ler_csv(JOGADORES)
    destaques = ler_csv(DESTAQUES)
    clubes = ler_csv(CLUBES_VISUAL)
    cli = Cliente()
    escudos, qids_clube, problemas_escudos = buscar_escudos(cli, clubes, hoje, log)
    fotos, escolhas, recusadas = buscar_fotos(cli, jogadores, qids_clube, hoje, log)
    gravar_csv(SAIDA_ESCUDOS, COLUNAS_ESCUDOS, escudos)
    gravar_csv(SAIDA_FOTOS, COLUNAS_FOTOS, fotos)
    SAIDA_RELATORIO.write_text(relatorio(jogadores, destaques, escolhas, fotos, escudos,
                                         problemas_escudos, hoje), encoding="utf-8")
    log(f"Fotos: {len(fotos)} de {len(jogadores)} jogadores ({len(recusadas)} arquivos recusados pela licença)")
    log(f"Pedidos às APIs: {cli.pedidos}")
    log(f"[OK] {SAIDA_ESCUDOS.relative_to(RAIZ)}, {SAIDA_FOTOS.relative_to(RAIZ)}, "
        f"{SAIDA_RELATORIO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
