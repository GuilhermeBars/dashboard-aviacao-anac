"""
preprocessing.py — Pipeline de Ciência de Dados (ANAC / VRA 2024)
=================================================================

Executa todas as etapas pedidas no projeto, na ordem:

  1. AQUISIÇÃO      -> lê os 12 CSVs mensais do VRA + aeroportos + companhias
  2. INTEGRAÇÃO     -> concatena os meses (concat) e junta as dimensões (merge)
  3. LIMPEZA        -> nulos, duplicatas, inconsistências, padronização
  4. TRANSFORMAÇÃO  -> novas variáveis (atraso, atrasado, rota, distância, etc.)

Resultado: data/processed/voos.parquet  (base limpa e enriquecida)
           data/processed/amostra_voos.csv (amostra de 2.000 linhas p/ inspeção)

Uso:
    python src/preprocessing.py
"""

from __future__ import annotations

import glob
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PASTA_RAW = RAIZ / "data" / "raw"
PASTA_PROC = RAIZ / "data" / "processed"

# Limiar de atraso considerado "voo atrasado" (padrão usado no setor: 15 min)
LIMIAR_ATRASO_MIN = 15
# Acima disso, tratamos como provável erro de digitação/fuso (remoção de inconsistência)
ATRASO_MAX_PLAUSIVEL_MIN = 12 * 60

# Mapeamentos de apoio -------------------------------------------------------

TIPO_LINHA = {
    "N": "Nacional (passageiros)",
    "I": "Internacional (passageiros)",
    "C": "Cargueiro nacional",
    "G": "Cargueiro internacional",
    "X": "Outros / ligação",
}

DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
MESES_NOME = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
              "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# UF -> Região (para análises regionais)
UF_REGIAO = {
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte",
    "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste",
    "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste",
    "MS": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}


# ---------------------------------------------------------------------------
# 1. AQUISIÇÃO
# ---------------------------------------------------------------------------

def ler_vra() -> pd.DataFrame:
    """Lê todos os CSVs mensais do VRA presentes em data/raw/."""
    arquivos = sorted(glob.glob(str(PASTA_RAW / "VRA_*.csv")))
    if not arquivos:
        raise FileNotFoundError(
            "Nenhum arquivo VRA encontrado em data/raw/. "
            "Rode antes: python src/crawler.py"
        )
    print(f"[1/4] Aquisição: lendo {len(arquivos)} arquivos mensais do VRA...")
    partes = []
    for arq in arquivos:
        # skiprows=1 pula a linha de metadado 'Atualizado em: ...'
        df = pd.read_csv(arq, sep=";", skiprows=1, dtype=str, encoding="utf-8")
        partes.append(df)
        print(f"      - {Path(arq).name}: {len(df):>7} voos")
    # INTEGRAÇÃO por concatenação (empilhamento dos meses)
    voos = pd.concat(partes, ignore_index=True)
    print(f"      => concatenado (concat): {len(voos):,} voos no total")
    return voos


def ler_aeroportos() -> pd.DataFrame:
    """Lê a base OurAirports e prepara a dimensão de aeroportos."""
    cam = PASTA_RAW / "airports.csv"
    aero = pd.read_csv(cam, dtype=str)
    aero = aero[["ident", "name", "municipality", "iso_country",
                 "iso_region", "latitude_deg", "longitude_deg"]].copy()
    aero["lat"] = pd.to_numeric(aero["latitude_deg"], errors="coerce")
    aero["lon"] = pd.to_numeric(aero["longitude_deg"], errors="coerce")
    # UF a partir de 'BR-SP' -> 'SP'
    uf = aero["iso_region"].str.split("-").str[-1]
    aero["uf"] = np.where(aero["iso_country"].eq("BR"), uf, np.nan)
    aero["regiao"] = aero["uf"].map(UF_REGIAO)
    return aero[["ident", "name", "municipality", "iso_country",
                 "uf", "regiao", "lat", "lon"]]


def ler_companhias() -> pd.DataFrame:
    return pd.read_csv(PASTA_RAW / "dim_companhias.csv", dtype=str)


# ---------------------------------------------------------------------------
# 2. INTEGRAÇÃO (merge das dimensões)
# ---------------------------------------------------------------------------

def integrar(voos: pd.DataFrame, aero: pd.DataFrame,
             comp: pd.DataFrame) -> pd.DataFrame:
    print("[2/4] Integração: merge com aeroportos (origem/destino) e companhias...")

    # Renomeia colunas do VRA para nomes limpos
    voos = voos.rename(columns={
        "ICAO Empresa Aérea": "empresa_icao",
        "Número Voo": "numero_voo",
        "Código Autorização (DI)": "di",
        "Código Tipo Linha": "tipo_linha",
        "ICAO Aeródromo Origem": "origem_icao",
        "ICAO Aeródromo Destino": "destino_icao",
        "Partida Prevista": "partida_prevista",
        "Partida Real": "partida_real",
        "Chegada Prevista": "chegada_prevista",
        "Chegada Real": "chegada_real",
        "Situação Voo": "situacao",
    })

    # merge companhias (com fallback para códigos não mapeados)
    voos = voos.merge(comp, left_on="empresa_icao",
                      right_on="codigo_icao", how="left")
    nao_mapeadas = voos["empresa"].isna().sum()
    voos["empresa"] = voos["empresa"].fillna("Outras (" + voos["empresa_icao"] + ")")
    voos["grupo"] = voos["grupo"].fillna("Outras")
    voos["pais"] = voos["pais"].fillna("Não identificado")
    voos["tipo_servico"] = voos["tipo_servico"].fillna("Passageiros")
    voos = voos.drop(columns=["codigo_icao"])
    print(f"      - companhias: {nao_mapeadas:,} voos de empresas raras "
          f"agrupadas como 'Outras'")

    # merge aeroportos de ORIGEM
    aero_o = aero.add_prefix("origem_").rename(columns={"origem_ident": "origem_icao"})
    voos = voos.merge(aero_o, on="origem_icao", how="left")
    # merge aeroportos de DESTINO
    aero_d = aero.add_prefix("destino_").rename(columns={"destino_ident": "destino_icao"})
    voos = voos.merge(aero_d, on="destino_icao", how="left")

    print(f"      => base integrada: {voos.shape[0]:,} linhas x {voos.shape[1]} colunas")
    return voos


# ---------------------------------------------------------------------------
# 3. LIMPEZA
# ---------------------------------------------------------------------------

def limpar(voos: pd.DataFrame) -> pd.DataFrame:
    print("[3/4] Limpeza: nulos, duplicatas, inconsistências, padronização...")
    n0 = len(voos)

    # 3.1 Coluna 100% vazia -> descartar (Código Justificativa)
    if "Código Justificativa" in voos.columns:
        voos = voos.drop(columns=["Código Justificativa"])
        print("      - coluna 'Código Justificativa' (100% nula) removida")

    # 3.2 Datas: converter os 4 timestamps para datetime
    # (format ISO8601 lida com casos que vêm com segundos fracionados, ex.: ".100000000")
    cols_dt = ["partida_prevista", "partida_real",
               "chegada_prevista", "chegada_real"]
    for c in cols_dt:
        voos[c] = pd.to_datetime(voos[c], format="ISO8601", errors="coerce")

    # 3.3 Padronização de categóricos
    voos["situacao"] = voos["situacao"].str.strip().str.capitalize()  # Realizado/Cancelado
    voos["empresa_icao"] = voos["empresa_icao"].str.strip().str.upper()
    voos["origem_icao"] = voos["origem_icao"].str.strip().str.upper()
    voos["destino_icao"] = voos["destino_icao"].str.strip().str.upper()
    voos["tipo_linha_desc"] = voos["tipo_linha"].map(TIPO_LINHA).fillna("Outros")

    # 3.4 Duplicatas exatas
    dup = voos.duplicated().sum()
    voos = voos.drop_duplicates()
    if dup:
        print(f"      - {dup:,} linhas duplicadas removidas")

    # 3.5 Inconsistência: remover apenas voos sem NENHUM horário utilizável
    # (nem previsto, nem real) — esses são impossíveis de posicionar no tempo.
    # Voos realizados sem horário PREVISTO são mantidos: usaremos a partida REAL
    # como referência temporal (ver transformação), preservando o volume.
    sem_horario = voos["partida_prevista"].isna() & voos["partida_real"].isna()
    voos = voos[~sem_horario]
    if sem_horario.sum():
        print(f"      - {sem_horario.sum():,} voos sem nenhum horário utilizável "
              f"removidos")

    print(f"      => {n0 - len(voos):,} linhas removidas na limpeza "
          f"({len(voos):,} restantes)")
    return voos


# ---------------------------------------------------------------------------
# 4. TRANSFORMAÇÃO (novas variáveis)
# ---------------------------------------------------------------------------

def _haversine(lat1, lon1, lat2, lon2):
    """Distância em km entre dois pontos (origem/destino) — variável derivada."""
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def transformar(voos: pd.DataFrame) -> pd.DataFrame:
    print("[4/4] Transformação: criando novas variáveis...")

    # Situação / cancelamento
    voos["cancelado"] = voos["situacao"].eq("Cancelado")

    # Tempo (em minutos) — atrasos de partida e chegada
    voos["atraso_partida_min"] = (
        (voos["partida_real"] - voos["partida_prevista"]).dt.total_seconds() / 60
    )
    voos["atraso_chegada_min"] = (
        (voos["chegada_real"] - voos["chegada_prevista"]).dt.total_seconds() / 60
    )

    # Remoção de inconsistências em atrasos absurdos (provável erro de fuso/registro)
    for c in ["atraso_partida_min", "atraso_chegada_min"]:
        fora = voos[c].abs() > ATRASO_MAX_PLAUSIVEL_MIN
        voos.loc[fora, c] = np.nan

    # Voo atrasado: chegou mais de 15 min depois do previsto (só voos realizados)
    voos["atrasado"] = (voos["atraso_chegada_min"] > LIMIAR_ATRASO_MIN)

    # Duração prevista e real do voo
    voos["duracao_prevista_min"] = (
        (voos["chegada_prevista"] - voos["partida_prevista"]).dt.total_seconds() / 60
    )
    voos["duracao_real_min"] = (
        (voos["chegada_real"] - voos["partida_real"]).dt.total_seconds() / 60
    )

    # Recortes temporais a partir da partida prevista; quando ela não existe
    # (voo realizado sem previsto), usa a partida real como referência.
    dt = voos["partida_prevista"].fillna(voos["partida_real"])
    voos["ano"] = dt.dt.year
    voos["mes"] = dt.dt.month
    voos["mes_nome"] = voos["mes"].apply(
        lambda m: MESES_NOME[int(m) - 1] if pd.notna(m) else np.nan)
    voos["dia_semana"] = dt.dt.dayofweek
    voos["dia_semana_nome"] = voos["dia_semana"].apply(
        lambda d: DIAS_SEMANA[int(d)] if pd.notna(d) else np.nan)
    voos["hora_prevista"] = dt.dt.hour

    def periodo(h):
        if pd.isna(h):
            return np.nan
        h = int(h)
        if h < 6:
            return "Madrugada"
        if h < 12:
            return "Manhã"
        if h < 18:
            return "Tarde"
        return "Noite"
    voos["periodo_dia"] = voos["hora_prevista"].apply(periodo)

    # Rota e tipo de voo (doméstico x internacional, a partir do país dos aeroportos)
    voos["rota"] = voos["origem_icao"] + "→" + voos["destino_icao"]
    ambos_br = voos["origem_iso_country"].eq("BR") & voos["destino_iso_country"].eq("BR")
    voos["tipo_voo"] = np.where(ambos_br, "Doméstico", "Internacional")

    # Distância em km (variável derivada via Haversine)
    voos["distancia_km"] = _haversine(
        voos["origem_lat"], voos["origem_lon"],
        voos["destino_lat"], voos["destino_lon"]
    ).round(0)

    print(f"      => {voos.shape[1]} colunas finais")
    return voos


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------

def main() -> None:
    PASTA_PROC.mkdir(parents=True, exist_ok=True)

    voos = ler_vra()
    aero = ler_aeroportos()
    comp = ler_companhias()

    voos = integrar(voos, aero, comp)
    voos = limpar(voos)
    voos = transformar(voos)

    # Restringe ao ano-calendário de 2024 (descarta poucas dezenas de voos que
    # cruzam a virada do ano e mantém a narrativa do estudo consistente)
    antes = len(voos)
    voos = voos[voos["ano"].eq(2024)]
    print(f"      - {antes - len(voos)} voos fora de 2024 descartados")

    # Seleciona e ordena colunas finais
    colunas = [
        "ano", "mes", "mes_nome", "dia_semana", "dia_semana_nome",
        "hora_prevista", "periodo_dia",
        "empresa_icao", "empresa", "grupo", "pais", "tipo_servico",
        "numero_voo", "tipo_linha", "tipo_linha_desc", "tipo_voo",
        "origem_icao", "origem_name", "origem_municipality", "origem_uf",
        "origem_regiao", "origem_iso_country", "origem_lat", "origem_lon",
        "destino_icao", "destino_name", "destino_municipality", "destino_uf",
        "destino_regiao", "destino_iso_country", "destino_lat", "destino_lon",
        "rota", "distancia_km",
        "partida_prevista", "partida_real", "chegada_prevista", "chegada_real",
        "situacao", "cancelado", "atrasado",
        "atraso_partida_min", "atraso_chegada_min",
        "duracao_prevista_min", "duracao_real_min",
    ]
    voos = voos[colunas]

    destino_parquet = PASTA_PROC / "voos.parquet"
    voos.to_parquet(destino_parquet, index=False)
    voos.sample(min(2000, len(voos)), random_state=42).to_csv(
        PASTA_PROC / "amostra_voos.csv", index=False)

    print("\n================ RESUMO ================")
    print(f"Voos finais            : {len(voos):,}")
    print(f"Período                : {voos['partida_prevista'].min()} "
          f"a {voos['partida_prevista'].max()}")
    print(f"Companhias             : {voos['empresa'].nunique()}")
    print(f"Aeroportos de origem   : {voos['origem_icao'].nunique()}")
    print(f"% cancelados           : {voos['cancelado'].mean()*100:.1f}%")
    real = voos[~voos['cancelado']]
    print(f"% atrasados (>15min)   : {real['atrasado'].mean()*100:.1f}%")
    print(f"Atraso médio chegada   : {real['atraso_chegada_min'].mean():.1f} min")
    print(f"Arquivo salvo          : {destino_parquet}")
    print("========================================")


if __name__ == "__main__":
    main()
