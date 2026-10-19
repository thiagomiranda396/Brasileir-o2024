"""Baixa as fontes de dados em versões fixadas e registra a procedência.

Cada fonte aponta para um commit Git ou revisão da Wikipédia imutável. O hash
SHA-256 esperado de cada arquivo fica registrado abaixo; se o conteúdo baixado
divergir, o script falha em vez de sobrescrever silenciosamente os dados.

Fontes de "produto" alimentam o modelo analítico. Fontes de "auditoria" (sem licença de
redistribuição) servem só para conferência local, ficam em data/external/ (fora do Git)
e só são baixadas com --auditoria.

Uso (a partir da raiz do projeto):
    python -I scripts/baixar_fontes.py                # baixa as fontes de produto
    python -I scripts/baixar_fontes.py --auditoria    # inclui as fontes de auditoria local
    python -I scripts/baixar_fontes.py --verificar    # só confere os arquivos locais
"""

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
USER_AGENT = "Brasileirao2024-BI/1.0 (projeto educacional de portfolio)"

OPENFOOTBALL_COMMIT = "119fa1724b2079a1072a0cb0ca0ccac26d92fd34"
ADAODUQUE_COMMIT = "15f027c3be337bb130d6ae94436b5cdca737377c"
WIKIPEDIA_REVID = 70400733

FONTES = [
    {
        "id": "openfootball_2024_br1",
        "descricao": "Partidas da Série A 2024 (Football.TXT)",
        "url": "https://raw.githubusercontent.com/openfootball/south-america/"
               f"{OPENFOOTBALL_COMMIT}/brazil/2024_br1.txt",
        "versao": f"commit {OPENFOOTBALL_COMMIT}",
        "licenca": "CC0-1.0 (domínio público)",
        "uso": "produto",
        "destino": "data/raw/openfootball/2024_br1.txt",
        "sha256": "9c39f868c78e85e53758482a2138d986b412606af541cc65cba88af211c1860d",
    },
    {
        "id": "wikipedia_tabela_2024",
        "descricao": "Predefinição da classificação final (wikitexto)",
        "url": "https://pt.wikipedia.org/w/index.php?"
               f"oldid={WIKIPEDIA_REVID}&action=raw",
        "versao": f"revisão {WIKIPEDIA_REVID} (2025-07-04T21:12:49Z)",
        "licenca": "CC BY-SA 4.0 (atribuição obrigatória)",
        "uso": "produto",
        "destino": "data/raw/wikipedia/tabela_serie_a_2024.wikitext",
        "sha256": "96cf6c51a5f3a28ad1dbf9d12d3a67d7cae0338d804962b7da8a240f9ae9fd8d",
    },
    {
        "id": "adaoduque_full",
        "descricao": "Partidas 2003-2024 (validação local, NÃO redistribuir)",
        "url": "https://raw.githubusercontent.com/adaoduque/Brasileirao_Dataset/"
               f"{ADAODUQUE_COMMIT}/campeonato-brasileiro-full.csv",
        "versao": f"commit {ADAODUQUE_COMMIT}",
        "licenca": "Não declarada (todos os direitos reservados)",
        "uso": "auditoria",
        "destino": "data/external/adaoduque/campeonato-brasileiro-full.csv",
        "sha256": "c09d03d36debfd7d7aee71da9a9f0909b5e420fc80a1705f215efc93c76e83fc",
    },
]


def sha256(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def baixar(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def registrar_procedencia(fonte: dict, hash_obtido: str, tamanho: int) -> None:
    """Grava o registro de procedência ao lado do arquivo baixado."""
    destino = RAIZ / fonte["destino"]
    manifesto = destino.parent / "PROCEDENCIA.json"
    registros = json.loads(manifesto.read_text(encoding="utf-8")) if manifesto.exists() else {}
    registros[fonte["id"]] = {
        "arquivo": destino.name,
        "descricao": fonte["descricao"],
        "url": fonte["url"],
        "versao": fonte["versao"],
        "licenca": fonte["licenca"],
        "sha256": hash_obtido,
        "bytes": tamanho,
        "adquirido_em_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    manifesto.write_text(json.dumps(registros, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--auditoria", action="store_true",
                        help="também baixa as fontes de auditoria local (data/external/)")
    parser.add_argument("--verificar", action="store_true",
                        help="não baixa; apenas confere o hash dos arquivos locais")
    args = parser.parse_args()

    falhas = 0
    for fonte in FONTES:
        destino = RAIZ / fonte["destino"]
        if args.verificar:
            if not destino.exists():
                if fonte["uso"] == "auditoria":
                    print(f"[AUSENTE, opcional] {fonte['id']}: fonte de auditoria local")
                    continue
                print(f"[AUSENTE] {fonte['id']}: {fonte['destino']}")
                falhas += 1
                continue
            conteudo = destino.read_bytes()
        elif fonte["uso"] == "auditoria" and not args.auditoria:
            print(f"[IGNORADA] {fonte['id']}: fonte de auditoria; use --auditoria")
            continue
        else:
            conteudo = baixar(fonte["url"])

        obtido = sha256(conteudo)
        esperado = fonte["sha256"]
        if esperado and obtido != esperado:
            print(f"[ERRO] {fonte['id']}: hash {obtido} difere do esperado {esperado}")
            falhas += 1
            continue

        if not args.verificar:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(conteudo)
            registrar_procedencia(fonte, obtido, len(conteudo))

        status = "OK" if esperado else "SEM HASH ESPERADO"
        print(f"[{status}] {fonte['id']}: {len(conteudo)} bytes, sha256={obtido}")

    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
