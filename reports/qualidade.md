# Relatório de qualidade dos dados

Gerado a partir de `data/processed/base_integrada.csv` (1728 dias úteis).

## Cobertura por variável

| variavel | inicio | fim | observacoes | faltantes_pct |
|---|---|---|---|---|
| preco_cafe | 2020-01-02 | 2026-11-19 | 1728 | 0.0 |
| preco_soja | 2020-01-02 | 2026-11-19 | 1728 | 0.0 |
| dolar | 2020-01-02 | 2026-11-19 | 1728 | 0.0 |
| cafe_ice_usd_saca | 2020-01-02 | 2026-11-19 | 1728 | 0.0 |
| soja_cbot_usd_saca | 2020-01-02 | 2026-11-19 | 1728 | 0.0 |
| ipca_mensal | 2020-01-02 | 2026-10-30 | 1715 | 0.8 |
| chuva_mm | 2020-01-02 | 2026-11-18 | 1727 | 0.1 |
| temp_med | 2020-01-02 | 2026-11-18 | 1727 | 0.1 |

## Maiores lacunas — preco_cafe

| de | ate | dias |
|---|---|---|
| 2020-02-21 | 2020-02-26 | 5 |
| 2021-02-12 | 2021-02-17 | 5 |
| 2022-02-25 | 2022-03-02 | 5 |
| 2023-02-17 | 2023-02-22 | 5 |
| 2024-02-09 | 2024-02-14 | 5 |

## Outliers de variação diária (IQR, k=3) — cafe

4 dias atípicos de 1727. Maiores:


| data | variacao_1d_pct |
|---|---|
| 2026-07-06 | 9.24 |
| 2021-07-22 | 7.06 |
| 2024-05-02 | -6.88 |
| 2021-07-21 | 6.41 |


Verificar se coincidem com eventos reais (ex.: geada de jul/2021) antes de remover.

## Maiores lacunas — preco_soja

| de | ate | dias |
|---|---|---|
| 2020-02-21 | 2020-02-26 | 5 |
| 2021-02-12 | 2021-02-17 | 5 |
| 2022-02-25 | 2022-03-02 | 5 |
| 2023-02-17 | 2023-02-22 | 5 |
| 2024-02-09 | 2024-02-14 | 5 |

## Outliers de variação diária (IQR, k=3) — soja

9 dias atípicos de 1727. Maiores:


| data | variacao_1d_pct |
|---|---|
| 2021-01-05 | 5.2 |
| 2020-11-12 | -5.09 |
| 2022-10-03 | -4.41 |
| 2020-12-09 | 4.31 |
| 2021-06-30 | 4.2 |
| 2022-04-01 | -4.14 |
| 2020-09-21 | 3.9 |
| 2020-11-09 | -3.82 |
| 2020-11-10 | 3.77 |


Verificar se coincidem com eventos reais (ex.: geada de jul/2021) antes de remover.

## Validação: Notícias Agrícolas × CEPEA

| produto | dias_em_comum | dif_media | dif_max |
|---|---|---|---|
| cafe | 1708 | 0.0 | 0.0 |
| soja | 1707 | 0.0004335090802577675 | 0.7400000000000091 |

## Validação: NASA POWER × INMET

| regiao | dias_em_comum | corr_chuva_mensal | corr_temp_med_diaria | corr_temp_min_diaria | vies_temp_min_C |
|---|---|---|---|---|---|
| cerrado_mineiro | 2465 | 0.947 | 0.845 | 0.843 | 1.85 |
| matas_de_minas | 2465 | 0.896 | 0.893 | 0.862 | 0.56 |
| sul_de_minas | 2465 | 0.855 | 0.931 | 0.928 | 0.79 |
