"""Relatorio de qualidade: cobertura, lacunas, outliers (IQR) e validacao cruzada de fontes."""

import pandas as pd

from src import config
from src.coleta import cepea
from src.utils import get_logger

log = get_logger(__name__)


def outliers_iqr(serie: pd.Series, k: float = 1.5) -> pd.Series:
    """Mascara booleana dos pontos fora de [Q1 - k*IQR, Q3 + k*IQR]."""
    q1, q3 = serie.quantile([0.25, 0.75])
    iqr = q3 - q1
    return (serie < q1 - k * iqr) | (serie > q3 + k * iqr)


def cobertura(base: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    linhas = []
    for col in colunas:
        s = base.set_index("data")[col]
        validos = s.dropna()
        linhas.append(
            {
                "variavel": col,
                "inicio": validos.index.min().date() if len(validos) else None,
                "fim": validos.index.max().date() if len(validos) else None,
                "observacoes": len(validos),
                "faltantes_pct": round(100 * s.isna().mean(), 1),
            }
        )
    return pd.DataFrame(linhas)


def maiores_lacunas(base: pd.DataFrame, coluna: str, n: int = 5) -> pd.DataFrame:
    datas = base.loc[base[coluna].notna(), "data"].sort_values()
    saltos = datas.diff().dt.days
    idx = saltos.nlargest(n).index
    return pd.DataFrame({"de": datas.shift().loc[idx].dt.date, "ate": datas.loc[idx].dt.date, "dias": saltos.loc[idx].astype(int)})


def validar_clima(nasa: pd.DataFrame, inmet: pd.DataFrame) -> pd.DataFrame:
    """Correlacao NASA POWER x INMET por regiao (chuva mensal e temperatura diaria)."""
    if inmet.empty:
        return pd.DataFrame()
    m = nasa.merge(inmet, on=["data", "regiao"], suffixes=("_nasa", "_inmet"))
    linhas = []
    for regiao, df in m.groupby("regiao"):
        mensal = df.set_index("data")[["chuva_mm_nasa", "chuva_mm_inmet"]].resample("MS").sum(min_count=20)
        linhas.append(
            {
                "regiao": regiao,
                "dias_em_comum": len(df),
                "corr_chuva_mensal": round(mensal.corr().iloc[0, 1], 3),
                "corr_temp_med_diaria": round(df["temp_med_nasa"].corr(df["temp_med_inmet"]), 3),
                "corr_temp_min_diaria": round(df["temp_min_nasa"].corr(df["temp_min_inmet"]), 3),
                "vies_temp_min_C": round((df["temp_min_nasa"] - df["temp_min_inmet"]).mean(), 2),
            }
        )
    return pd.DataFrame(linhas)


def validar_precos(precos_na: pd.DataFrame, precos_cepea: pd.DataFrame) -> pd.DataFrame:
    if precos_cepea.empty or precos_na.empty:
        return pd.DataFrame()
    m = precos_na.merge(precos_cepea, on=["data", "produto"], suffixes=("_na", "_cepea"))
    m["dif_abs"] = (m["preco_na"] - m["preco_cepea"]).abs()
    return m.groupby("produto").agg(dias_em_comum=("dif_abs", "size"), dif_media=("dif_abs", "mean"), dif_max=("dif_abs", "max")).reset_index()


def _md(df: pd.DataFrame) -> str:
    if df.empty:
        return "_sem dados_\n"
    cab = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "---|" * len(df.columns)
    linhas = ["| " + " | ".join(map(str, r)) + " |" for r in df.itertuples(index=False)]
    return "\n".join([cab, sep, *linhas]) + "\n"


def gerar_relatorio(base: pd.DataFrame, limpos: dict[str, pd.DataFrame]) -> str:
    colunas = [c for c in ["preco_cafe", "preco_soja", "dolar", "cafe_ice_usd_saca", "soja_cbot_usd_saca", "ipca_mensal", "chuva_mm", "temp_med"] if c in base]
    partes = ["# Relatório de qualidade dos dados\n", f"Gerado a partir de `{config.BASE_INTEGRADA.relative_to(config.RAIZ)}` ({len(base)} dias úteis).\n"]
    partes += ["## Cobertura por variável\n", _md(cobertura(base, colunas))]

    for produto in config.COMMODITIES:
        col = f"preco_{produto}"
        if col not in base:
            continue
        partes += [f"## Maiores lacunas — {col}\n", _md(maiores_lacunas(base, col))]
        var = base.set_index("data")[f"{produto}_var_1d"].dropna()
        mask = outliers_iqr(var, k=3)
        top = var[mask].abs().sort_values(ascending=False).head(10)
        tabela = pd.DataFrame({"data": top.index.date, "variacao_1d_pct": var.loc[top.index].round(2).values})
        partes += [
            f"## Outliers de variação diária (IQR, k=3) — {produto}\n",
            f"{int(mask.sum())} dias atípicos de {len(var)}. Maiores:\n\n",
            _md(tabela),
            "\nVerificar se coincidem com eventos reais (ex.: geada de jul/2021) antes de remover.\n",
        ]

    arquivo_na = config.RAW_NA / "cotacoes.csv"
    precos_na = pd.read_csv(arquivo_na, parse_dates=["data"]) if arquivo_na.exists() else pd.DataFrame()
    partes += [
        "## Validação: Notícias Agrícolas × CEPEA\n",
        _md(validar_precos(precos_na, cepea.coletar())),
        "## Validação: NASA POWER × INMET\n",
        _md(validar_clima(limpos["clima_nasa"], limpos["clima_inmet"])),
    ]
    texto = "\n".join(partes)
    config.REPORTS.mkdir(parents=True, exist_ok=True)
    (config.REPORTS / "qualidade.md").write_text(texto, encoding="utf-8")
    log.info("reports/qualidade.md gerado")
    return texto
