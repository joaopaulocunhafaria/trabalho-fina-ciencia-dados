"""Orquestrador do projeto.

Uso:
    python -m src.pipeline coleta [--backfill] [--sem-inmet]
    python -m src.pipeline tratamento
    python -m src.pipeline analise
    python -m src.pipeline modelagem
    python -m src.pipeline tudo
"""

import argparse

import pandas as pd

from src import config
from src.utils import get_logger

log = get_logger("pipeline")


def coleta(backfill: bool = False, inmet: bool = True) -> None:
    from src.coleta import bcb, cepea, mercado_internacional, nasa_power, noticias_agricolas
    from src.coleta import inmet as coleta_inmet

    noticias_agricolas.coletar_atual()
    if backfill:
        noticias_agricolas.backfill()
    cepea.coletar()
    bcb.coletar()
    nasa_power.coletar()
    mercado_internacional.coletar()
    if inmet:
        coleta_inmet.coletar()


def tratamento() -> pd.DataFrame:
    from src.tratamento import features, integracao, limpeza, qualidade

    limpos = limpeza.executar()
    base, regional, clima_diario = integracao.integrar(limpos)
    base = features.criar_features(base)
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    base.to_csv(config.BASE_INTEGRADA, index=False)
    regional.to_csv(config.BASE_REGIONAL, index=False)
    clima_diario.to_csv(config.CLIMA_DIARIO, index=False)
    log.info("Salvo %s (%d x %d)", config.BASE_INTEGRADA.relative_to(config.RAIZ), *base.shape)
    qualidade.gerar_relatorio(base, limpos)
    return base


def carregar_base() -> pd.DataFrame:
    if not config.BASE_INTEGRADA.exists():
        raise FileNotFoundError("Base integrada nao encontrada. Rode: python -m src.pipeline tratamento")
    return pd.read_csv(config.BASE_INTEGRADA, parse_dates=["data"])


def analise() -> None:
    from src.analise import estatistica, graficos

    df = carregar_base()
    graficos.gerar_todos(df)
    saida = config.REPORTS / "tabelas"
    saida.mkdir(parents=True, exist_ok=True)
    estatistica.resumo_evolucao(df).to_csv(saida / "p1_resumo_anual.csv", index=False)
    for produto in config.COMMODITIES:
        tabela, p = estatistica.sazonalidade(df, produto)
        tabela.assign(kruskal_p=p).to_csv(saida / f"p2_sazonalidade_{produto}.csv", index=False)
        estatistica.correlacao_cruzada(df, produto).to_csv(saida / f"p3_correlacao_cruzada_{produto}.csv", index=False)
        estatistica.clima_vs_preco_futuro(df, produto).to_csv(saida / f"p4_clima_preco_futuro_{produto}.csv", index=False)
    pd.DataFrame([estatistica.repasse_cambial(df, p) for p in config.COMMODITIES]).to_csv(saida / "p3_repasse_cambial.csv", index=False)
    estatistica.impacto_geada(df).to_csv(saida / "p5_impacto_geada.csv", index=False)
    estatistica.sensibilidade(df).to_csv(saida / "p6_sensibilidade.csv", index=False)
    log.info("Tabelas salvas em reports/tabelas/")


def modelagem() -> None:
    from src.modelagem import modelos

    modelos.executar(carregar_base())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("etapas", nargs="+", choices=["coleta", "tratamento", "analise", "modelagem", "tudo"])
    parser.add_argument("--backfill", action="store_true", help="coleta o historico do Noticias Agricolas desde 2020")
    parser.add_argument("--sem-inmet", action="store_true", help="pula o download dos arquivos do INMET (~centenas de MB)")
    args = parser.parse_args()

    etapas = ["coleta", "tratamento", "analise", "modelagem"] if "tudo" in args.etapas else args.etapas
    for etapa in etapas:
        log.info("=== %s ===", etapa)
        if etapa == "coleta":
            coleta(backfill=args.backfill, inmet=not args.sem_inmet)
        else:
            {"tratamento": tratamento, "analise": analise, "modelagem": modelagem}[etapa]()


if __name__ == "__main__":
    main()
