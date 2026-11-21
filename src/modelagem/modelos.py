"""Regressao Linear e Random Forest como ferramentas de analise (P6).

Para cada commodity sao treinados dois alvos:
* `nivel`     -> preco (R$/saca) explicado por cambio, clima e sazonalidade;
* `var_21d`   -> variacao % do preco em 21 dias uteis explicada pela variacao do
                 dolar na mesma janela e pelo clima observado ANTES da janela.

O R2 fora da amostra tende a ser baixo/negativo: precos de commodities mudam de
patamar e os modelos nao extrapolam. O objetivo aqui e comparar a importancia dos
grupos de variaveis (cambio x clima x sazonalidade), nao prever precos; por isso
reporta-se tambem um baseline (media do treino) e o R2 de ajuste na serie completa.

Todas as features de clima sao defasadas em 21 dias uteis (sem vazamento do futuro)
e a validacao usa TimeSeriesSplit (treino sempre anterior ao teste).
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src import config
from src.analise.estilo import CORES, NOMES, aplicar_estilo_matplotlib
from src.utils import get_logger

log = get_logger(__name__)

DEFASAGEM_CLIMA = 21
CLIMA = ["chuva_30d", "chuva_90d", "chuva_180d", "dias_secos_30d", "temp_min_30d", "temp_max_30d", "anomalia_chuva_90d"]
GRUPOS = {
    "nivel": {
        "cambio": ["dolar_lag1", "dolar_lag5", "dolar_lag20"],
        "clima": [f"{c}_lag{DEFASAGEM_CLIMA}" for c in CLIMA],
        "sazonalidade": ["mes_sin", "mes_cos"],
    },
    "var_21d": {
        "cambio": ["dolar_var_21d"],
        "clima": [f"{c}_lag{DEFASAGEM_CLIMA}" for c in CLIMA],
        "sazonalidade": ["mes_sin", "mes_cos"],
    },
}


def preparar(df: pd.DataFrame, produto: str, alvo: str) -> tuple[pd.DataFrame, pd.Series, dict]:
    d = df.sort_values("data").set_index("data")
    for c in CLIMA:
        d[f"{c}_lag{DEFASAGEM_CLIMA}"] = d[c].shift(DEFASAGEM_CLIMA)
    grupos = GRUPOS[alvo]
    features = [f for cols in grupos.values() for f in cols]
    y_col = f"preco_{produto}" if alvo == "nivel" else f"{produto}_var_21d"
    d = d.dropna(subset=features + [y_col])
    return d[features], d[y_col], grupos


def modelos() -> dict:
    return {
        "baseline_media": DummyRegressor(strategy="mean"),
        "linear": make_pipeline(StandardScaler(), LinearRegression()),
        "random_forest": RandomForestRegressor(n_estimators=300, min_samples_leaf=5, n_jobs=-1, random_state=42),
    }


def avaliar(X: pd.DataFrame, y: pd.Series, n_splits: int = 5) -> pd.DataFrame:
    linhas = []
    for fold, (tr, te) in enumerate(TimeSeriesSplit(n_splits=n_splits).split(X), 1):
        for nome, modelo in modelos().items():
            modelo.fit(X.iloc[tr], y.iloc[tr])
            pred = modelo.predict(X.iloc[te])
            linhas.append(
                {
                    "modelo": nome,
                    "fold": fold,
                    "teste_inicio": X.index[te[0]].date(),
                    "MAE": mean_absolute_error(y.iloc[te], pred),
                    "RMSE": float(np.sqrt(mean_squared_error(y.iloc[te], pred))),
                    "R2": r2_score(y.iloc[te], pred),
                }
            )
    return pd.DataFrame(linhas)


def importancias(X: pd.DataFrame, y: pd.Series, grupos: dict) -> pd.DataFrame:
    """Coeficientes padronizados (LR) e feature importance (RF) treinados em toda a serie."""
    ms = modelos()
    lr, rf = ms["linear"].fit(X, y), ms["random_forest"].fit(X, y)
    log.info("R2 de ajuste (serie completa, poder explicativo): linear=%.3f  random_forest=%.3f", lr.score(X, y), rf.score(X, y))
    coef = lr[-1].coef_
    grupo_de = {f: g for g, cols in grupos.items() for f in cols}
    tabela = pd.DataFrame(
        {
            "feature": X.columns,
            "grupo": [grupo_de[f] for f in X.columns],
            "coef_padronizado": coef,
            "importancia_lr": np.abs(coef) / np.abs(coef).sum(),
            "importancia_rf": rf.feature_importances_,
        }
    )
    return tabela.sort_values("importancia_rf", ascending=False)


def grafico_importancia_grupos(imp: pd.DataFrame) -> plt.Figure:
    aplicar_estilo_matplotlib()
    alvos = imp["alvo"].unique()
    fig, eixos = plt.subplots(1, len(alvos), figsize=(6 * len(alvos), 4), sharey=True)
    eixos = np.atleast_1d(eixos)
    for ax, alvo in zip(eixos, alvos):
        g = imp[imp["alvo"] == alvo].groupby(["produto", "grupo"])[["importancia_lr", "importancia_rf"]].sum().reset_index()
        grupos = sorted(g["grupo"].unique())
        x = np.arange(len(grupos))
        for i, produto in enumerate(config.COMMODITIES):
            valores = g[g["produto"] == produto].set_index("grupo").reindex(grupos)["importancia_rf"]
            ax.bar(x + (i - 0.5) * 0.38, valores, width=0.36, color=CORES[produto], label=NOMES[produto])
        ax.set_xticks(x, grupos)
        ax.set_title(f"Alvo: {alvo}")
        ax.set_ylabel("Importância Random Forest (soma do grupo)")
    eixos[0].legend()
    fig.suptitle("P6. Quanto câmbio × clima explicam cada commodity", x=0.01, ha="left", fontweight="bold")
    return fig


def executar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    config.MODELOS.mkdir(parents=True, exist_ok=True)
    metricas, imps = [], []
    for produto in config.COMMODITIES:
        for alvo in GRUPOS:
            X, y, grupos = preparar(df, produto, alvo)
            if len(X) < 200:
                log.warning("%s/%s: apenas %d linhas, modelo ignorado", produto, alvo, len(X))
                continue
            m = avaliar(X, y)
            m.insert(0, "alvo", alvo)
            m.insert(0, "produto", produto)
            metricas.append(m)
            imp = importancias(X, y, grupos)
            imp.insert(0, "alvo", alvo)
            imp.insert(0, "produto", produto)
            imps.append(imp)
            resumo = m.groupby("modelo")[["MAE", "RMSE", "R2"]].mean().round(3)
            log.info("%s / %s (%d obs):\n%s", produto, alvo, len(X), resumo.to_string())

    if not metricas:
        log.error("Dados insuficientes para modelar. Complete a serie de precos (backfill ou planilhas do CEPEA).")
        return pd.DataFrame(), pd.DataFrame()
    metricas = pd.concat(metricas, ignore_index=True)
    imps = pd.concat(imps, ignore_index=True)
    metricas.to_csv(config.MODELOS / "metricas_por_fold.csv", index=False)
    metricas.groupby(["produto", "alvo", "modelo"])[["MAE", "RMSE", "R2"]].mean().round(3).to_csv(config.MODELOS / "metricas_resumo.csv")
    imps.to_csv(config.MODELOS / "importancias.csv", index=False)
    fig = grafico_importancia_grupos(imps)
    fig.savefig(config.FIGURES / "p6_importancia_grupos.png")
    plt.close(fig)
    log.info("reports/modelos/: metricas e importancias salvas")
    return metricas, imps
