"""Aquisição de fontes: gravação só do que mudou, preservação da data e recusas.

Nenhum teste acessa a rede: baixar() é substituído por downloads simulados e
urllib.request.urlopen é bloqueado. RAIZ e FONTES apontam para um diretório temporário;
os arquivos reais do projeto nunca são tocados.
"""

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import apoio  # noqa: F401  (coloca scripts/ no caminho de importação)
import baixar_fontes as bf

DATA_1 = "2026-01-01T00:00:00+00:00"
DATA_2 = "2026-02-02T00:00:00+00:00"


def sha(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def fonte(id_fonte="fonte_a", conteudo=b"conteudo v1", uso="produto",
          destino="data/raw/exemplo/a.txt", **extra) -> dict:
    base = {
        "id": id_fonte,
        "descricao": f"Fonte sintética {id_fonte}",
        "url": f"https://exemplo.invalid/{id_fonte}/{sha(conteudo)[:8]}",
        "versao": "v1",
        "licenca": "CC0-1.0",
        "uso": uso,
        "destino": destino,
        "sha256": sha(conteudo),
    }
    base.update(extra)
    return base


class BaseAquisicao(unittest.TestCase):

    def setUp(self):
        temporario = tempfile.TemporaryDirectory(prefix="baixar_")
        self.addCleanup(temporario.cleanup)
        self.raiz = Path(temporario.name)
        self.downloads: dict[str, bytes] = {}
        self.urls_baixadas: list[str] = []
        self.agora = DATA_1

    def executar(self, fontes: list[dict], *args: str) -> tuple[int, str]:
        def baixar_simulado(url: str) -> bytes:
            self.urls_baixadas.append(url)
            return self.downloads[url]

        saida = io.StringIO()
        with contextlib.ExitStack() as pilha:
            pilha.enter_context(mock.patch.object(bf, "RAIZ", self.raiz))
            pilha.enter_context(mock.patch.object(bf, "FONTES", fontes))
            pilha.enter_context(mock.patch.object(bf, "baixar", baixar_simulado))
            pilha.enter_context(mock.patch.object(bf, "agora_utc", lambda: self.agora))
            pilha.enter_context(mock.patch.object(
                bf.urllib.request, "urlopen",
                side_effect=AssertionError("acesso à rede nos testes")))
            pilha.enter_context(contextlib.redirect_stdout(saida))
            codigo = bf.main(list(args))
        return codigo, saida.getvalue()

    def disponibilizar(self, f: dict, conteudo: bytes) -> None:
        self.downloads[f["url"]] = conteudo

    def estado(self) -> dict:
        """Bytes e data de modificação de cada arquivo, e o conjunto de pastas."""
        arquivos = {str(p.relative_to(self.raiz)): (p.read_bytes(), p.stat().st_mtime_ns)
                    for p in self.raiz.rglob("*") if p.is_file()}
        pastas = {str(p.relative_to(self.raiz)) for p in self.raiz.rglob("*") if p.is_dir()}
        return {"arquivos": arquivos, "pastas": pastas}

    def registro(self, f: dict) -> dict | None:
        manifesto = (self.raiz / f["destino"]).parent / "PROCEDENCIA.json"
        if not manifesto.exists():
            return None
        return json.loads(manifesto.read_text(encoding="utf-8")).get(f["id"])

    def adquirir(self, f: dict, conteudo: bytes = b"conteudo v1") -> None:
        """Primeira aquisição bem-sucedida, com a data DATA_1."""
        self.disponibilizar(f, conteudo)
        self.assertEqual(self.executar([f])[0], 0)


class TestAquisicao(BaseAquisicao):

    def test_01_primeira_aquisicao_cria_dados_e_registro(self):
        f = fonte()
        self.disponibilizar(f, b"conteudo v1")
        codigo, saida = self.executar([f])
        self.assertEqual(codigo, 0)
        self.assertEqual((self.raiz / f["destino"]).read_bytes(), b"conteudo v1")
        r = self.registro(f)
        self.assertEqual((r["sha256"], r["bytes"], r["adquirido_em_utc"]),
                         (f["sha256"], 11, DATA_1))
        self.assertIn("registro criado", saida)

    def test_02_conteudo_identico_nao_regrava_nada(self):
        f = fonte()
        self.adquirir(f)
        antes = self.estado()
        self.agora = DATA_2
        codigo, saida = self.executar([f])
        self.assertEqual(codigo, 0)
        self.assertEqual(self.estado(), antes)  # bytes e datas de modificação idênticos
        self.assertEqual(self.registro(f)["adquirido_em_utc"], DATA_1)
        self.assertIn("inalterado", saida)

    def test_03_so_metadados_mudaram_preserva_data_e_dados(self):
        f = fonte()
        self.adquirir(f)
        dados_antes = self.estado()["arquivos"][str(Path(f["destino"]))]
        self.agora = DATA_2
        f2 = dict(f, descricao="Descrição corrigida", licenca="CC0-1.0 (domínio público)")
        codigo, saida = self.executar([f2])
        self.assertEqual(codigo, 0)
        r = self.registro(f2)
        self.assertEqual((r["descricao"], r["licenca"], r["adquirido_em_utc"]),
                         ("Descrição corrigida", "CC0-1.0 (domínio público)", DATA_1))
        self.assertEqual(self.estado()["arquivos"][str(Path(f["destino"]))], dados_antes)
        self.assertIn("metadados atualizados", saida)

    def test_04_nova_versao_validada_atualiza_dados_e_data(self):
        f = fonte()
        self.adquirir(f)
        self.agora = DATA_2
        f2 = fonte(conteudo=b"conteudo v2", versao="v2")
        self.disponibilizar(f2, b"conteudo v2")
        codigo, saida = self.executar([f2])
        self.assertEqual(codigo, 0)
        self.assertEqual((self.raiz / f2["destino"]).read_bytes(), b"conteudo v2")
        r = self.registro(f2)
        self.assertEqual((r["sha256"], r["versao"], r["adquirido_em_utc"]),
                         (sha(b"conteudo v2"), "v2", DATA_2))
        self.assertIn("nova versão registrada", saida)

    def test_05_hash_divergente_nao_grava(self):
        with self.subTest("sem nada local"):
            f = fonte()
            self.disponibilizar(f, b"conteudo adulterado")
            codigo, saida = self.executar([f])
            self.assertEqual(codigo, 1)
            self.assertIn("[ERRO]", saida)
            self.assertEqual(self.estado()["arquivos"], {})
        with self.subTest("com aquisição anterior"):
            self.adquirir(f)
            antes = self.estado()
            self.disponibilizar(f, b"pagina de erro <html>")
            self.assertEqual(self.executar([f])[0], 1)
            self.assertEqual(self.estado(), antes)
        with self.subTest("arquivo local sem registro e download inválido"):
            g = fonte("fonte_b", destino="data/raw/outra/b.txt")
            (self.raiz / g["destino"]).parent.mkdir(parents=True)
            (self.raiz / g["destino"]).write_bytes(b"conteudo v1")
            self.disponibilizar(g, b"truncado")
            self.assertEqual(self.executar([g])[0], 1)
            self.assertIsNone(self.registro(g))

    def test_06_fonte_sem_hash_e_recusada_antes_do_download(self):
        f = fonte(sha256=None)
        self.disponibilizar(f, b"conteudo v1")
        codigo, saida = self.executar([f])
        self.assertEqual(codigo, 1)
        self.assertIn("[RECUSADA]", saida)
        self.assertEqual(self.urls_baixadas, [])
        self.assertEqual(self.estado(), {"arquivos": {}, "pastas": set()})

    def test_07_dados_ausentes_com_registro_igual_restaura_e_preserva_data(self):
        f = fonte()
        self.adquirir(f)
        manifesto = str(Path(f["destino"]).parent / "PROCEDENCIA.json")
        json_antes = self.estado()["arquivos"][manifesto]
        (self.raiz / f["destino"]).unlink()
        self.agora = DATA_2
        codigo, saida = self.executar([f])
        self.assertEqual(codigo, 0)
        self.assertEqual((self.raiz / f["destino"]).read_bytes(), b"conteudo v1")
        self.assertEqual(self.estado()["arquivos"][manifesto], json_antes)
        self.assertIn("arquivo de dados restaurado", saida)

    def test_08_arquivo_local_sem_registro_cria_registro_apos_validar(self):
        f = fonte()
        destino = self.raiz / f["destino"]
        destino.parent.mkdir(parents=True)
        destino.write_bytes(b"conteudo v1")
        dados_antes = self.estado()["arquivos"][str(Path(f["destino"]))]
        self.agora = DATA_2
        self.disponibilizar(f, b"conteudo v1")
        codigo, saida = self.executar([f])
        self.assertEqual(codigo, 0)
        self.assertEqual(self.urls_baixadas, [f["url"]])  # o download foi validado antes
        self.assertEqual(self.registro(f)["adquirido_em_utc"], DATA_2)
        self.assertEqual(self.estado()["arquivos"][str(Path(f["destino"]))], dados_antes)
        self.assertIn("registro criado", saida)

    def test_09_atualizar_uma_fonte_preserva_as_outras_do_mesmo_registro(self):
        a = fonte("fonte_a", destino="data/raw/comum/a.txt")
        b = fonte("fonte_b", destino="data/raw/comum/b.txt")
        self.disponibilizar(a, b"conteudo v1")
        self.disponibilizar(b, b"conteudo v1")
        self.assertEqual(self.executar([a, b])[0], 0)
        registro_b = self.registro(b)
        self.agora = DATA_2
        self.assertEqual(self.executar([dict(a, descricao="nova"), b])[0], 0)
        self.assertEqual(self.registro(b), registro_b)
        self.assertEqual(self.registro(a)["descricao"], "nova")

    def test_12_auditoria_ignorada_sem_opcao_e_processada_com_ela(self):
        f = fonte("aud", uso="auditoria", destino="data/external/aud/a.csv")
        self.disponibilizar(f, b"conteudo v1")
        codigo, saida = self.executar([f])
        self.assertEqual((codigo, self.urls_baixadas), (0, []))
        self.assertIn("[IGNORADA]", saida)
        self.assertEqual(self.estado()["arquivos"], {})
        codigo, saida = self.executar([f], "--auditoria")
        self.assertEqual(codigo, 0)
        self.assertEqual(self.registro(f)["adquirido_em_utc"], DATA_1)

    def test_13_data_anterior_invalida_nao_e_preservada(self):
        # Mesmo SHA-256, mas a data registrada não é texto ISO 8601 com fuso UTC: a data
        # original é desconhecida, então a atual é gravada e o status diz isso.
        corrigido = "registro corrigido: data de aquisição anterior ausente ou inválida"
        casos = {
            "ausente": (None, corrigido),
            "vazia": ("", corrigido),
            "texto": ("ontem", corrigido),
            "impossível": ("2026-13-45T00:00:00+00:00", corrigido),
            "sem fuso": ("2026-10-18T00:27:41", corrigido),
            "fuso não UTC": ("2026-10-18T00:27:41-03:00", corrigido),
            "número": (12345, corrigido),
            "registro não objeto": ("x", "registro anterior inválido substituído"),
        }
        self.agora = DATA_2
        for i, (nome, (valor, status)) in enumerate(casos.items()):
            with self.subTest(nome):
                f = fonte(f"fonte_{i}", destino=f"data/raw/caso_{i}/a.txt")
                destino = self.raiz / f["destino"]
                destino.parent.mkdir(parents=True)
                destino.write_bytes(b"conteudo v1")
                if nome == "registro não objeto":
                    anterior = valor
                else:
                    anterior = {"arquivo": "a.txt", "descricao": f["descricao"], "url": f["url"],
                                "versao": f["versao"], "licenca": f["licenca"],
                                "sha256": f["sha256"], "bytes": 11}
                    if nome != "ausente":
                        anterior["adquirido_em_utc"] = valor
                (destino.parent / "PROCEDENCIA.json").write_text(
                    json.dumps({f["id"]: anterior}), encoding="utf-8")
                dados_antes = self.estado()["arquivos"][str(Path(f["destino"]))]
                self.disponibilizar(f, b"conteudo v1")

                codigo, saida = self.executar([f])

                self.assertEqual(codigo, 0)
                self.assertIn(status, saida)
                self.assertNotIn("data de aquisição preservada", saida)
                r = self.registro(f)
                self.assertEqual((r["sha256"], r["bytes"], r["adquirido_em_utc"]),
                                 (f["sha256"], 11, DATA_2))
                self.assertEqual(self.estado()["arquivos"][str(Path(f["destino"]))], dados_antes)


class TestVerificar(BaseAquisicao):

    def test_10_verificar_e_somente_leitura_em_todos_os_cenarios(self):
        ok = fonte("ok", destino="data/raw/ok/a.txt")
        errado = fonte("errado", destino="data/raw/errado/a.txt")
        self.adquirir(ok)
        self.adquirir(errado)
        (self.raiz / errado["destino"]).write_bytes(b"corrompido")
        ausente = fonte("ausente", destino="data/raw/nao_existe/a.txt")
        opcional = fonte("opcional", uso="auditoria", destino="data/external/nao_existe/a.csv")
        antes = self.estado()
        self.agora = DATA_2
        casos = [([ok], 0, "verificado"), ([errado], 1, "[ERRO]"),
                 ([ausente], 1, "[AUSENTE]"), ([opcional], 0, "AUSENTE, opcional")]
        for fontes, codigo_esperado, trecho in casos:
            with self.subTest(fontes[0]["id"]):
                codigo, saida = self.executar(fontes, "--verificar")
                self.assertEqual(codigo, codigo_esperado)
                self.assertIn(trecho, saida)
        self.assertEqual(self.urls_baixadas, [ok["url"], errado["url"]])  # só nas aquisições
        self.assertEqual(self.estado(), antes)  # nada gravado nem criado, inclusive pastas

    def test_11_verificar_recusa_fonte_sem_hash(self):
        f = fonte()
        self.adquirir(f)
        antes = self.estado()
        codigo, saida = self.executar([dict(f, sha256=None)], "--verificar")
        self.assertEqual(codigo, 1)
        self.assertIn("[RECUSADA]", saida)
        self.assertEqual(self.estado(), antes)


if __name__ == "__main__":
    unittest.main()
