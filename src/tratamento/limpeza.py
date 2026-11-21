"""Padronizacao de cada fonte bruta (data/raw) em tabelas limpas (data/interim).

Padroes adotados: datas em `datetime64` (coluna `data`), valores numericos em
float com ponto decimal, precos em R$/saca de 60 kg, temperaturas em graus C e
chuva em mm. Valores sentinela (-999 da NASA, -9999 do INMET) viram NaN.
"""

import numpy as np
import pandas as pd

from src import config
from src.coleta import cepea
from src.coleta.inmet import ler_csv_estacao
from src.utils import get_logger

log = get_logger(__name__)


def _salvar(df: pd.DataFrame, nome: str) -> pd.DataFrame:
    config.INTERIM.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.INTERIM / f"{nome}.csv", index=False)
    log.info("interim/%s.csv: %d linhas", nome, len(df))
    return df


def limpar_precos() -> pd.DataFrame:
    """Une CEPEA (prioritario, se baixado) e o crawler do Noticias Agricolas.

    As duas fontes publicam o mesmo indicador Cepea/Esalq; o crawler cobre os dias
    que faltarem na planilha (ex.: os mais recentes).
    """
    partes = []
    arquivo_na = config.RAW_NA / "cotacoes.csv"
    if arquivo_na.exists():
        na = pd.read_csv(arquivo_na, parse_dates=["data"])[["data", "produto", "preco", "fonte"]]
        partes.append(na)
    cep = cepea.coletar()
    if not cep.empty:
        partes.append(cep)
    if not partes:
        raise FileNotFoundError("Nenhuma fonte de precos encontrada em data/raw. Rode a coleta antes.")

    df = pd.concat(partes, ignore_index=True).dropna(subset=["preco"])
    df = df[df["preco"] > 0]
    df["prioridade"] = (df["fonte"] == "cepea").astype(int)
    df = df.sort_values(["data", "produto", "prioridade"]).drop_duplicates(["data", "produto"], keep="last")
    return _salvar(df.drop(columns="prioridade").reset_index(drop=True), "precos")


def limpar_bcb() -> tuple[pd.DataFrame, pd.DataFrame]:
    dolar = pd.read_csv(config.RAW_BCB / "dolar.csv", parse_dates=["data"])
    dolar["dolar"] = pd.to_numeric(dolar["dolar"], errors="coerce")
    ipca = pd.read_csv(config.RAW_BCB / "ipca.csv", parse_dates=["data"])
    ipca["ipca"] = pd.to_numeric(ipca["ipca"], errors="coerce")
    return _salvar(dolar.dropna(), "dolar"), _salvar(ipca.dropna(), "ipca")


def limpar_internacional() -> pd.DataFrame:
    """Futuros em USD/saca de 60 kg (KC=F em cents/lb, ZS=F em cents/bushel)."""
    fatores = {"cafe_ice": config.LIBRAS_POR_SACA / 100, "soja_cbot": config.BUSHELS_POR_SACA / 100}
    partes = []
    for ativo, fator in fatores.items():
        caminho = config.RAW_YF / f"{ativo}.csv"
        if not caminho.exists():
            continue
        df = pd.read_csv(caminho, parse_dates=["data"])
        df[f"{ativo}_usd_saca"] = df["fechamento"] * fator
        partes.append(df.set_index("data")[[f"{ativo}_usd_saca"]])
    if not partes:
        return pd.DataFrame(columns=["data"])
    return _salvar(pd.concat(partes, axis=1).reset_index(), "internacional")


def limpar_nasa() -> pd.DataFrame:
    partes = [pd.read_csv(config.RAW_NASA / f"{r}.csv", parse_dates=["data"]) for r in config.REGIOES]
    df = pd.concat(partes, ignore_index=True)
    variaveis = list(config.NASA_PARAMETROS.values())
    df[variaveis] = df[variaveis].where(df[variaveis] > -900)
    df = df.dropna(subset=variaveis, how="all")
    return _salvar(df, "clima_nasa")


def _coluna(df: pd.DataFrame, *trechos: str) -> str | None:
    for col in df.columns:
        if all(t in col.upper() for t in trechos):
            return col
    return None


def agregar_inmet_diario(bruto: pd.DataFrame, min_horas: int = 20) -> pd.DataFrame:
    """Converte registros horarios (UTC) em diarios no horario de Brasilia."""
    col_data = bruto.columns[0]
    col_hora = bruto.columns[1]
    hora = bruto[col_hora].astype(str).str.extract(r"(\d{2})")[0].astype(float)
    instante = pd.to_datetime(bruto[col_data].astype(str).str.replace("/", "-"), errors="coerce") + pd.to_timedelta(hora, unit="h")
    colunas = {
        "chuva_mm": _coluna(bruto, "PRECIPITA"),
        "temp_med": _coluna(bruto, "BULBO SECO"),
        "temp_max": _coluna(bruto, "TEMPERATURA M", "X", "HORA ANT"),
        "temp_min": _coluna(bruto, "TEMPERATURA M", "NIMA NA HORA ANT"),
        "umidade": _coluna(bruto, "UMIDADE RELATIVA DO AR, HORARIA"),
    }
    df = pd.DataFrame({nome: pd.to_numeric(bruto[c], errors="coerce") for nome, c in colunas.items() if c})
    df["data"] = (instante - pd.Timedelta(hours=3)).dt.normalize()
    df = df.dropna(subset=["data"])

    agregado = df.groupby("data").agg(
        chuva_mm=("chuva_mm", "sum"),
        horas_chuva=("chuva_mm", "count"),
        temp_med=("temp_med", "mean"),
        temp_min=("temp_min", "min"),
        temp_max=("temp_max", "max"),
        umidade=("umidade", "mean"),
    )
    agregado.loc[agregado["horas_chuva"] < min_horas, "chuva_mm"] = np.nan
    return agregado.drop(columns="horas_chuva").reset_index()


def limpar_inmet() -> pd.DataFrame:
    partes = []
    for regiao in config.REGIOES:
        for caminho in sorted(config.RAW_INMET.glob(f"{regiao}_*.csv")):
            diario = agregar_inmet_diario(ler_csv_estacao(caminho))
            diario.insert(1, "regiao", regiao)
            partes.append(diario)
    if not partes:
        log.warning("Sem arquivos do INMET; validacao do clima sera pulada")
        return pd.DataFrame()
    df = pd.concat(partes, ignore_index=True).drop_duplicates(["data", "regiao"])
    return _salvar(df, "clima_inmet")


def executar() -> dict[str, pd.DataFrame]:
    dolar, ipca = limpar_bcb()
    return {
        "precos": limpar_precos(),
        "dolar": dolar,
        "ipca": ipca,
        "internacional": limpar_internacional(),
        "clima_nasa": limpar_nasa(),
        "clima_inmet": limpar_inmet(),
    }
