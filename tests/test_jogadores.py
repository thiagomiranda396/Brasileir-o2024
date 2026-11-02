"""Testes dos dados derivados de jogadores (gols, cartões, jogadores, complemento das partidas).

Os testes sobre os CSVs versionados rodam sempre. A regeneração a partir da fonte externa só
roda se os arquivos de data/external/ existirem (fora do Git).
"""

import csv
import unittest
from collections import Counter

from apoio import RAIZ, partidas_reais

import preparar_jogadores as pj

PROCESSADOS = RAIZ / "data/processed"
WIKI = RAIZ / "data/reference/wikipedia_en"
EXTERNOS_DISPONIVEIS = all(c.exists() for c in (pj.ADA_PARTIDAS, pj.ADA_GOLS, pj.ADA_CARTOES,
                                                 pj.MAPA_CLUBES))


def ler(caminho):
    with caminho.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class TestGols(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gols = ler(PROCESSADOS / "gols.csv")
        cls.partidas = {int(p["id_partida"]): p for p in partidas_reais()}
        cls.jogadores = {j["id_jogador"]: j for j in ler(PROCESSADOS / "jogadores.csv")}

    def test_total_de_gols_igual_ao_do_campeonato(self):
        self.assertEqual(len(self.gols), 929)

    def test_gols_por_clube_e_partida_batem_com_o_placar(self):
        contagem = Counter((int(g["id_partida"]), g["id_clube_beneficiado"]) for g in self.gols)
        for pid, p in self.partidas.items():
            self.assertEqual(contagem[(pid, p["id_mandante"])], int(p["gols_mandante"]), pid)
            self.assertEqual(contagem[(pid, p["id_visitante"])], int(p["gols_visitante"]), pid)

    def test_gol_contra_e_creditado_ao_adversario(self):
        for g in self.gols:
            p = self.partidas[int(g["id_partida"])]
            self.assertIn(g["id_clube_beneficiado"], (p["id_mandante"], p["id_visitante"]))
            mesmo = g["id_clube_jogador"] == g["id_clube_beneficiado"]
            self.assertEqual(mesmo, g["tipo"] != "Contra", g)

    def test_rodada_e_jogador_consistentes(self):
        for g in self.gols:
            self.assertEqual(g["rodada"], self.partidas[int(g["id_partida"])]["rodada"])
            self.assertEqual(self.jogadores[g["id_jogador"]]["id_clube"], g["id_clube_jogador"])

    def test_artilharia_igual_a_da_wikipedia(self):
        artilharia = Counter(g["id_jogador"] for g in self.gols if g["tipo"] != "Contra")
        exibicao = {(j["nome_exibicao"], j["id_clube"]): jid for jid, j in self.jogadores.items()}
        exibicao[("José Manuel López", "PAL")] = exibicao[("Flaco López", "PAL")]  # apelido
        referencia = ler(WIKI / "artilheiros.csv")
        for r in referencia:
            jid = exibicao[(r["jogador"], r["id_clube"])]
            self.assertEqual(artilharia[jid], int(r["gols"]), r["jogador"])
        # Ninguém fora da lista tem mais gols que o último colocado dela.
        minimo = min(int(r["gols"]) for r in referencia)
        listados = {exibicao[(r["jogador"], r["id_clube"])] for r in referencia}
        for jid, n in artilharia.items():
            if jid not in listados:
                self.assertLess(n, minimo, jid)

    def test_placar_do_intervalo_diverge_so_nos_casos_documentados(self):
        """O período do gol vem do minuto; 2 partidas divergem do 1º tempo do openfootball."""
        primeiro_tempo = Counter((int(g["id_partida"]), g["id_clube_beneficiado"])
                                 for g in self.gols if g["periodo"] == "1T")
        divergentes = set()
        for pid, p in self.partidas.items():
            if p["gols_mandante_1t"] == "":
                continue
            if (primeiro_tempo[(pid, p["id_mandante"])] != int(p["gols_mandante_1t"])
                    or primeiro_tempo[(pid, p["id_visitante"])] != int(p["gols_visitante_1t"])):
                divergentes.add(pid)
        self.assertEqual(divergentes, {201, 203})


class TestCartoesEComplemento(unittest.TestCase):
    def test_cartoes(self):
        cartoes = ler(PROCESSADOS / "cartoes.csv")
        self.assertEqual(Counter(c["cartao"] for c in cartoes),
                         Counter({"Amarelo": 1968, "Vermelho": 128}))
        partidas = {int(p["id_partida"]): p for p in partidas_reais()}
        for c in cartoes:
            p = partidas[int(c["id_partida"])]
            self.assertIn(c["id_clube"], (p["id_mandante"], p["id_visitante"]))

    def test_complemento_cobre_as_380_partidas(self):
        complemento = ler(PROCESSADOS / "partidas_complemento.csv")
        self.assertEqual([int(c["id_partida"]) for c in complemento], list(range(1, 381)))
        self.assertTrue(all(c["estadio"] and c["estadio"] == c["estadio"].strip()
                            for c in complemento))

    def test_ids_de_jogador_unicos(self):
        jogadores = ler(PROCESSADOS / "jogadores.csv")
        ids = [j["id_jogador"] for j in jogadores]
        self.assertEqual(len(ids), len(set(ids)))

    def test_jogadores_da_wikipedia_tem_correspondencia(self):
        """A carga SQL liga as listas da Wikipédia aos jogadores por (nome de exibição, clube)."""
        exibicao = {(j["nome_exibicao"], j["id_clube"]) for j in ler(PROCESSADOS / "jogadores.csv")}
        for nome in ("assistencias", "jogos_sem_sofrer_gols", "selecao_do_campeonato",
                     "premios_mensais"):
            for r in ler(WIKI / f"{nome}.csv"):
                self.assertIn((r["jogador"], r["id_clube"]), exibicao, nome)

    def test_minutos(self):
        self.assertEqual(pj.separar_minuto("45+4"), (45, 4, "1T"))
        self.assertEqual(pj.separar_minuto("45"), (45, 0, "1T"))
        self.assertEqual(pj.separar_minuto("46"), (46, 0, "2T"))
        self.assertEqual(pj.separar_minuto("90+13"), (90, 13, "2T"))
        for invalido in ("", "0", "91", "45+", "x"):
            with self.assertRaises(ValueError):
                pj.separar_minuto(invalido)


@unittest.skipUnless(EXTERNOS_DISPONIVEIS, "fonte externa ausente (fora do Git)")
class TestRegeneracao(unittest.TestCase):
    def test_regenerar_reproduz_os_csvs_versionados(self):
        dados = pj.preparar()
        for chave, nome, colunas in (("gols", "gols.csv", pj.COLUNAS_GOLS),
                                     ("cartoes", "cartoes.csv", pj.COLUNAS_CARTOES),
                                     ("jogadores", "jogadores.csv", pj.COLUNAS_JOGADORES),
                                     ("complemento", "partidas_complemento.csv",
                                      pj.COLUNAS_COMPLEMENTO)):
            gerado = [{k: str(v) for k, v in linha.items()} for linha in dados[chave]]
            versionado = ler(PROCESSADOS / nome)
            self.assertEqual([{k: g[k] for k in colunas} for g in gerado], versionado, nome)


if __name__ == "__main__":
    unittest.main()
