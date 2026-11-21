"""Cotacoes internacionais (futuros) do cafe arabica (ICE) e da soja (CBOT) via Yahoo Finance.

Usadas como complemento: preco internacional x cambio (P3/P6).
Uso: python -m src.coleta.mercado_internacional
"""

from datetime import timedelta

import pandas as pd
import yfinance as yf

from src import config
from src.utils import get_logger

log = get_logger(__name__)


def coletar() -> pd.DataFrame:
    config.RAW_YF.mkdir(parents=True, exist_ok=True)
    partes = []
    for nome, ticker in config.YF_TICKERS.items():
        df = yf.download(
            ticker,
            start=config.DATA_INICIO.isoformat(),
            end=(config.DATA_FIM + timedelta(days=1)).isoformat(),
            progress=False,
            auto_adjust=False,
        )
        if df.empty:
            log.warning("Yahoo Finance nao retornou dados para %s", ticker)
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename_axis("data").reset_index()[["data", "Close"]].rename(columns={"Close": "fechamento"})
        df.insert(1, "ativo", nome)
        df.insert(2, "ticker", ticker)
        df.to_csv(config.RAW_YF / f"{nome}.csv", index=False)
        log.info("Yahoo Finance %s (%s): %d pregoes", nome, ticker, len(df))
        partes.append(df)
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


if __name__ == "__main__":
    coletar()
