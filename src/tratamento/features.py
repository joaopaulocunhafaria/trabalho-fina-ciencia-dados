"""Engenharia de atributos sobre a base integrada (dias uteis)."""

import numpy as np
import pandas as pd

from src import config

LAGS_DOLAR = (1, 5, 20)
DIAS_UTEIS_MES = 21


def adicionar_calendario(df: pd.DataFrame) -> pd.DataFrame:
    df["ano"] = df["data"].dt.year
    df["mes"] = df["data"].dt.month
    df["mes_sin"] = np.sin(2 * np.pi * df["mes"] / 12)
    df["mes_cos"] = np.cos(2 * np.pi * df["mes"] / 12)
    for produto, meses in config.MESES_SAFRA.items():
        df[f"periodo_safra_{produto}"] = np.where(df["mes"].isin(meses), "safra", "entressafra")
    return df


def adicionar_defasagens_e_variacoes(df: pd.DataFrame) -> pd.DataFrame:
    for lag in LAGS_DOLAR:
        df[f"dolar_lag{lag}"] = df["dolar"].shift(lag)
    df["dolar_var_1d"] = df["dolar"].pct_change(fill_method=None) * 100
    df["dolar_var_21d"] = df["dolar"].pct_change(DIAS_UTEIS_MES, fill_method=None) * 100

    for produto in config.COMMODITIES:
        col = f"preco_{produto}"
        if col not in df:
            continue
        df[f"{produto}_var_1d"] = df[col].pct_change(fill_method=None) * 100
        df[f"{produto}_var_21d"] = df[col].pct_change(DIAS_UTEIS_MES, fill_method=None) * 100
        df[f"{produto}_mm20"] = df[col].rolling(20, min_periods=15).mean()
        df[f"{produto}_mm60"] = df[col].rolling(60, min_periods=45).mean()
        # variacao futura (alvo de modelos/analises: o que acontece DEPOIS do clima observado)
        df[f"{produto}_var_fut_21d"] = (df[col].shift(-DIAS_UTEIS_MES) / df[col] - 1) * 100
        df[f"{produto}_var_fut_63d"] = (df[col].shift(-63) / df[col] - 1) * 100
    return df


def adicionar_deflacao(df: pd.DataFrame) -> pd.DataFrame:
    """Precos reais em R$ do ultimo mes com IPCA disponivel."""
    ipca_mensal = df.groupby(df["data"].dt.to_period("M"))["ipca_mensal"].first()
    indice = (1 + ipca_mensal.fillna(0) / 100).cumprod()
    referencia = indice[ipca_mensal.last_valid_index()]
    fator = df["data"].dt.to_period("M").map(referencia / indice)
    for produto in config.COMMODITIES:
        if f"preco_{produto}" in df:
            df[f"preco_{produto}_real"] = df[f"preco_{produto}"] * fator
    return df


def adicionar_eventos(df: pd.DataFrame) -> pd.DataFrame:
    geada = pd.Timestamp(config.GEADA_2021)
    df["dias_desde_geada_2021"] = (df["data"] - geada).dt.days
    df["pos_geada_2021"] = df["data"].between(geada, geada + pd.Timedelta(days=180)).astype(int)
    return df


def criar_features(base: pd.DataFrame) -> pd.DataFrame:
    df = base.sort_values("data").reset_index(drop=True)
    df = adicionar_calendario(df)
    df = adicionar_defasagens_e_variacoes(df)
    df = adicionar_deflacao(df)
    return adicionar_eventos(df)
