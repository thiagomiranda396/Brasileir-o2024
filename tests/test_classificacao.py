"""Classificação recalculada: regras com dados sintéticos e regressão com a tabela oficial.

Os valores esperados reproduzem a classificação final publicada pela CBF e conferida em
2026-10-18 (docs/qualidade/auditoria_fase2.md, seção B1).
"""

import unittest

from apoio import partidas_reais, validador

# clube: (posição, Pts, J, V, E, D, GP, GC)
OFICIAL_CBF = {
    "BOT": (1, 79, 38, 23, 10, 5, 59, 29), "PAL": (2, 73, 38, 22, 7, 9, 60, 33),
    "FLA": (3, 70, 38, 20, 10, 8, 61, 42), "FOR": (4, 68, 38, 19, 11, 8, 53, 39),
    "INT": (5, 65, 38, 18, 11, 9, 53, 36), "SPA": (6, 59, 38, 17, 8, 13, 53, 43),
    "COR": (7, 56, 38, 15, 11, 12, 54, 45), "BAH": (8, 53, 38, 15, 8, 15, 49, 49),
    "CRU": (9, 52, 38, 14, 10, 14, 43, 41), "VAS": (10, 50, 38, 14, 8, 16, 43, 56),
    "VIT": (11, 47, 38, 13, 8, 17, 45, 52), "ATM": (12, 47, 38, 11, 14, 13, 47, 54),
    "FLU": (13, 46, 38, 12, 10, 16, 33, 39), "GRE": (14, 45, 38, 12, 9, 17, 44, 50),
    "JUV": (15, 45, 38, 11, 12, 15, 48, 59), "RBB": (16, 44, 38, 10, 14, 14, 44, 48),
    "ATP": (17, 42, 38, 11, 9, 18, 40, 46), "CRI": (18, 38, 38, 9, 11, 18, 42, 61),
    "ATG": (19, 30, 38, 7, 9, 22, 29, 58), "CUI": (20, 30, 38, 6, 12, 20, 29, 49),
}


def jogo(m, v, gm, gv):
    return {"id_mandante": m, "id_visitante": v, "gols_mandante": str(gm),
            "gols_visitante": str(gv)}


class TestRegras(unittest.TestCase):

    def test_pontuacao_3_1_0(self):
        t = {s["clube"]: s for s in validador.calcular_classificacao(
            [jogo("AAA", "BBB", 2, 0), jogo("BBB", "CCC", 1, 1)])}
        self.assertEqual((t["AAA"]["Pts"], t["BBB"]["Pts"], t["CCC"]["Pts"]), (3, 1, 1))

    def test_desempate_por_vitorias_antes_do_saldo(self):
        # AAA e BBB com 4 pontos; AAA tem 1 vitória e saldo menor, BBB tem 4 empates.
        partidas = [jogo("AAA", "CCC", 1, 0), jogo("AAA", "DDD", 0, 3), jogo("EEE", "AAA", 0, 0),
                    jogo("BBB", "CCC", 5, 5), jogo("BBB", "DDD", 5, 5), jogo("BBB", "EEE", 5, 5),
                    jogo("FFF", "BBB", 5, 5)]
        ordem = [s["clube"] for s in validador.calcular_classificacao(partidas)]
        self.assertLess(ordem.index("AAA"), ordem.index("BBB"))

    def test_empate_nos_criterios_1_a_3_e_sinalizado(self):
        tabela = validador.calcular_classificacao([jogo("AAA", "BBB", 1, 1)])
        self.assertEqual(validador.empates_nao_resolvidos(tabela), [["AAA", "BBB"]])


class TestRegressaoOficial(unittest.TestCase):

    def test_classificacao_final_igual_a_cbf(self):
        tabela = validador.calcular_classificacao(partidas_reais())
        obtido = {s["clube"]: (s["pos"], s["Pts"], s["J"], s["V"], s["E"], s["D"],
                               s["GP"], s["GC"]) for s in tabela}
        self.assertEqual(obtido, OFICIAL_CBF)

    def test_nenhum_empate_depende_dos_criterios_4_a_7(self):
        tabela = validador.calcular_classificacao(partidas_reais())
        self.assertEqual(validador.empates_nao_resolvidos(tabela), [])

    def test_total_de_gols_consistente(self):
        tabela = validador.calcular_classificacao(partidas_reais())
        self.assertEqual(sum(s["GP"] for s in tabela), 929)
        self.assertEqual(sum(s["GC"] for s in tabela), 929)


if __name__ == "__main__":
    unittest.main()
