"""Comparação com o dataset adaoduque (apenas auditoria local).

O dataset não tem licença declarada e, assim como o mapa de nomes usado para cruzá-lo, fica
fora do Git (data/external/adaoduque/) e não entra no produto analítico. Se qualquer um dos dois
faltar, os testes de comparação são pulados e os demais continuam executáveis.
"""

import unittest

from apoio import (ADAODUQUE_DISPONIVEL, MOTIVO_SEM_ADAODUQUE, copia, mapa_adaoduque,
                   partidas_reais, validador)


class TestDisponibilidadeAuditoria(unittest.TestCase):
    """Executado sempre: a detecção de ausência deve ser coerente com o disco."""

    def test_ausentes_correspondem_aos_arquivos_que_faltam(self):
        esperados = {str(p.relative_to(validador.RAIZ)).replace("\\", "/")
                     for p in validador.ARQUIVOS_AUDITORIA if not p.exists()}
        self.assertEqual(set(validador.auditoria_ausente()), esperados)

    def test_arquivos_de_auditoria_ficam_em_data_external(self):
        for caminho in validador.ARQUIVOS_AUDITORIA:
            self.assertEqual(caminho.relative_to(validador.RAIZ).parts[:2], ("data", "external"))


@unittest.skipUnless(ADAODUQUE_DISPONIVEL, MOTIVO_SEM_ADAODUQUE)
class TestComparacaoAdaoduque(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.partidas = partidas_reais()
        cls.adaoduque, cls.sem_mapa = validador.carregar_adaoduque(mapa_adaoduque())

    def comparar(self, partidas):
        return validador.comparar_adaoduque(partidas, self.adaoduque)

    def test_todos_os_clubes_mapeados(self):
        self.assertEqual(self.sem_mapa, [])

    def test_mesmas_380_partidas(self):
        r = self.comparar(self.partidas)
        self.assertEqual((r["comuns"], r["so_openfootball"], r["so_adaoduque"]), (380, [], []))

    def test_placar_rodada_e_data_sem_divergencia(self):
        r = self.comparar(self.partidas)
        self.assertEqual((r["placar"], r["rodada"], r["data"]), ([], [], []))

    def test_unica_divergencia_relevante_de_horario_e_a_documentada(self):
        # "18:06" é o valor registrado pela fonte secundária (adaoduque) e é DIVERGENTE:
        # o horário correto é 16:00 (openfootball, confirmado na CBF). Ver
        # docs/qualidade/auditoria_fase2.md, seção D.
        r = self.comparar(self.partidas)
        relevantes = [(chave, a, b) for chave, a, b in r["hora"]
                      if abs(validador.minutos(a) - validador.minutos(b)) > validador.TOLERANCIA_MIN]
        self.assertEqual(relevantes, [(("ATP", "INT"), "16:00", "18:06")])

    def test_horarios_herdados_coincidem(self):
        h = self.comparar(self.partidas)["herdados"]
        self.assertEqual((h["total"], h["ate_tolerancia"]), (150, 150))

    def test_placar_alterado_e_detectado(self):
        p = copia(self.partidas)
        p[10]["gols_visitante"] = str(int(p[10]["gols_visitante"]) + 1)
        self.assertEqual(len(self.comparar(p)["placar"]), 1)

    def test_rodada_alterada_e_detectada(self):
        p = copia(self.partidas)
        p[20]["rodada"] = "7"
        self.assertEqual(len(self.comparar(p)["rodada"]), 1)

    def test_data_alterada_e_detectada(self):
        p = copia(self.partidas)
        p[30]["data"] = "2024-12-31"
        self.assertEqual(len(self.comparar(p)["data"]), 1)


if __name__ == "__main__":
    unittest.main()
