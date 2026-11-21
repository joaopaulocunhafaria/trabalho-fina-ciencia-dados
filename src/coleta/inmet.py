"""Dados horarios das estacoes automaticas do INMET proximas as regioes cafeeiras.

O INMET publica um ZIP por ano com todas as estacoes do pais. O coletor baixa cada
ZIP (cache em data/raw/inmet/zips, fora do git), escolhe a estacao de MG mais
proxima de cada municipio representativo e extrai apenas esses CSVs, sem alteracao.
Usado de forma complementar, para validar os dados da NASA POWER.

Uso: python -m src.coleta.inmet
"""

import io
import math
import zipfile

import pandas as pd

from src import config
from src.utils import criar_sessao, get_logger, parse_numero_br

log = get_logger(__name__)

PASTA_ZIPS = config.RAW_INMET / "zips"


def distancia_km(lat1, lon1, lat2, lon2) -> float:
    """Distancia haversine entre dois pontos."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def ler_metadados(conteudo: bytes) -> dict:
    """Le as 8 primeiras linhas (ESTACAO, CODIGO, LATITUDE...) de um CSV do INMET."""
    meta = {}
    for linha in conteudo.decode("latin-1").splitlines()[:8]:
        chave, _, valor = linha.partition(";")
        meta[chave.strip(" :").upper()] = valor.strip()
    return {
        "estacao": meta.get("ESTACAO", meta.get("ESTAÇÃO", "")),
        "codigo": meta.get("CODIGO (WMO)", ""),
        "lat": parse_numero_br(meta.get("LATITUDE")),
        "lon": parse_numero_br(meta.get("LONGITUDE")),
    }


def baixar_zip(ano: int, forcar: bool = False):
    PASTA_ZIPS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_ZIPS / f"{ano}.zip"
    if destino.exists() and not forcar and ano < config.DATA_FIM.year:
        return destino
    resp = criar_sessao().get(config.INMET_URL.format(ano=ano), timeout=600, stream=True)
    if resp.status_code == 404:
        log.warning("INMET ainda nao publicou o arquivo de %d", ano)
        return None
    resp.raise_for_status()
    with destino.open("wb") as f:
        for bloco in resp.iter_content(1 << 20):
            f.write(bloco)
    log.info("INMET %d: %.0f MB baixados", ano, destino.stat().st_size / 1e6)
    return destino


def extrair_estacoes(caminho_zip) -> list[dict]:
    """Salva o CSV da estacao de MG mais proxima de cada regiao."""
    salvos = []
    with zipfile.ZipFile(caminho_zip) as zf:
        candidatos = []
        for nome in zf.namelist():
            if "_MG_" not in nome.upper() or not nome.upper().endswith(".CSV"):
                continue
            with zf.open(nome) as f:
                meta = ler_metadados(f.read(2048))
            candidatos.append((nome, meta))

        for regiao, info in config.REGIOES.items():
            distancias = [
                (distancia_km(info["lat"], info["lon"], m["lat"], m["lon"]), nome, m)
                for nome, m in candidatos
                if not math.isnan(m["lat"])
            ]
            if not distancias:
                continue
            dist, nome, meta = min(distancias)
            if dist > config.INMET_DISTANCIA_MAX_KM:
                log.warning("%s: estacao mais proxima (%s) a %.0f km, ignorada", regiao, meta["estacao"], dist)
                continue
            ano = caminho_zip.stem
            destino = config.RAW_INMET / f"{regiao}_{meta['codigo']}_{ano}.csv"
            destino.write_bytes(zf.read(nome))
            salvos.append({"regiao": regiao, "ano": ano, **meta, "distancia_km": round(dist, 1), "arquivo": destino.name})
    return salvos


def coletar(forcar: bool = False) -> pd.DataFrame:
    config.RAW_INMET.mkdir(parents=True, exist_ok=True)
    registros = []
    for ano in range(config.DATA_INICIO.year, config.DATA_FIM.year + 1):
        caminho = baixar_zip(ano, forcar)
        if caminho:
            registros += extrair_estacoes(caminho)
    estacoes = pd.DataFrame(registros)
    estacoes.to_csv(config.RAW_INMET / "estacoes_selecionadas.csv", index=False)
    log.info("INMET: %d arquivos de estacao extraidos", len(estacoes))
    return estacoes


def ler_csv_estacao(caminho) -> pd.DataFrame:
    """Le um CSV bruto do INMET (latin-1, ';', decimal ',', 8 linhas de metadados)."""
    texto = caminho.read_bytes().decode("latin-1")
    return pd.read_csv(io.StringIO(texto), sep=";", skiprows=8, decimal=",", na_values=["-9999", "-9999,0"])


if __name__ == "__main__":
    coletar()
