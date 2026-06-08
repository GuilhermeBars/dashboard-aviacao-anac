"""
app.py — Dashboard interativo da Aviação Civil Brasileira (ANAC / VRA 2024)
==========================================================================

Aplicação Dash com DOIS dashboards (abas):

  • Dashboard 1 — Visão Geral (painel executivo):
        indicadores-chave + gráficos sintéticos que contam a história
        principal dos dados de forma rápida e objetiva.

  • Dashboard 2 — Exploração Interativa:
        4 filtros + 7 visualizações de tipos diferentes para o usuário
        explorar os dados em detalhe (companhias, rotas, atrasos, mapa...).

Rodar:
    python src/app.py
    -> abrir http://127.0.0.1:8050 no navegador
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output

# ---------------------------------------------------------------------------
# Configuração visual (boas práticas de Storytelling with Data:
# paleta sóbria, 1 cor de destaque por ideia, vermelho só p/ algo negativo)
# ---------------------------------------------------------------------------

COR_AZUL = "#1F77B4"
COR_LATAM = "#8E44AD"
COR_GOL = "#E67E22"
COR_DESTAQUE = "#1A5276"
COR_NEGATIVO = "#C0392B"
COR_POSITIVO = "#1E8449"
COR_NEUTRO = "#95A5A6"
COR_FUNDO = "#F4F6F7"

GRUPO_CORES = {
    "Azul": COR_AZUL,
    "LATAM": COR_LATAM,
    "Gol": COR_GOL,
    "Outras nacionais": "#16A085",
    "Internacional": "#34495E",
    "Cargueiro": "#7F8C8D",
    "Outras": "#BDC3C7",
}

TEMPLATE = "plotly_white"
FONTE = dict(family="Segoe UI, Helvetica, Arial, sans-serif")

RAIZ = Path(__file__).resolve().parent.parent
ARQ_DADOS = RAIZ / "data" / "processed" / "voos.parquet"


# ---------------------------------------------------------------------------
# Carregamento dos dados (uma vez, na inicialização)
# ---------------------------------------------------------------------------

if not ARQ_DADOS.exists():
    raise SystemExit(
        "Base processada não encontrada. Rode antes:\n"
        "  python src/crawler.py\n  python src/preprocessing.py"
    )

print("Carregando base processada...")
df = pd.read_parquet(ARQ_DADOS)
df_real = df[~df["cancelado"]].copy()   # voos realizados (p/ métricas de atraso)
print(f"Base carregada: {len(df):,} voos")

MESES_ORD = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
             "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
DIAS_ORD = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


# ---------------------------------------------------------------------------
# Funções utilitárias
# ---------------------------------------------------------------------------

def card_kpi(titulo: str, valor: str, cor: str = COR_DESTAQUE,
             sub: str = "") -> html.Div:
    """Cartão de indicador-chave (número grande)."""
    return html.Div(className="kpi-card", children=[
        html.Div(titulo, className="kpi-titulo"),
        html.Div(valor, className="kpi-valor", style={"color": cor}),
        html.Div(sub, className="kpi-sub"),
    ])


def fig_vazia(msg="Sem dados para os filtros selecionados") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False,
                       font=dict(size=16, color=COR_NEUTRO))
    fig.update_layout(template=TEMPLATE, font=FONTE,
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def estilizar(fig: go.Figure, titulo: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=16, color="#2C3E50")),
        template=TEMPLATE, font=FONTE,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="white", plot_bgcolor="white",
    )
    return fig


# ===========================================================================
# DASHBOARD 1 — VISÃO GERAL (figuras calculadas uma vez)
# ===========================================================================

def kpis_gerais() -> html.Div:
    total = len(df)
    pct_canc = df["cancelado"].mean() * 100
    pct_atras = df_real["atrasado"].mean() * 100
    atraso_med = df_real.loc[df_real["atraso_chegada_min"].notna(),
                             "atraso_chegada_min"].mean()
    pct_dom = (df["tipo_voo"].eq("Doméstico").mean()) * 100
    return html.Div(className="kpi-row", children=[
        card_kpi("Voos no ano", f"{total/1e6:.2f} mi", COR_DESTAQUE,
                 "registros do VRA 2024"),
        card_kpi("Cancelamentos", f"{pct_canc:.1f}%", COR_NEGATIVO,
                 "do total de voos"),
        card_kpi("Voos atrasados", f"{pct_atras:.1f}%", COR_NEGATIVO,
                 "chegada > 15 min"),
        card_kpi("Atraso médio", f"{atraso_med:.0f} min", COR_DESTAQUE,
                 "na chegada (realizados)"),
        card_kpi("Companhias", f"{df['empresa'].nunique()}", COR_POSITIVO,
                 "operando no país"),
        card_kpi("Aeroportos", f"{df['origem_icao'].nunique()}", COR_POSITIVO,
                 "de origem"),
        card_kpi("Voos domésticos", f"{pct_dom:.0f}%", COR_DESTAQUE,
                 "vs. internacionais"),
    ])


def fig_evolucao_mensal() -> go.Figure:
    g = (df.groupby("mes")
           .agg(voos=("situacao", "size"),
                cancelados=("cancelado", "sum"))
           .reindex(range(1, 13)))
    g["mes_nome"] = MESES_ORD
    pico = int(g["voos"].idxmax())
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=g["mes_nome"], y=g["voos"], mode="lines+markers",
        line=dict(color=COR_DESTAQUE, width=3),
        marker=dict(size=8), name="Voos",
        hovertemplate="%{x}: %{y:,} voos<extra></extra>"))
    fig.add_annotation(x=g.loc[pico, "mes_nome"], y=g.loc[pico, "voos"],
                       text=f"Pico: {g.loc[pico,'voos']/1000:.0f} mil",
                       showarrow=True, arrowhead=2, ay=-35,
                       font=dict(color=COR_DESTAQUE))
    fig.update_yaxes(rangemode="tozero", tickformat=",")
    return estilizar(fig, "Volume de voos por mês — sazonalidade ao longo de 2024")


def fig_market_share() -> go.Figure:
    dom = df[df["tipo_voo"].eq("Doméstico")].copy()
    g3 = ["Azul", "LATAM", "Gol"]
    dom["cat"] = np.where(dom["grupo"].isin(g3), dom["grupo"], "Outras")
    ordem = ["Azul", "LATAM", "Gol", "Outras"]
    g = (dom["cat"].value_counts(normalize=True) * 100).reindex(ordem)
    fig = go.Figure(go.Pie(
        labels=ordem, values=g.values, hole=0.55,
        marker=dict(colors=[GRUPO_CORES.get(x, COR_NEUTRO) for x in ordem]),
        textinfo="label+percent", sort=False,
        hovertemplate="%{label}: %{value:.1f}%<extra></extra>"))
    fig.update_layout(showlegend=False)
    return estilizar(fig, "Participação no mercado doméstico (3 grandes dominam)")


def fig_pontualidade_grupos() -> go.Figure:
    grandes = ["Gol", "Azul", "LATAM"]
    sub = df_real[df_real["grupo"].isin(grandes)]
    g = (sub.groupby("grupo")["atrasado"].mean() * 100).reindex(grandes)
    fig = go.Figure(go.Bar(
        x=g.index, y=g.values,
        marker_color=[GRUPO_CORES[x] for x in g.index],
        text=[f"{v:.1f}%" for v in g.values], textposition="outside",
        hovertemplate="%{x}: %{y:.1f}% atrasados<extra></extra>"))
    fig.update_yaxes(title="% de voos atrasados", rangemode="tozero")
    return estilizar(fig, "Pontualidade das 3 maiores companhias")


def fig_top_aeroportos() -> go.Figure:
    mov = pd.concat([
        df["origem_municipality"].rename("cidade"),
        df["destino_municipality"].rename("cidade"),
    ]).value_counts().head(10).sort_values()
    fig = go.Figure(go.Bar(
        x=mov.values, y=mov.index, orientation="h",
        marker_color=COR_DESTAQUE,
        hovertemplate="%{y}: %{x:,} movimentos<extra></extra>"))
    fig.update_xaxes(title="Movimentos (pousos + decolagens)", tickformat=",")
    return estilizar(fig, "Top 10 cidades por movimentação aérea")


def layout_visao_geral() -> html.Div:
    return html.Div(className="aba", children=[
        html.Div(className="aba-header", children=[
            html.H2("Panorama da Aviação Civil Brasileira — 2024"),
            html.P("Visão executiva de ~1 milhão de voos regulares registrados "
                   "pela ANAC. Em uma olhada: quem voa, quando voa e onde "
                   "estão os gargalos de pontualidade."),
        ]),
        kpis_gerais(),
        html.Div(className="grid-2", children=[
            dcc.Graph(figure=fig_evolucao_mensal()),
            dcc.Graph(figure=fig_market_share()),
        ]),
        html.Div(className="grid-2", children=[
            dcc.Graph(figure=fig_pontualidade_grupos()),
            dcc.Graph(figure=fig_top_aeroportos()),
        ]),
        html.Div(className="rodape-insight", children=[
            html.B("Leitura rápida: "),
            "três companhias (Gol, Azul e LATAM) concentram a quase totalidade "
            "do mercado doméstico; o volume tem picos sazonais (férias e fim de "
            "ano); e há diferença clara de pontualidade entre as grandes — "
            "explore os detalhes na aba ao lado.",
        ]),
    ])


# ===========================================================================
# DASHBOARD 2 — EXPLORAÇÃO INTERATIVA (filtros + callbacks)
# ===========================================================================

OPCOES_GRUPO = [{"label": g, "value": g}
                for g in df["grupo"].value_counts().index]
OPCOES_REGIAO = [{"label": r, "value": r}
                 for r in sorted(df["origem_regiao"].dropna().unique())]


def painel_filtros() -> html.Div:
    return html.Div(className="filtros", children=[
        html.Div(className="filtro-item", children=[
            html.Label("Grupo / Companhia"),
            dcc.Dropdown(id="f-grupo", options=OPCOES_GRUPO, multi=True,
                         placeholder="Todas as companhias"),
        ]),
        html.Div(className="filtro-item", children=[
            html.Label("Tipo de voo"),
            dcc.RadioItems(
                id="f-tipo",
                options=[{"label": " Todos", "value": "Todos"},
                         {"label": " Doméstico", "value": "Doméstico"},
                         {"label": " Internacional", "value": "Internacional"}],
                value="Todos", inline=True),
        ]),
        html.Div(className="filtro-item", children=[
            html.Label("Região de origem"),
            dcc.Dropdown(id="f-regiao", options=OPCOES_REGIAO, multi=True,
                         placeholder="Todas as regiões"),
        ]),
        html.Div(className="filtro-item filtro-mes", children=[
            html.Label("Período (meses)"),
            dcc.RangeSlider(id="f-mes", min=1, max=12, step=1, value=[1, 12],
                            marks={i: MESES_ORD[i-1] for i in range(1, 13)}),
        ]),
    ])


def layout_exploracao() -> html.Div:
    return html.Div(className="aba", children=[
        html.Div(className="aba-header", children=[
            html.H2("Exploração Interativa"),
            html.P("Use os filtros para recortar os dados por companhia, tipo "
                   "de voo, região e período. Todos os gráficos reagem em conjunto."),
        ]),
        painel_filtros(),
        html.Div(id="kpis-filtro", className="kpi-row kpi-row-sm"),
        html.Div(className="grid-2", children=[
            dcc.Graph(id="g-evolucao"),
            dcc.Graph(id="g-rotas"),
        ]),
        html.Div(className="grid-2", children=[
            dcc.Graph(id="g-atraso-cia"),
            dcc.Graph(id="g-heatmap"),
        ]),
        html.Div(className="grid-2", children=[
            dcc.Graph(id="g-dispersao"),
            dcc.Graph(id="g-tipo-linha"),
        ]),
        dcc.Graph(id="g-mapa"),
    ])


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = Dash(__name__, title="Aviação Brasil 2024 — ANAC",
           assets_folder=str((RAIZ / "assets").resolve()))
server = app.server

app.layout = html.Div(children=[
    html.Div(className="topo", children=[
        html.H1("✈️  Aviação Civil Brasileira — Análise do VRA 2024"),
        html.Span("Fonte: ANAC (Voo Regular Ativo) • OurAirports • dados abertos",
                  className="topo-sub"),
    ]),
    dcc.Tabs(id="abas", value="visao", className="abas", children=[
        dcc.Tab(label="📊 Dashboard 1 — Visão Geral", value="visao",
                className="tab", selected_className="tab-sel"),
        dcc.Tab(label="🔎 Dashboard 2 — Exploração Interativa", value="explora",
                className="tab", selected_className="tab-sel"),
    ]),
    html.Div(id="conteudo-aba"),
    html.Div(className="creditos",
             children="Projeto Final — Análise de Dados • Dash + Plotly + Pandas"),
])


@app.callback(Output("conteudo-aba", "children"), Input("abas", "value"))
def trocar_aba(aba):
    return layout_visao_geral() if aba == "visao" else layout_exploracao()


# --- Filtro central da aba 2 ----------------------------------------------

def aplicar_filtros(grupos, tipo, regioes, meses):
    d = df
    if grupos:
        d = d[d["grupo"].isin(grupos)]
    if tipo and tipo != "Todos":
        d = d[d["tipo_voo"].eq(tipo)]
    if regioes:
        d = d[d["origem_regiao"].isin(regioes)]
    if meses:
        d = d[d["mes"].between(meses[0], meses[1])]
    return d


@app.callback(
    Output("kpis-filtro", "children"),
    Output("g-evolucao", "figure"),
    Output("g-rotas", "figure"),
    Output("g-atraso-cia", "figure"),
    Output("g-heatmap", "figure"),
    Output("g-dispersao", "figure"),
    Output("g-tipo-linha", "figure"),
    Output("g-mapa", "figure"),
    Input("f-grupo", "value"),
    Input("f-tipo", "value"),
    Input("f-regiao", "value"),
    Input("f-mes", "value"),
)
def atualizar(grupos, tipo, regioes, meses):
    d = aplicar_filtros(grupos, tipo, regioes, meses)
    if len(d) == 0:
        v = fig_vazia()
        return (html.Div("Nenhum voo para os filtros."),
                v, v, v, v, v, v, v)
    d_real = d[~d["cancelado"]]

    # ----- KPIs do recorte -----
    kpis = html.Div(className="kpi-row kpi-row-sm", children=[
        card_kpi("Voos no recorte", f"{len(d):,}", COR_DESTAQUE),
        card_kpi("% cancelados", f"{d['cancelado'].mean()*100:.1f}%", COR_NEGATIVO),
        card_kpi("% atrasados", f"{d_real['atrasado'].mean()*100:.1f}%", COR_NEGATIVO),
        card_kpi("Atraso médio",
                 f"{d_real['atraso_chegada_min'].mean():.0f} min", COR_DESTAQUE),
        card_kpi("Rotas distintas", f"{d['rota'].nunique():,}", COR_POSITIVO),
    ])

    # ----- 1) Evolução mensal (linha) -----
    g = d.groupby("mes").size().reindex(range(1, 13), fill_value=0)
    fig_evo = go.Figure(go.Scatter(
        x=MESES_ORD, y=g.values, mode="lines+markers",
        line=dict(color=COR_DESTAQUE, width=3), fill="tozeroy",
        fillcolor="rgba(26,82,118,0.08)",
        hovertemplate="%{x}: %{y:,} voos<extra></extra>"))
    fig_evo.update_yaxes(rangemode="tozero", tickformat=",")
    fig_evo = estilizar(fig_evo, "Volume de voos por mês")

    # ----- 2) Top 15 rotas (barra horizontal) -----
    rt = d["rota"].value_counts().head(15).sort_values()
    fig_rotas = go.Figure(go.Bar(
        x=rt.values, y=rt.index, orientation="h",
        marker_color=COR_DESTAQUE,
        hovertemplate="%{y}: %{x:,} voos<extra></extra>"))
    fig_rotas.update_xaxes(title="Voos", tickformat=",")
    fig_rotas = estilizar(fig_rotas, "Top 15 rotas mais movimentadas")

    # ----- 3) Atraso médio por companhia (barra) -----
    ca = (d_real.groupby("empresa")
          .agg(atraso=("atraso_chegada_min", "mean"), n=("empresa", "size"))
          .query("n >= 200").sort_values("atraso").tail(15).reset_index())
    cor_barra = np.where(ca["atraso"] > 15, COR_NEGATIVO, COR_POSITIVO)
    fig_cia = go.Figure(go.Bar(
        x=ca["atraso"], y=ca["empresa"], orientation="h",
        marker_color=cor_barra,
        text=[f"{v:.0f}" for v in ca["atraso"]], textposition="outside",
        hovertemplate="%{y}: %{x:.1f} min (%{customdata:,} voos)<extra></extra>",
        customdata=ca["n"]))
    fig_cia.update_xaxes(title="Atraso médio na chegada (min)")
    fig_cia = estilizar(fig_cia, "Atraso médio por companhia (≥200 voos)")

    # ----- 4) Heatmap dia da semana × hora (% atrasados) -----
    hm = (d_real.dropna(subset=["dia_semana_nome", "hora_prevista"])
          .groupby(["dia_semana_nome", "hora_prevista"])["atrasado"]
          .mean().mul(100).reset_index())
    if len(hm):
        piv = hm.pivot(index="dia_semana_nome", columns="hora_prevista",
                       values="atrasado").reindex(DIAS_ORD)
        fig_hm = go.Figure(go.Heatmap(
            z=piv.values, x=piv.columns, y=piv.index,
            colorscale="OrRd", colorbar=dict(title="% atras."),
            hovertemplate="%{y}, %{x}h: %{z:.0f}% atrasados<extra></extra>"))
        fig_hm.update_xaxes(title="Hora do dia")
    else:
        fig_hm = fig_vazia()
    fig_hm = estilizar(fig_hm, "% de atrasos por dia da semana e hora")

    # ----- 5) Dispersão distância × atraso por rota (bolhas) -----
    rr = (d_real.dropna(subset=["distancia_km", "atraso_chegada_min"])
          .groupby("rota")
          .agg(dist=("distancia_km", "first"),
               atraso=("atraso_chegada_min", "mean"),
               n=("rota", "size")).query("n >= 100"))
    if len(rr):
        fig_disp = px.scatter(
            rr, x="dist", y="atraso", size="n", size_max=40,
            color="atraso", color_continuous_scale="RdYlGn_r",
            labels={"dist": "Distância da rota (km)",
                    "atraso": "Atraso médio (min)", "n": "Voos"})
        fig_disp.update_traces(
            hovertemplate="Dist.: %{x:.0f} km<br>Atraso: %{y:.1f} min<extra></extra>")
    else:
        fig_disp = fig_vazia()
    fig_disp = estilizar(fig_disp, "Distância da rota × atraso médio (bolha = nº de voos)")

    # ----- 6) Distribuição por tipo de linha (pizza) -----
    tl = d["tipo_linha_desc"].value_counts()
    fig_tl = go.Figure(go.Pie(
        labels=tl.index, values=tl.values, hole=0.45,
        hovertemplate="%{label}: %{value:,} (%{percent})<extra></extra>"))
    fig_tl = estilizar(fig_tl, "Composição por tipo de linha")

    # ----- 7) Mapa dos aeroportos (geo) -----
    mp = (d.groupby(["origem_icao", "origem_municipality",
                     "origem_lat", "origem_lon"])
          .size().reset_index(name="voos")
          .dropna(subset=["origem_lat", "origem_lon"])
          .sort_values("voos", ascending=False).head(60))
    if len(mp):
        fig_mapa = px.scatter_geo(
            mp, lat="origem_lat", lon="origem_lon",
            size="voos", size_max=35, color="voos",
            color_continuous_scale="Blues",
            hover_name="origem_municipality",
            scope="south america",
            labels={"voos": "Voos"})
        fig_mapa.update_geos(
            showcountries=True, countrycolor="#D5DBDB",
            showland=True, landcolor="#FbFcFc",
            lataxis_range=[-35, 6], lonaxis_range=[-75, -32])
    else:
        fig_mapa = fig_vazia()
    fig_mapa = estilizar(fig_mapa,
                         "Aeroportos de origem por volume de voos (60 maiores)")
    fig_mapa.update_layout(height=520)

    return kpis, fig_evo, fig_rotas, fig_cia, fig_hm, fig_disp, fig_tl, fig_mapa


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8050)
