"""Painel interativo: Café e Soja × Dólar × Clima.

Execute a partir da raiz do projeto:
    streamlit run app/streamlit_app.py
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402
from src.analise import estatistica  # noqa: E402
from src.analise.estilo import CORES, DESTAQUE_EVENTO, NOMES  # noqa: E402

st.set_page_config(page_title="Café e Soja × Dólar × Clima", layout="wide")
LAYOUT = dict(template="plotly_white", hovermode="x unified", margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=1.08))


@st.cache_data
def carregar() -> pd.DataFrame:
    return pd.read_csv(config.BASE_INTEGRADA, parse_dates=["data"])


@st.cache_data
def carregar_csv(caminho: Path) -> pd.DataFrame | None:
    return pd.read_csv(caminho) if caminho.exists() else None


def marcar_geada(fig, rotulo: str | None = None):
    geada = pd.Timestamp(config.GEADA_2021)
    fig.add_vline(x=geada, line_dash="dash", line_color=DESTAQUE_EVENTO, line_width=1)
    if rotulo:  # anotacao separada: add_vline(annotation_text=...) falha com datas no plotly
        fig.add_annotation(x=geada, y=1, yref="paper", text=rotulo, showarrow=False, xanchor="left", font=dict(color=DESTAQUE_EVENTO))


if not config.BASE_INTEGRADA.exists():
    st.error("Base integrada não encontrada. Rode `python -m src.pipeline coleta tratamento` antes de abrir o painel.")
    st.stop()

base = carregar()

# --- Filtros ---------------------------------------------------------------
st.sidebar.title("Filtros")
inicio, fim = st.sidebar.slider(
    "Período",
    min_value=base["data"].min().date(),
    max_value=base["data"].max().date(),
    value=(base["data"].min().date(), base["data"].max().date()),
    format="MM/YYYY",
)
produto = st.sidebar.radio("Commodity", list(config.COMMODITIES), format_func=NOMES.get)
regiao = st.sidebar.selectbox("Região (clima)", ["media", *config.REGIOES], format_func=NOMES.get)
real = st.sidebar.toggle("Preços reais (deflacionados pelo IPCA)", value=False)
st.sidebar.caption("Fontes: Notícias Agrícolas / CEPEA, Banco Central (SGS), NASA POWER, INMET, Yahoo Finance.")

df = base[(base["data"].dt.date >= inicio) & (base["data"].dt.date <= fim)].copy()
col_preco = f"preco_{produto}" + ("_real" if real else "")
sufixo = "" if regiao == "media" else f"_{regiao}"

st.title("Café e Soja × Dólar × Clima")
st.caption("Commodities agrícolas mineiras — CEFET-MG, Ciência de Dados")

ultimo = df.dropna(subset=[f"preco_{produto}"]).iloc[-1] if df[f"preco_{produto}"].notna().any() else None
c1, c2, c3, c4 = st.columns(4)
if ultimo is not None:
    c1.metric(f"{NOMES[produto]} (R$/saca)", f"{ultimo[f'preco_{produto}']:,.2f}", f"{ultimo[f'{produto}_var_21d']:.1f}% em 21 d.u.")
    c2.metric("Dólar (R$/US$)", f"{ultimo['dolar']:.4f}", f"{ultimo['dolar_var_21d']:.1f}% em 21 d.u.")
    c3.metric(f"Chuva 90 dias — {NOMES[regiao]}", f"{ultimo[f'chuva_90d{sufixo}']:.0f} mm")
    c4.metric("Última cotação", ultimo["data"].strftime("%d/%m/%Y"))

abas = st.tabs(["P1 Evolução", "P2 Sazonalidade", "P3 Dólar", "P4 Clima", "P5 Geada 2021", "P6 Sensibilidade", "Modelos", "Dados"])

# --- P1 --------------------------------------------------------------------
with abas[0]:
    fig = go.Figure()
    for p in config.COMMODITIES:
        c = f"preco_{p}" + ("_real" if real else "")
        fig.add_scatter(x=df["data"], y=df[c], name=NOMES[p], line=dict(color=CORES[p], width=2))
    marcar_geada(fig)
    fig.update_layout(title="Preço (R$/saca de 60 kg)", **LAYOUT)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(estatistica.resumo_evolucao(df), use_container_width=True, hide_index=True)

# --- P2 --------------------------------------------------------------------
with abas[1]:
    d = df[["ano", "mes", f"preco_{produto}_real", f"periodo_safra_{produto}"]].dropna()
    if len(d) > 30:
        d["relativo"] = d[f"preco_{produto}_real"] / d.groupby("ano")[f"preco_{produto}_real"].transform("mean") * 100
        fig = px.box(d, x="mes", y="relativo", color=f"periodo_safra_{produto}",
                     color_discrete_map={"safra": CORES["safra"], "entressafra": CORES["entressafra"]},
                     labels={"mes": "Mês", "relativo": "Preço relativo à média do ano (=100)", f"periodo_safra_{produto}": ""})
        fig.add_hline(y=100, line_color="#52514e", line_width=1)
        fig.update_layout(title=f"{NOMES[produto]}: preço real por mês", **LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
        _, p = estatistica.sazonalidade(df, produto)
        st.info(f"Teste de Kruskal-Wallis entre meses: p = {p:.3g} " + ("(há diferença significativa entre meses)" if p < 0.05 else "(sem evidência de sazonalidade)"))
    else:
        st.warning("Período curto demais para analisar sazonalidade.")

# --- P3 --------------------------------------------------------------------
with abas[2]:
    s = df.set_index("data")[[f"preco_{produto}", "dolar"]].dropna()
    if not s.empty:
        indice = s / s.iloc[0] * 100
        fig = go.Figure()
        fig.add_scatter(x=indice.index, y=indice["dolar"], name=NOMES["dolar"], line=dict(color=CORES["dolar"], width=2))
        fig.add_scatter(x=indice.index, y=indice[f"preco_{produto}"], name=NOMES[produto], line=dict(color=CORES[produto], width=2))
        if f"{produto}_ice_brl_saca" in df or f"{produto}_cbot_brl_saca" in df:
            col_int = f"{produto}_ice_brl_saca" if produto == "cafe" else f"{produto}_cbot_brl_saca"
            ref = df.set_index("data")[col_int].dropna()
            if not ref.empty:
                fig.add_scatter(x=ref.index, y=ref / ref.iloc[0] * 100, name="Bolsa internacional × dólar", line=dict(color="#52514e", width=1, dash="dot"))
        fig.add_hline(y=100, line_color="#52514e", line_width=1)
        fig.update_layout(title=f"Índice base 100 em {indice.index[0]:%d/%m/%Y}", **LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    freq = col_a.radio("Frequência das variações", ["Diária", "Semanal"], horizontal=True)
    cc = estatistica.correlacao_cruzada(df, produto, frequencia="W" if freq == "Semanal" else None,
                                        defasagens=range(0, 13) if freq == "Semanal" else range(0, 31))
    fig = px.bar(cc, x="defasagem", y="correlacao", hover_data=["p_valor", "n"], color_discrete_sequence=[CORES[produto]],
                 labels={"defasagem": f"Defasagem k ({'semanas' if freq == 'Semanal' else 'dias úteis'})", "correlacao": "Correlação"})
    fig.update_layout(title="Correlação: variação do preço (t) × variação do dólar (t−k)", **{**LAYOUT, "hovermode": "closest"})
    col_a.plotly_chart(fig, use_container_width=True)
    rep = estatistica.repasse_cambial(df, produto)
    col_b.metric("Elasticidade preço–câmbio (mensal)", f"{rep['elasticidade']:.2f}", help="Variação % do preço para 1% de variação do dólar (regressão log-log mensal).")
    col_b.metric("R² da regressão mensal", f"{rep['r2']:.2f}")
    col_b.caption(f"p-valor = {rep['p_valor']:.3g}, {rep['meses']} meses.")

# --- P4 --------------------------------------------------------------------
with abas[3]:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        subplot_titles=(f"{NOMES[produto]} (R$/saca)", "Chuva acumulada em 90 dias (mm)", "Menor temperatura mínima em 30 dias (°C)"))
    fig.add_scatter(x=df["data"], y=df[col_preco], name=NOMES[produto], line=dict(color=CORES[produto]), row=1, col=1)
    regioes = list(config.REGIOES) if regiao == "media" else [regiao]
    for r in regioes:
        fig.add_scatter(x=df["data"], y=df[f"chuva_90d_{r}"], name=NOMES[r], legendgroup=r, line=dict(color=CORES[r], width=1.5), row=2, col=1)
        fig.add_scatter(x=df["data"], y=df[f"temp_min_30d_{r}"], name=NOMES[r], legendgroup=r, showlegend=False, line=dict(color=CORES[r], width=1.5), row=3, col=1)
    marcar_geada(fig)
    fig.update_layout(height=750, **LAYOUT)
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Clima recente × variação do preço nos ~3 meses seguintes (Spearman)")
    st.dataframe(estatistica.clima_vs_preco_futuro(df, produto).round(3), use_container_width=True, hide_index=True)

# --- P5 --------------------------------------------------------------------
with abas[4]:
    geada = pd.Timestamp(config.GEADA_2021)
    j = base[(base["data"] >= geada - pd.Timedelta(days=120)) & (base["data"] <= geada + pd.Timedelta(days=240))]
    if j[["preco_cafe", "preco_soja"]].notna().any().all():
        ref = j[j["data"] < geada].ffill().iloc[-1]
        fig = go.Figure()
        for p in config.COMMODITIES:
            fig.add_scatter(x=j["data"], y=j[f"preco_{p}"] / ref[f"preco_{p}"] * 100, name=NOMES[p], line=dict(color=CORES[p], width=2))
        fig.add_vrect(x0="2021-06-30", x1="2021-07-21", fillcolor=DESTAQUE_EVENTO, opacity=0.08, line_width=0)
        marcar_geada(fig, rotulo="Geada 20/07/2021")
        fig.add_hline(y=100, line_color="#52514e", line_width=1)
        fig.update_layout(title="Índice (véspera da geada = 100) — soja como controle", **LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(estatistica.impacto_geada(base), use_container_width=True, hide_index=True)
    else:
        st.warning("Sem preços em 2021 — rode o backfill do crawler ou adicione as planilhas do CEPEA.")

# --- P6 --------------------------------------------------------------------
with abas[5]:
    variaveis = ["dolar", "dolar_lag20", f"chuva_30d{sufixo}", f"chuva_90d{sufixo}", f"temp_min_30d{sufixo}", f"temp_max_30d{sufixo}"]
    variaveis += ["dias_secos_30d", "anomalia_chuva_90d"] if regiao == "media" else []
    linhas = [f"preco_{produto}", f"{produto}_var_21d", f"{produto}_var_fut_63d"]
    corr = df[linhas + variaveis].corr(method="spearman").loc[linhas, variaveis]
    fig = px.imshow(corr, text_auto=".2f", zmin=-1, zmax=1, color_continuous_scale="RdBu_r", aspect="auto")
    fig.update_layout(title=f"Correlação de Spearman — {NOMES[produto]} / clima: {NOMES[regiao]}", **{**LAYOUT, "hovermode": "closest"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(estatistica.sensibilidade(df), use_container_width=True, hide_index=True)

# --- Modelos ---------------------------------------------------------------
with abas[6]:
    resumo = carregar_csv(config.MODELOS / "metricas_resumo.csv")
    imp = carregar_csv(config.MODELOS / "importancias.csv")
    if resumo is None or imp is None:
        st.warning("Rode `python -m src.pipeline modelagem` para gerar os resultados.")
    else:
        st.markdown("Validação com **TimeSeriesSplit** (5 folds, treino sempre anterior ao teste). "
                    "O objetivo é comparar a importância de câmbio × clima, não prever preços.")
        st.dataframe(resumo, use_container_width=True, hide_index=True)
        alvo = st.radio("Alvo", sorted(imp["alvo"].unique()), horizontal=True)
        g = imp[imp["alvo"] == alvo].groupby(["produto", "grupo"], as_index=False)[["importancia_lr", "importancia_rf"]].sum()
        g["produto"] = g["produto"].map(NOMES)
        fig = px.bar(g, x="grupo", y="importancia_rf", color="produto", barmode="group",
                     color_discrete_map={NOMES[p]: CORES[p] for p in config.COMMODITIES},
                     labels={"importancia_rf": "Importância (Random Forest)", "grupo": "", "produto": ""})
        fig.update_layout(title="Importância por grupo de variáveis", **{**LAYOUT, "hovermode": "closest"})
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(imp[(imp["alvo"] == alvo) & (imp["produto"] == produto)].round(4), use_container_width=True, hide_index=True)

# --- Dados -----------------------------------------------------------------
with abas[7]:
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("Baixar CSV filtrado", df.to_csv(index=False).encode("utf-8"), "base_filtrada.csv", "text/csv")
    qualidade = config.REPORTS / "qualidade.md"
    if qualidade.exists():
        with st.expander("Relatório de qualidade dos dados"):
            st.markdown(qualidade.read_text(encoding="utf-8"))
