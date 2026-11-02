"""Testes das regras de scripts/buscar_fotos.py (sem rede: respostas das APIs simuladas).

O script em si precisa de internet; aqui se confere a parte que decide: comparação de nomes,
escolha do item da Wikidata (curado, por nome, ambíguo), leitura dos metadados do arquivo e
aceitação da licença. Também se confere que os arquivos gerados, quando existem, são coerentes.
"""

import csv
import re
import unittest

from apoio import RAIZ

import buscar_fotos as bf


def ligacao(qid, nome=None, inicio=None, fim=None, img=None, ptwiki=None):
    """Uma linha do SPARQL no formato JSON de resultados."""
    b = {"p": {"type": "uri", "value": f"http://www.wikidata.org/entity/{qid}"}}
    if nome:
        b["nome"] = {"type": "literal", "value": nome, "xml:lang": "pt"}
    if inicio:
        b["inicio"] = {"type": "literal", "value": inicio}
    if fim:
        b["fim"] = {"type": "literal", "value": fim}
    if img:
        b["img"] = {"type": "uri", "value": f"http://commons.wikimedia.org/wiki/Special:FilePath/{img}"}
    if ptwiki:
        b["ptwiki"] = {"type": "uri", "value": f"https://pt.wikipedia.org/wiki/{ptwiki}"}
    return b


def jogador(jid, nome_fonte, nome_exibicao=None, wiki=""):
    return {"id_jogador": jid, "nome_fonte": nome_fonte, "nome_exibicao": nome_exibicao or nome_fonte,
            "id_clube": jid[-3:].upper(), "wiki": wiki}


class TestTexto(unittest.TestCase):
    def test_chave_nome_ignora_acentos_caixa_pontuacao_e_particulas(self):
        self.assertEqual(bf.chave_nome("Giorgian De Arrascaeta"), bf.chave_nome("giorgian de arrascaeta"))
        self.assertEqual(bf.chave_nome("Ígor Jesus"), "igor jesus")
        self.assertEqual(bf.chave_nome("Thiago Emiliano da Silva"), "thiago emiliano silva")
        self.assertEqual(bf.chave_nome("Léo Jardim"), bf.chave_nome("Leo  Jardim"))
        self.assertNotEqual(bf.chave_nome("Pedro"), bf.chave_nome("Pedro Henrique"))

    def test_nome_arquivo(self):
        self.assertEqual(bf.nome_arquivo("http://commons.wikimedia.org/wiki/Special:FilePath/Pedro%20Guilherme%202019.jpg"),
                         "Pedro Guilherme 2019.jpg")
        self.assertEqual(bf.nome_arquivo("File:Pedro_Guilherme_2019.jpg"), "Pedro Guilherme 2019.jpg")
        self.assertEqual(bf.nome_arquivo("Ficheiro:Escudo do Botafogo.svg"), "Escudo do Botafogo.svg")
        # Dois-pontos no próprio nome não é prefixo.
        self.assertEqual(bf.nome_arquivo("Hulk: treino 2023.jpg"), "Hulk: treino 2023.jpg")

    def test_texto_puro(self):
        self.assertEqual(bf.texto_puro('<a href="//commons.wikimedia.org/wiki/User:X">Fulano&nbsp;de Tal</a>\n'),
                         "Fulano de Tal")

    def test_licencas(self):
        for livre in ("CC BY-SA 4.0", "CC BY 2.0", "CC0", "Public domain", "CC BY-SA 3.0 br", "PD-textlogo",
                      "PDM-owner"):
            self.assertTrue(bf.licenca_livre(livre), livre)
        for outra in ("", "Fair use", "Copyrighted", "CC BY-NC 2.0", "CC BY-ND 4.0", "GFDL", "PDF"):
            self.assertFalse(bf.licenca_livre(outra), outra)

    def test_curados(self):
        self.assertEqual(bf.candidatos_curados("en:Pedro (footballer, born 1997)|pt:Pedro (futebolista)"),
                         [("en.wikipedia.org", "Pedro (footballer, born 1997)"),
                          ("pt.wikipedia.org", "Pedro (futebolista)")])
        self.assertEqual(bf.candidatos_curados(""), [])


class TestEscolha(unittest.TestCase):
    def cands(self, *linhas):
        return bf.agrupar_candidatos(list(linhas))

    def test_agrupa_nomes_imagens_e_paginas(self):
        c = self.cands(ligacao("Q1", "Pedro", img="Pedro 2019.jpg"),
                       ligacao("Q1", "Pedro Guilherme Abreu dos Santos", inicio="2020-01-01T00:00:00Z",
                               ptwiki="Pedro_(futebolista,_nascido_em_1997)"))["Q1"]
        self.assertEqual(c.nomes, {"pedro", "pedro guilherme abreu santos"})
        self.assertEqual(c.imagens, {"Pedro 2019.jpg"})
        self.assertTrue(c.datado)
        self.assertEqual(c.ptwiki, "Pedro (futebolista, nascido em 1997)")

    def test_nome_unico_casa(self):
        e = bf.escolher([jogador("hulk-atm", "Hulk")],
                        self.cands(ligacao("Q10", "Hulk"), ligacao("Q11", "Paulinho")), {})
        self.assertEqual((e["hulk-atm"].qid, e["hulk-atm"].criterio), ("Q10", "nome"))

    def test_nome_de_exibicao_tambem_casa(self):
        j = jogador("jose-manuel-alberto-lopez-pal", "José Manuel Alberto López", "Flaco López")
        e = bf.escolher([j], self.cands(ligacao("Q20", "Flaco López")), {})
        self.assertEqual(e[j["id_jogador"]].qid, "Q20")

    def test_sem_correspondencia_fica_sem_foto(self):
        e = bf.escolher([jogador("abner-juv", "Abner")], self.cands(ligacao("Q30", "Abner Vinícius")), {})
        self.assertIsNone(e["abner-juv"].qid)
        self.assertEqual(e["abner-juv"].criterio, "sem correspondência")

    def test_dois_candidatos_desempata_pelo_vinculo_datado(self):
        cands = self.cands(ligacao("Q40", "John"), ligacao("Q41", "John", inicio="2023-01-01T00:00:00Z"))
        e = bf.escolher([jogador("john-bot", "John")], cands, {})
        self.assertEqual(e["john-bot"].qid, "Q41")

    def test_dois_candidatos_sem_desempate_e_ambiguo(self):
        cands = self.cands(ligacao("Q40", "John"), ligacao("Q41", "John"))
        e = bf.escolher([jogador("john-bot", "John")], cands, {})
        self.assertIsNone(e["john-bot"].qid)
        self.assertEqual(e["john-bot"].criterio, "ambíguo")

    def test_mesmo_item_para_dois_jogadores_do_clube_nao_e_usado(self):
        cands = self.cands(ligacao("Q50", "Gabriel"), ligacao("Q50", "Gabriel Barbosa"))
        js = [jogador("gabriel-fla", "Gabriel"), jogador("gabriel-barbosa-fla", "Gabriel Barbosa")]
        e = bf.escolher(js, cands, {})
        self.assertIsNone(e["gabriel-fla"].qid)
        self.assertIsNone(e["gabriel-barbosa-fla"].qid)

    def test_curado_tem_prioridade_e_reserva_o_item(self):
        cands = self.cands(ligacao("Q60", "Hugo Souza"), ligacao("Q60", "Hugo"), ligacao("Q61", "Hugo"))
        js = [jogador("hugo-souza-cor", "Hugo Souza", wiki="en:Hugo Souza"), jogador("hugo-cor", "Hugo")]
        e = bf.escolher(js, cands, {"hugo-souza-cor": "Q60"})
        self.assertEqual((e["hugo-souza-cor"].qid, e["hugo-souza-cor"].criterio), ("Q60", "curado"))
        self.assertEqual((e["hugo-cor"].qid, e["hugo-cor"].criterio), ("Q61", "nome"))

    def test_curado_sem_vinculo_com_o_clube_nao_entra(self):
        e = bf.escolher([jogador("pedro-fla", "Pedro", wiki="en:X")], self.cands(ligacao("Q70", "Outro")),
                        {"pedro-fla": "Q99"})
        self.assertIsNone(e["pedro-fla"].qid)
        self.assertEqual(e["pedro-fla"].criterio, "curado sem vínculo")


class TestMetadados(unittest.TestCase):
    RESPOSTA = {"query": {
        "normalized": [{"fromencoded": False, "from": "File:Pedro_2019.jpg", "to": "File:Pedro 2019.jpg"}],
        "pages": [
            {"ns": 6, "title": "File:Pedro 2019.jpg", "imageinfo": [{
                "thumburl": ("https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/Pedro_2019.jpg/"
                             "330px-Pedro_2019.jpg?utm_source=commons&utm_medium=api"),
                "url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Pedro_2019.jpg",
                "descriptionurl": "https://commons.wikimedia.org/wiki/File:Pedro_2019.jpg",
                "extmetadata": {
                    "Artist": {"value": '<a href="//commons.wikimedia.org/wiki/User:Fulano">Fulano</a>'},
                    "LicenseShortName": {"value": "CC BY-SA 4.0"},
                    "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0"}}}]},
            {"ns": 6, "title": "File:Sem metadados.jpg", "missing": True},
        ]}}

    def test_le_imageinfo_pelo_nome_pedido(self):
        m = bf.ler_imageinfo(self.RESPOSTA, ["Pedro_2019.jpg", "Sem metadados.jpg"])
        self.assertEqual(set(m), {"Pedro_2019.jpg"})
        p = m["Pedro_2019.jpg"]
        self.assertEqual(p["autor"], "Fulano")
        self.assertEqual(p["licenca"], "CC BY-SA 4.0")
        self.assertEqual(p["url_imagem"],
                         "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/Pedro_2019.jpg/330px-Pedro_2019.jpg")
        self.assertIsNone(bf.recusa_licenca(p))

    def test_limpar_url_tira_so_os_utm(self):
        self.assertEqual(bf.limpar_url("https://thumb.wikimedia.org/a/330px-X%C3%A9.jpg?utm_source=x&utm_campaign=y"),
                         "https://thumb.wikimedia.org/a/330px-X%C3%A9.jpg")
        self.assertEqual(bf.limpar_url("https://upload.wikimedia.org/a.png?lang=pt&utm_medium=api"),
                         "https://upload.wikimedia.org/a.png?lang=pt")
        self.assertEqual(bf.limpar_url("https://upload.wikimedia.org/a.png"), "https://upload.wikimedia.org/a.png")

    def test_recusa(self):
        base = {"nao_livre": False, "autor": "Fulano", "licenca": "CC BY 2.0",
                "url_imagem": "https://upload.wikimedia.org/x.jpg"}
        self.assertIsNone(bf.recusa_licenca(base))
        self.assertIsNotNone(bf.recusa_licenca({**base, "autor": ""}))
        self.assertIsNone(bf.recusa_licenca({**base, "autor": "", "licenca": "Public domain"}))
        self.assertIsNotNone(bf.recusa_licenca({**base, "licenca": "Fair use"}))
        self.assertIsNotNone(bf.recusa_licenca({**base, "nao_livre": True}))
        self.assertIsNone(bf.recusa_licenca({**base, "url_imagem": "https://thumb.wikimedia.org/x.jpg"}))
        self.assertIsNotNone(bf.recusa_licenca({**base, "url_imagem": "http://exemplo.com/x.jpg"}))
        self.assertIsNotNone(bf.recusa_licenca({**base, "url_imagem": "https://thumb.wikimedia.org.exemplo.com/x.jpg"}))

    def test_primeira_aceita_segue_a_ordem_e_guarda_os_motivos(self):
        livre = {"nao_livre": False, "autor": "Fulano", "licenca": "CC BY 2.0",
                 "url_imagem": "https://upload.wikimedia.org/x.jpg"}
        meta = {"commons.wikimedia.org": {"P18.jpg": {**livre, "licenca": "Fair use"}},
                "pt.wikipedia.org": {"Pagina.jpg": livre}}
        fontes = [("commons.wikimedia.org", "P18.jpg", "wikidata_p18"),
                  ("commons.wikimedia.org", "Sumiu.jpg", "wikidata_p18"),
                  ("pt.wikipedia.org", "Pagina.jpg", "pagina_pt"),
                  ("en.wikipedia.org", "Outra.jpg", "pagina_en")]
        aceita, motivos = bf.primeira_aceita(fontes, meta)
        self.assertEqual(aceita[:2], ("Pagina.jpg", "pagina_pt"))
        self.assertEqual(len(motivos), 2)
        self.assertTrue(motivos[0].startswith("P18.jpg: licença não aceita"))
        self.assertEqual(motivos[1], "Sumiu.jpg: sem metadados do arquivo")
        self.assertEqual(bf.primeira_aceita(fontes[:2], meta)[0], None)

    def test_resolver_titulos_segue_redirecionamento(self):
        r = {"query": {"normalized": [{"from": "Pedro_(futebolista)", "to": "Pedro (futebolista)"}],
                       "redirects": [{"from": "Pedro (futebolista)", "to": "Pedro Guilherme"}],
                       "pages": [{"title": "Pedro Guilherme", "pageprops": {"wikibase_item": "Q1"}}]}}
        self.assertEqual(bf.resolver_titulos(r, ["Pedro_(futebolista)"])["Pedro_(futebolista)"]["title"],
                         "Pedro Guilherme")


def ler(caminho):
    with caminho.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class TestArquivosDeReferencia(unittest.TestCase):
    """Os arquivos curados e gerados não podem ter colunas a mais nem chaves inválidas."""

    def test_destaques_sem_colunas_a_mais(self):
        for i, linha in enumerate(ler(RAIZ / "data/reference/jogadores_destaque.csv"), start=2):
            self.assertNotIn(None, linha, f"linha {i}: vírgula sem aspas")

    def test_fotos_e_escudos_gerados(self):
        jogadores = {j["id_jogador"] for j in ler(RAIZ / "data/processed/jogadores.csv")}
        clubes = {c["id_clube"] for c in ler(RAIZ / "data/reference/clubes.csv")}
        for caminho, chave, ids, colunas in ((bf.SAIDA_FOTOS, "id_jogador", jogadores, bf.COLUNAS_FOTOS),
                                             (bf.SAIDA_ESCUDOS, "id_clube", clubes, bf.COLUNAS_ESCUDOS)):
            if not caminho.exists():
                continue
            linhas = ler(caminho)
            with caminho.open(encoding="utf-8") as f:
                self.assertEqual(f.readline().strip().split(","), colunas)
            self.assertEqual(len({l[chave] for l in linhas}), len(linhas), f"{caminho.name}: chave repetida")
            for l in linhas:
                self.assertIn(l[chave], ids)
                self.assertRegex(l["wikidata"], r"^Q\d+$")
                self.assertRegex(l["url_imagem"], bf.HOST_IMAGEM, l[chave])
                self.assertNotIn("utm_", l["url_imagem"], l[chave])
                if l["origem_imagem"] == "pagina_pt_uso_justo":      # só escudos
                    self.assertEqual((caminho, l["licenca"]), (bf.SAIDA_ESCUDOS, "Uso justo"))
                    continue
                self.assertTrue(bf.licenca_livre(l["licenca"]), l[chave])
                self.assertIsNone(bf.recusa_licenca({**l, "nao_livre": False}), l[chave])


def entidade(qid, rotulo, enwiki=None, nascido=None, humano=True, apelidos=()):
    """Item no formato do wbgetentities."""
    def afirmacao(valor):
        return {"mainsnak": {"snaktype": "value", "datavalue": {"value": valor}}}
    claims = {}
    if humano:
        claims["P31"] = [afirmacao({"id": "Q5"})]
    if nascido:
        claims["P569"] = [afirmacao({"time": f"+{nascido}-05-01T00:00:00Z", "precision": 11})]
    return {"id": qid, "labels": {"pt": {"language": "pt", "value": rotulo}},
            "aliases": {"en": [{"language": "en", "value": a} for a in apelidos]},
            "sitelinks": {"enwiki": {"site": "enwiki", "title": enwiki}} if enwiki else {},
            "claims": claims}


def ficha(*clubes):
    """Wikitext com a Infobox football biography: clubes = [(anos, clube), ...]."""
    linhas = ["{{Infobox football biography", "| name = X", "| youthyears1 = 2010–2015",
              "| youthclubs1 = [[Botafogo FR|Botafogo]]"]
    for n, (anos, clube) in enumerate(clubes, start=1):
        linhas += [f"| years{n} = {anos}", f"| clubs{n} = {clube}", f"| caps{n} = 10 | goals{n} = 1"]
    return "\n".join(linhas + ["}}", "X is a footballer."])


class ClienteSimulado:
    """Responde às chamadas do script como as APIs responderiam, para um caso pequeno.

    Escudos: Botafogo livre na página; Corinthians com a página não livre e, na P154, uma foto
    (JPG, recusada) e um logotipo livre; Vasco com a página não livre e só uma foto na P154.
    Jogadores do Botafogo confirmados pela Wikidata (P54): John (P18), Igor Jesus (página pt),
    Gregore (só imagem não livre), Bastos (sem imagem), Marlon Freitas (P18 não livre, página en
    livre; casa pelo nome de nascimento, P1477). Sem vínculo na Wikidata: Luiz Henrique (achado
    pela busca e confirmado pela ficha), Savarino (curado, confirmado pela ficha), Gabriel (dois
    itens confirmados: ambíguo), Danilo (ficha só com "2015–" no meio da carreira) e Tiquinho
    Soares (sem item).
    """

    VINCULOS = {"Q2": "2023-01-01T00:00:00Z", "Q3": None, "Q4": None, "Q5": None, "Q6": None}
    ROTULOS = {"Q2": ["John"], "Q3": ["Ígor Jesus"], "Q4": ["Gregore"], "Q5": ["Bastos"]}
    PROPRIOS = {"Q6": ["Marlon Rodrigues de Freitas"]}
    IMAGENS = {"Q2": {"img": "John_2024.jpg"}, "Q3": {"ptwiki": "Igor_Jesus"},
               "Q4": {"img": "Fair_use.jpg"}, "Q6": {"img": "Fair_use_Marlon.jpg", "enwiki": "Marlon_Freitas"},
               "Q7": {"img": "Luiz_Henrique_2024.jpg"}, "Q11": {"enwiki": "Jefferson_Savarino"},
               "Q16": {"img": "Luciano_2024.jpg"}, "Q18": {"img": "Alan_Patrick_2024.jpg"}}
    PAGINAS = {"Botafogo de Futebol e Regatas": ("Q100", "Escudo_BOT.svg"),
               "Sport Club Corinthians Paulista": ("Q200", "Escudo_COR_Fair_use.png"),
               "Club de Regatas Vasco da Gama": ("Q300", "Escudo_VAS_Fair_use.svg"),
               "Pedro (footballer, born 1997)": ("Q1", None),
               "Igor Jesus": ("Q3", "Igor_Jesus_2024.jpg"),
               "Marlon Freitas": ("Q6", "Marlon_Freitas_2024.jpg"),
               "Jefferson Savarino": ("Q11", "Savarino_2024.jpg"),
               "Luciano (footballer, born 1993)": ("Q16", None),
               "Alan Patrick": ("Q17", None),                 # página de desambiguação
               "Botafogo FR": ("Q100", None),               # outro título, mesmo item do clube
               "Clube X": ("Q999", None)}
    LOGOS = {"Q200": ["Corinthians23022007 (cropped).jpg", "Corinthians logo.svg"],
             "Q300": ["Vasco torcida.jpg"]}
    ENTIDADES = {
        "Q7": entidade("Q7", "Luiz Henrique", "Luiz Henrique (footballer, born 2001)", 2001),
        "Q8": entidade("Q8", "Luiz Henrique", "Luiz Henrique (footballer, born 1970)", 1970),
        "Q9": entidade("Q9", "Luiz Henrique", "Luiz Henrique (footballer, born 1990)", 1990),
        "Q10": entidade("Q10", "Luiz Henrique André", "Luiz Henrique André", 2001),
        "Q11": entidade("Q11", "Jefferson Savarino", "Jefferson Savarino", 1996),
        "Q12": entidade("Q12", "Gabriel", "Gabriel (footballer, born 1998)", 1998),
        "Q13": entidade("Q13", "Gabriel Silva", "Gabriel (footballer, born 2000)", 2000, apelidos=["Gabriel"]),
        "Q14": entidade("Q14", "Danilo", "Danilo (footballer, born 1995)", 1995),
        "Q15": entidade("Q15", "Danilo", None, 1996),                 # sem página em inglês
        "Q16": entidade("Q16", "Luciano", "Luciano (footballer, born 1993)", 1993),
        "Q17": entidade("Q17", "Alan Patrick", "Alan Patrick", humano=False),
        "Q18": entidade("Q18", "Alan Patrick", "Alan Patrick (footballer, born 1991)", 1991),
    }
    # Uma segunda data de nascimento errada (1965) no item do Luciano, como na Wikidata.
    ENTIDADES["Q16"]["claims"]["P569"].append(
        {"mainsnak": {"snaktype": "value", "datavalue": {"value": {"time": "+1965-01-01T00:00:00Z"}}}})
    FICHAS = {
        "Luiz Henrique (footballer, born 2001)": ficha(("2019–2022", "[[Fluminense FC|Fluminense]]"),
                                                       ("2022–2024", "[[Real Betis]]"),
                                                       ("2024–", "[[Botafogo FR|Botafogo]]")),
        "Luiz Henrique (footballer, born 1970)": ficha(("1990–", "[[Botafogo FR|Botafogo]]")),
        "Luiz Henrique (footballer, born 1990)": ficha(("2010–2012", "[[Botafogo FR|Botafogo]]"),
                                                       ("2013–", "[[Clube X]]")),
        "Luiz Henrique André": ficha(("2024–", "[[Botafogo FR|Botafogo]]")),
        "Jefferson Savarino": ficha(("2023–2024", "[[Clube X]]"), ("2024–", "[[Botafogo FR|Botafogo]]")),
        "Gabriel (footballer, born 1998)": ficha(("2024", "[[Botafogo FR|Botafogo]]")),
        "Gabriel (footballer, born 2000)": ficha(("2023–2025", "[[Botafogo FR]]")),
        "Danilo (footballer, born 1995)": ficha(("2015–", "[[Botafogo FR|Botafogo]]"), ("2018–2020", "[[Clube X]]")),
        "Luciano (footballer, born 1993)": ficha(("2024–", "[[Botafogo FR|Botafogo]]")),
        "Alan Patrick (footballer, born 1991)": ficha(("2023–", "[[Botafogo FR|Botafogo]]"),
                                                      ("2026–", "→ [[Clube X]] (loan)")),
    }
    BUSCA = {"Luiz Henrique": ["Q7", "Q8", "Q9", "Q10"], "Gabriel": ["Q12", "Q13"], "Danilo": ["Q14", "Q15"],
             "Luciano": ["Q16"], "Alan Patrick": ["Q17", "Q18"]}

    def __init__(self):
        self.consultas = []
        self.buscas = []

    def wiki(self, host, **p):
        if p.get("list") == "search":
            assert host == "www.wikidata.org" and "haswbstatement:P106=Q937857" in p["srsearch"]
            termo = re.match(r'"([^"]+)"', p["srsearch"])[1]
            self.buscas.append(termo)
            return {"query": {"search": [{"ns": 0, "title": q} for q in self.BUSCA.get(termo, [])]}}
        titulos = p["titles"].split("|")
        if p["prop"] == "imageinfo":
            paginas = []
            for t in titulos:
                nome = bf.nome_arquivo(t)
                livre = "Fair" not in nome
                paginas.append({"title": f"File:{nome}", "imageinfo": [{
                    "thumburl": (f"https://thumb.wikimedia.org/thumb/{nome.replace(' ', '_')}/"
                                 f"{p['iiurlwidth']}px.jpg?utm_source={host}"),
                    "descriptionurl": f"https://commons.wikimedia.org/wiki/File:{nome.replace(' ', '_')}",
                    "extmetadata": {"Artist": {"value": "<b>Autor</b>"},
                                    "LicenseShortName": {"value": "CC BY-SA 4.0" if livre else "Fair use"},
                                    "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0"}}}]})
            return {"query": {"pages": paginas}}
        if p["prop"] == "revisions":
            assert host == "en.wikipedia.org"
            return {"query": {"pages": [{"title": t, "revisions": [{"slots": {"main": {"content": self.FICHAS[t]}}}]}
                                        for t in titulos if t in self.FICHAS]}}
        paginas = []
        for t in titulos:
            if t in self.PAGINAS:
                qid, imagem = self.PAGINAS[t]
                pagina = {"title": t, "pageprops": {"wikibase_item": qid}}
                if imagem:
                    pagina["pageimage"] = imagem
                paginas.append(pagina)
        return {"query": {"pages": paginas}}

    def json(self, url, params, aceitar=None, post=False):
        assert params["action"] == "wbgetentities"
        saida = {}
        for q in params["ids"].split("|"):
            if q in self.LOGOS:
                saida[q] = {"id": q, "claims": {"P154": [
                    {"mainsnak": {"snaktype": "value", "datavalue": {"value": v}}} for v in self.LOGOS[q]]}}
            elif q in self.ENTIDADES:
                e = self.ENTIDADES[q]
                saida[q] = {k: e[k] for k in ["id"] + params["props"].split("|")}
            else:
                saida[q] = {"id": q, "missing": ""}
        return {"entities": saida}

    def sparql(self, consulta):
        self.consultas.append(consulta)
        if "p:P54" in consulta:
            assert "wd:Q100" in consulta and "UNION" not in consulta
            return [ligacao(q, inicio=d) for q, d in self.VINCULOS.items()]
        itens = re.search(r"VALUES \?p \{([^}]*)\}", consulta).group(1).split()
        qids = [i.removeprefix("wd:") for i in itens]
        if "rdfs:label" in consulta:
            return [ligacao(q, n) for q in qids for n in self.ROTULOS.get(q, [])]
        if "P1477" in consulta:
            return [ligacao(q, n) for q in qids for n in self.PROPRIOS.get(q, [])]
        assert "P18" in consulta
        saida = []
        for q in qids:
            b = ligacao(q, img=self.IMAGENS.get(q, {}).get("img"), ptwiki=self.IMAGENS.get(q, {}).get("ptwiki"))
            if "enwiki" in self.IMAGENS.get(q, {}):
                b["enwiki"] = {"type": "uri", "value": f"https://en.wikipedia.org/wiki/{self.IMAGENS[q]['enwiki']}"}
            saida.append(b)
        return saida


class TestFluxoSimulado(unittest.TestCase):
    def test_escudos(self):
        cli = ClienteSimulado()
        clubes = [{"id_clube": "BOT", "wiki_pt": "Botafogo de Futebol e Regatas"},
                  {"id_clube": "COR", "wiki_pt": "Sport Club Corinthians Paulista"},
                  {"id_clube": "VAS", "wiki_pt": "Club de Regatas Vasco da Gama"}]
        escudos, qids, problemas = bf.buscar_escudos(cli, clubes, "2026-11-01", lambda m: None)
        self.assertEqual(qids, {"BOT": "Q100", "COR": "Q200", "VAS": "Q300"})
        self.assertEqual([(e["id_clube"], e["arquivo"], e["origem_imagem"], e["licenca"]) for e in escudos],
                         [("BOT", "Escudo BOT.svg", "pagina_pt", "CC BY-SA 4.0"),
                          ("COR", "Corinthians logo.svg", "wikidata_p154", "CC BY-SA 4.0"),
                          # Sem escudo livre: o da página pt, registrado como uso justo.
                          ("VAS", "Escudo VAS Fair use.svg", "pagina_pt_uso_justo", "Uso justo")])
        self.assertTrue(all("utm_" not in e["url_imagem"] for e in escudos))
        self.assertEqual(problemas, [])

    def test_uso_justo_so_para_a_pagina_pt(self):
        meta = {"pt.wikipedia.org": {"Logo.jpg": {"url_imagem": "https://upload.wikimedia.org/x.png",
                                                 "licenca": "Fair use", "licenca_url": "", "autor": "",
                                                 "pagina_arquivo": "https://x", "nao_livre": True}}}
        self.assertIsNone(bf.escudo_uso_justo([("pt.wikipedia.org", "Logo.jpg", "wikidata_p154")], meta))
        self.assertEqual(bf.escudo_uso_justo([("pt.wikipedia.org", "Logo.jpg", "pagina_pt")], meta)[1],
                         "pagina_pt_uso_justo")

    def test_fotos_e_relatorio(self):
        cli = ClienteSimulado()
        js = [jogador("john-bot", "John"), jogador("igor-jesus-bot", "Ígor Jesus", "Igor Jesus"),
              jogador("gregore-bot", "Gregore"), jogador("bastos-bot", "Bastos"),
              jogador("marlon-rodrigues-de-freitas-bot", "Marlon Rodrigues de Freitas", "Marlon Freitas"),
              jogador("luiz-henrique-andre-rosa-da-silva-bot", "Luiz Henrique André Rosa da Silva", "Luiz Henrique"),
              jogador("savarino-bot", "Jefferson Savarino", "Savarino", wiki="en:Jefferson Savarino"),
              jogador("gabriel-bot", "Gabriel"), jogador("danilo-bot", "Danilo"),
              jogador("luciano-bot", "Luciano", wiki="en:Luciano (footballer, born 1993)"),
              jogador("alan-patrick-bot", "Alan Patrick", wiki="en:Alan Patrick"),
              jogador("tiquinho-bot", "Tiquinho Soares")]
        fotos, escolhas, recusadas = bf.buscar_fotos(cli, js, {"BOT": "Q100"}, "2026-11-01", lambda m: None)
        por_id = {f["id_jogador"]: f for f in fotos}
        self.assertEqual(set(por_id), {"john-bot", "igor-jesus-bot", "marlon-rodrigues-de-freitas-bot",
                                       "luiz-henrique-andre-rosa-da-silva-bot", "savarino-bot",
                                       "luciano-bot", "alan-patrick-bot"})
        self.assertEqual(por_id["john-bot"]["origem_imagem"], "wikidata_p18")
        self.assertEqual(por_id["igor-jesus-bot"]["origem_imagem"], "pagina_pt")
        self.assertEqual(por_id["marlon-rodrigues-de-freitas-bot"]["origem_imagem"], "pagina_en")
        self.assertEqual(por_id["marlon-rodrigues-de-freitas-bot"]["arquivo"], "Marlon Freitas 2024.jpg")
        self.assertEqual(por_id["john-bot"]["autor"], "Autor")
        self.assertTrue(all(bf.HOST_IMAGEM.match(f["url_imagem"]) and "utm_" not in f["url_imagem"] for f in fotos))
        # Pela ficha: só o Luiz Henrique certo (não o nascido em 1970, nem o de 2010–2012, nem o
        # de outro nome) e o curado.
        lh = por_id["luiz-henrique-andre-rosa-da-silva-bot"]
        self.assertEqual((lh["wikidata"], lh["criterio"], lh["confirmado_por"]), ("Q7", "nome", "wikipedia_en"))
        sv = por_id["savarino-bot"]
        self.assertEqual((sv["wikidata"], sv["criterio"], sv["confirmado_por"], sv["origem_imagem"]),
                         ("Q11", "curado", "wikipedia_en", "pagina_en"))
        self.assertEqual(por_id["john-bot"]["confirmado_por"], "wikidata")
        # Curado com uma data de nascimento errada na Wikidata: vale, a pessoa foi escolhida à mão.
        self.assertEqual((por_id["luciano-bot"]["wikidata"], por_id["luciano-bot"]["criterio"]), ("Q16", "curado"))
        # Curado numa página de desambiguação: a busca por nome acha o jogador (empréstimo depois
        # do clube não encerra o vínculo).
        ap = por_id["alan-patrick-bot"]
        self.assertEqual((ap["wikidata"], ap["criterio"], ap["confirmado_por"]), ("Q18", "nome", "wikipedia_en"))
        self.assertEqual((escolhas["gabriel-bot"].criterio, escolhas["gabriel-bot"].qid), ("ambíguo", None))
        self.assertIn("Q12, Q13", escolhas["gabriel-bot"].detalhe)
        self.assertEqual(escolhas["danilo-bot"].criterio, "sem correspondência")
        self.assertEqual(escolhas["gregore-bot"].criterio, "licença recusada")
        self.assertEqual(escolhas["bastos-bot"].criterio, "sem imagem livre")
        self.assertEqual(escolhas["tiquinho-bot"].criterio, "sem correspondência")
        self.assertEqual(len(recusadas), 1)        # Fair_use.jpg (Gregore); o Marlon fica com a página antes da P18
        destaques = [{"nome_exibicao": "Bastos", "id_clube": "BOT"}]
        texto = bf.relatorio(js, destaques, escolhas, fotos, [], [], "2026-11-01")
        self.assertIn("| Bastos | BOT | sem imagem livre |", texto)
        self.assertIn("| Com foto | 7 |", texto)
        self.assertIn("a ficha da Wikipédia em inglês confirmou 4", texto)
        self.assertTrue(all("UNION" not in c for c in cli.consultas))
        self.assertEqual(len(cli.buscas), len(set(cli.buscas)))      # cada nome é buscado uma vez


class TestFicha(unittest.TestCase):
    def test_faixa(self):
        self.assertEqual(bf.faixa("2019–2021"), (2019, 2021, False))
        self.assertEqual(bf.faixa("2023–"), (2023, 9999, True))
        self.assertEqual(bf.faixa("2019–20"), (2019, 2020, False))
        self.assertEqual(bf.faixa("1999–00"), (1999, 2000, False))
        self.assertEqual(bf.faixa("{{0|0000}}2024"), (2024, 2024, False))
        self.assertEqual(bf.faixa("2022 – 2024"), (2022, 2024, False))
        self.assertIsNone(bf.faixa(""))

    def test_clubes_no_ano(self):
        texto = """Texto antes.
{{Short description|Brazilian footballer}}
{{Infobox football biography
| name = Fulano <ref>{{cite web|url=http://x|title=a|b}}</ref>
| image = Fulano.jpg <!-- years9 = 2024 | clubs9 = [[Comentário]] -->
| youthyears1 = 2014–2016 | youthclubs1 = [[Clube Base]]
| years1 = 2017–2020 | clubs1 = [[Clube A|A]]
| years2 = 2021 | clubs2 = → [[Clube B]] (loan)
| years3 = 2021–2024 | clubs3 = [[Clube C#Futebol|C]]
| years4 = 2024– | clubs4 = [[Sport_Club_D|D]]
| nationalyears1 = 2024 | nationalteam1 = [[Brazil national football team|Brazil]]
}}
'''Fulano''' é jogador."""
        self.assertEqual(bf.clubes_no_ano(texto, 2024), {"Clube C", "Sport Club D"})
        self.assertEqual(bf.clubes_no_ano(texto, 2021), {"Clube B", "Clube C"})
        self.assertEqual(bf.clubes_no_ano("Sem ficha.", 2024), set())
        # "Sem fim" antes de outro clube é ficha desatualizada; antes de um empréstimo, não.
        self.assertEqual(bf.clubes_no_ano(ficha(("2015–", "[[A]]"), ("2018–2020", "[[B]]")), 2024), set())
        self.assertEqual(bf.clubes_no_ano(ficha(("2023–", "[[A]]"), ("2026–", "→ [[B]] (loan)")), 2024), {"A"})
        self.assertEqual(bf.clubes_no_ano(ficha(("2022–", "[[A]]"), ("2024", "→ [[B]] (loan)"),
                                                ("2025–", "[[C]]")), 2024), {"B"})

    def test_pessoa_recente_e_nomes(self):
        self.assertTrue(bf.pessoa_recente(entidade("Q1", "X", nascido=1990)))
        self.assertTrue(bf.pessoa_recente(entidade("Q1", "X")))
        self.assertFalse(bf.pessoa_recente(entidade("Q1", "X", nascido=1970)))
        self.assertFalse(bf.pessoa_recente(entidade("Q1", "X", humano=False)))
        e = entidade("Q1", "Gabriel Silva", apelidos=["Gabriel"])
        e["labels"]["ru"] = {"language": "ru", "value": "Габриэл"}
        self.assertEqual(bf.nomes_do_item(e), {"gabriel silva", "gabriel"})


class TestPorItem(unittest.TestCase):
    def test_por_item_consulta_cada_item_uma_vez(self):
        cli = ClienteSimulado()
        cache = {}
        primeira = bf.por_item(cli, bf.CONSULTA_ROTULOS, {"Q2", "Q3"}, cache)
        segunda = bf.por_item(cli, bf.CONSULTA_ROTULOS, {"Q3", "Q5", "Q9"}, cache)
        self.assertEqual(len(cli.consultas), 2)
        self.assertNotIn("wd:Q3", cli.consultas[1])
        self.assertEqual({bf.qid_de(b) for b in primeira}, {"Q2", "Q3"})
        self.assertEqual({bf.qid_de(b) for b in segunda}, {"Q3", "Q5"})   # Q9 não tem rótulo


if __name__ == "__main__":
    unittest.main()
