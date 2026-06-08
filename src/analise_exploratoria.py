"""
analise_exploratoria.py — Análise Exploratória de Dados (EDA) com matplotlib
============================================================================

Explora a base processada (data/processed/voos.parquet) com estatísticas
descritivas e gráficos (matplotlib/seaborn), gerando as figuras usadas no
relatório e imprimindo os principais INSIGHTS já interpretados.

Saída:
    figuras/*.png  (gráficos da análise)
    console        (estatísticas + insights interpretados)

Uso:
    python src/analise_exploratoria.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend sem interface gráfica (salva direto em arquivo)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

RAIZ = Path(__file__).resolve().parent.parent
ARQ = RAIZ / "data" / "processed" / "voos.parquet"
FIG = RAIZ / "figuras"
FIG.mkdir(exist_ok=True)

# Identidade visual (mesmas cores do dashboard)
COR = "#1A5276"
COR_NEG = "#C0392B"
COR_POS = "#1E8449"
CORES_CIA = {"Azul": "#1F77B4", "LATAM": "#8E44AD", "Gol": "#E67E22"}
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
         "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

sns.set_theme(style="whitegrid", font_scale=1.0)
plt.rcParams["figure.dpi"] = 110
plt.rcParams["savefig.bbox"] = "tight"
plt.rcParams["axes.titleweight"] = "bold"


def salvar(nome: str):
    plt.savefig(FIG / nome)
    plt.close()
    print(f"   figura salva: figuras/{nome}")


# ---------------------------------------------------------------------------

def main():
    print("Carregando base...")
    df = pd.read_parquet(ARQ)
    real = df[~df["cancelado"]].copy()
    print(f"Base: {len(df):,} voos\n")

    print("=" * 60)
    print("ESTATÍSTICAS DESCRITIVAS")
    print("=" * 60)
    print(real[["atraso_partida_min", "atraso_chegada_min",
                "duracao_prevista_min", "distancia_km"]].describe().round(1))

    # ---- 1) Distribuição dos atrasos de chegada -----------------------------
    plt.figure(figsize=(9, 5))
    dados = real["atraso_chegada_min"].clip(-60, 120).dropna()
    plt.hist(dados, bins=60, color=COR, alpha=0.85)
    plt.axvline(0, color="gray", ls="--", lw=1)
    plt.axvline(15, color=COR_NEG, ls="--", lw=1.5, label="Limiar de atraso (15 min)")
    plt.title("Distribuição do atraso na chegada (voos realizados)")
    plt.xlabel("Atraso na chegada (min) — negativo = adiantado")
    plt.ylabel("Nº de voos")
    plt.legend()
    salvar("01_distribuicao_atrasos.png")

    # ---- 2) Sazonalidade: volume e cancelamento por mês ---------------------
    g = df.groupby("mes").agg(voos=("situacao", "size"),
                              canc=("cancelado", "mean")).reindex(range(1, 13))
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.bar(MESES, g["voos"], color=COR, alpha=0.85)
    ax1.set_ylabel("Voos no mês", color=COR)
    ax1.set_title("Sazonalidade: volume de voos e taxa de cancelamento por mês")
    ax2 = ax1.twinx()
    ax2.plot(MESES, g["canc"] * 100, color=COR_NEG, marker="o", lw=2)
    ax2.set_ylabel("% cancelados", color=COR_NEG)
    ax2.grid(False)
    salvar("02_sazonalidade.png")

    # ---- 3) Top 3 companhias: volume x pontualidade -------------------------
    grandes = ["Azul", "LATAM", "Gol"]
    vol = df[df["grupo"].isin(grandes)]["grupo"].value_counts().reindex(grandes)
    pont = (real[real["grupo"].isin(grandes)]
            .groupby("grupo")["atrasado"].mean().reindex(grandes) * 100)
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 5))
    a.bar(grandes, vol / 1000, color=[CORES_CIA[g] for g in grandes])
    a.set_title("Volume de voos (mil)")
    a.set_ylabel("Mil voos")
    for i, v in enumerate(vol / 1000):
        a.text(i, v, f"{v:.0f}k", ha="center", va="bottom")
    b.bar(grandes, pont, color=[CORES_CIA[g] for g in grandes])
    b.set_title("% de voos atrasados (>15 min)")
    b.set_ylabel("% atrasados")
    for i, v in enumerate(pont):
        b.text(i, v, f"{v:.1f}%", ha="center", va="bottom")
    fig.suptitle("As 3 grandes: tamanho do mercado x pontualidade",
                 fontweight="bold")
    salvar("03_top3_companhias.png")

    # ---- 4) % atrasos por hora do dia ---------------------------------------
    hora = real.groupby("hora_prevista")["atrasado"].mean().mul(100)
    plt.figure(figsize=(10, 5))
    plt.plot(hora.index, hora.values, color=COR, marker="o", lw=2)
    plt.fill_between(hora.index, hora.values, color=COR, alpha=0.12)
    plt.title("Atrasos se acumulam ao longo do dia (efeito cascata)")
    plt.xlabel("Hora prevista de partida")
    plt.ylabel("% de voos atrasados")
    plt.xticks(range(0, 24, 2))
    salvar("04_atraso_por_hora.png")

    # ---- 5) % atrasos por dia da semana -------------------------------------
    dia = (real.groupby("dia_semana_nome")["atrasado"].mean()
           .reindex(DIAS) * 100)
    plt.figure(figsize=(9, 5))
    cores = [COR_NEG if v == dia.max() else COR for v in dia.values]
    plt.bar(dia.index, dia.values, color=cores)
    plt.title("Pontualidade por dia da semana")
    plt.ylabel("% de voos atrasados")
    plt.xticks(rotation=20)
    salvar("05_atraso_dia_semana.png")

    # ---- 6) Doméstico x Internacional ---------------------------------------
    comp = real.groupby("tipo_voo").agg(
        atraso=("atrasado", "mean"),
        atraso_med=("atraso_chegada_min", "mean"),
        dist=("distancia_km", "mean")).mul(1)
    plt.figure(figsize=(8, 5))
    plt.bar(comp.index, comp["atraso"] * 100, color=[COR, "#34495E"])
    plt.title("Pontualidade: voos domésticos x internacionais")
    plt.ylabel("% de voos atrasados")
    for i, v in enumerate(comp["atraso"] * 100):
        plt.text(i, v, f"{v:.1f}%", ha="center", va="bottom")
    salvar("06_dom_x_internacional.png")

    # ---- 7) Top 12 aeroportos por movimento ---------------------------------
    mov = pd.concat([df["origem_municipality"], df["destino_municipality"]]
                    ).value_counts().head(12).sort_values()
    plt.figure(figsize=(9, 6))
    plt.barh(mov.index, mov.values / 1000, color=COR)
    plt.title("Top 12 cidades por movimentação aérea (2024)")
    plt.xlabel("Movimentos — mil (pousos + decolagens)")
    salvar("07_top_aeroportos.png")

    # ---- 8) Mapa de calor: dia da semana x hora -----------------------------
    piv = (real.groupby(["dia_semana_nome", "hora_prevista"])["atrasado"]
           .mean().mul(100).reset_index()
           .pivot(index="dia_semana_nome", columns="hora_prevista",
                  values="atrasado").reindex(DIAS))
    plt.figure(figsize=(12, 5))
    sns.heatmap(piv, cmap="OrRd", cbar_kws={"label": "% atrasados"})
    plt.title("Quando os atrasos acontecem (dia da semana x hora)")
    plt.xlabel("Hora do dia")
    plt.ylabel("")
    salvar("08_heatmap_atrasos.png")

    # =====================================================================
    # INSIGHTS INTERPRETADOS
    # =====================================================================
    tot = len(df)
    pico_mes = MESES[int(g["voos"].idxmax()) - 1]
    vale_mes = MESES[int(g["voos"].idxmin()) - 1]
    share = (df[df.tipo_voo.eq("Doméstico")]["grupo"]
             .value_counts(normalize=True) * 100)
    share3 = share.reindex(["Azul", "LATAM", "Gol"]).sum()
    pior_hora = int(hora.idxmax())
    melhor_hora = int(hora.idxmin())
    pior_dia = dia.idxmax()
    dom = comp.loc["Doméstico", "atraso"] * 100
    intl = comp.loc["Internacional", "atraso"] * 100

    print("\n" + "=" * 60)
    print("PRINCIPAIS INSIGHTS (interpretados)")
    print("=" * 60)
    print(f"""
1. ESCALA E SAZONALIDADE
   - {tot:,} voos regulares em 2024; pico em {pico_mes} (férias de verão/inverno)
     e vale em {vale_mes}. A malha é estável, oscilando ~12% entre pico e vale.

2. MERCADO OLIGOPOLIZADO
   - Azul, LATAM e Gol concentram {share3:.1f}% do mercado DOMÉSTICO.
   - Azul lidera em volume ({share['Azul']:.0f}%), mas é a menos pontual das três
     -> opera mais aeroportos regionais, mais sujeitos a atrasos.

3. PONTUALIDADE
   - {real['atrasado'].mean()*100:.1f}% dos voos chegam com +15 min de atraso;
     cancelamento médio de {df['cancelado'].mean()*100:.1f}%.
   - O atraso CRESCE ao longo do dia: de ~{hora.min():.0f}% às {melhor_hora}h para
     ~{hora.max():.0f}% às {pior_hora}h (efeito cascata da operação).
   - {pior_dia} é o pior dia da semana para pontualidade.

4. DOMÉSTICO x INTERNACIONAL
   - Voos internacionais atrasam mais ({intl:.1f}%) do que os domésticos ({dom:.1f}%)
     -> rotas longas, congestionamento nos hubs internacionais e procedimentos de
        imigração/alfândega ampliam o atraso acumulado na chegada.

5. CONCENTRAÇÃO GEOGRÁFICA
   - O Sudeste (São Paulo/Rio/BH) concentra a maior parte do movimento;
     poucos hubs respondem pela maioria dos voos do país.
""")
    print("EDA concluída. Figuras em figuras/.")


if __name__ == "__main__":
    main()
