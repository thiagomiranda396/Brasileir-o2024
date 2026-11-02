"""Testes do jogo de técnico do site (web/js/tecnico), executados em Node.

O motor do jogo é JavaScript puro; este teste roda tests/jogo_tecnico.mjs e falha se algum caso
falhar. Sem Node instalado, o teste é pulado.
"""

import shutil
import subprocess
import unittest

from apoio import RAIZ


@unittest.skipIf(shutil.which("node") is None, "Node.js não instalado")
class TestJogoTecnico(unittest.TestCase):
    def test_motor_e_elencos(self):
        resultado = subprocess.run(
            ["node", str(RAIZ / "tests/jogo_tecnico.mjs")],
            capture_output=True, text=True, encoding="utf-8", timeout=180,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)


if __name__ == "__main__":
    unittest.main()
