"""Analises estatisticas que respondem as perguntas de pesquisa P1-P6."""

import numpy as np
import pandas as pd
from scipy import stats

from src import config

DEFASAGENS = range(0, 31)


def resumo_evolucao(df: pd.DataFrame) -> pd.DataFrame:
    """P1: preco medio, minimo e maximo por ano e variacao no ano (nominal)."""
    linhas = []
    for produto in config.COMMODITIES:
        col = f"preco_{produto}"
        anual = df.groupby("ano")[col].agg(["mean", "min", "max", "first", "last"])
        anual["variacao_ano_pct"] = (anual["last"] / anual["first"] - 1) * 100
        anual["produto"] = produto
        linhas.append(anual.drop(columns=["first", "last"]).round(2).reset_index())
    return pd.concat(linhas, ignore_index=True)


def sazonalidade(df: pd.DataFrame, produto: str) -> tuple[pd.DataFrame, float]:
    """P2: preco relativo a media do ano (remove tendencia) por mes + teste de Kruskal-Wallis.

    Retorna a tabela por mes e o p-valor (p < 0.05 sugere diferenca entre meses).
    """
    col = f"preco_{produto}_real"
    d = df[["data", "ano", "mes", col]].dropna().copy()
    d["preco_relativo"] = d[col] / d.groupby("ano")[col].transform("mean") * 100
    grupos = [g["preco_relativo"].to_numpy() for _, g in d.groupby("mes")]
    p_valor = stats.kruskal(*grupos).pvalue if len(grupos) > 1 else np.nan
    tabela = d.groupby("mes")["preco_relativo"].agg(["mean", "median", "std"]).round(2)
    tabela["periodo"] = np.where(tabela.index.isin(config.MESES_SAFRA[produto]), "safra", "entressafra")
    return tabela.reset_index(), p_valor


def correlacao_cruzada(df: pd.DataFrame, produto: str, var_exogena: str = "dolar_var_1d",
                       defasagens=DEFASAGENS, frequencia: str | None = None) -> pd.DataFrame:
    """P3: corr(variacao do preco em t, variacao do dolar em t-k) para k em `defasagens`.

    Usa variacoes (e nao niveis) para evitar correlacoes espurias entre series com tendencia.
    Com `frequencia='W'` as variacoes sao semanais.
    """
    serie = df.set_index("data")[[f"preco_{produto}", "dolar"]].dropna()
    if frequencia:
        serie = serie.resample(frequencia).last()
        preco, exog = serie.iloc[:, 0].pct_change(), serie["dolar"].pct_change()
    else:
        preco = df.set_index("data")[f"{produto}_var_1d"]
        exog = df.set_index("data")[var_exogena]
    linhas = []
    for k in defasagens:
        par = pd.concat([preco, exog.shift(k)], axis=1).dropna()
        r, p = stats.pearsonr(par.iloc[:, 0], par.iloc[:, 1]) if len(par) > 10 else (np.nan, np.nan)
        linhas.append({"defasagem": k, "correlacao": r, "p_valor": p, "n": len(par)})
    return pd.DataFrame(linhas)


def repasse_cambial(df: pd.DataFrame, produto: str) -> dict:
    """P3: elasticidade preco-cambio por regressao log-log das variacoes mensais (beta ~ % repassado)."""
    mensal = df.set_index("data")[[f"preco_{produto}", "dolar"]].resample("ME").last().dropna()
    dl = np.log(mensal).diff().dropna()
    res = stats.linregress(dl["dolar"], dl[f"preco_{produto}"])
    return {"produto": produto, "elasticidade": res.slope, "r2": res.rvalue**2, "p_valor": res.pvalue, "meses": len(dl)}


def clima_vs_preco_futuro(df: pd.DataFrame, produto: str = "cafe", horizonte: str = "63d") -> pd.DataFrame:
    """P4: correlacao de Spearman entre clima recente e a variacao do preco nos ~3 meses seguintes."""
    alvo = f"{produto}_var_fut_{horizonte}"
    variaveis = [c for c in df.columns if c.startswith(("chuva_30d", "chuva_90d", "temp_min_30d", "temp_max_30d"))]
    variaveis += [c for c in ["dias_secos_30d", "anomalia_chuva_90d"] if c in df]
    linhas = []
    for v in variaveis:
        par = df[[v, alvo]].dropna()
        rho, p = stats.spearmanr(par[v], par[alvo])
        linhas.append({"variavel_clima": v, "spearman": rho, "p_valor": p, "n": len(par)})
    return pd.DataFrame(linhas).sort_values("spearman", key=abs, ascending=False)


def impacto_geada(df: pd.DataFrame, janelas=(30, 90, 180)) -> pd.DataFrame:
    """P5: variacao do preco apos a geada de 20/07/2021, cafe x soja (controle)."""
    geada = pd.Timestamp(config.GEADA_2021)
    serie = df.set_index("data")
    linhas = []
    for produto in config.COMMODITIES:
        col = f"preco_{produto}"
        antes = serie.loc[geada - pd.Timedelta(days=30): geada - pd.Timedelta(days=1), col].mean()
        linha = {"produto": produto, "media_30d_antes": round(antes, 2)}
        for j in janelas:
            depois = serie.loc[geada: geada + pd.Timedelta(days=j), col]
            linha[f"media_{j}d_depois"] = round(depois.mean(), 2)
            linha[f"var_{j}d_pct"] = round((depois.mean() / antes - 1) * 100, 1)
            linha[f"maximo_{j}d"] = round(depois.max(), 2)
        linhas.append(linha)
    return pd.DataFrame(linhas)


def sensibilidade(df: pd.DataFrame) -> pd.DataFrame:
    """P6: resumo comparativo de sensibilidade ao cambio e ao clima por commodity."""
    linhas = []
    for produto in config.COMMODITIES:
        rep = repasse_cambial(df, produto)
        clima = clima_vs_preco_futuro(df, produto)
        linhas.append(
            {
                "produto": produto,
                "corr_diaria_dolar_t0": correlacao_cruzada(df, produto, defasagens=[0])["correlacao"].iloc[0],
                "elasticidade_cambio_mensal": rep["elasticidade"],
                "r2_cambio_mensal": rep["r2"],
                "max_abs_spearman_clima": clima["spearman"].abs().max(),
                "variavel_clima_mais_associada": clima["variavel_clima"].iloc[0],
            }
        )
    return pd.DataFrame(linhas).round(3)
