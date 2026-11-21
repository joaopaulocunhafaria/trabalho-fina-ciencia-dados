from pathlib import Path

import pytest

from src.coleta.inmet import distancia_km, ler_metadados
from src.coleta.noticias_agricolas import parse_cotacoes
from src.utils import parse_numero_br

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("R$ 1.234,56", 1234.56),
        ("1.593,89", 1593.89),
        ("-1,01%", -1.01),
        ("+0,50", 0.5),
        ("2,17", 2.17),
        (544.28, 544.28),
    ],
)
def test_parse_numero_br(texto, esperado):
    assert parse_numero_br(texto) == pytest.approx(esperado)


@pytest.mark.parametrize("texto", ["", "-", "s/c", None])
def test_parse_numero_br_invalido(texto):
    assert parse_numero_br(texto) != parse_numero_br(texto)  # NaN


def test_parse_pagina_atual():
    registros = parse_cotacoes((FIXTURES / "na_cafe_atual.html").read_text(encoding="utf-8"), "cafe")
    assert [r["data"] for r in registros] == ["2026-10-28", "2026-10-27", "2026-10-26"]
    assert registros[0]["preco"] == pytest.approx(1593.89)
    assert registros[0]["variacao_pct"] == pytest.approx(-1.01)
    assert {r["produto"] for r in registros} == {"cafe"}


def test_parse_pagina_por_data():
    registros = parse_cotacoes((FIXTURES / "na_cafe_2020-03-10.html").read_text(encoding="utf-8"), "cafe")
    assert len(registros) == 1
    assert registros[0]["data"] == "2020-03-10"
    assert registros[0]["preco"] == pytest.approx(544.28)


def test_parse_pagina_sem_tabela():
    assert parse_cotacoes("<html><body><p>sem cotacao</p></body></html>", "soja") == []


def test_metadados_inmet():
    cabecalho = (
        "REGIAO:;SE\nUF:;MG\nESTACAO:;VARGINHA\nCODIGO (WMO):;A515\n"
        "LATITUDE:;-21,56638888\nLONGITUDE:;-45,40444444\nALTITUDE:;918\nDATA DE FUNDACAO:;2006-07-15\n"
    ).encode("latin-1")
    meta = ler_metadados(cabecalho)
    assert meta["codigo"] == "A515"
    assert meta["lat"] == pytest.approx(-21.56638888)
    assert distancia_km(-21.5514, -45.4303, meta["lat"], meta["lon"]) < 5
