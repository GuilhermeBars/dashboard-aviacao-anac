"""
crawler.py — Coleta automática de dados (BÔNUS)
===============================================

Baixa automaticamente os dados brutos usados no projeto, direto das fontes
oficiais, sem necessidade de login ou credenciais:

1. VRA — Voo Regular Ativo (ANAC / dados abertos)
   12 arquivos CSV mensais de 2024, um por mês. Cada arquivo tem ~85 mil voos.
   Fonte: https://sistemas.anac.gov.br/dadosabertos/

2. OurAirports — base aberta de aeroportos do mundo todo
   Usada como tabela de referência (dimensão) para fazer o merge dos
   códigos ICAO dos aeroportos com cidade, estado, região e coordenadas.
   Fonte: https://davidmegginson.github.io/ourairports-data/airports.csv

Uso:
    python src/crawler.py            # baixa o ano de 2024 inteiro
    python src/crawler.py --ano 2023 # baixa outro ano
    python src/crawler.py --meses 1 2 3   # baixa apenas alguns meses

Os arquivos são salvos em data/raw/. Arquivos já baixados são pulados
(permite retomar o download sem baixar tudo de novo).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------

BASE_ANAC = "https://sistemas.anac.gov.br/dadosabertos"
URL_AIRPORTS = "https://davidmegginson.github.io/ourairports-data/airports.csv"

# Pasta data/raw/ relativa à raiz do projeto (um nível acima de src/)
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_RAW = RAIZ_PROJETO / "data" / "raw"

# Nome das pastas mensais no portal da ANAC (ex.: "01 - Janeiro")
MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (projeto-academico ANAC/VRA)"}


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def url_vra(ano: int, mes: int) -> str:
    """Monta a URL do CSV mensal do VRA, codificando espaços e acentos."""
    pasta_mes = f"{mes:02d} - {MESES_PT[mes]}"
    caminho = (
        f"Voos e operações aéreas/Voo Regular Ativo (VRA)/"
        f"{ano}/{pasta_mes}/VRA_{ano}{mes}.csv"
    )
    # quote mantém as barras "/" e codifica espaços/acentos
    return f"{BASE_ANAC}/{quote(caminho)}"


def baixar(url: str, destino: Path, tentativas: int = 3) -> bool:
    """Baixa um arquivo com barra de progresso simples e algumas tentativas."""
    if destino.exists() and destino.stat().st_size > 0:
        print(f"  [pulado] {destino.name} já existe "
              f"({destino.stat().st_size/1e6:.1f} MB)")
        return True

    for tentativa in range(1, tentativas + 1):
        try:
            with requests.get(url, headers=HEADERS, stream=True, timeout=120) as r:
                r.raise_for_status()
                total = int(r.headers.get("Content-Length", 0))
                baixado = 0
                destino_tmp = destino.with_suffix(destino.suffix + ".part")
                with open(destino_tmp, "wb") as f:
                    for bloco in r.iter_content(chunk_size=1024 * 256):
                        f.write(bloco)
                        baixado += len(bloco)
                        if total:
                            pct = baixado / total * 100
                            print(f"\r  baixando {destino.name}: {pct:5.1f}%",
                                  end="", flush=True)
                destino_tmp.rename(destino)
                print(f"\r  [ok] {destino.name} "
                      f"({baixado/1e6:.1f} MB)            ")
                return True
        except requests.RequestException as e:
            print(f"\r  [tentativa {tentativa}/{tentativas}] erro: {e}")
            time.sleep(2 * tentativa)

    print(f"  [FALHA] não foi possível baixar {destino.name}")
    return False


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Coleta automática dos dados de voos da ANAC (VRA) + aeroportos."
    )
    parser.add_argument("--ano", type=int, default=2024,
                        help="Ano dos dados do VRA (padrão: 2024).")
    parser.add_argument("--meses", type=int, nargs="*",
                        default=list(range(1, 13)),
                        help="Meses a baixar (padrão: 1..12).")
    parser.add_argument("--sem-aeroportos", action="store_true",
                        help="Não baixar a base de aeroportos.")
    args = parser.parse_args()

    PASTA_RAW.mkdir(parents=True, exist_ok=True)
    print(f"Salvando dados brutos em: {PASTA_RAW}\n")

    ok = 0
    total = 0

    # 1) Voos mensais (VRA)
    print(f">> Baixando VRA {args.ano} ({len(args.meses)} meses)")
    for mes in args.meses:
        total += 1
        destino = PASTA_RAW / f"VRA_{args.ano}_{mes:02d}.csv"
        if baixar(url_vra(args.ano, mes), destino):
            ok += 1

    # 2) Tabela de referência de aeroportos (dimensão p/ o merge)
    if not args.sem_aeroportos:
        print("\n>> Baixando base de aeroportos (OurAirports)")
        total += 1
        if baixar(URL_AIRPORTS, PASTA_RAW / "airports.csv"):
            ok += 1

    print(f"\nConcluído: {ok}/{total} arquivos disponíveis em data/raw/")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
