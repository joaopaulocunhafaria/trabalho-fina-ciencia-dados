"""Series temporais do Banco Central (SGS): dolar comercial (venda) e IPCA.

Uso: python -m src.coleta.bcb
"""

import pandas as pd

from src import config
from src.utils import criar_sessao, get_logger

log = get_logger(__name__)


def baixar_serie(nome: str, codigo: int, inicio=config.DATA_INICIO, fim=config.DATA_FIM) -> pd.DataFrame:
    """Consulta a API ano a ano (o SGS limita o intervalo de cada consulta)."""
    sessao = criar_sessao()
    partes = []
    for ano in range(inicio.year, fim.year + 1):
        params = {
            "formato": "json",
            "dataInicial": f"01/01/{ano}" if ano > inicio.year else inicio.strftime("%d/%m/%Y"),
            "dataFinal": f"31/12/{ano}" if ano < fim.year else fim.strftime("%d/%m/%Y"),
        }
        resp = sessao.get(config.SGS_URL.format(codigo=codigo), params=params, timeout=config.TIMEOUT)
        if resp.status_code == 404:  # sem dados no intervalo (ex.: IPCA do mes corrente)
            continue
        resp.raise_for_status()
        partes.append(pd.DataFrame(resp.json()))
    df = pd.concat(partes, ignore_index=True).rename(columns={"valor": nome})
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y").dt.date
    return df[["data", nome]]


def coletar() -> dict[str, pd.DataFrame]:
    config.RAW_BCB.mkdir(parents=True, exist_ok=True)
    saida = {}
    for nome, codigo in config.SGS_SERIES.items():
        df = baixar_serie(nome, codigo)
        df.to_csv(config.RAW_BCB / f"{nome}.csv", index=False)
        log.info("SGS %s (%d): %d observacoes", nome, codigo, len(df))
        saida[nome] = df
    return saida


if __name__ == "__main__":
    coletar()
