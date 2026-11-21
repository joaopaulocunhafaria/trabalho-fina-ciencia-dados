"""Crawler direcionado e continuo das cotacoes do portal Noticias Agricolas.

Coleta o Indicador Cepea/Esalq do cafe arabica e da soja (Paranagua) publicado em
https://www.noticiasagricolas.com.br/cotacoes/. Dois modos:

* atual    -> le a pagina principal de cada produto (ultimos ~10 fechamentos);
              e o modo executado diariamente pelo GitHub Actions.
* backfill -> percorre as paginas por data (.../AAAA-MM-DD) para reconstruir o
              historico desde 2020. Retomavel: dias ja tentados sao pulados.

Uso:
    python -m src.coleta.noticias_agricolas            # modo atual
    python -m src.coleta.noticias_agricolas --backfill # historico
"""

import argparse
from datetime import date, datetime

import pandas as pd
from bs4 import BeautifulSoup

from src import config
from src.utils import BloqueioError, baixar_html, criar_sessao, get_logger, parse_numero_br, pausa, salvar_csv_incremental

log = get_logger(__name__)

ARQUIVO = config.RAW_NA / "cotacoes.csv"
TENTADOS = config.RAW_NA / "backfill_dias_tentados.txt"
CHAVES = ["data", "produto"]


def parse_cotacoes(html: str, produto: str) -> list[dict]:
    """Extrai as linhas (Data | Valor R$ | Variacao %) de todas as tabelas `cot-fisicas`."""
    soup = BeautifulSoup(html, "lxml")
    agora = datetime.now().isoformat(timespec="seconds")
    registros = []
    for tabela in soup.select("table.cot-fisicas"):
        cabecalho = [th.get_text(strip=True).lower() for th in tabela.select("thead th")]
        if not cabecalho or not cabecalho[0].startswith("data"):
            continue
        for linha in tabela.select("tbody tr"):
            colunas = [td.get_text(strip=True) for td in linha.find_all("td")]
            if len(colunas) < 2:
                continue
            try:
                dia = datetime.strptime(colunas[0], "%d/%m/%Y").date()
            except ValueError:
                continue
            registros.append(
                {
                    "data": dia.isoformat(),
                    "produto": produto,
                    "preco": parse_numero_br(colunas[1]),
                    "variacao_pct": parse_numero_br(colunas[2]) if len(colunas) > 2 else float("nan"),
                    "fonte": "noticias_agricolas",
                    "coletado_em": agora,
                }
            )
    return registros


def coletar_atual() -> pd.DataFrame:
    sessao = criar_sessao()
    registros = []
    for produto, caminho in config.NA_PAGINAS.items():
        url = config.NA_BASE_URL + caminho
        try:
            registros += parse_cotacoes(baixar_html(sessao, url), produto)
            log.info("%s: %s", produto, url)
        except BloqueioError as exc:
            log.error("Coleta interrompida: %s", exc)
            break
        pausa()
    return _salvar(registros)


def backfill(inicio: date = config.DATA_INICIO, fim: date = config.DATA_FIM, limite: int | None = None) -> pd.DataFrame:
    """Baixa uma pagina por produto e dia util ainda nao tentado. `limite` = max. de requisicoes."""
    sessao = criar_sessao()
    tentados = set(TENTADOS.read_text().split()) if TENTADOS.exists() else set()
    existentes = set()
    if ARQUIVO.exists():
        df = pd.read_csv(ARQUIVO, dtype=str)
        existentes = set(df["produto"] + "|" + df["data"])

    pendentes = [
        (produto, dia.date().isoformat())
        for dia in pd.bdate_range(inicio, fim)
        for produto in config.NA_PAGINAS
        if f"{produto}|{dia.date().isoformat()}" not in tentados | existentes
    ]
    if limite:
        pendentes = pendentes[:limite]
    log.info("Backfill: %d paginas pendentes (~%.0f min)", len(pendentes), len(pendentes) * (config.INTERVALO_REQUISICOES + 1) / 60)

    registros, feitos = [], []
    for i, (produto, dia) in enumerate(pendentes, 1):
        url = f"{config.NA_BASE_URL}{config.NA_PAGINAS[produto]}/{dia}"
        try:
            registros += parse_cotacoes(baixar_html(sessao, url), produto)
            feitos.append(f"{produto}|{dia}")
        except BloqueioError as exc:
            log.error("Backfill interrompido: %s", exc)
            break
        except Exception as exc:  # erro pontual de rede: segue para o proximo dia
            log.warning("Falha em %s: %s", url, exc)
        if i % 25 == 0:
            _salvar(registros, feitos)
            registros, feitos = [], []
            log.info("Backfill: %d/%d", i, len(pendentes))
        pausa()
    return _salvar(registros, feitos)


def _salvar(registros: list[dict], tentados: list[str] | None = None) -> pd.DataFrame:
    if tentados:
        TENTADOS.parent.mkdir(parents=True, exist_ok=True)
        with TENTADOS.open("a") as f:
            f.write("\n".join(tentados) + "\n")
    if not registros:
        return pd.read_csv(ARQUIVO) if ARQUIVO.exists() else pd.DataFrame()
    df = salvar_csv_incremental(pd.DataFrame(registros), ARQUIVO, CHAVES)
    log.info("%s: %d registros no total", ARQUIVO.name, len(df))
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backfill", action="store_true", help="reconstroi o historico desde 2020")
    parser.add_argument("--limite", type=int, default=None, help="maximo de paginas no backfill")
    args = parser.parse_args()
    backfill(limite=args.limite) if args.backfill else coletar_atual()
