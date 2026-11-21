import numpy as np
import pandas as pd
import pytest

from src.modelagem.modelos import DEFASAGEM_CLIMA, preparar
from src.tratamento.features import criar_features
from src.tratamento.integracao import clima_com_janelas
from src.tratamento.limpeza import agregar_inmet_diario
from src.tratamento.qualidade import outliers_iqr


@pytest.fixture
def base_sintetica():
    datas = pd.bdate_range("2021-01-01", "2022-12-30")
    rng = np.random.default_rng(0)
    n = len(datas)
    df = pd.DataFrame(
        {
            "data": datas,
            "preco_cafe": 1000 + rng.normal(0, 5, n).cumsum(),
            "preco_soja": 150 + rng.normal(0, 1, n).cumsum(),
            "dolar": 5 + rng.normal(0, 0.02, n).cumsum(),
            "ipca_mensal": 0.5,
            "chuva_30d": rng.uniform(0, 300, n),
            "chuva_90d": rng.uniform(0, 600, n),
            "chuva_180d": rng.uniform(0, 1000, n),
            "dias_secos_30d": rng.integers(0, 30, n).astype(float),
            "temp_min_30d": rng.uniform(0, 15, n),
            "temp_max_30d": rng.uniform(25, 35, n),
            "anomalia_chuva_90d": rng.normal(0, 50, n),
        }
    )
    return criar_features(df)


def test_defasagens_do_dolar(base_sintetica):
    df = base_sintetica
    assert df["dolar_lag1"].iloc[10] == df["dolar"].iloc[9]
    assert df["dolar_lag20"].iloc[30] == df["dolar"].iloc[10]
    assert df["dolar_lag20"].iloc[:20].isna().all()


def test_variacao_e_safra(base_sintetica):
    df = base_sintetica
    esperado = (df["preco_cafe"].iloc[5] / df["preco_cafe"].iloc[4] - 1) * 100
    assert df["cafe_var_1d"].iloc[5] == pytest.approx(esperado)
    assert set(df.loc[df["mes"] == 7, "periodo_safra_cafe"]) == {"safra"}
    assert set(df.loc[df["mes"] == 12, "periodo_safra_cafe"]) == {"entressafra"}


def test_deflacao_ultimo_mes_igual_nominal(base_sintetica):
    df = base_sintetica
    ultimo = df["data"].dt.to_period("M") == df["data"].dt.to_period("M").max()
    assert np.allclose(df.loc[ultimo, "preco_cafe_real"], df.loc[ultimo, "preco_cafe"])
    assert (df.loc[~ultimo, "preco_cafe_real"] > df.loc[~ultimo, "preco_cafe"]).all()


def test_modelo_sem_vazamento(base_sintetica):
    """As features de clima do dia t devem vir de t-21 (nunca do proprio dia ou do futuro)."""
    X, _, _ = preparar(base_sintetica, "cafe", "nivel")
    serie = base_sintetica.set_index("data")["chuva_30d"]
    dia = X.index[50]
    pos = serie.index.get_loc(dia)
    assert X.loc[dia, f"chuva_30d_lag{DEFASAGEM_CLIMA}"] == serie.iloc[pos - DEFASAGEM_CLIMA]


def test_janelas_de_chuva():
    datas = pd.date_range("2021-01-01", periods=120, freq="D")
    clima = pd.DataFrame({"data": datas, "regiao": "x", "chuva_mm": 1.0, "temp_med": 20.0, "temp_min": 15.0, "temp_max": 25.0, "umidade": 70.0})
    out = clima_com_janelas(clima)
    x = out[out["regiao"] == "x"].set_index("data")
    assert x["chuva_30d"].iloc[29] == 30
    assert x["chuva_90d"].iloc[-1] == 90
    assert set(out["regiao"]) == {"x", "media"}


def test_agregacao_inmet_utc_para_brasilia():
    horas = pd.date_range("2021-01-01 00:00", periods=48, freq="h")
    bruto = pd.DataFrame(
        {
            "Data": horas.strftime("%Y/%m/%d"),
            "Hora UTC": horas.strftime("%H00 UTC"),
            "PRECIPITAÇÃO TOTAL, HORÁRIO (mm)": 1.0,
            "TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)": 20.0,
            "TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C)": 22.0,
            "TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)": 18.0,
            "UMIDADE RELATIVA DO AR, HORARIA (%)": 80.0,
        }
    )
    diario = agregar_inmet_diario(bruto).set_index("data")
    # 48 h a partir de 01/01 00h UTC = 31/12 21h a 02/01 20h em Brasilia (UTC-3)
    assert diario.loc["2021-01-01", "chuva_mm"] == 24
    assert diario.loc["2021-01-02", "chuva_mm"] == 21
    assert diario.loc["2021-01-01", "temp_min"] == 18
    assert np.isnan(diario.loc["2020-12-31", "chuva_mm"])  # so 3 horas: descartado


def test_outliers_iqr():
    s = pd.Series([1, 2, 2, 3, 2, 1, 100])
    assert outliers_iqr(s).tolist() == [False] * 6 + [True]
