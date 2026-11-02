"""Testes do JSON do site (web/data/brasileirao2024.json), exportado do PostgreSQL.

Conferem que o arquivo publicado concorda com os CSVs versionados e com a tabela oficial, sem
precisar de banco: se a exportação ficar desatualizada em relação aos dados, estes testes falham.
"""

import csv
import json
import unittest
from collections import Counter

from apoio import RAIZ, partidas_reais
from test_classificacao import OFICIAL_CBF

WEB = RAIZ / "web/data/brasileirao2024.json"


class TestJsonDoSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(WEB.read_text(encoding="utf-8"))

    def test_partidas_iguais_ao_csv(self):
        csv_ = {int(p["id_partida"]): p for p in partidas_reais()}
        self.assertEqual(len(self.d["partidas"]), 380)
        for p in self.d["partidas"]:
            c = csv_[p["id"]]
            self.assertEqual((p["r"], p["data"], p["m"], p["v"], p["gm"], p["gv"]),
                             (int(c["rodada"]), c["data"], c["id_mandante"], c["id_visitante"],
                              int(c["gols_mandante"]), int(c["gols_visitante"])))

    def test_classificacao_final_igual_a_cbf(self):
        final = self.d["classificacao"][37]
        obtido = {c: (pos, pts, j, v, e, d, gp, gc) for c, pos, j, pts, v, e, d, gp, gc in final}
        self.assertEqual(obtido, OFICIAL_CBF)

    def test_classificacao_tem_38_rodadas_com_n_jogos(self):
        self.assertEqual(len(self.d["classificacao"]), 38)
        for n, tabela in enumerate(self.d["classificacao"], start=1):
            self.assertEqual(len(tabela), 20)
            self.assertTrue(all(linha[2] == n for linha in tabela))

    def test_gols_e_cartoes_iguais_aos_csvs(self):
        with (RAIZ / "data/processed/gols.csv").open(encoding="utf-8") as f:
            gols = list(csv.DictReader(f))
        self.assertEqual(len(self.d["gols"]), len(gols))
        self.assertEqual(Counter(g[1] for g in self.d["gols"]), Counter(g["id_jogador"] for g in gols))
        self.assertEqual(len(self.d["cartoes"]), 2096)

    def test_referencias_existem(self):
        jogadores = {j["id"] for j in self.d["jogadores"]}
        clubes = {c["id"] for c in self.d["clubes"]}
        self.assertEqual(len(clubes), 20)
        for g in self.d["gols"]:
            self.assertIn(g[1], jogadores)
            self.assertIn(g[2], clubes)
        for k in self.d["cartoes"]:
            self.assertIn(k[1], jogadores)
        for s in self.d["selecao"]:
            self.assertIn(s["jogador"], jogadores)
        self.assertEqual(len(self.d["selecao"]), 11)
        self.assertEqual(set(self.d["destinos"]), clubes)

    def test_imagens_iguais_aos_csvs_e_com_credito(self):
        def ler(nome):
            with (RAIZ / "data/reference" / nome).open(encoding="utf-8") as f:
                return list(csv.DictReader(f))
        fotos = {l["id_jogador"]: l["url_imagem"] for l in ler("fotos_jogadores.csv")}
        escudos = {l["id_clube"]: l["url_imagem"] for l in ler("escudos_clubes.csv")}
        self.assertEqual({j["id"]: j["foto"] for j in self.d["jogadores"] if j["foto"]}, fotos)
        self.assertEqual({c["id"]: c["escudo"] for c in self.d["clubes"] if c["escudo"]}, escudos)
        creditos = {(c["tipo"], c["id"]) for c in self.d["creditos"]}
        self.assertEqual(creditos, {("Foto", j) for j in fotos} | {("Escudo", c) for c in escudos})
        self.assertEqual(len(self.d["creditos"]), len(fotos) + len(escudos))

    def test_estatisticas_de_jogador_batem_com_os_eventos(self):
        gols = Counter(g[1] for g in self.d["gols"] if g[6] != "Contra")
        for j in self.d["jogadores"]:
            self.assertEqual(j["gols"], gols.get(j["id"], 0), j["id"])


if __name__ == "__main__":
    unittest.main()
