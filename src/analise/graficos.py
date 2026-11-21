"""Graficos estaticos (matplotlib/seaborn) que respondem as perguntas P1-P6.

Cada funcao recebe a base integrada e devolve a Figure; `gerar_todos` salva os PNGs
em reports/figures/. Comparacoes entre series de escalas diferentes (preco x dolar)
usam indice base 100 em um unico eixo, em vez de eixo duplo.
"""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src import config
from src.analise import estatistica
from src.analise.estilo import CORES, DESTAQUE_EVENTO, DIVERGENTE, NOMES, aplicar_estilo_matplotlib
from src.utils import get_logger

log = get_logger(__name__)
GEADA = pd.Timestamp(config.GEADA_2021)


def _marcar_geada(ax, rotulo=True):
    ax.axvline(GEADA, color=DESTAQUE_EVENTO, linewidth=1, linestyle="--")
    if rotulo:
        ax.annotate("Geada jul/2021", xy=(GEADA, 1), xycoords=("data", "axes fraction"),
                    xytext=(4, -12), textcoords="offset points", color=DESTAQUE_EVENTO, fontsize=9)


def p1_evolucao(df: pd.DataFrame) -> plt.Figure:
    fig, eixos = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    for ax, produto in zip(eixos, config.COMMODITIES):
        ax.plot(df["data"], df[f"preco_{produto}"], color=CORES[produto], label="Nominal")
        ax.plot(df["data"], df[f"preco_{produto}_real"], color=CORES[produto], alpha=0.45, linestyle=":", label="Real (IPCA)")
        ax.set_title(f"{NOMES[produto]} — R$/saca de 60 kg")
        ax.legend(loc="upper left")
        _marcar_geada(ax, rotulo=produto == "cafe")
    fig.suptitle("P1. Evolução dos preços (indicador Cepea/Esalq)", x=0.01, ha="left", fontweight="bold")
    return fig


def p2_sazonalidade(df: pd.DataFrame) -> plt.Figure:
    fig, eixos = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
    for ax, produto in zip(eixos, config.COMMODITIES):
        col = f"preco_{produto}_real"
        d = df[["ano", "mes", col, f"periodo_safra_{produto}"]].dropna().copy()
        d["relativo"] = d[col] / d.groupby("ano")[col].transform("mean") * 100
        sns.boxplot(data=d, x="mes", y="relativo", hue=f"periodo_safra_{produto}",
                    palette={"safra": CORES["safra"], "entressafra": CORES["entressafra"]},
                    dodge=False, fliersize=1.5, linewidth=0.8, ax=ax)
        _, p = estatistica.sazonalidade(df, produto)
        ax.axhline(100, color="#52514e", linewidth=0.8)
        ax.set_title(f"{NOMES[produto]} (Kruskal-Wallis p={p:.3g})")
        ax.set_xlabel("Mês")
        ax.set_ylabel("Preço relativo à média do ano (=100)")
        ax.legend(title=None, loc="upper left")
    fig.suptitle("P2. Sazonalidade: preço real por mês, safra × entressafra", x=0.01, ha="left", fontweight="bold")
    return fig


def p3_dolar(df: pd.DataFrame) -> plt.Figure:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4.8), gridspec_kw={"width_ratios": [1.6, 1]})
    base = df.set_index("data")[["preco_cafe", "preco_soja", "dolar"]].dropna()
    indice = base / base.iloc[0] * 100
    for col, chave in [("dolar", "dolar"), ("preco_cafe", "cafe"), ("preco_soja", "soja")]:
        ax1.plot(indice.index, indice[col], color=CORES[chave], label=NOMES[chave])
    ax1.axhline(100, color="#52514e", linewidth=0.8)
    ax1.set_title(f"Índice base 100 ({indice.index[0]:%d/%m/%Y})")
    ax1.legend(loc="upper left")

    for produto, desloc in zip(config.COMMODITIES, (-0.2, 0.2)):
        cc = estatistica.correlacao_cruzada(df, produto, defasagens=range(0, 21))
        ax2.bar(cc["defasagem"] + desloc, cc["correlacao"], width=0.4, color=CORES[produto], label=NOMES[produto])
    ax2.axhline(0, color="#52514e", linewidth=0.8)
    ax2.set_title("Correlação: var. preço (t) × var. dólar (t−k)")
    ax2.set_xlabel("Defasagem k (dias úteis)")
    ax2.legend()
    fig.suptitle("P3. Preços acompanham o dólar? Com que defasagem?", x=0.01, ha="left", fontweight="bold")
    return fig


def p4_clima(df: pd.DataFrame) -> plt.Figure:
    fig, eixos = plt.subplots(3, 1, figsize=(11, 9), sharex=True, gridspec_kw={"height_ratios": [1.2, 1, 1]})
    eixos[0].plot(df["data"], df["preco_cafe"], color=CORES["cafe"])
    eixos[0].set_title("Café arábica (R$/saca)")
    for regiao in config.REGIOES:
        eixos[1].plot(df["data"], df[f"chuva_90d_{regiao}"], color=CORES[regiao], label=NOMES[regiao], linewidth=1.2)
        eixos[2].plot(df["data"], df[f"temp_min_30d_{regiao}"], color=CORES[regiao], label=NOMES[regiao], linewidth=1.2)
    eixos[1].set_title("Chuva acumulada em 90 dias (mm)")
    eixos[2].set_title("Menor temperatura mínima em 30 dias (°C)")
    eixos[2].axhline(3, color=DESTAQUE_EVENTO, linewidth=0.8, linestyle=":")
    eixos[1].legend(loc="upper left", ncol=3)
    for ax in eixos:
        _marcar_geada(ax, rotulo=ax is eixos[0])
    fig.suptitle("P4. Clima nas regiões produtoras × preço do café", x=0.01, ha="left", fontweight="bold")
    return fig


def p5_geada(df: pd.DataFrame) -> plt.Figure:
    janela = df[(df["data"] >= GEADA - pd.Timedelta(days=120)) & (df["data"] <= GEADA + pd.Timedelta(days=240))]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ref = janela[janela["data"] < GEADA].tail(1)
    for produto in config.COMMODITIES:
        col = f"preco_{produto}"
        ax.plot(janela["data"], janela[col] / ref[col].iloc[0] * 100, color=CORES[produto], label=NOMES[produto])
    ax.axvspan(pd.Timestamp("2021-06-30"), pd.Timestamp("2021-07-21"), color=DESTAQUE_EVENTO, alpha=0.08)
    _marcar_geada(ax)
    ax.axhline(100, color="#52514e", linewidth=0.8)
    ax.set_ylabel("Índice (véspera da geada = 100)")
    ax.legend(loc="upper left")
    ax.set_title("P5. Impacto da geada de julho/2021 — soja como grupo de controle")
    return fig


def p6_correlacoes(df: pd.DataFrame) -> plt.Figure:
    variaveis = ["dolar", "dolar_lag20", "chuva_30d", "chuva_90d", "dias_secos_30d", "temp_min_30d", "temp_max_30d", "anomalia_chuva_90d"]
    fig, eixos = plt.subplots(1, 2, figsize=(13, 5.5))
    for ax, produto in zip(eixos, config.COMMODITIES):
        cols = [f"preco_{produto}", f"{produto}_var_21d", f"{produto}_var_fut_63d"] + variaveis
        corr = df[cols].corr(method="spearman").loc[cols[:3], variaveis]
        sns.heatmap(corr, cmap=DIVERGENTE, vmin=-1, vmax=1, center=0, annot=True, fmt=".2f",
                    annot_kws={"size": 8}, linewidths=2, linecolor="#fcfcfb", cbar=ax is eixos[1], ax=ax)
        ax.set_title(NOMES[produto])
        ax.grid(False)
        ax.tick_params(axis="x", rotation=45)
    fig.suptitle("P6. Correlação de Spearman: preço/variações × câmbio e clima", x=0.01, ha="left", fontweight="bold")
    return fig


FIGURAS = {
    "p1_evolucao_precos": p1_evolucao,
    "p2_sazonalidade": p2_sazonalidade,
    "p3_preco_dolar": p3_dolar,
    "p4_clima_regioes": p4_clima,
    "p5_geada_2021": p5_geada,
    "p6_correlacoes": p6_correlacoes,
}


def gerar_todos(df: pd.DataFrame) -> list:
    aplicar_estilo_matplotlib()
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    salvos = []
    for nome, funcao in FIGURAS.items():
        fig = funcao(df)
        caminho = config.FIGURES / f"{nome}.png"
        fig.savefig(caminho)
        plt.close(fig)
        salvos.append(caminho)
        log.info("reports/figures/%s.png", nome)
    return salvos
