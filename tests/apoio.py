"""Utilitários compartilhados pelos testes: caminhos e importação dos scripts."""

import copy
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import converter_openfootball as conversor  # noqa: E402
import validar_dados as validador  # noqa: E402

AUSENTES_AUDITORIA = validador.auditoria_ausente()
ADAODUQUE_DISPONIVEL = not AUSENTES_AUDITORIA
MOTIVO_SEM_ADAODUQUE = ("auditoria local indisponível (fora do Git); ausentes: "
                        + ", ".join(AUSENTES_AUDITORIA))


def partidas_reais() -> list[dict]:
    return validador.ler_csv(validador.PARTIDAS)


def ids_clubes() -> set[str]:
    return {c["id_clube"] for c in validador.ler_csv(validador.CLUBES)}


def mapa_adaoduque() -> dict:
    return validador.carregar_mapa_adaoduque()


def reprovados(partidas: list[dict]) -> set[str]:
    """Nomes dos testes de integridade que falham para a lista de partidas."""
    return {nome for nome, ok, _ in validador.testes_integridade(partidas, ids_clubes()) if not ok}


def copia(partidas: list[dict]) -> list[dict]:
    return copy.deepcopy(partidas)
