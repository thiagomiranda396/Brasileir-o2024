"""Interpretação do formato Football.TXT com entradas sintéticas."""

import unittest

from apoio import conversor

MAPA = {"Time A": "AAA", "Time B": "BBB", "Time C": "CCC", "Time D": "DDD"}


def converter(texto: str) -> list[dict]:
    return conversor.converter_linhas(texto.splitlines(), MAPA)


class TestConversor(unittest.TestCase):

    def test_jogo_completo_com_intervalo(self):
        p = converter("▪ Matchday 1\n  Sat Apr 13 2024\n"
                      "    18:30  Time A  v Time B  2-1 (0-0)\n")
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["data"], "2024-04-13")
        self.assertEqual((p[0]["id_mandante"], p[0]["id_visitante"]), ("AAA", "BBB"))
        self.assertEqual((p[0]["gols_mandante"], p[0]["gols_visitante"]), (2, 1))
        self.assertEqual((p[0]["gols_mandante_1t"], p[0]["gols_visitante_1t"]), (0, 0))

    def test_zero_a_zero_sem_intervalo_fica_vazio(self):
        p = converter("▪ Matchday 1\n  Sat Apr 13 2024\n    16:00  Time A  v Time B  0-0\n")
        self.assertEqual((p[0]["gols_mandante_1t"], p[0]["gols_visitante_1t"]), ("", ""))

    def test_horario_herdado_e_marcado(self):
        p = converter("▪ Matchday 1\n  Sat Apr 13 2024\n"
                      "    18:30  Time A  v Time B  1-0 (1-0)\n"
                      "           Time C  v Time D  0-0\n")
        self.assertEqual([x["hora"] for x in p], ["18:30", "18:30"])
        self.assertEqual([x["hora_explicita"] for x in p], [1, 0])

    def test_nova_data_nao_herda_horario(self):
        p = converter("▪ Matchday 1\n  Sat Apr 13 2024\n"
                      "    18:30  Time A  v Time B  1-0 (1-0)\n"
                      "  Sun Apr 14\n"
                      "           Time C  v Time D  0-0\n")
        self.assertEqual((p[1]["hora"], p[1]["hora_explicita"]), ("", 0))

    def test_data_sem_ano_herda_ano_anterior(self):
        p = converter("▪ Matchday 1\n  Sat Apr 13 2024\n  Sun Apr 14\n"
                      "    16:00  Time A  v Time B  1-1 (0-0)\n")
        self.assertEqual(p[0]["data"], "2024-04-14")

    def test_jogo_adiado_mantem_rodada_original(self):
        p = converter("▪ Matchday 7\n  Sat Jun 1 2024\n    16:00  Time A  v Time B  1-0 (0-0)\n"
                      "▪ Matchday 8\n  Sat Jun 8\n    16:00  Time A  v Time C  1-0 (0-0)\n"
                      "▪ Matchday 7\n  Wed Jul 10\n    19:00  Time C  v Time D  2-2 (1-1)\n")
        self.assertEqual([(x["rodada"], x["data"]) for x in p],
                         [(7, "2024-06-01"), (8, "2024-06-08"), (7, "2024-07-10")])

    def test_linha_origem_aponta_arquivo_bruto(self):
        p = converter("= Titulo\n\n▪ Matchday 1\n  Sat Apr 13 2024\n"
                      "    16:00  Time A  v Time B  1-0 (0-0)\n")
        self.assertEqual(p[0]["linha_origem"], 5)

    def test_dia_da_semana_incoerente_falha(self):
        with self.assertRaisesRegex(ValueError, "não confere"):
            converter("▪ Matchday 1\n  Sun Apr 13 2024\n    16:00  Time A  v Time B  1-0\n")

    def test_clube_sem_mapeamento_falha(self):
        with self.assertRaisesRegex(ValueError, "sem mapeamento"):
            converter("▪ Matchday 1\n  Sat Apr 13 2024\n    16:00  Time X  v Time B  1-0\n")

    def test_linha_desconhecida_falha(self):
        with self.assertRaisesRegex(ValueError, "não reconhecido"):
            converter("▪ Matchday 1\n  Sat Apr 13 2024\n    jogo cancelado\n")

    def test_jogo_antes_de_rodada_falha(self):
        with self.assertRaisesRegex(ValueError, "antes de rodada"):
            converter("  Sat Apr 13 2024\n    16:00  Time A  v Time B  1-0\n")


class TestArquivoReal(unittest.TestCase):

    def test_conversao_do_arquivo_fixado(self):
        p = conversor.converter()
        self.assertEqual(len(p), 380)
        self.assertEqual(sum(x["hora_explicita"] for x in p), 230)


if __name__ == "__main__":
    unittest.main()
