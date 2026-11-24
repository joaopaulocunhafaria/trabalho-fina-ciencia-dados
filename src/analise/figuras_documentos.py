"""Figuras do artigo e dos slides, em PDF vetorial e no tamanho final de impressao.

Diferem das de `graficos.py` (notebooks/README) por serem desenhadas ja na largura em que
aparecem no documento: assim o texto nao encolhe, e o titulo fica so na legenda do LaTeX.

Uso: python -m src.analise.figuras_documentos
"""

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.ticker import FuncFormatter

from src import config
from src.analise import estatistica
from src.analise.estilo import CORES, DESTAQUE_EVENTO, DIVERGENTE, NOMES, aplicar_estilo_matplotlib

GEADA = pd.Timestamp(config.GEADA_2021)
COLUNA = 3.45  # largura (pol.) da coluna do IEEEtran
TAMANHOS = {
    "artigo": {"p1": (COLUNA, 3.5), "p2": (COLUNA, 3.7), "p3": (COLUNA, 3.9), "p4": (COLUNA, 4.4),
               "p5": (COLUNA, 2.3), "p6c": (COLUNA, 3.2), "p6i": (COLUNA, 2.1)},
    # 4:3, largura util de ~4,25 pol.; mesma fracao de coluna usada em slides.tex
    "slides": {"p1": (4.2, 1.8), "p2": (2.5, 1.75), "p3": (4.2, 1.7), "p4": (2.5, 2.35),
               "p5": (2.45, 1.7), "p6c": (4.2, 1.75), "p6i": (2.35, 1.55)},
}
EIXO_VARIAVEIS = {
    "dolar": "Dólar", "dolar_lag20": "Dólar (20 d antes)", "chuva_30d": "Chuva 30 d",
    "chuva_90d": "Chuva 90 d", "dias_secos_30d": "Dias secos 30 d", "temp_min_30d": "Temp. mín. 30 d",
    "temp_max_30d": "Temp. máx. 30 d", "anomalia_chuva_90d": "Anomalia chuva 90 d",
}


def _estilo():
    aplicar_estilo_matplotlib()
    plt.rcParams.update({
        "font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5,
        "ytick.labelsize": 6.5, "legend.fontsize": 6.5, "lines.linewidth": 0.9, "axes.titlepad": 4,
        "figure.facecolor": "white", "axes.facecolor": "white", "figure.constrained_layout.use": True,
        "savefig.bbox": None, "pdf.fonttype": 42, "grid.linewidth": 0.4, "axes.linewidth": 0.5,
        "xtick.major.size": 2, "ytick.major.size": 2, "axes.axisbelow": True,
    })


def _decimal(fmt):
    return FuncFormatter(lambda v, _: format(v, fmt).replace(".", ",").replace("-", "−"))


def _anos(ax, passo=1):
    ax.xaxis.set_major_locator(mdates.YearLocator(passo))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


def _geada(ax, rotulo=False):
    ax.axvline(GEADA, color=DESTAQUE_EVENTO, linewidth=0.8, linestyle="--",
               label="Geada jul/2021" if rotulo else None)


def _legenda(fig, ax, n):
    """Legenda acima de todos os eixos, fora da area de dados."""
    h, r = ax.get_legend_handles_labels()
    leg = fig.legend(h, r, loc="outside upper center", ncol=n, columnspacing=1.2, handlelength=1.6)
    for linha in leg.get_lines():
        linha.set_linewidth(1.4)


def p1(df, tam, doc):
    fig, eixos = plt.subplots(*((2, 1) if doc == "artigo" else (1, 2)), figsize=tam, sharex=True)
    for ax, produto in zip(eixos, config.COMMODITIES):
        cor = CORES[produto]
        ax.plot(df["data"], df[f"preco_{produto}"], color=cor, label="Nominal")
        ax.plot(df["data"], df[f"preco_{produto}_real"], color="#52514e", linewidth=0.8, linestyle=":", label="Real (IPCA)")
        _geada(ax, True)
        ax.set_title(NOMES[produto])
        ax.set_ylabel("R$/saca de 60 kg" if doc == "artigo" else "R$/saca")
        _anos(ax, 1 if doc == "artigo" else 2)
    h, r = eixos[0].get_legend_handles_labels()
    h2, _ = eixos[1].get_legend_handles_labels()
    fig.legend([h[0], h2[0], h[1], h[2]], ["Nominal (café)", "Nominal (soja)", r[1], r[2]],
               loc="outside upper center", ncol=4 if doc == "slides" else 2, handlelength=1.6)
    return fig


def p2(df, tam, doc):
    fig, eixos = plt.subplots(2, 1, figsize=tam, sharex=True, sharey=True)
    for ax, produto in zip(eixos, config.COMMODITIES):
        col, per = f"preco_{produto}_real", f"periodo_safra_{produto}"
        d = df[["ano", "mes", col, per]].dropna().copy()
        d["relativo"] = d[col] / d.groupby("ano")[col].transform("mean") * 100
        sns.boxplot(data=d, x="mes", y="relativo", hue=per, dodge=False, fliersize=0.8, linewidth=0.5, ax=ax,
                    hue_order=["safra", "entressafra"],
                    palette={"safra": CORES["safra"], "entressafra": CORES["entressafra"]}, legend=False)
        ax.axhline(100, color="#52514e", linewidth=0.6)
        ax.set_title(NOMES[produto])
        ax.set_xlabel("Mês" if ax is eixos[-1] else "")
        ax.set_ylabel("Índice")
    marcas = [plt.Rectangle((0, 0), 1, 1, color=CORES[c]) for c in ("safra", "entressafra")]
    fig.legend(marcas, ["Safra", "Entressafra"], loc="outside upper center", ncol=2, handlelength=1.2)
    return fig


def p3(df, tam, doc):
    kw = {"nrows": 2} if doc == "artigo" else {"ncols": 2, "width_ratios": [1.4, 1]}
    fig, (a, b) = plt.subplots(figsize=tam, **kw)
    base = df.set_index("data")[["dolar", "preco_cafe", "preco_soja"]].dropna()
    indice = base / base.iloc[0] * 100
    for col, chave in [("dolar", "dolar"), ("preco_cafe", "cafe"), ("preco_soja", "soja")]:
        a.plot(indice.index, indice[col], color=CORES[chave], label=NOMES[chave])
    a.axhline(100, color="#52514e", linewidth=0.5)
    a.set_title(f"(a) Índice ({indice.index[0]:%d/%m/%Y} = 100)")
    _anos(a, 1 if doc == "artigo" else 2)
    for produto, d in zip(config.COMMODITIES, (-0.2, 0.2)):
        cc = estatistica.correlacao_cruzada(df, produto, defasagens=range(0, 21))
        b.bar(cc["defasagem"] + d, cc["correlacao"], width=0.4, color=CORES[produto])
    b.axhline(0, color="#52514e", linewidth=0.5)
    b.set_xticks(range(0, 21, 5))
    b.yaxis.set_major_formatter(_decimal(".1f"))
    b.set_title("(b) Correlação × dólar")
    b.set_xlabel("Defasagem k (dias úteis)")
    _legenda(fig, a, 3)
    return fig


def p4(df, tam, doc):
    fig, eixos = plt.subplots(3, 1, figsize=tam, sharex=True)
    eixos[0].plot(df["data"], df["preco_cafe"], color=CORES["media"])
    for regiao in config.REGIOES:
        for ax, v in zip(eixos[1:], ("chuva_90d", "temp_min_30d")):
            ax.plot(df["data"], df[f"{v}_{regiao}"], color=CORES[regiao], label=NOMES[regiao], linewidth=0.7)
    titulos = ("(a) Café arábica (R$/saca)", "(b) Chuva acumulada em 90 dias (mm)",
               "(c) Menor temp. mínima em 30 dias (°C)")
    if doc == "slides":
        titulos = ("(a) Café (R$/saca)", "(b) Chuva em 90 dias (mm)", "(c) Mínima em 30 dias (°C)")
    for ax, t in zip(eixos, titulos):
        ax.set_title(t)
        _geada(ax, rotulo=ax is eixos[1])
    _anos(eixos[-1], 1 if doc == "artigo" else 2)
    _legenda(fig, eixos[1], 2)
    return fig


def p5(df, tam, doc):
    j = df[df["data"].between(GEADA - pd.Timedelta(days=120), GEADA + pd.Timedelta(days=240))]
    ref = j[j["data"] < GEADA].iloc[-1]
    fig, ax = plt.subplots(figsize=tam)
    for produto in config.COMMODITIES:
        ax.plot(j["data"], j[f"preco_{produto}"] / ref[f"preco_{produto}"] * 100, color=CORES[produto], label=NOMES[produto])
    _geada(ax, True)
    ax.axhline(100, color="#52514e", linewidth=0.5)
    ax.set_ylabel("Véspera da geada = 100")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2 if doc == "artigo" else 3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
    _legenda(fig, ax, 3 if doc == "artigo" else 2)
    return fig


def p6c(df, tam, doc):
    fig, eixos = plt.subplots(1, 2, figsize=tam, sharey=True)
    variaveis = list(EIXO_VARIAVEIS)
    for ax, produto in zip(eixos, config.COMMODITIES):
        alvos = [f"preco_{produto}", f"{produto}_var_21d", f"{produto}_var_fut_63d"]
        corr = df[alvos + variaveis].corr(method="spearman").loc[variaveis, alvos]
        textos = corr.map(lambda v: f"{v:.2f}".replace("-0.00", "0.00").replace(".", ",").replace("-", "−"))
        sns.heatmap(corr, cmap=DIVERGENTE, vmin=-0.5, vmax=0.5, center=0, annot=textos, fmt="", cbar=False,
                    annot_kws={"size": 6.5}, linewidths=1, linecolor="white", ax=ax)
        ax.set_title(NOMES[produto])
        ax.set_xticklabels(["Preço", "Var.\n21 d", "Var. fut.\n63 d"], rotation=0)
        ax.set_yticks(np.arange(len(variaveis)) + 0.5, list(EIXO_VARIAVEIS.values()), rotation=0)
        ax.tick_params(length=0)
        ax.grid(False)
    barra = fig.colorbar(eixos[-1].collections[0], ax=eixos, location="bottom", shrink=0.6, aspect=35, pad=0.02)
    barra.outline.set_visible(False)
    barra.set_ticks([-0.5, -0.25, 0, 0.25, 0.5])
    barra.ax.xaxis.set_major_formatter(_decimal(".2f"))
    return fig


def p6i(imp, tam, doc):
    fig, eixos = plt.subplots(1, 2, figsize=tam, sharey=True)
    grupos = {"cambio": "Câmbio", "clima": "Clima", "sazonalidade": "Sazon."}
    for ax, (alvo, titulo) in zip(eixos, {"nivel": "Nível do preço", "var_21d": "Variação em 21 d" if doc == "artigo" else "Var. 21 d"}.items()):
        g = imp[imp["alvo"] == alvo].groupby(["produto", "grupo"])["importancia_rf"].sum()
        for produto, d in zip(config.COMMODITIES, (-0.19, 0.19)):
            barras = ax.bar(np.arange(3) + d, g[produto].reindex(grupos), width=0.36, color=CORES[produto], label=NOMES[produto])
            if doc == "artigo":  # nos slides os rotulos se sobrepoem
                ax.bar_label(barras, fmt=lambda v: f"{v:.2f}".replace(".", ","), fontsize=5.5 if doc == "artigo" else 4, padding=1)
        ax.set_xticks(range(3), grupos.values(), fontsize=6.5 if doc == "artigo" else 5)
        ax.set_title(titulo)
        ax.set_ylim(0, 1)
        ax.set_yticks(np.arange(0, 1.01, 0.2))
        ax.grid(axis="x", visible=False)
        ax.yaxis.set_major_formatter(_decimal(".1f"))
    eixos[0].set_ylabel("Importância (soma do grupo)" if doc == "artigo" else "Importância")
    _legenda(fig, eixos[0], 2)
    return fig


FIGURAS = {"p1": (p1, "p1_evolucao_precos"), "p2": (p2, "p2_sazonalidade"), "p3": (p3, "p3_preco_dolar"),
           "p4": (p4, "p4_clima_regioes"), "p5": (p5, "p5_geada_2021"), "p6c": (p6c, "p6_correlacoes"),
           "p6i": (p6i, "p6_importancia_grupos")}


def gerar():
    _estilo()
    df = pd.read_csv(config.PROCESSED / "base_integrada.csv", parse_dates=["data"])
    imp = pd.read_csv(config.MODELOS / "importancias.csv")
    for doc, tamanhos in TAMANHOS.items():
        destino = config.RAIZ / "docs" / doc / "figuras"
        destino.mkdir(parents=True, exist_ok=True)
        for chave, (funcao, nome) in FIGURAS.items():
            fig = funcao(imp if chave == "p6i" else df, tamanhos[chave], doc)
            fig.savefig(destino / f"{nome}.pdf")
            plt.close(fig)


if __name__ == "__main__":
    gerar()
