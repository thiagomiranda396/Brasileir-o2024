"""Regravação do relatório de validação: só quando o conteúdo relevante muda.

Os testes de integração executam validar_dados.main() gravando o relatório num diretório
temporário; o relatório versionado em docs/qualidade/ nunca é tocado.
"""

import contextlib
import csv
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from apoio import ADAODUQUE_DISPONIVEL, MOTIVO_SEM_ADAODUQUE, partidas_reais, validador


def relatorio(data: str, secao1: str = "tudo aprovado", secao2: str | None = "380 em comum",
              secao3: str = "BOT 79") -> str:
    """Relatório sintético no mesmo formato de seções do real."""
    linhas = ["# Relatório", "", f"{validador.PREFIXO_DATA}`x` em {data} (UTC).", "",
              "## 1. Integridade", secao1, "", "## 2. Comparação", ""]
    linhas.append(secao2 if secao2 is not None
                  else f"{validador.MARCA_NAO_EXECUTADA} arquivos ausentes.")
    linhas += ["", "## 3. Classificação", secao3]
    return "\n".join(linhas) + "\n"


class TestDecisaoDeGravacao(unittest.TestCase):

    def decidir(self, atual, novo):
        return validador.decidir_gravacao(atual, novo)

    def test_sem_relatorio_anterior_grava(self):
        self.assertTrue(self.decidir(None, relatorio("t2"))[0])

    def test_so_a_data_mudou_nao_grava(self):
        gravar, motivo = self.decidir(relatorio("t1"), relatorio("t2"))
        self.assertFalse(gravar)
        self.assertIn("inalterado", motivo)

    def test_mudanca_real_na_secao_1_grava(self):
        self.assertTrue(self.decidir(relatorio("t1"), relatorio("t2", secao1="1 reprovado"))[0])

    def test_mudanca_real_na_secao_3_grava(self):
        self.assertTrue(self.decidir(relatorio("t1"), relatorio("t2", secao3="BOT 80"))[0])

    def test_mudanca_real_na_auditoria_grava(self):
        self.assertTrue(self.decidir(relatorio("t1"), relatorio("t2", secao2="379 em comum"))[0])

    def test_auditoria_ausente_preserva_auditoria_anterior_valida(self):
        gravar, motivo = self.decidir(relatorio("t1"), relatorio("t2", secao2=None))
        self.assertFalse(gravar)
        self.assertIn("PRESERVADO", motivo)

    def test_auditoria_ausente_com_resultados_novos_grava_com_aviso(self):
        gravar, motivo = self.decidir(relatorio("t1"),
                                      relatorio("t2", secao2=None, secao3="BOT 80"))
        self.assertTrue(gravar)
        self.assertIn("ATENÇÃO", motivo)

    def test_auditoria_obtida_substitui_nao_executada(self):
        gravar, _ = self.decidir(relatorio("t1", secao2=None), relatorio("t2"))
        self.assertTrue(gravar)

    def test_nao_executada_nas_duas_vezes_e_igual_nao_grava(self):
        self.assertFalse(self.decidir(relatorio("t1", secao2=None),
                                      relatorio("t2", secao2=None))[0])

    def test_relatorio_anterior_sem_secao_2_nao_conta_como_auditoria(self):
        anterior = relatorio("t1").replace("## 2. Comparação", "## X. Outra")
        gravar, motivo = self.decidir(anterior, relatorio("t2", secao2=None))
        self.assertTrue(gravar)
        self.assertNotIn("PRESERVADO", motivo)


class TestExecucaoReal(unittest.TestCase):
    """main() real, com o relatório redirecionado para um diretório temporário."""

    def setUp(self):
        temporario = tempfile.TemporaryDirectory(prefix="relatorio_")
        self.addCleanup(temporario.cleanup)
        self.tmp = Path(temporario.name)
        self.destino = self.tmp / "relatorio.md"
        # main() exibe caminhos relativos a RAIZ; usa-se um ancestral comum ao projeto e ao
        # diretório temporário (os caminhos de dados continuam absolutos e inalterados).
        try:
            self.raiz_comum = Path(os.path.commonpath([validador.RAIZ, self.tmp]))
        except ValueError:
            self.skipTest("projeto e diretório temporário em unidades diferentes")

    def executar(self, **substituicoes) -> str:
        saida = io.StringIO()
        alvos = {"RELATORIO": self.destino, "RAIZ": self.raiz_comum, **substituicoes}
        with contextlib.ExitStack() as pilha:
            for nome, valor in alvos.items():
                pilha.enter_context(mock.patch.object(validador, nome, valor))
            pilha.enter_context(contextlib.redirect_stdout(saida))
            self.assertEqual(validador.main(), 0)
        return saida.getvalue()

    def sem_auditoria(self) -> dict:
        ausente = self.tmp / "nao_existe.csv"
        return {"ARQUIVOS_AUDITORIA": (ausente,), "ADAODUQUE": ausente, "MAPA_ADAODUQUE": ausente}

    def partidas_alteradas(self, campo: str = "gols_mandante", valor: str | None = None) -> Path:
        partidas = partidas_reais()
        partidas[0][campo] = valor if valor is not None else str(int(partidas[0][campo]) + 1)
        caminho = self.tmp / "partidas.csv"
        with caminho.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(partidas[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(partidas)
        return caminho

    def test_execucoes_repetidas_nao_regravam(self):
        self.assertIn("relatório criado", self.executar())
        primeiro = self.destino.read_bytes()
        self.assertIn("inalterado", self.executar())
        self.assertEqual(self.destino.read_bytes(), primeiro)

    def test_mudanca_real_regrava(self):
        self.executar()
        antes = self.destino.read_text(encoding="utf-8")
        self.assertIn("atualizado", self.executar(PARTIDAS=self.partidas_alteradas()))
        self.assertNotEqual(validador.secoes_relevantes(antes)["3"],
                            validador.secoes_relevantes(self.destino.read_text(encoding="utf-8"))["3"])

    def test_sem_auditoria_desde_o_inicio_registra_nao_executada(self):
        self.executar(**self.sem_auditoria())
        self.assertIn(validador.MARCA_NAO_EXECUTADA, self.destino.read_text(encoding="utf-8"))

    @unittest.skipUnless(ADAODUQUE_DISPONIVEL, MOTIVO_SEM_ADAODUQUE)
    def test_sem_auditoria_preserva_auditoria_anterior(self):
        self.executar()
        com_auditoria = self.destino.read_bytes()
        self.assertIn("PRESERVADO", self.executar(**self.sem_auditoria()))
        self.assertEqual(self.destino.read_bytes(), com_auditoria)

    @unittest.skipUnless(ADAODUQUE_DISPONIVEL, MOTIVO_SEM_ADAODUQUE)
    def test_sem_auditoria_com_resultados_novos_avisa_e_regrava(self):
        self.executar()
        saida = self.executar(PARTIDAS=self.partidas_alteradas(), **self.sem_auditoria())
        self.assertIn("ATENÇÃO", saida)
        self.assertIn(validador.MARCA_NAO_EXECUTADA, self.destino.read_text(encoding="utf-8"))

    @unittest.skipUnless(ADAODUQUE_DISPONIVEL, MOTIVO_SEM_ADAODUQUE)
    def test_sem_auditoria_mudanca_que_nao_afeta_classificacao_invalida_auditoria(self):
        # Trocar a data de uma partida não altera as seções 1 e 3, mas a auditoria anterior
        # deixa de corresponder aos dados: o hash dos dados validados no cabeçalho impede a
        # preservação.
        self.executar()
        saida = self.executar(PARTIDAS=self.partidas_alteradas("data", "2024-04-14"),
                              **self.sem_auditoria())
        self.assertIn("ATENÇÃO", saida)
        self.assertIn(validador.MARCA_NAO_EXECUTADA, self.destino.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
