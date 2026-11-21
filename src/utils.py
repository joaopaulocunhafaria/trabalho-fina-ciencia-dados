"""Funcoes utilitarias: HTTP etico, robots.txt, parse de numeros e logging."""

import logging
import re
import time
from functools import lru_cache
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src import config


def get_logger(nome: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger(nome)


log = get_logger(__name__)


class BloqueioError(RuntimeError):
    """O servidor recusou a requisicao (403/429/desafio anti-bot)."""


def criar_sessao() -> requests.Session:
    """Sessao com User-Agent descritivo e retry com backoff exponencial."""
    sessao = requests.Session()
    sessao.headers["User-Agent"] = config.USER_AGENT
    retry = Retry(
        total=4,
        backoff_factor=2,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    sessao.mount("https://", HTTPAdapter(max_retries=retry))
    sessao.mount("http://", HTTPAdapter(max_retries=retry))
    return sessao


@lru_cache(maxsize=None)
def _robots(base: str) -> RobotFileParser:
    rp = RobotFileParser()
    try:
        resp = requests.get(
            f"{base}/robots.txt", headers={"User-Agent": config.USER_AGENT}, timeout=config.TIMEOUT
        )
    except requests.RequestException as exc:
        log.warning("Nao foi possivel ler robots.txt de %s (%s); assumindo permitido", base, exc)
        rp.parse([])
        return rp
    if resp.status_code in (401, 403) or "Just a moment" in resp.text[:2000]:
        rp.disallow_all = True
    elif resp.status_code >= 400:
        rp.allow_all = True
    else:
        rp.parse(resp.text.splitlines())
    return rp


def pode_acessar(url: str) -> bool:
    partes = urlparse(url)
    return _robots(f"{partes.scheme}://{partes.netloc}").can_fetch(config.USER_AGENT, url)


def baixar_html(sessao: requests.Session, url: str) -> str:
    """GET respeitando robots.txt; levanta BloqueioError se o site recusar o acesso."""
    if not pode_acessar(url):
        raise BloqueioError(f"robots.txt nao permite acessar {url}")
    resp = sessao.get(url, timeout=config.TIMEOUT)
    if resp.status_code in (403, 429) or "<title>Just a moment" in resp.text[:3000]:
        raise BloqueioError(f"acesso recusado ({resp.status_code}) em {url}")
    resp.raise_for_status()
    return resp.text


def pausa() -> None:
    time.sleep(config.INTERVALO_REQUISICOES)


def parse_numero_br(valor) -> float:
    """Converte textos como 'R$ 1.234,56', '-1,01%' ou '2,17' em float."""
    if valor is None:
        return float("nan")
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = re.sub(r"[^\d,.\-+]", "", str(valor))
    if not texto or texto in "+-":
        return float("nan")
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return float("nan")


def salvar_csv_incremental(novos: pd.DataFrame, caminho, chaves: list[str]) -> pd.DataFrame:
    """Une `novos` ao CSV existente sem duplicar as `chaves` (o registro mais novo prevalece)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.exists():
        antigos = pd.read_csv(caminho, dtype=str)
        novos = pd.concat([antigos, novos.astype(str)], ignore_index=True)
    final = novos.drop_duplicates(subset=chaves, keep="last").sort_values(chaves)
    final.to_csv(caminho, index=False)
    return final
