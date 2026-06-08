# ✈️ Aviação Civil Brasileira em 2024
### Relatório do Projeto Final — Estudos Avançados de Banco de Dados (Pipeline + Dashboard)

> **Fonte principal:** ANAC — Voo Regular Ativo (VRA), ano de 2024
> **Volume analisado:** ~988 mil voos regulares · 62 companhias · 385 aeroportos
> **Ferramentas:** Python · Pandas · Matplotlib · Dash · Plotly

**Disciplina:** Estudos Avançados de Banco de Dados · **Professor:** José Guilherme Picolo · **PUC-Campinas**

**Integrantes:**

| Nome | RA |
|---|---|
| Felipe Cosmo Granziol | 24021602 |
| Guilherme Bars | 24014122 |
| Gustavo Kurten | 24008150 |
| João Celso | 24012463 |
| Pedro Tiezo Sales Shimizu | 24005158 |

---

## 1. Tema e pergunta de pesquisa

A aviação comercial é um termômetro da economia e da mobilidade do país. Com os
dados abertos da ANAC, este projeto responde, de forma orientada a dados:

> **Quem voa no Brasil, quando voa e onde estão os gargalos de pontualidade?**

A escolha do tema atende aos critérios do projeto: base pública, mais de 10.000
registros, múltiplos arquivos e grande potencial de **análise comparativa**
(companhias, regiões, rotas, períodos) e geração de **insights**.

---

## 2. Fonte dos dados

Foram integradas **três fontes públicas**:

| Fonte | Arquivos | Conteúdo |
|---|---|---|
| **VRA — ANAC** (`sistemas.anac.gov.br/dadosabertos`) | 12 CSVs mensais | Cada voo regular: empresa, origem, destino, horários previsto/real, situação |
| **OurAirports** | `airports.csv` | Cidade, UF, região e coordenadas de cada aeroporto (por código ICAO) |
| **Dimensão de companhias** | `dim_companhias.csv` | Nome, país e grupo de cada companhia (a partir de ANAC/OpenFlights) |

> Cada arquivo mensal do VRA tem ~85 mil voos. **Um único mês já supera o
> mínimo de 10 mil registros**; o ano inteiro chega a quase 1 milhão.

**Bônus — coleta automática:** o script `src/crawler.py` baixa sozinho os 12
arquivos mensais do VRA e a base de aeroportos, direto das fontes oficiais, sem
necessidade de login.

---

## 3. Pipeline de preparação dos dados

```
 Aquisição → Integração → Limpeza → Transformação → Análise → Dashboard
```

### 3.1 Aquisição
Leitura dos 12 CSVs mensais com Pandas (`sep=";"`, pulando a linha de metadado
"Atualizado em:" no topo de cada arquivo).

### 3.2 Integração
- **Concatenação (`concat`):** os 12 meses são empilhados em uma única base de
  ~988 mil linhas.
- **Merge:** a base é cruzada com a dimensão de **aeroportos** (duas vezes — para
  origem e destino) e com a dimensão de **companhias**, enriquecendo cada voo com
  cidade, UF, região, coordenadas e nome da empresa.

### 3.3 Limpeza
- Coluna **`Código Justificativa`** estava **100% vazia** → removida.
- Conversão dos 4 horários para `datetime` (formato ISO8601, tratando registros
  com segundos fracionados que falhavam no parsing padrão).
- **Padronização** de categóricos (situação, códigos ICAO em maiúsculas).
- Remoção de **duplicatas** e de voos sem nenhum horário utilizável.
- Voos realizados sem horário **previsto** foram mantidos (usando a partida real
  como referência temporal), preservando o volume sem perder ~3% dos registros.

### 3.4 Transformação (novas variáveis)
A partir dos dados crus, foram criadas variáveis derivadas para a análise:

| Variável | Como é calculada |
|---|---|
| `atraso_partida_min`, `atraso_chegada_min` | diferença entre horário real e previsto |
| `atrasado` | chegada com mais de **15 min** de atraso (padrão do setor) |
| `cancelado` | situação do voo = cancelado |
| `rota` | origem → destino |
| `distancia_km` | distância geográfica (fórmula de **Haversine** sobre lat/lon) |
| `mes`, `dia_semana`, `hora_prevista`, `periodo_dia` | recortes temporais |
| `tipo_voo` | doméstico × internacional (pelo país dos aeroportos) |

Resultado: **base limpa e enriquecida com 46 colunas**, salva em
`data/processed/voos.parquet`.

---

## 4. Análise exploratória e insights

### Insight 1 — Um mercado de três gigantes
Azul, LATAM e Gol concentram **~95% do mercado doméstico**. A Azul é a maior em
volume (40%), seguida de LATAM (30%) e Gol (25%).

![Top 3 companhias](figuras/03_top3_companhias.png)

> **Por que importa:** é um oligopólio. Decisões de poucas empresas afetam preço
> e oferta no país inteiro — e, como veremos, a líder em volume não é a líder em
> pontualidade.

### Insight 2 — A maior companhia é a menos pontual
Entre as três grandes, a **Azul tem a maior taxa de atrasos** (16,7%), contra
14,5% da Gol e 14,8% da LATAM. A explicação está no modelo de negócio: a Azul
voa para muitos **aeroportos regionais menores**, mais sujeitos a atrasos
operacionais e com menos folga na malha.

### Insight 3 — Os atrasos se acumulam ao longo do dia
Voos da **manhã são pontuais**; a taxa de atraso **cresce de ~8% (madrugada)
para ~22% no fim da tarde/noite**. É o clássico **efeito cascata**: um atraso
cedo se propaga para os voos seguintes da mesma aeronave/tripulação.

![Atraso por hora](figuras/04_atraso_por_hora.png)

O mapa de calor abaixo cruza dia da semana × hora e mostra o ponto mais crítico:
**quinta e sexta à noite**.

![Heatmap de atrasos](figuras/08_heatmap_atrasos.png)

> **Aplicação prática:** quem precisa de pontualidade (conexões, compromissos)
> deve preferir **voos pela manhã** e evitar fim de tarde de quinta/sexta.

### Insight 4 — Sazonalidade do volume e dos cancelamentos
O volume tem **picos em julho** (férias de inverno) e no fim de ano, com **vale
em fevereiro**. Já os **cancelamentos** são mais altos no **início do ano**
(janeiro ~5%), período de chuvas de verão no Sudeste.

![Sazonalidade](figuras/02_sazonalidade.png)

### Insight 5 — Internacionais atrasam mais que domésticos
Voos internacionais chegam atrasados em **22,5%** dos casos, contra **15,8%** dos
domésticos. Rotas longas, congestionamento nos grandes hubs e procedimentos de
imigração/alfândega ampliam o atraso acumulado.

![Doméstico x Internacional](figuras/06_dom_x_internacional.png)

### Insight 6 — O Brasil voa pelo Sudeste
A movimentação é **fortemente concentrada**: São Paulo (Guarulhos + Congonhas),
seguido de Brasília, Rio e Belo Horizonte, respondem pela maior parte dos voos.

![Top aeroportos](figuras/07_top_aeroportos.png)
![Mapa de aeroportos](figuras/mapa_aeroportos.png)

---

## 5. Os dashboards

### Dashboard 1 — Visão Geral (executivo)
Indicadores-chave e gráficos sintéticos para entender o panorama em segundos.

![Dashboard 1](figuras/dashboard1_visao_geral.png)

### Dashboard 2 — Exploração Interativa
4 filtros (companhia, tipo de voo, região, período) e 7 visualizações que reagem
em conjunto, permitindo recortar os dados e comparar grupos livremente.

![Dashboard 2](figuras/dashboard2_exploracao.png)

---

## 6. Conclusão

A análise do VRA 2024 revela uma aviação brasileira **concentrada** (3 empresas,
Sudeste), com padrões de pontualidade **previsíveis** (pioram ao longo do dia e
no fim de semana) e diferenças claras entre **perfis de operação** (a líder Azul
paga o preço da capilaridade regional). Esses padrões, comunicados pelos dois
dashboards, transformam ~1 milhão de linhas de dados crus em informação útil para
o passageiro e para o setor.

---

### Como reproduzir
Instruções completas no **[README.md](README.md)**. Em resumo:
`crawler.py` → `preprocessing.py` → `app.py`.

*Projeto desenvolvido em Python com Pandas, Matplotlib, Dash e Plotly.*
