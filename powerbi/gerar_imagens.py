"""Embute no Power BI os escudos e as fotos já escolhidos para o site.

Por que existe: o Power BI Desktop nem sempre consegue exibir imagens da Wikimedia
pela URL (a tabela mostrava só o nome do clube). Este script baixa cada imagem uma
vez e grava o conteúdo em base64, em pedaços de até 30.000 caracteres, porque o
Power BI corta textos maiores que 32.766 caracteres ao carregar. As medidas
'Escudo ou sigla' e 'Foto ou camisa' juntam os pedaços e exibem a imagem sem
depender da internet, inclusive no Power BI Service.

Entradas (geradas pelo pipeline do projeto, nada é inventado aqui):
    powerbi/dados/dim_clube.csv    coluna escudo_url
    powerbi/dados/dim_jogador.csv  coluna foto_url
Saídas:
    powerbi/dados/imagem_escudo.csv  id_clube, parte, conteudo
    powerbi/dados/imagem_foto.csv    id_jogador, parte, conteudo

Imagem que não baixa fica fora do CSV: a medida volta a usar a URL e, sem URL,
a sigla do clube ou a camisa com as iniciais (nunca um rosto genérico).

Uso, na raiz do projeto (precisa de internet):
    py -3.14 -I powerbi/gerar_imagens.py
"""

import base64
import csv
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DADOS = Path(__file__).resolve().parent / "dados"
AGENTE = ("Brasileirao2024-portfolio/1.0 "
          "(https://github.com/thiagomiranda396/Brasileir-o2024; powerbi/gerar_imagens.py)")
PEDACO = 30000
LARGURA_FOTO = 330          # mesma largura das miniaturas que o site já usa
LIMITE_BYTES = 1_500_000    # acima disso a imagem não entra (deixaria o modelo pesado)
ORIGINAL = re.compile(r"^https://upload\.wikimedia\.org/wikipedia/commons/(?!thumb/)(\w/\w\w)/([^/?#]+)$")


def miniatura(url: str) -> str | None:
    """URL do arquivo original no Commons -> miniatura de 330 px (mesmo arquivo, menor)."""
    m = ORIGINAL.match(url)
    if not m:
        return None
    pasta, arquivo = m.groups()
    sufixo = ".png" if arquivo.lower().endswith((".svg", ".tif", ".tiff")) else ""
    return (f"https://upload.wikimedia.org/wikipedia/commons/thumb/{pasta}/{arquivo}/"
            f"{LARGURA_FOTO}px-{arquivo}{sufixo}")


def baixar(url: str, tentativas: int = 5) -> tuple[bytes, str] | None:
    espera = 2.0
    for tentativa in range(1, tentativas + 1):
        time.sleep(0.25)
        pedido = urllib.request.Request(url, headers={"User-Agent": AGENTE, "Accept": "image/*"})
        try:
            with urllib.request.urlopen(pedido, timeout=60) as r:
                tipo = r.headers.get_content_type()
                corpo = r.read()
                if not tipo.startswith("image/"):
                    print(f"  não é imagem ({tipo}): {url}")
                    return None
                return corpo, tipo
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or tentativa == tentativas:
                print(f"  HTTP {e.code}: {url}")
                return None
            espera = float(e.headers.get("Retry-After") or espera)
        except urllib.error.URLError as e:
            if tentativa == tentativas:
                print(f"  falha de rede ({e.reason}): {url}")
                return None
        time.sleep(espera)
        espera *= 2
    return None


def gerar(entrada: str, chave: str, coluna_url: str, saida: str) -> None:
    linhas = list(csv.DictReader(open(DADOS / entrada, encoding="utf-8", newline="")))
    com_url = [l for l in linhas if (l.get(coluna_url) or "").strip()]
    cache: dict[str, str | None] = {}
    gravadas, falhas = 0, []
    with open(DADOS / saida, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([chave, "parte", "conteudo"])
        for i, l in enumerate(com_url, 1):
            url = l[coluna_url].strip()
            if url not in cache:
                cache[url] = None
                for alvo in filter(None, [miniatura(url), url]):
                    r = baixar(alvo)
                    if r and len(r[0]) <= LIMITE_BYTES:
                        corpo, tipo = r
                        cache[url] = f"data:{tipo};base64," + base64.b64encode(corpo).decode("ascii")
                        break
                    if r:
                        print(f"  grande demais ({len(r[0]):,} bytes): {alvo}")
            texto = cache[url]
            if texto is None:
                falhas.append(l[chave])
                continue
            for p in range(0, len(texto), PEDACO):
                w.writerow([l[chave], p // PEDACO + 1, texto[p:p + PEDACO]])
            gravadas += 1
            if i % 50 == 0:
                print(f"  {saida}: {i} de {len(com_url)}")
    print(f"{saida}: {gravadas} de {len(com_url)} imagens gravadas.")
    if falhas:
        print("  Sem imagem embutida (o Power BI usa a URL ou a sigla/camisa):", ", ".join(falhas))


def main() -> int:
    gerar("dim_clube.csv", "id_clube", "escudo_url", "imagem_escudo.csv")
    gerar("dim_jogador.csv", "id_jogador", "foto_url", "imagem_foto.csv")
    print("Pronto. No Power BI Desktop, clique em Atualizar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
