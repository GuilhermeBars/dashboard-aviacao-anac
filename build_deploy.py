"""
build_deploy.py — prepara o pacote de deploy do dashboard para o Hugging Face
=============================================================================

Gera, a partir da base completa (data/processed/voos.parquet):

  1. data/processed/voos_deploy.parquet  -> base enxuta (~5 MB, só as 20 colunas
     usadas pelo app; MESMOS números, só sem as colunas que não entram em
     nenhum gráfico). Cabe no limite de 10 MB do Hugging Face sem Git LFS.
  2. data/processed/aeroportos_label.json -> rótulos "Cidade (IATA)" prontos,
     para o app não precisar do airports.csv (12 MB) em produção.
  3. deploy_hf/  -> pasta autocontida pronta para 'git push' no Space do HF
     (código, assets, dados enxutos, Dockerfile, requirements e README).

Uso:
    python build_deploy.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent
PROC = RAIZ / "data" / "processed"
RAW = RAIZ / "data" / "raw"
DEPLOY = RAIZ / "deploy_hf"

# Colunas REALMENTE usadas pelo app (conferidas uma a uma no src/app.py).
COLS = [
    "mes", "dia_semana_nome", "hora_prevista", "situacao",
    "empresa", "grupo", "tipo_voo", "tipo_linha_desc",
    "origem_icao", "origem_municipality", "origem_regiao",
    "origem_lat", "origem_lon", "destino_icao", "destino_municipality",
    "rota", "distancia_km",
    "cancelado", "atrasado", "atraso_chegada_min",
]


def gerar_base_enxuta() -> Path:
    df = pd.read_parquet(PROC / "voos.parquet")
    faltando = [c for c in COLS if c not in df.columns]
    if faltando:
        raise SystemExit(f"Colunas ausentes na base: {faltando}")
    d = df[COLS].copy()
    for c in d.select_dtypes("float64").columns:
        d[c] = pd.to_numeric(d[c], downcast="float")
    saida = PROC / "voos_deploy.parquet"
    d.to_parquet(saida, index=False)
    mb = saida.stat().st_size / 1e6
    print(f"[1/3] {saida.name}: {len(d):,} linhas x {d.shape[1]} cols -> {mb:.1f} MB")
    if mb > 10:
        print("      AVISO: passou de 10 MB; o Hugging Face vai exigir Git LFS.")
    return saida


def gerar_rotulos() -> Path:
    """ICAO -> 'Cidade (IATA)'. Mesma lógica do app, salva em JSON."""
    df = pd.read_parquet(PROC / "voos.parquet")
    cidade = {}
    for lado in ("origem", "destino"):
        sub = (df[[f"{lado}_icao", f"{lado}_municipality"]]
               .dropna(subset=[f"{lado}_icao"]).drop_duplicates(f"{lado}_icao"))
        for icao, mun in sub.itertuples(index=False):
            if icao not in cidade and pd.notna(mun):
                cidade[icao] = str(mun).strip()
    iata = {}
    if (RAW / "airports.csv").exists():
        ap = (pd.read_csv(RAW / "airports.csv", usecols=["ident", "iata_code"])
              .dropna(subset=["iata_code"]))
        iata = dict(ap.itertuples(index=False))
    rot = {}
    for icao in set(cidade) | set(iata):
        c, s = cidade.get(icao), iata.get(icao)
        if c and s:
            rot[icao] = f"{c} ({s})"
        elif c:
            rot[icao] = c
        elif s:
            rot[icao] = f"{icao} ({s})"
        else:
            rot[icao] = icao
    saida = PROC / "aeroportos_label.json"
    saida.write_text(json.dumps(rot, ensure_ascii=False), encoding="utf-8")
    print(f"[2/3] {saida.name}: {len(rot)} aeroportos com rótulo legível")
    return saida


DOCKERFILE = """\
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 7860
# 1 worker basta para a apresentação; --preload carrega os dados uma vez só.
CMD ["gunicorn", "src.app:server", "--bind", "0.0.0.0:7860", \
     "--workers", "1", "--preload", "--timeout", "180"]
"""

REQUIREMENTS = """\
# Dependências mínimas do dashboard em produção (Hugging Face Space)
pandas==2.2.2
numpy==1.26.4
dash==2.17.1
plotly==5.23.0
pyarrow==17.0.0
gunicorn==22.0.0
"""

README_HF = """\
---
title: Dashboard Aviacao ANAC 2024
emoji: ✈️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Aviação Civil Brasileira — Dashboard (VRA / ANAC 2024)

Dashboard interativo em Dash sobre ~988 mil voos regulares de 2024 (fonte ANAC).
Dois painéis: Visão Geral (executivo) e Exploração Interativa (filtros, seletor de
métrica e 7 visualizações). Projeto da disciplina de Estudos Avançados de Banco
de Dados — PUC-Campinas.
"""


def montar_pasta_deploy():
    # Limpa o conteúdo MAS preserva o .git (pra não perder o remote do Space
    # entre rebuilds; assim o re-deploy é só add/commit/push).
    if DEPLOY.exists():
        for item in DEPLOY.iterdir():
            if item.name == ".git":
                continue
            shutil.rmtree(item) if item.is_dir() else item.unlink()
    (DEPLOY / "src").mkdir(parents=True)
    (DEPLOY / "assets").mkdir()
    (DEPLOY / "data" / "processed").mkdir(parents=True)

    shutil.copy(RAIZ / "src" / "app.py", DEPLOY / "src" / "app.py")
    shutil.copy(RAIZ / "assets" / "style.css", DEPLOY / "assets" / "style.css")
    shutil.copy(PROC / "voos_deploy.parquet",
                DEPLOY / "data" / "processed" / "voos_deploy.parquet")
    shutil.copy(PROC / "aeroportos_label.json",
                DEPLOY / "data" / "processed" / "aeroportos_label.json")

    (DEPLOY / "Dockerfile").write_text(DOCKERFILE, encoding="utf-8")
    (DEPLOY / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")
    (DEPLOY / "README.md").write_text(README_HF, encoding="utf-8")
    print(f"[3/3] pasta deploy_hf/ montada ({sum(1 for _ in DEPLOY.rglob('*'))} itens)")


if __name__ == "__main__":
    print("Gerando pacote de deploy...\n")
    gerar_base_enxuta()
    gerar_rotulos()
    montar_pasta_deploy()
    print("\nPronto. Pasta 'deploy_hf/' pronta para subir no Hugging Face.")
    print("Veja o passo a passo em DEPLOY_HF.md.")
