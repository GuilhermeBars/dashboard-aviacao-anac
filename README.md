# ✈️ Aviação Civil Brasileira — Dashboard de Análise (VRA / ANAC 2024)

Projeto final da disciplina de **Estudos Avançados de Banco de Dados**
(Prof. José Guilherme Picolo): um *pipeline* completo de Ciência de Dados em
Python + um **dashboard interativo em Dash**, analisando **~988 mil voos
regulares** registrados pela ANAC ao longo de **2024**.

> **Pergunta que guia o estudo:** quem voa no Brasil, quando voa e onde estão os
> gargalos de pontualidade da aviação comercial?

![Dashboard 1 — Visão Geral](figuras/dashboard1_visao_geral.png)

---

## 👥 Integrantes

**Disciplina:** Estudos Avançados de Banco de Dados — **Prof.** José Guilherme Picolo
**Instituição:** PUC-Campinas

| Nome | RA |
|---|---|
| Felipe Cosmo Granziol | 24021602 |
| Guilherme Bars | 24014122 |
| Gustavo Kurten | *(a confirmar)* |
| João Celso | 24012463 |
| Pedro Tiezo Sales Shimizu | 24005158 |

---

## 🎯 O que o projeto entrega

| Etapa do pipeline | Onde está |
|---|---|
| **1. Aquisição** (leitura com Pandas + crawler de coleta automática) | `src/crawler.py` |
| **2. Integração** (concatenação dos 12 meses + *merge* das dimensões) | `src/preprocessing.py` |
| **3. Limpeza** (nulos, duplicatas, inconsistências, padronização) | `src/preprocessing.py` |
| **4. Transformação** (novas variáveis, agregações) | `src/preprocessing.py` |
| **5. Análise exploratória** (estatística + matplotlib + insights) | `src/analise_exploratoria.py` |
| **Dashboards** (2 painéis interativos em Dash) | `src/app.py` |

---

## 📊 Fontes de dados

São **três fontes públicas**, integradas por operações de *merge* e *concat*
(atende o requisito de **≥ 2 arquivos distintos** e **≥ 10.000 registros**):

| Fonte | Arquivos | Papel | Registros |
|---|---|---|---|
| **VRA — Voo Regular Ativo (ANAC)** | 12 CSVs mensais (`VRA_2024_01..12.csv`) | Tabela-fato (voos) | **~988 mil** |
| **OurAirports** | `airports.csv` | Dimensão de aeroportos (cidade, UF, região, lat/lon) | ~80 mil |
| **Companhias aéreas** (curada a partir de ANAC/OpenFlights) | `dim_companhias.csv` | Dimensão de companhias (nome, país, grupo) | 62 |

Cada arquivo mensal do VRA já tem **~85 mil voos** — um único mês supera o
mínimo de 10.000 registros, e o ano inteiro chega a quase **1 milhão**.

---

## 🚀 Como executar

```bash
# 1. Criar o ambiente e instalar dependências
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Coletar os dados brutos automaticamente (BÔNUS: crawler)
python src/crawler.py              # baixa 12 meses do VRA + aeroportos

# 3. Rodar o pipeline (integração + limpeza + transformação)
python src/preprocessing.py        # gera data/processed/voos.parquet

# 4. (Opcional) Análise exploratória com matplotlib
python src/analise_exploratoria.py # gera as figuras em figuras/

# 5. Subir o dashboard
python src/app.py                  # abrir http://127.0.0.1:8050
```

> Os dados brutos já acompanham o repositório em `data/raw/`. Se quiser regerar
> do zero, basta rodar o passo 2 (o crawler pula arquivos já baixados).

---

## 🗂️ Estrutura do projeto

```
trabalhopicolofinal/
├── src/
│   ├── crawler.py              # coleta automática (BÔNUS +1 ponto)
│   ├── preprocessing.py        # pipeline: concat + merge + limpeza + transformação
│   ├── analise_exploratoria.py # EDA com matplotlib/seaborn + insights
│   └── app.py                  # dashboard Dash (2 painéis)
├── data/
│   ├── raw/                    # dados brutos (VRA mensal, aeroportos, companhias)
│   └── processed/              # base limpa (voos.parquet + amostra)
├── assets/style.css            # estilo do dashboard
├── figuras/                    # gráficos da EDA + screenshots dos dashboards
├── RELATORIO.md                # relatório/apresentação do pipeline e insights
├── requirements.txt
└── README.md
```

---

## 🧭 Os dois dashboards

**Dashboard 1 — Visão Geral (painel executivo):** indicadores-chave + 4 gráficos
sintéticos que resumem a história principal em uma olhada (volume, mercado,
pontualidade, hubs).

**Dashboard 2 — Exploração Interativa:** **4 filtros** (grupo/companhia, tipo de
voo, região e período) e **7 visualizações** de tipos diferentes (linha, barras,
*heatmap*, dispersão, pizza e mapa geográfico) que reagem em conjunto.

![Dashboard 2 — Exploração Interativa](figuras/dashboard2_exploracao.png)

---

## 💡 Principais insights (resumo)

1. **Oligopólio:** Azul, LATAM e Gol concentram **~95%** do mercado doméstico.
2. **Azul é a maior, mas a menos pontual** das três — reflexo de voar mais
   aeroportos regionais.
3. **Atrasos se acumulam ao longo do dia** (efeito cascata): manhãs pontuais,
   fim de tarde/noite é o pior momento — pior ainda às **sextas-feiras**.
4. **Internacionais atrasam mais** (22,5%) que **domésticos** (15,8%).
5. **Sudeste concentra** a maior parte da movimentação; poucos hubs respondem
   pela maioria dos voos.

> A análise completa, com gráficos e interpretação, está em **[RELATORIO.md](RELATORIO.md)**.

---

## ✅ Atendimento aos requisitos

- [x] Dataset público com **≥ 10.000 registros** (~988 mil voos)
- [x] **≥ 2 arquivos distintos** (12 CSVs do VRA + aeroportos + companhias)
- [x] Aquisição com Pandas **+ crawler de coleta automática (bônus)**
- [x] Integração por **concat** (meses) e **merge** (dimensões)
- [x] Limpeza: nulos, duplicatas, inconsistências, padronização
- [x] Transformação: novas variáveis (atraso, atrasado, rota, distância, recortes temporais)
- [x] EDA com estatística + gráficos **e insights interpretados**
- [x] **Dashboard 1** (visão geral / executivo)
- [x] **Dashboard 2** (≥ 5 visualizações, ≥ 2 filtros, comparações, seleção de categorias)
- [x] Boas práticas de comunicação visual (*Storytelling with Data*)

---

*Stack: Python · Pandas · NumPy · Matplotlib · Seaborn · Dash · Plotly*
