"""Baixa as fontes de dados em versões fixadas e registra a procedência.

Cada fonte aponta para um commit Git ou revisão da Wikipédia imutável. O hash
SHA-256 esperado de cada arquivo fica registrado abaixo; se o conteúdo baixado
divergir, o script falha em vez de sobrescrever silenciosamente os dados. Fontes
sem hash esperado são recusadas antes de qualquer download ou verificação.

Gravação: o arquivo de dados só é gravado se o conteúdo validado for diferente do
arquivo local, e o PROCEDENCIA.json só é gravado se o registro da fonte mudar.
O campo adquirido_em_utc é o momento da primeira obtenção e validação
bem-sucedida daquela versão do conteúdo (identificada pelo SHA-256): ele é
preservado em novos downloads idênticos, mesmo que metadados descritivos mudem,
e só recebe a data atual quando uma nova versão é validada, quando não há
registro anterior ou quando a data registrada é ausente ou inválida (não é texto
ISO 8601 com fuso UTC); nesses casos a data original não é conhecida.

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


def agora_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def data_aquisicao_valida(valor) -> bool:
    """Texto ISO 8601 com fuso UTC (deslocamento zero), como o gerado por agora_utc()."""
    if not isinstance(valor, str):
        return False
    try:
        data = datetime.fromisoformat(valor)
    except ValueError:
        return False
    return data.utcoffset() is not None and data.utcoffset().total_seconds() == 0


def registro_esperado(fonte: dict, hash_obtido: str, tamanho: int,
                      anterior: dict | None) -> dict:
    """Registro de procedência para o conteúdo validado.

    A data de aquisição do registro anterior só é mantida se ele for um objeto, se referir à
    mesma versão do conteúdo (mesmo SHA-256) e contiver uma data válida; caso contrário, recebe
    a data atual (versão nova, ou data anterior ausente ou inválida e, portanto, desconhecida).
    """
    mesma_versao = (isinstance(anterior, dict) and anterior.get("sha256") == hash_obtido
                    and data_aquisicao_valida(anterior.get("adquirido_em_utc")))
    return {
        "arquivo": Path(fonte["destino"]).name,
        "descricao": fonte["descricao"],
        "url": fonte["url"],
        "versao": fonte["versao"],
        "licenca": fonte["licenca"],
        "sha256": hash_obtido,
        "bytes": tamanho,
        "adquirido_em_utc": anterior["adquirido_em_utc"] if mesma_versao else agora_utc(),
    }


def gravar_se_necessario(fonte: dict, conteudo: bytes, hash_obtido: str) -> str:
    """Grava dados e registro de uma fonte já validada, só no que mudou; devolve o status."""
    destino = RAIZ / fonte["destino"]
    dados_iguais = destino.exists() and sha256(destino.read_bytes()) == hash_obtido
    if not dados_iguais:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)

    manifesto = destino.parent / "PROCEDENCIA.json"
    registros = json.loads(manifesto.read_text(encoding="utf-8")) if manifesto.exists() else {}
    anterior = registros.get(fonte["id"])
    novo = registro_esperado(fonte, hash_obtido, len(conteudo), anterior)
    if novo != anterior:
        registros[fonte["id"]] = novo
        manifesto.write_text(json.dumps(registros, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8", newline="\n")

    if anterior is None:
        return "registro criado (data atual)"
    if not isinstance(anterior, dict):
        return "registro anterior inválido substituído (data atual)"
    if anterior.get("sha256") != hash_obtido:
        return "nova versão registrada (data atual)"
    if novo["adquirido_em_utc"] != anterior.get("adquirido_em_utc"):
        return ("registro corrigido: data de aquisição anterior ausente ou inválida; "
                "data atual registrada")
    if novo != anterior:
        return "metadados atualizados; data de aquisição preservada"
    if not dados_iguais:
        return "arquivo de dados restaurado; registro inalterado"
    return "inalterado; nada foi gravado"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--auditoria", action="store_true",
                        help="também baixa as fontes de auditoria local (data/external/)")
    parser.add_argument("--verificar", action="store_true",
                        help="não baixa nem grava; apenas confere o hash dos arquivos locais")
    args = parser.parse_args(argv)

    falhas = 0
    for fonte in FONTES:
        destino = RAIZ / fonte["destino"]
        if not args.verificar and fonte["uso"] == "auditoria" and not args.auditoria:
            print(f"[IGNORADA] {fonte['id']}: fonte de auditoria; use --auditoria")
            continue

        esperado = fonte.get("sha256")
        if not esperado:
            print(f"[RECUSADA] {fonte['id']}: sem hash SHA-256 esperado; nada foi baixado, "
                  "verificado ou registrado")
            falhas += 1
            continue

        if args.verificar:  # somente leitura: nenhum caminho abaixo grava ou cria pastas
            if not destino.exists():
                if fonte["uso"] == "auditoria":
                    print(f"[AUSENTE, opcional] {fonte['id']}: fonte de auditoria local")
                    continue
                print(f"[AUSENTE] {fonte['id']}: {fonte['destino']}")
                falhas += 1
                continue
            conteudo = destino.read_bytes()
        else:
            conteudo = baixar(fonte["url"])

        obtido = sha256(conteudo)
        if obtido != esperado:
            print(f"[ERRO] {fonte['id']}: hash {obtido} difere do esperado {esperado}; "
                  "nada foi gravado")
            falhas += 1
            continue

        situacao = "verificado" if args.verificar else gravar_se_necessario(fonte, conteudo, obtido)
        print(f"[OK] {fonte['id']}: {len(conteudo)} bytes, sha256={obtido} ({situacao})")

    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
