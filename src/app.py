"""
app.py — Dashboard interativo da Aviação Civil Brasileira (ANAC / VRA 2024)
==========================================================================

Aplicação Dash com DOIS dashboards (abas):

  • Dashboard 1 — Visão Geral (painel executivo):
        indicadores-chave + gráficos sintéticos que contam a história
        principal dos dados de forma rápida e objetiva.

  • Dashboard 2 — Exploração Interativa:
        4 filtros + seletor de métrica + 7 visualizações de tipos diferentes
        para o usuário explorar os dados em detalhe e, a cada recorte, ver os
        insights do relatório (companhias, rotas, atrasos, mapa...).

Rodar:
    python src/app.py
    -> abrir http://127.0.0.1:8050 no navegador
"""

from __future__ import annotations

import json
import os
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
_PROC = RAIZ / "data" / "processed"
# Localmente usamos a base completa; no deploy (Hugging Face) usamos a base
# enxuta de ~5 MB (mesmos números, só as colunas usadas), gerada por
# build_deploy.py.
ARQ_DADOS = (_PROC / "voos.parquet" if (_PROC / "voos.parquet").exists()
             else _PROC / "voos_deploy.parquet")


# ---------------------------------------------------------------------------
# Carregamento dos dados (uma vez, na inicialização)
# ---------------------------------------------------------------------------

if not ARQ_DADOS.exists():
    raise SystemExit(
        "Base processada não encontrada. Rode antes:\n"
        "  python src/crawler.py\n  python src/preprocessing.py\n"
        "(ou python build_deploy.py para gerar a base enxuta de deploy)"
    )

print("Carregando base processada...")
df = pd.read_parquet(ARQ_DADOS)
df_real = df[~df["cancelado"]].copy()   # voos realizados (p/ métricas de atraso)
print(f"Base carregada: {len(df):,} voos")

# Atraso médio do país — referência p/ colorir barras (acima da média = vermelho)
MEDIA_ATRASO_PCT = df_real["atrasado"].mean() * 100


# ---------------------------------------------------------------------------
# Rótulos legíveis de aeroporto/rota — o leitor não precisa conhecer aviação.
# Traduz a sigla ICAO (SBSP) para "Cidade (IATA)", ex.: "São Paulo (CGH)".
# ---------------------------------------------------------------------------

def _rotulos_aeroportos() -> dict:
    # No deploy, os rótulos já vêm prontos num JSON pequeno (evita depender do
    # airports.csv de 12 MB em produção).
    arq_json = _PROC / "aeroportos_label.json"
    if arq_json.exists():
        return json.loads(arq_json.read_text(encoding="utf-8"))
    cidade = {}
    for lado in ("origem", "destino"):
        sub = (df[[f"{lado}_icao", f"{lado}_municipality"]]
               .dropna(subset=[f"{lado}_icao"]).drop_duplicates(f"{lado}_icao"))
        for icao, mun in sub.itertuples(index=False):
            if icao not in cidade and pd.notna(mun):
                cidade[icao] = str(mun).strip()
    # IATA (a sigla de 3 letras que aparece na passagem) vem da base de aeroportos
    iata = {}
    arq = RAIZ / "data" / "raw" / "airports.csv"
    if arq.exists():
        ap = (pd.read_csv(arq, usecols=["ident", "iata_code"])
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
    return rot


ROTULO_AEROPORTO = _rotulos_aeroportos()


def rota_legivel(rota) -> str:
    """'SBRJ→SBSP'  ->  'Rio De Janeiro (SDU) → São Paulo (CGH)'."""
    if not isinstance(rota, str) or "→" not in rota:
        return str(rota)
    o, d = rota.split("→", 1)
    return f"{ROTULO_AEROPORTO.get(o, o)} → {ROTULO_AEROPORTO.get(d, d)}"


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


def fmt_milhar(n) -> str:
    """Contagem de voos legível em pt-BR.

    987997 -> '988 mil' | 12345 -> '12.345' | 532 -> '532'
    (evita o pouco intuitivo '0,99 mi' e usa '.' como separador de milhar).
    """
    n = int(round(float(n)))
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} mi".replace(".", ",")
    if n >= 100_000:
        return f"{round(n / 1000)} mil"
    return f"{n:,}".replace(",", ".")


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
        separators=",.",  # pt-BR: vírgula decimal, ponto de milhar (1.234,5)
    )
    return fig


# ===========================================================================
# DASHBOARD 1 — VISÃO GERAL (figuras calculadas uma vez)
# ===========================================================================

def kpis_gerais() -> html.Div:
    total = len(df)
    pct_canc = df["cancelado"].mean() * 100
    pct_atras = df_real["atrasado"].mean() * 100
    # Atraso médio considerando SÓ os voos atrasados (>15 min) — sem isso a
    # média afunda perto de zero, pois 60% dos voos chegam adiantados.
    atraso_med = df_real.loc[df_real["atrasado"], "atraso_chegada_min"].mean()
    pct_dom = (df["tipo_voo"].eq("Doméstico").mean()) * 100
    return html.Div(className="kpi-row", children=[
        card_kpi("Voos em 2024", fmt_milhar(total), COR_DESTAQUE,
                 "registros do VRA"),
        card_kpi("Cancelamentos", f"{pct_canc:.1f}%", COR_NEGATIVO,
                 "do total de voos"),
        card_kpi("Voos atrasados", f"{pct_atras:.1f}%", COR_NEGATIVO,
                 "chegada acima de 15 min"),
        card_kpi("Atraso médio", f"{atraso_med:.0f} min", COR_NEGATIVO,
                 "dos voos atrasados (>15 min)"),
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
    return estilizar(fig, "Volume de voos por mês: sazonalidade ao longo de 2024")


def fig_market_share() -> go.Figure:
    dom = df[df["tipo_voo"].eq("Doméstico")].copy()
    g3 = ["Azul", "LATAM", "Gol"]
    dom["cat"] = np.where(dom["grupo"].isin(g3), dom["grupo"], "Outras")
    ordem = ["Azul", "LATAM", "Gol", "Outras"]
    g = (dom["cat"].value_counts(normalize=True) * 100).reindex(ordem)
    fig = go.Figure(go.Pie(
        labels=ordem, values=g.values, hole=0.55,
        marker=dict(colors=[GRUPO_CORES.get(x, COR_NEUTRO) for x in ordem]),
        textinfo="label+percent", sort=False, domain=dict(x=[0.0, 0.58]),
        hovertemplate="%{label}: %{value:.1f}%<extra></extra>"))

    # "Outras" reúne dezenas de companhias menores — mostra exemplos no cantinho
    out = dom[~dom["grupo"].isin(g3)]["empresa"]
    exemplos = [e for e in out.value_counts().index
                if not str(e).startswith("Outras (")][:5]
    curtos = [str(e).replace(" Linhas Aéreas", "").replace(" Brasil", "")
              for e in exemplos]
    n_total = out.nunique()
    txt = ("<b>O que é “Outras” (4,7%)</b><br>"
           + "<br>".join(f"• {c}" for c in curtos)
           + f"<br>+ {n_total - len(curtos)} companhias menores<br>"
           "<span style='font-size:10px'>(regionais e cargueiras)</span>")
    fig.add_annotation(
        text=txt, x=0.62, xanchor="left", y=0.5, yanchor="middle",
        xref="paper", yref="paper", showarrow=False, align="left",
        font=dict(size=11, color="#5D6D7E"),
        bordercolor="#D5DBDB", borderwidth=1, borderpad=8, bgcolor="#FbFcFc")
    fig.update_layout(showlegend=False)
    return estilizar(fig,
                     "Participação no mercado doméstico em 2024 (3 grandes dominam)")


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
    return estilizar(fig, "Pontualidade das 3 maiores companhias em 2024")


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
    return estilizar(fig, "Top 10 cidades por movimentação aérea em 2024")


def fig_tipo_linha() -> go.Figure:
    """Composição da operação por tipo de linha — barra horizontal.

    Mais clara que a pizza quando há uma categoria dominante e várias
    minúsculas. Cores agrupam por natureza: azul = passageiros, âmbar = carga,
    cinza = outros.
    """
    tl = df["tipo_linha_desc"].value_counts()
    pct = (tl / tl.sum() * 100).sort_values()   # ascending: maior fica no topo
    paleta = {
        "Nacional (passageiros)": "#1A5276",
        "Internacional (passageiros)": "#5499C7",
        "Cargueiro nacional": "#CA6F1E",
        "Cargueiro internacional": "#E59866",
        "Outros / ligação": "#7F8C8D",
        "Outros": "#BDC3C7",
    }
    cores = [paleta.get(k, COR_NEUTRO) for k in pct.index]

    def _fmt(v):
        if v >= 1:
            return f"{v:.1f}%"
        return f"{v:.2f}%" if v >= 0.01 else f"{v:.4f}%"

    fig = go.Figure(go.Bar(
        x=pct.values, y=pct.index, orientation="h",
        marker_color=cores,
        text=[_fmt(v) for v in pct.values], textposition="outside",
        customdata=tl.reindex(pct.index).values,
        hovertemplate="%{y}: %{x:.2f}% (%{customdata:,} voos)<extra></extra>"))
    fig.update_xaxes(title="% dos voos no ano", ticksuffix="%",
                     range=[0, 100])
    fig.update_yaxes(automargin=True)
    return estilizar(fig, "Composição da operação por tipo de linha em 2024 "
                          "(passageiros dominam)")


def layout_visao_geral() -> html.Div:
    return html.Div(className="aba", children=[
        html.Div(className="aba-header", children=[
            html.H2("Panorama da Aviação Civil Brasileira em 2024"),
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
        dcc.Graph(figure=fig_tipo_linha()),
        html.Div(className="rodape-insight", children=[
            html.B("Leitura rápida: "),
            "três companhias (Gol, Azul e LATAM) concentram a quase totalidade "
            "do mercado doméstico; o volume tem picos sazonais (férias e fim de "
            "ano); e há diferença clara de pontualidade entre as grandes. "
            "Explore os detalhes na aba ao lado.",
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
            html.P("Os mesmos padrões da Visão Geral, agora nas suas mãos. "
                   "Recorte por companhia, tipo de voo, região e período: todos os "
                   "gráficos e indicadores reagem juntos. Cada painel abaixo "
                   "aprofunda um dos insights do relatório."),
        ]),
        html.Div(className="story-guia", children=[
            html.B("Como ler esta aba: "),
            "o ", html.B("volume"), " mostra a sazonalidade (Insight 4); as ",
            html.B("rotas"), " e o ", html.B("mapa"),
            " mostram a concentração no Sudeste (Insights 1 e 6); e os três painéis "
            "de atraso revelam ", html.B("onde mora a falta de pontualidade"),
            " — por companhia (Insight 2), por dia e hora (Insight 3) e por "
            "distância da rota (Insight 5). ",
            html.I("Dica: selecione só a Azul e veja o heatmap acender no fim de tarde."),
        ]),
        painel_filtros(),
        html.Div(className="metrica-bar", children=[
            html.Label("Métrica de pontualidade:"),
            dcc.RadioItems(
                id="f-metrica",
                options=[{"label": " % de voos atrasados", "value": "pct"},
                         {"label": " Atraso médio (min)", "value": "min"}],
                value="pct", inline=True, className="metrica-radio"),
            html.Span("aplica-se ao gráfico por companhia e ao mapa de calor",
                      className="metrica-dica"),
        ]),
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
            dcc.Graph(id="g-distribuicao"),
        ]),
        dcc.Graph(id="g-mapa"),
    ])


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = Dash(__name__, title="Aviação Brasil 2024 (ANAC)",
           assets_folder=str((RAIZ / "assets").resolve()))
server = app.server

app.layout = html.Div(children=[
    html.Div(className="topo", children=[
        html.H1("Aviação Civil Brasileira: análise do VRA 2024"),
        html.Span("Fonte: ANAC (Voo Regular Ativo), OurAirports, dados abertos",
                  className="topo-sub"),
    ]),
    dcc.Tabs(id="abas", value="visao", className="abas", children=[
        dcc.Tab(label="Dashboard 1: Visão Geral", value="visao",
                className="tab", selected_className="tab-sel"),
        dcc.Tab(label="Dashboard 2: Exploração Interativa", value="explora",
                className="tab", selected_className="tab-sel"),
    ]),
    html.Div(id="conteudo-aba"),
    html.Div(className="creditos",
             children="Projeto final · Estudos Avançados de Banco de Dados · Dash, Plotly e Pandas"),
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
    Output("g-distribuicao", "figure"),
    Output("g-mapa", "figure"),
    Input("f-grupo", "value"),
    Input("f-tipo", "value"),
    Input("f-regiao", "value"),
    Input("f-mes", "value"),
    Input("f-metrica", "value"),
)
def atualizar(grupos, tipo, regioes, meses, metrica):
    d = aplicar_filtros(grupos, tipo, regioes, meses)
    if len(d) == 0:
        v = fig_vazia()
        return (html.Div("Nenhum voo para os filtros."),
                v, v, v, v, v, v, v)
    d_real = d[~d["cancelado"]]

    # ----- KPIs do recorte -----
    # Atraso médio só dos atrasados (>15 min): "quando atrasa, atrasa quanto?"
    atr_atrasados = d_real.loc[d_real["atrasado"], "atraso_chegada_min"]
    atraso_med_rec = atr_atrasados.mean() if len(atr_atrasados) else 0
    kpis = html.Div(className="kpi-row kpi-row-sm", children=[
        card_kpi("Voos no recorte", fmt_milhar(len(d)), COR_DESTAQUE),
        card_kpi("% cancelados", f"{d['cancelado'].mean()*100:.1f}%", COR_NEGATIVO),
        card_kpi("% atrasados", f"{d_real['atrasado'].mean()*100:.1f}%", COR_NEGATIVO),
        card_kpi("Atraso quando atrasa", f"{atraso_med_rec:.0f} min", COR_NEGATIVO),
        card_kpi("Rotas distintas", fmt_milhar(d['rota'].nunique()), COR_POSITIVO),
    ])

    # ----- 1) Evolução mensal (linha) -----
    g = d.groupby("mes").size().reindex(range(1, 13), fill_value=0)
    fig_evo = go.Figure(go.Scatter(
        x=MESES_ORD, y=g.values, mode="lines+markers",
        line=dict(color=COR_DESTAQUE, width=3), fill="tozeroy",
        fillcolor="rgba(26,82,118,0.08)",
        hovertemplate="%{x}: %{y:,} voos<extra></extra>"))
    fig_evo.update_yaxes(rangemode="tozero", tickformat=",")
    fig_evo = estilizar(fig_evo, "Sazonalidade: volume de voos mês a mês (2024)")
    fig_evo.update_layout(hovermode="x unified")
    fig_evo.update_xaxes(showspikes=True, spikethickness=1,
                         spikecolor=COR_NEUTRO, spikemode="across", spikedash="dot")

    # ----- 2) Top 15 rotas (barra horizontal) — rótulos por cidade -----
    rt = d["rota"].value_counts().head(15).sort_values()
    rotas_nome = [rota_legivel(r) for r in rt.index]
    fig_rotas = go.Figure(go.Bar(
        x=rt.values, y=rotas_nome, orientation="h",
        marker_color=COR_DESTAQUE,
        customdata=list(rt.index),
        hovertemplate="<b>%{y}</b><br>%{x:,} voos<br>"
                      "<span style='font-size:11px;color:#888'>código: %{customdata}</span>"
                      "<extra></extra>"))
    fig_rotas.update_xaxes(title="Voos", tickformat=",")
    fig_rotas.update_yaxes(automargin=True)
    fig_rotas = estilizar(fig_rotas,
                          "Concentração de rotas: as 15 mais movimentadas (2024)")

    # ----- 3) Quem mais atrasa seus voos no Brasil (barra) — Insight 2 -----
    # Todo voo da malha brasileira (ANAC/VRA) conta — inclusive companhias
    # estrangeiras em rotas internacionais de/para o Brasil. A métrica escolhida
    # define o que a barra mostra: % de atrasados ou minutos médios.
    if metrica == "min":
        ca = (d_real.groupby("empresa")
              .agg(val=("atraso_chegada_min", "mean"), n=("empresa", "size"))
              .query("n >= 200").sort_values("val").tail(15).reset_index())
        ref, eixo, detalhe = 15, "Atraso médio na chegada (min)", "atraso médio na chegada"
        texto = [f"{v:.0f}" for v in ca["val"]]
        hover_cia = "%{y}: %{x:.1f} min (%{customdata:,} voos no Brasil)<extra></extra>"
    else:
        ca = (d_real.groupby("empresa")
              .agg(val=("atrasado", "mean"), n=("empresa", "size"))
              .query("n >= 200"))
        ca["val"] *= 100
        ca = ca.sort_values("val").tail(15).reset_index()
        ref, eixo, detalhe = MEDIA_ATRASO_PCT, "% de voos atrasados", "% de voos atrasados"
        texto = [f"{v:.0f}%" for v in ca["val"]]
        hover_cia = "%{y}: %{x:.1f}% atrasados (%{customdata:,} voos no Brasil)<extra></extra>"
    escopo = {
        "Doméstico": "voos domésticos no Brasil",
        "Internacional": "voos internacionais de/para o Brasil (inclui estrangeiras)",
    }.get(tipo, "voos domésticos e internacionais (inclui estrangeiras)")
    titulo_cia = ("Quem mais atrasa seus voos no Brasil"
                  "<br><span style='font-size:11px;color:#7F8C8D'>"
                  f"{detalhe} · {escopo} · companhias com ≥200 voos no recorte "
                  "(2024 · fonte ANAC/VRA)</span>")
    cor_barra = np.where(ca["val"] > ref, COR_NEGATIVO, COR_POSITIVO)
    fig_cia = go.Figure(go.Bar(
        x=ca["val"], y=ca["empresa"], orientation="h",
        marker_color=cor_barra,
        text=texto, textposition="outside",
        hovertemplate=hover_cia, customdata=ca["n"]))
    fig_cia.add_vline(x=ref, line_dash="dot", line_color=COR_NEUTRO,
                      annotation_text="média do país" if metrica == "pct"
                      else "limiar 15 min",
                      annotation_position="top")
    fig_cia.update_xaxes(title=eixo)
    fig_cia = estilizar(fig_cia, titulo_cia)
    fig_cia.update_layout(margin=dict(t=64))

    # ----- 4) Heatmap dia × período do dia — Insight 3 -----
    # Agrupa as 24h em 4 períodos nomeados e ESCREVE o valor em cada célula
    # (cor do texto contrasta com o fundo). Fica direto de ler, sem decifrar tons.
    base_hm = d_real.dropna(subset=["dia_semana_nome", "hora_prevista"]).copy()
    PERIODOS = ["Madrugada", "Manhã", "Tarde", "Noite"]
    base_hm["periodo"] = pd.cut(base_hm["hora_prevista"], bins=[-1, 5, 11, 17, 23],
                                labels=PERIODOS)
    if metrica == "min":
        hm = (base_hm.groupby(["dia_semana_nome", "periodo"], observed=True)
              ["atraso_chegada_min"].mean().reset_index(name="val"))
        cbar, sufixo = "min", " min"
        titulo_hm = ("Quando os atrasos acontecem em 2024: "
                     "atraso médio (min) por dia e período")
    else:
        hm = (base_hm.groupby(["dia_semana_nome", "periodo"], observed=True)
              ["atrasado"].mean().mul(100).reset_index(name="val"))
        cbar, sufixo = "% atras.", "%"
        titulo_hm = ("Quando os atrasos acontecem em 2024: % de voos atrasados por "
                     "dia e período (pior: tarde/noite de quinta e sexta)")
    if len(hm):
        piv = (hm.pivot(index="dia_semana_nome", columns="periodo", values="val")
               .reindex(index=DIAS_ORD, columns=PERIODOS))
        z = piv.values.astype(float)
        zmin, zmax = np.nanmin(z), np.nanmax(z)
        lim = zmin + 0.55 * (zmax - zmin) if zmax > zmin else zmax
        fig_hm = go.Figure(go.Heatmap(
            z=z, x=PERIODOS, y=list(piv.index), colorscale="OrRd",
            colorbar=dict(title=cbar), xgap=2, ygap=2,
            hovertemplate="%{y}, %{x}: %{z:.1f}" + sufixo + "<extra></extra>"))
        # valor em cada célula, branco no fundo escuro e escuro no claro
        for i, dia in enumerate(piv.index):
            for j, per in enumerate(PERIODOS):
                v = z[i][j]
                if not np.isnan(v):
                    fig_hm.add_annotation(
                        x=per, y=dia, text=f"{v:.0f}{sufixo}", showarrow=False,
                        font=dict(size=13,
                                  color="white" if v >= lim else "#2C3E50"))
        fig_hm.update_xaxes(title="Período do dia")
    else:
        fig_hm = fig_vazia()
    fig_hm = estilizar(fig_hm, titulo_hm)

    # ----- 5) Dispersão distância × atraso por rota (bolhas) -----
    rr = (d_real.dropna(subset=["distancia_km", "atraso_chegada_min"])
          .groupby("rota")
          .agg(dist=("distancia_km", "first"),
               atraso=("atraso_chegada_min", "mean"),
               n=("rota", "size")).query("n >= 100").reset_index())
    if len(rr):
        rr["rota_nome"] = rr["rota"].map(rota_legivel)
        fig_disp = px.scatter(
            rr, x="dist", y="atraso", size="n", size_max=40,
            color="atraso", color_continuous_scale="RdYlGn_r",
            custom_data=["rota_nome", "n"],
            labels={"dist": "Distância da rota (km)",
                    "atraso": "Atraso médio (min)", "n": "Voos"})
        fig_disp.update_traces(
            hovertemplate="<b>%{customdata[0]}</b><br>Distância: %{x:.0f} km<br>"
                          "Atraso médio: %{y:.1f} min<br>%{customdata[1]:,} voos<extra></extra>")
    else:
        fig_disp = fig_vazia()
    fig_disp = estilizar(fig_disp,
                         "Distância × atraso em 2024: rotas mais longas tendem a atrasar mais")

    # ----- 6) Distribuição dos atrasos na chegada (histograma) -----
    # Pré-agrega no servidor (np.histogram) p/ não enviar ~1M de pontos ao browser.
    serie = d_real["atraso_chegada_min"].dropna().clip(-60, 120)
    if len(serie):
        contagem, bordas = np.histogram(serie, bins=36, range=(-60, 120))
        centros = (bordas[:-1] + bordas[1:]) / 2
        # verde = adiantado/no horário | azul = até 15 min | vermelho = atrasado
        cores = [COR_NEGATIVO if c > 15 else (COR_POSITIVO if c <= 0 else COR_DESTAQUE)
                 for c in centros]
        fig_dist = go.Figure(go.Bar(
            x=centros, y=contagem, marker_color=cores,
            width=(bordas[1] - bordas[0]) * 0.95,
            hovertemplate="~%{x:.0f} min: %{y:,} voos<extra></extra>"))
        fig_dist.add_vline(x=15, line_dash="dash", line_color=COR_NEGATIVO,
                           annotation_text="limiar 15 min", annotation_position="top")
        fig_dist.update_xaxes(title="Atraso na chegada (min) — negativo = adiantado")
        fig_dist.update_yaxes(title="Nº de voos", tickformat=",")
    else:
        fig_dist = fig_vazia()
    fig_dist = estilizar(fig_dist,
                         "Distribuição dos atrasos na chegada em 2024 "
                         "(a maioria chega no horário)")

    # ----- 7) Mapa dos aeroportos (geo) -----
    mp = (d.groupby(["origem_icao", "origem_municipality",
                     "origem_lat", "origem_lon"])
          .size().reset_index(name="voos")
          .dropna(subset=["origem_lat", "origem_lon"])
          .sort_values("voos", ascending=False).head(60))
    if len(mp):
        mp["aeroporto"] = (mp["origem_icao"].map(ROTULO_AEROPORTO)
                           .fillna(mp["origem_municipality"]))
        fig_mapa = px.scatter_geo(
            mp, lat="origem_lat", lon="origem_lon",
            size="voos", size_max=35, color="voos",
            color_continuous_scale="Blues",
            hover_name="aeroporto", custom_data=["voos"],
            scope="south america",
            labels={"voos": "Voos"})
        fig_mapa.update_traces(
            hovertemplate="<b>%{hovertext}</b><br>%{customdata[0]:,} voos<extra></extra>")
        fig_mapa.update_geos(
            showcountries=True, countrycolor="#D5DBDB",
            showland=True, landcolor="#FbFcFc",
            lataxis_range=[-35, 6], lonaxis_range=[-75, -32])
    else:
        fig_mapa = fig_vazia()
    fig_mapa = estilizar(fig_mapa,
                         "Onde o Brasil voa em 2024: concentração geográfica (60 maiores aeroportos)")
    fig_mapa.update_layout(height=520)

    return kpis, fig_evo, fig_rotas, fig_cia, fig_hm, fig_disp, fig_dist, fig_mapa


if __name__ == "__main__":
    # PORT/HOST por variável de ambiente (deploy define; local usa o padrão).
    app.run(debug=False,
            host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", 8050)))
