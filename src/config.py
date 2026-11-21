"""Configuracoes centrais do projeto: caminhos, periodo, fontes e regioes."""

import os
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
REPORTS = RAIZ / "reports"
FIGURES = REPORTS / "figures"
MODELOS = REPORTS / "modelos"

RAW_NA = RAW / "noticias_agricolas"
RAW_CEPEA = RAW / "cepea"
RAW_BCB = RAW / "bcb"
RAW_NASA = RAW / "nasa_power"
RAW_INMET = RAW / "inmet"
RAW_YF = RAW / "yfinance"

BASE_INTEGRADA = Path(os.getenv("BASE_INTEGRADA", PROCESSED / "base_integrada.csv"))
BASE_REGIONAL = PROCESSED / "base_regional.csv"
CLIMA_DIARIO = PROCESSED / "clima_diario.csv"

# ---------------------------------------------------------------------------
# Periodo de estudo
# ---------------------------------------------------------------------------
DATA_INICIO = date(2020, 1, 1)
DATA_FIM = date.today()

# ---------------------------------------------------------------------------
# Web scraping (etica: User-Agent descritivo + intervalo entre requisicoes)
# ---------------------------------------------------------------------------
_CONTATO = os.getenv("CRAWLER_CONTATO", "")
USER_AGENT = "CEFET-MG CD - projeto academico de Ciencia de Dados" + (
    f" (contato: {_CONTATO})" if _CONTATO else ""
)
INTERVALO_REQUISICOES = float(os.getenv("CRAWLER_INTERVALO", "3"))  # segundos
TIMEOUT = 30

NA_BASE_URL = "https://www.noticiasagricolas.com.br/cotacoes/"
NA_PAGINAS = {
    "cafe": "cafe/indicador-cepea-esalq-cafe-arabica",
    "soja": "soja/soja-indicador-cepea-esalq-porto-paranagua",
}

# ---------------------------------------------------------------------------
# CEPEA (download manual pelo navegador; ver README)
# ---------------------------------------------------------------------------
CEPEA_SERIES = {
    "cafe": "https://www.cepea.org.br/br/indicador/series/cafe.aspx?id=23",
    "soja": "https://www.cepea.org.br/br/indicador/series/soja.aspx?id=92",
}

# ---------------------------------------------------------------------------
# Banco Central - SGS
# ---------------------------------------------------------------------------
SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
SGS_SERIES = {
    "dolar": 1,  # Dolar comercial (venda), R$/US$, diario
    "ipca": 433,  # IPCA, variacao % mensal
}

# ---------------------------------------------------------------------------
# Mercado internacional (Yahoo Finance) e conversao de unidades
# ---------------------------------------------------------------------------
YF_TICKERS = {
    "cafe_ice": "KC=F",  # Cafe arabica ICE NY, centavos de US$/libra-peso
    "soja_cbot": "ZS=F",  # Soja CBOT, centavos de US$/bushel
}
LIBRAS_POR_SACA = 60 / 0.45359237  # saca de 60 kg em lb
BUSHELS_POR_SACA = 60 / 27.2155  # saca de 60 kg em bushels de soja

# ---------------------------------------------------------------------------
# Clima: regioes cafeeiras de MG e municipios representativos
# ---------------------------------------------------------------------------
REGIOES = {
    "sul_de_minas": {"nome": "Sul de Minas", "municipio": "Varginha", "lat": -21.5514, "lon": -45.4303},
    "cerrado_mineiro": {"nome": "Cerrado Mineiro", "municipio": "Patrocinio", "lat": -18.9439, "lon": -46.9925},
    "matas_de_minas": {"nome": "Matas de Minas", "municipio": "Manhuacu", "lat": -20.2581, "lon": -42.0336},
}

NASA_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_PARAMETROS = {
    "PRECTOTCORR": "chuva_mm",
    "T2M": "temp_med",
    "T2M_MIN": "temp_min",
    "T2M_MAX": "temp_max",
    "RH2M": "umidade",
}

INMET_URL = "https://portal.inmet.gov.br/uploads/dadoshistoricos/{ano}.zip"
INMET_DISTANCIA_MAX_KM = 80  # estacao mais proxima do municipio, ate este raio

# ---------------------------------------------------------------------------
# Calendario agricola e eventos
# ---------------------------------------------------------------------------
MESES_SAFRA = {
    "cafe": [5, 6, 7, 8, 9],  # colheita do arabica em MG: maio a setembro
    "soja": [2, 3, 4, 5],  # colheita da soja no Brasil: fevereiro a maio
}
GEADA_2021 = date(2021, 7, 20)

COMMODITIES = {"cafe": "Café arábica", "soja": "Soja (Paranaguá)"}
