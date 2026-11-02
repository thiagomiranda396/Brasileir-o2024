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
redistribuição) ficam em data/external/ (fora do Git) e só são baixadas com --auditoria. Elas
servem para a conferência local das partidas e para gerar os dados derivados de jogadores
(gols e cartões) com scripts/preparar_jogadores.py; o arquivo bruto nunca é versionado.

Falhas são tratadas por fonte: erros de rede, de leitura local e procedência
inválida fazem só aquela fonte falhar; as demais são processadas, há um resumo
final e o código de saída é 1 se houver qualquer falha. O PROCEDENCIA.json é lido
e validado antes de qualquer gravação; se estiver inválido, nada daquela fonte é
gravado e o arquivo não é reconstruído. Exceções inesperadas interrompem a execução.

Uso (a partir da raiz do projeto):
    python -I scripts/baixar_fontes.py                # baixa as fontes de produto
    python -I scripts/baixar_fontes.py --auditoria    # inclui as fontes de auditoria local
    python -I scripts/baixar_fontes.py --verificar    # só confere os arquivos locais
"""

import argparse
import hashlib
import http.client
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
USER_AGENT = "Brasileirao2024-BI/1.0 (projeto educacional de portfolio)"

# Falhas de rede tratadas por fonte. Lista explícita: nenhum OSError genérico é capturado
# em torno do download (um PermissionError, por exemplo, é inesperado e interrompe).
ERROS_DE_REDE = (urllib.error.URLError, TimeoutError, http.client.HTTPException,
                 ConnectionError, ssl.SSLError)

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
    {
        "id": "adaoduque_gols",
        "descricao": "Gols 2003-2024, um por linha (base dos dados derivados de jogadores; "
                     "NÃO redistribuir)",
        "url": "https://raw.githubusercontent.com/adaoduque/Brasileirao_Dataset/"
               f"{ADAODUQUE_COMMIT}/campeonato-brasileiro-gols.csv",
        "versao": f"commit {ADAODUQUE_COMMIT}",
        "licenca": "Não declarada (todos os direitos reservados)",
        "uso": "auditoria",
        "destino": "data/external/adaoduque/campeonato-brasileiro-gols.csv",
        "sha256": "625262ca9e7301907f94a0ef235b672d803a488d1e9d8833c31e51d4ffbe5664",
    },
    {
        "id": "adaoduque_cartoes",
        "descricao": "Cartões 2003-2024, um por linha (base dos dados derivados de jogadores; "
                     "NÃO redistribuir)",
        "url": "https://raw.githubusercontent.com/adaoduque/Brasileirao_Dataset/"
               f"{ADAODUQUE_COMMIT}/campeonato-brasileiro-cartoes.csv",
        "versao": f"commit {ADAODUQUE_COMMIT}",
        "licenca": "Não declarada (todos os direitos reservados)",
        "uso": "auditoria",
        "destino": "data/external/adaoduque/campeonato-brasileiro-cartoes.csv",
        "sha256": "4376ed95901b25d6c425127bf542b7746e086e1a20116b49d7a5d87949ac95e8",
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


def existe(caminho: Path) -> bool:
    """Como Path.exists(), mas só considera ausente o que o sistema informa como inexistente.

    Path.exists() devolve False para qualquer OSError (por exemplo, acesso negado à pasta), o
    que faria um arquivo inacessível parecer ausente. Aqui, apenas FileNotFoundError significa
    ausência; qualquer outro erro propaga e é tratado como erro de leitura.
    """
    try:
        os.stat(caminho)
    except FileNotFoundError:
        return False
    return True


class ErroProcedencia(Exception):
    """PROCEDENCIA.json inutilizável: JSON inválido, não UTF-8 ou raiz que não é objeto."""


def caminho_procedencia(fonte: dict) -> Path:
    return (RAIZ / fonte["destino"]).parent / "PROCEDENCIA.json"


def ler_procedencia(manifesto: Path) -> dict:
    """Lê e valida o PROCEDENCIA.json; ausente equivale a {}. Erros de leitura (OSError)
    propagam; conteúdo inválido levanta ErroProcedencia e o arquivo nunca é reconstruído."""
    if not existe(manifesto):
        return {}
    bruto = manifesto.read_bytes()
    try:
        registros = json.loads(bruto.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ErroProcedencia(f"{manifesto.name} inválido ({type(erro).__name__}: {erro})") \
            from erro
    if not isinstance(registros, dict):
        raise ErroProcedencia(f"{manifesto.name} inválido (a raiz não é um objeto JSON)")
    return registros


def avisos_de_consistencia(fonte: dict) -> list[str]:
    """Só leitura: diferenças entre o hash esperado e o registro de procedência.

    Usado em --verificar; os avisos não alteram o código de saída. Erros de leitura (OSError)
    propagam e são tratados como falha.
    """
    manifesto = caminho_procedencia(fonte)
    if not existe(manifesto):
        return [f"{manifesto.name} ausente"]
    try:
        registros = ler_procedencia(manifesto)
    except ErroProcedencia as erro:
        return [str(erro)]
    registro = registros.get(fonte["id"])
    if not isinstance(registro, dict):
        return ["registro de procedência ausente"]
    if registro.get("sha256") != fonte["sha256"]:
        return [f"sha256 registrado ({registro.get('sha256')}) difere do esperado"]
    return []


def descrever(erro: BaseException) -> str:
    return f"{type(erro).__name__}: {erro}"


def gravar_se_necessario(fonte: dict, conteudo: bytes, hash_obtido: str, registros: dict,
                         dados_iguais: bool) -> str:
    """Grava dados e registro de uma fonte já validada, só no que mudou; devolve o status.

    `registros` é o PROCEDENCIA.json já lido e validado, antes de qualquer gravação.
    """
    destino = RAIZ / fonte["destino"]
    if not dados_iguais:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)

    anterior = registros.get(fonte["id"])
    novo = registro_esperado(fonte, hash_obtido, len(conteudo), anterior)
    if novo != anterior:
        registros = dict(registros, **{fonte["id"]: novo})
        caminho_procedencia(fonte).write_text(
            json.dumps(registros, ensure_ascii=False, indent=2) + "\n",
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

    falhas: list[str] = []
    sucessos = nao_processadas = 0
    for fonte in FONTES:
        destino = RAIZ / fonte["destino"]
        fid = fonte["id"]
        if not args.verificar and fonte["uso"] == "auditoria" and not args.auditoria:
            print(f"[IGNORADA] {fid}: fonte de auditoria; use --auditoria")
            nao_processadas += 1
            continue

        esperado = fonte.get("sha256")
        if not esperado:
            print(f"[RECUSADA] {fid}: sem hash SHA-256 esperado; nada foi baixado, "
                  "verificado ou registrado")
            falhas.append(fid)
            continue

        if args.verificar:  # somente leitura: nenhum caminho abaixo grava ou cria pastas
            try:  # existe() só devolve False para FileNotFoundError; acesso negado é erro
                conteudo = destino.read_bytes() if existe(destino) else None
            except OSError as erro:
                print(f"[ERRO DE LEITURA] {fid}: {descrever(erro)}")
                falhas.append(fid)
                continue
            if conteudo is None:
                if fonte["uso"] == "auditoria":
                    print(f"[AUSENTE, opcional] {fid}: fonte de auditoria local")
                    nao_processadas += 1
                    continue
                print(f"[AUSENTE] {fid}: {fonte['destino']}")
                falhas.append(fid)
                continue
        else:
            try:
                conteudo = baixar(fonte["url"])
            except ERROS_DE_REDE as erro:
                print(f"[ERRO DE REDE] {fid}: {descrever(erro)}; nada foi gravado")
                falhas.append(fid)
                continue

        obtido = sha256(conteudo)
        if obtido != esperado:
            print(f"[ERRO] {fid}: hash {obtido} difere do esperado {esperado}; "
                  "nada foi gravado")
            falhas.append(fid)
            continue

        if args.verificar:
            try:
                avisos = avisos_de_consistencia(fonte)
            except OSError as erro:
                print(f"[ERRO DE LEITURA] {fid}: PROCEDENCIA.json: {descrever(erro)}")
                falhas.append(fid)
                continue
            for aviso in avisos:  # avisos não alteram o código de saída
                print(f"[AVISO] {fid}: {aviso}")
            situacao = "verificado"
        else:
            # Procedência lida e validada, e arquivo local lido, ANTES de qualquer gravação.
            try:
                registros = ler_procedencia(caminho_procedencia(fonte))
                dados_iguais = existe(destino) and sha256(destino.read_bytes()) == obtido
            except ErroProcedencia as erro:
                print(f"[ERRO DE PROCEDÊNCIA] {fid}: {erro}; nada foi gravado e o arquivo não "
                      "foi alterado; corrija-o manualmente")
                falhas.append(fid)
                continue
            except OSError as erro:
                print(f"[ERRO DE LEITURA] {fid}: {descrever(erro)}; nada foi gravado")
                falhas.append(fid)
                continue
            situacao = gravar_se_necessario(fonte, conteudo, obtido, registros, dados_iguais)
        print(f"[OK] {fid}: {len(conteudo)} bytes, sha256={obtido} ({situacao})")
        sucessos += 1

    resumo = f"Resumo: {sucessos} fonte(s) OK, {len(falhas)} com falha"
    if falhas:
        resumo += f": {', '.join(falhas)}"
    if nao_processadas:
        resumo += f"; {nao_processadas} não processada(s) (ignorada ou ausente opcional)"
    print(resumo)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
