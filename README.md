# Aviação Civil Brasileira: dashboard de análise (VRA / ANAC 2024)

Projeto final da disciplina de Estudos Avançados de Banco de Dados (Prof. José
Guilherme Picolo). É um pipeline completo de Ciência de Dados em Python com um
dashboard interativo em Dash, sobre cerca de 988 mil voos regulares registrados
pela ANAC durante o ano de 2024.

A pergunta que guia o trabalho: quem voa no Brasil, quando voa e onde estão os
gargalos de pontualidade da aviação comercial?

![Dashboard 1: Visão Geral](figuras/dashboard1_visao_geral.png)

## Integrantes

Disciplina: Estudos Avançados de Banco de Dados. Professor: José Guilherme
Picolo. PUC-Campinas, Curso de Engenharia de Software.

| Nome | RA |
|---|---|
| Felipe Cosmo Granziol | 24021602 |
| Guilherme Bars | 24014122 |
| Gustavo Kurten | 24008150 |
| João Celso | 24012463 |
| Pedro Tiezo Sales Shimizu | 24005158 |

## O que o projeto entrega

| Etapa do pipeline | Onde está |
|---|---|
| 1. Aquisição (leitura com Pandas e crawler de coleta automática) | `src/crawler.py` |
| 2. Integração (concatenação dos 12 meses e merge das dimensões) | `src/preprocessing.py` |
| 3. Limpeza (nulos, duplicatas, inconsistências, padronização) | `src/preprocessing.py` |
| 4. Transformação (novas variáveis e agregações) | `src/preprocessing.py` |
| 5. Análise exploratória (estatística, matplotlib e insights) | `src/analise_exploratoria.py` |
| Dashboards (dois painéis interativos em Dash) | `src/app.py` |

A apresentação do trabalho em slides está em `apresentacao.pdf`, e o relatório
escrito em [RELATORIO.md](RELATORIO.md).

## Fonte dos dados

São três fontes públicas, integradas por operações de merge e concat. Isso já
cobre o requisito de pelo menos dois arquivos distintos e mais de 10.000
registros:

| Fonte | Arquivos | Papel | Registros |
|---|---|---|---|
| VRA, Voo Regular Ativo (ANAC) | 12 CSVs mensais (`VRA_2024_01..12.csv`) | tabela-fato (voos) | ~988 mil |
| OurAirports | `airports.csv` | dimensão de aeroportos (cidade, UF, região, lat/lon) | ~80 mil |
| Companhias aéreas (a partir de ANAC e OpenFlights) | `dim_companhias.csv` | dimensão de companhias (nome, país, grupo) | 62 |

Um único arquivo mensal do VRA já traz cerca de 85 mil voos, então um mês
sozinho supera o mínimo de 10.000 registros, e o ano inteiro chega perto de um
milhão.

## Coleta automática de dados — crawler (bônus +1)

O script **`src/crawler.py`** baixa **sozinho** todos os dados brutos do projeto,
direto das fontes oficiais, **sem necessidade de login ou credenciais**. É o item
que atende ao **bônus de +1 ponto** (coleta automática de dados).

O que ele faz:

- **Voos (VRA / ANAC):** monta a URL de cada mês no portal de dados abertos da
  ANAC (`sistemas.anac.gov.br/dadosabertos`) e baixa os **12 CSVs de 2024**.
- **Aeroportos (OurAirports):** baixa o `airports.csv` (dimensão usada no merge).
- **Robustez:** barra de progresso, **3 tentativas** com espera em caso de erro,
  download para arquivo temporário `.part` (não corrompe se cair no meio) e
  **pula arquivos já baixados** (permite retomar sem baixar tudo de novo).
- **Parametrizável** por linha de comando:

```bash
python src/crawler.py                  # baixa o ano de 2024 inteiro (padrão)
python src/crawler.py --ano 2023       # baixa outro ano
python src/crawler.py --meses 1 2 3    # baixa apenas alguns meses
python src/crawler.py --sem-aeroportos # pula a base de aeroportos
```

Os arquivos vão para `data/raw/`. Ou seja: **a base inteira do projeto pode ser
recriada do zero com um único comando**, sem baixar nada manualmente.

## Como executar

```bash
# 1. Criar o ambiente e instalar dependências
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Coletar os dados brutos automaticamente (o crawler vale o ponto de bônus)
python src/crawler.py              # baixa 12 meses do VRA e os aeroportos

# 3. Rodar o pipeline (integração, limpeza e transformação)
python src/preprocessing.py        # gera data/processed/voos.parquet

# 4. (Opcional) Análise exploratória com matplotlib
python src/analise_exploratoria.py # gera as figuras em figuras/

# 5. Subir o dashboard
python src/app.py                  # abrir http://127.0.0.1:8050
```

Os dados brutos já acompanham o repositório em `data/raw/`. Para regerar do zero,
basta rodar o passo 2 (o crawler pula arquivos que já existem).

## Estrutura do projeto

```
trabalhopicolofinal/
├── src/
│   ├── crawler.py              # coleta automática (bônus)
│   ├── preprocessing.py        # pipeline: concat, merge, limpeza, transformação
│   ├── analise_exploratoria.py # EDA com matplotlib/seaborn e insights
│   └── app.py                  # dashboard Dash (dois painéis)
├── data/
│   ├── raw/                    # dados brutos (VRA mensal, aeroportos, companhias)
│   └── processed/              # base limpa (voos.parquet e amostra)
├── assets/style.css            # estilo do dashboard
├── figuras/                    # gráficos da EDA e screenshots dos dashboards
├── apresentacao.pdf            # apresentação em slides
├── RELATORIO.md                # relatório escrito do pipeline e dos insights
├── requirements.txt
└── README.md
```

## Os dois dashboards

Dashboard 1, Visão Geral: um painel executivo com os indicadores-chave e cinco
gráficos sintéticos, para entender o panorama em uma olhada (volume, mercado,
pontualidade, principais hubs e composição da operação por tipo de linha).

Dashboard 2, Exploração Interativa: quatro filtros (grupo/companhia, tipo de
voo, região e período), um seletor de métrica de pontualidade (% de atrasados ou
atraso médio em minutos) e sete visualizações de tipos diferentes (linha, barras,
heatmap, dispersão, histograma e mapa). Tudo reage em conjunto, e um guia de
leitura liga cada painel ao insight correspondente do relatório.

![Dashboard 2: Exploração Interativa](figuras/dashboard2_exploracao.png)

## Principais insights

1. Azul, LATAM e Gol concentram cerca de 95% do mercado doméstico.
2. A Azul é a maior em volume, mas a menos pontual das três, porque voa para
   mais aeroportos regionais.
3. Os atrasos crescem ao longo do dia (efeito cascata): a manhã é pontual e o
   fim de tarde é o pior momento, com pico nas sextas-feiras.
4. Voos internacionais atrasam mais (22,5%) que os domésticos (15,8%).
5. A movimentação se concentra no Sudeste, e poucos hubs respondem pela maior
   parte dos voos.

A análise completa, com gráficos e interpretação, está em
[RELATORIO.md](RELATORIO.md) e nos slides em `apresentacao.pdf`.

## Atendimento aos requisitos

- [x] Dataset público com mais de 10.000 registros (~988 mil voos)
- [x] Pelo menos dois arquivos distintos (12 CSVs do VRA, aeroportos e companhias)
- [x] Aquisição com Pandas
- [x] **Crawler de coleta automática de dados — bônus +1** (`src/crawler.py`, baixa os 12 CSVs do VRA + aeroportos das fontes oficiais sem login)
- [x] Integração por concat (meses) e merge (dimensões)
- [x] Limpeza: nulos, duplicatas, inconsistências e padronização
- [x] Transformação: novas variáveis (atraso, atrasado, rota, distância, recortes temporais)
- [x] EDA com estatística, gráficos e insights interpretados
- [x] Dashboard 1 (visão geral / executivo)
- [x] Dashboard 2 (sete visualizações, quatro filtros, comparações, seleção de categorias)
- [x] Boas práticas de comunicação visual (baseadas em Storytelling with Data)

## Ferramentas por etapa

Cada parte do projeto usa a ferramenta adequada — em especial, **o dashboard
interativo é feito em Dash + Plotly, não em Matplotlib**. O Matplotlib/Seaborn
gera apenas as figuras estáticas da análise exploratória que aparecem no
relatório.

| Etapa | Ferramenta | Arquivo |
|---|---|---|
| Coleta automática (crawler, bônus) | requests | `src/crawler.py` |
| Pipeline (integração, limpeza, transformação) | pandas, numpy | `src/preprocessing.py` |
| Análise exploratória (gráficos **estáticos** do relatório) | **matplotlib, seaborn** | `src/analise_exploratoria.py` |
| **Dashboards interativos** (no link público, com filtros) | **Dash, Plotly** | `src/app.py` |

Em resumo: a análise exploratória (as figuras `figuras/01_*.png`…`08_*.png`) foi
feita em **matplotlib/seaborn**; os **dois dashboards interativos**, em
**Dash e Plotly**.

Stack completo: Python, Pandas, NumPy, Matplotlib, Seaborn, Dash e Plotly.
