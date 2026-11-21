"""Integracao das fontes limpas em uma base unica indexada por data.

* Clima: as janelas moveis (chuva acumulada 30/90 dias etc.) sao calculadas no
  calendario diario completo, antes de reduzir aos dias uteis, para nao perder
  fins de semana e feriados. A chuva dos dias sem cotacao e somada ao proximo
  dia util e as temperaturas sao resumidas (media, minima, maxima).
* Precos e cambio: forward fill de no maximo 3 dias uteis (feriados isolados).
"""

import pandas as pd

from src import config
from src.utils import get_logger

log = get_logger(__name__)

LIMITE_FFILL = 3
REGIAO_MEDIA = "media"


def clima_com_janelas(clima: pd.DataFrame) -> pd.DataFrame:
    """Adiciona a regiao 'media' (3 regioes) e as variaveis acumuladas em janelas moveis."""
    variaveis = ["chuva_mm", "temp_med", "temp_min", "temp_max", "umidade"]
    media = clima.groupby("data", as_index=False)[variaveis].mean()
    media["regiao"] = REGIAO_MEDIA
    clima = pd.concat([clima, media], ignore_index=True)

    partes = []
    for regiao, df in clima.groupby("regiao"):
        df = df.set_index("data").sort_index().asfreq("D")
        df["regiao"] = regiao
        chuva = df["chuva_mm"]
        df["chuva_30d"] = chuva.rolling(30, min_periods=25).sum()
        df["chuva_90d"] = chuva.rolling(90, min_periods=80).sum()
        df["chuva_180d"] = chuva.rolling(180, min_periods=160).sum()
        df["dias_secos_30d"] = (chuva < 1).astype(float).where(chuva.notna()).rolling(30, min_periods=25).sum()
        df["temp_min_30d"] = df["temp_min"].rolling(30, min_periods=25).min()
        df["temp_max_30d"] = df["temp_max"].rolling(30, min_periods=25).mean()
        df["temp_med_30d"] = df["temp_med"].rolling(30, min_periods=25).mean()
        # anomalia de chuva: acumulado 90d menos a media historica do mesmo dia do ano
        clim = df["chuva_90d"].groupby(df.index.dayofyear).transform("mean")
        df["anomalia_chuva_90d"] = df["chuva_90d"] - clim
        partes.append(df.reset_index())
    return pd.concat(partes, ignore_index=True)


def _clima_em_dias_uteis(clima: pd.DataFrame, dias: pd.DatetimeIndex) -> pd.DataFrame:
    """Leva o clima diario para os dias de cotacao (formato longo por regiao)."""
    # cada dia do calendario e atribuido ao proximo dia util (sabado/domingo -> segunda)
    destino = pd.Series(dias, index=dias)
    partes = []
    for regiao, df in clima.groupby("regiao"):
        df = df.set_index("data").sort_index()
        df = df[(df.index >= dias.min() - pd.Timedelta(days=7)) & (df.index <= dias.max())]
        df["dia_util"] = destino.reindex(df.index, method="bfill").to_numpy()
        agregado = df.groupby("dia_util").agg(
            chuva_mm=("chuva_mm", "sum"),
            temp_med=("temp_med", "mean"),
            temp_min=("temp_min", "min"),
            temp_max=("temp_max", "max"),
            umidade=("umidade", "mean"),
        )
        janelas = [c for c in df.columns if c.endswith(("_30d", "_90d", "_180d"))]
        agregado = agregado.join(df[janelas])  # valor da janela no proprio dia util
        agregado.index.name = "data"
        agregado["regiao"] = regiao
        partes.append(agregado.reset_index())
    return pd.concat(partes, ignore_index=True)


def integrar(limpos: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Retorna (base_integrada larga, base_regional longa, clima_diario)."""
    precos = limpos["precos"].pivot_table(index="data", columns="produto", values="preco")
    precos.columns = [f"preco_{c}" for c in precos.columns]
    dolar = limpos["dolar"].set_index("data")[["dolar"]]

    dias = precos.index.union(dolar.index)
    dias = dias[(dias.dayofweek < 5) & (dias >= pd.Timestamp(config.DATA_INICIO))]
    base = pd.DataFrame(index=pd.DatetimeIndex(dias, name="data"))
    base = base.join(precos).join(dolar)

    internacional = limpos["internacional"]
    if not internacional.empty:
        base = base.join(internacional.set_index("data"))
    base = base.ffill(limit=LIMITE_FFILL)
    for ativo in ("cafe_ice", "soja_cbot"):
        if f"{ativo}_usd_saca" in base:
            base[f"{ativo}_brl_saca"] = base[f"{ativo}_usd_saca"] * base["dolar"]

    ipca = limpos["ipca"].copy()
    ipca["mes"] = ipca["data"].dt.to_period("M")
    base["ipca_mensal"] = base.index.to_period("M").map(ipca.set_index("mes")["ipca"])

    clima_diario = clima_com_janelas(limpos["clima_nasa"])
    regional = _clima_em_dias_uteis(clima_diario, base.index)

    # versao larga: clima medio sem sufixo + cada regiao com sufixo
    media = regional[regional["regiao"] == REGIAO_MEDIA].drop(columns="regiao").set_index("data")
    base = base.join(media)
    for regiao in config.REGIOES:
        r = regional[regional["regiao"] == regiao].drop(columns="regiao").set_index("data")
        base = base.join(r[["chuva_mm", "chuva_30d", "chuva_90d", "temp_min", "temp_min_30d", "temp_max_30d"]].add_suffix(f"_{regiao}"))

    regional = regional.merge(base[[c for c in base.columns if c.startswith("preco_")] + ["dolar"]], left_on="data", right_index=True)
    log.info("Base integrada: %d dias uteis x %d colunas", *base.shape)
    return base.reset_index(), regional, clima_diario
