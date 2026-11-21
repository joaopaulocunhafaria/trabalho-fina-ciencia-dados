"""Paleta e estilo comuns aos graficos estaticos (matplotlib) e interativos (plotly).

Cores categoricas em ordem fixa (paleta validada para daltonismo); cada entidade
tem sempre a mesma cor, independentemente do filtro aplicado.
"""

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
GRADE = "#e4e3df"
DESTAQUE_EVENTO = "#d03b3b"  # reservado para eventos (geada)

CORES = {
    "dolar": "#2a78d6",
    "cafe": "#eb6834",
    "soja": "#1baf7a",
    "sul_de_minas": "#2a78d6",
    "cerrado_mineiro": "#eb6834",
    "matas_de_minas": "#1baf7a",
    "media": "#52514e",
    "safra": "#eda100",
    "entressafra": "#2a78d6",
    "linear": "#2a78d6",
    "random_forest": "#eb6834",
}
DIVERGENTE = "RdBu_r"  # correlacoes: dois polos + neutro no zero

NOMES = {
    "cafe": "Café arábica",
    "soja": "Soja (Paranaguá)",
    "dolar": "Dólar (R$/US$)",
    "sul_de_minas": "Sul de Minas",
    "cerrado_mineiro": "Cerrado Mineiro",
    "matas_de_minas": "Matas de Minas",
    "media": "Média das 3 regiões",
}


def aplicar_estilo_matplotlib() -> None:
    import matplotlib as mpl

    mpl.rcParams.update(
        {
            "text.parse_math": False,  # "R$/US$" sem virar formula
            "figure.facecolor": SUPERFICIE,
            "axes.facecolor": SUPERFICIE,
            "axes.edgecolor": GRADE,
            "axes.labelcolor": TINTA_SECUNDARIA,
            "axes.titlecolor": TINTA,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": GRADE,
            "grid.linewidth": 0.6,
            "xtick.color": TINTA_SECUNDARIA,
            "ytick.color": TINTA_SECUNDARIA,
            "lines.linewidth": 1.6,
            "legend.frameon": False,
            "figure.dpi": 110,
            "savefig.dpi": 150,
            "savefig.bbox": "tight",
        }
    )
