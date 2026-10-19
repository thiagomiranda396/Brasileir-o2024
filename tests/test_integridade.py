"""Testes de integridade: o CSV real passa e erros injetados são detectados.

Cada caso altera uma cópia em memória de data/processed/partidas.csv; o arquivo
nunca é modificado.
"""

import unittest

from apoio import copia, partidas_reais, reprovados


class TestIntegridade(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.partidas = partidas_reais()

    def assertDetecta(self, partidas, teste_esperado):
        falhas = reprovados(partidas)
        self.assertIn(teste_esperado, falhas, f"falhas obtidas: {sorted(falhas)}")

    def test_csv_real_aprovado(self):
        self.assertEqual(reprovados(self.partidas), set())

    def test_partida_duplicada(self):
        p = copia(self.partidas)
        p.append(dict(p[0], id_partida="381"))
        self.assertDetecta(p, "380 partidas")
        self.assertDetecta(p, "cada confronto mandante×visitante ocorre uma única vez "
                              "(turno e returno)")

    def test_id_partida_repetido(self):
        p = copia(self.partidas)
        p[1]["id_partida"] = p[0]["id_partida"]
        self.assertDetecta(p, "id_partida único")

    def test_partida_ausente(self):
        p = copia(self.partidas)[:-1]
        self.assertDetecta(p, "380 partidas")
        self.assertDetecta(p, "rodadas 1 a 38 com 10 jogos cada")

    def test_clube_contra_si_mesmo(self):
        p = copia(self.partidas)
        p[5]["id_visitante"] = p[5]["id_mandante"]
        self.assertDetecta(p, "mandante diferente do visitante")

    def test_clube_fora_do_cadastro(self):
        p = copia(self.partidas)
        p[3]["id_mandante"] = "XXX"
        self.assertDetecta(p, "20 clubes, todos no cadastro")

    def test_rodada_trocada(self):
        p = copia(self.partidas)
        p[0]["rodada"] = "2"
        self.assertDetecta(p, "cada clube joga exatamente uma vez por rodada")

    def test_data_fora_da_temporada(self):
        p = copia(self.partidas)
        p[7]["data"] = "2025-01-10"
        self.assertDetecta(p, "datas entre 13/04/2024 e 08/12/2024")

    def test_horario_vazio(self):
        p = copia(self.partidas)
        p[4]["hora"] = ""
        self.assertDetecta(p, "horário preenchido (HH:MM)")

    def test_hora_explicita_invalida(self):
        p = copia(self.partidas)
        p[4]["hora_explicita"] = "talvez"
        self.assertDetecta(p, "hora_explicita é 0 ou 1")

    def test_placar_negativo(self):
        p = copia(self.partidas)
        p[2]["gols_visitante"] = "-1"
        self.assertDetecta(p, "placar final preenchido e não negativo")

    def test_intervalo_maior_que_final(self):
        p = copia(self.partidas)
        p[0]["gols_mandante_1t"] = "9"
        self.assertDetecta(p, "gols do intervalo ≤ gols finais")

    def test_intervalo_ausente_em_jogo_com_gols(self):
        p = copia(self.partidas)
        com_gols = next(x for x in p if x["gols_mandante"] != "0")
        com_gols["gols_mandante_1t"] = com_gols["gols_visitante_1t"] = ""
        self.assertDetecta(p, "placar do intervalo ausente somente em jogos 0-0")


if __name__ == "__main__":
    unittest.main()
