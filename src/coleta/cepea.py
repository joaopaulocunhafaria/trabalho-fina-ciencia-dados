"""Leitura das series historicas do CEPEA/ESALQ (download manual).

O site do CEPEA bloqueia downloads automatizados, entao as planilhas devem ser
baixadas pelo navegador (ver README) e salvas em data/raw/cepea/ com o nome
`cafe.xls` e `soja.xls` (ou .xlsx). Este modulo apenas as le e padroniza.

Uso: python -m src.coleta.cepea
"""

import pandas as pd

from src import config
from src.utils import get_logger, parse_numero_br

log = get_logger(__name__)


def _ler_planilha(caminho) -> pd.DataFrame:
    try:
        # os .xls do CEPEA tem um defeito de estrutura (OLE) que o xlrd recusa por padrao
        kwargs = {"engine_kwargs": {"ignore_workbook_corruption": True}} if str(caminho).endswith(".xls") else {}
        return pd.read_excel(caminho, header=None, **kwargs)
    except Exception:
        # algumas exportacoes do CEPEA sao HTML com extensao .xls
        return pd.read_html(caminho, decimal=",", thousands=".")[0]


def ler_serie(produto: str) -> pd.DataFrame:
    arquivos = sorted(config.RAW_CEPEA.glob(f"{produto}.xls*"))
    if not arquivos:
        log.warning(
            "CEPEA %s ausente. Baixe em %s e salve como data/raw/cepea/%s.xls",
            produto, config.CEPEA_SERIES[produto], produto,
        )
        return pd.DataFrame(columns=["data", "produto", "preco", "fonte"])

    bruto = _ler_planilha(arquivos[0])
    # o cabecalho real comeca na linha cuja primeira celula e "Data"
    linha_cab = bruto.index[bruto.iloc[:, 0].astype(str).str.strip().str.lower() == "data"][0]
    df = bruto.iloc[linha_cab + 1 :, :2].copy()
    df.columns = ["data", "preco"]
    df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="coerce")
    df["preco"] = df["preco"].map(parse_numero_br)
    df = df.dropna()
    df = df[df["data"].dt.date >= config.DATA_INICIO]
    df["produto"] = produto
    df["fonte"] = "cepea"
    log.info("CEPEA %s: %d observacoes", produto, len(df))
    return df[["data", "produto", "preco", "fonte"]]


def coletar() -> pd.DataFrame:
    return pd.concat([ler_serie(p) for p in config.NA_PAGINAS], ignore_index=True)


if __name__ == "__main__":
    coletar()
