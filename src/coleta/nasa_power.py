"""Clima diario (chuva, temperatura, umidade) da API NASA POWER por regiao cafeeira.

Uso: python -m src.coleta.nasa_power
"""

import pandas as pd

from src import config
from src.utils import criar_sessao, get_logger

log = get_logger(__name__)


def baixar_regiao(regiao: str, inicio=config.DATA_INICIO, fim=config.DATA_FIM) -> pd.DataFrame:
    info = config.REGIOES[regiao]
    params = {
        "parameters": ",".join(config.NASA_PARAMETROS),
        "community": "AG",
        "latitude": info["lat"],
        "longitude": info["lon"],
        "start": inicio.strftime("%Y%m%d"),
        "end": fim.strftime("%Y%m%d"),
        "format": "JSON",
    }
    resp = criar_sessao().get(config.NASA_URL, params=params, timeout=120)
    resp.raise_for_status()
    dados = resp.json()["properties"]["parameter"]
    df = pd.DataFrame(dados).rename(columns=config.NASA_PARAMETROS)
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df = df.rename_axis("data").reset_index()
    df.insert(1, "regiao", regiao)
    return df


def coletar() -> pd.DataFrame:
    config.RAW_NASA.mkdir(parents=True, exist_ok=True)
    partes = []
    for regiao in config.REGIOES:
        df = baixar_regiao(regiao)
        df.to_csv(config.RAW_NASA / f"{regiao}.csv", index=False)
        log.info("NASA POWER %s: %d dias", regiao, len(df))
        partes.append(df)
    return pd.concat(partes, ignore_index=True)


if __name__ == "__main__":
    coletar()
