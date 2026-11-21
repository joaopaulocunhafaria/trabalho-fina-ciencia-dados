# Preço do Café e da Soja × Dólar × Clima

Trabalho final de **Ciência de Dados** (Engenharia de Computação, CEFET-MG, Divinópolis), por
Alvaro Augusto José da Silva e João Paulo da Cunha Faria.

O projeto monta uma base integrada (2020 → hoje) com os preços do café arábica e da soja, a cotação
do dólar e o clima das três principais regiões cafeeiras de Minas Gerais, e analisa como esses fatores se
relacionam. O pré-projeto e os slides estão em [`docs/`](docs/).

## Perguntas de pesquisa

| | Pergunta | Onde é respondida |
|---|---|---|
| P1 | Como os preços evoluíram entre 2020 e 2026? | `p1_evolucao_precos.png`, `tabelas/p1_resumo_anual.csv` |
| P2 | Há sazonalidade (safra × entressafra)? | `p2_sazonalidade.png`, teste de Kruskal-Wallis |
| P3 | Os preços acompanham o dólar? Com que defasagem? | `p3_preco_dolar.png`, correlação cruzada, elasticidade |
| P4 | Pouca chuva / temperaturas extremas antecedem alta do café? | `p4_clima_regioes.png`, Spearman clima × preço futuro |
| P5 | Qual o impacto da geada de julho/2021? | `p5_geada_2021.png`, `tabelas/p5_impacto_geada.csv` |
| P6 | Qual commodity é mais sensível ao clima e qual ao câmbio? | `p6_correlacoes.png`, `p6_importancia_grupos.png`, modelos |

Todos os arquivos ficam em `reports/` e o painel Streamlit reúne tudo com filtros.

## Fontes de dados

| Fonte | Dado | Técnica | Módulo |
|---|---|---|---|
| [Notícias Agrícolas](https://www.noticiasagricolas.com.br/cotacoes/) | Indicador Cepea/Esalq do café arábica e da soja (Paranaguá), R$/saca | Web scraping (requests + BeautifulSoup) | `src/coleta/noticias_agricolas.py` |
| [CEPEA/ESALQ](https://www.cepea.org.br/) | Séries históricas dos indicadores (validação) | Planilha, download manual | `src/coleta/cepea.py` |
| [Banco Central — SGS](https://www3.bcb.gov.br/sgspub/) | Dólar comercial venda (série 1), IPCA (série 433) | API REST (JSON) | `src/coleta/bcb.py` |
| [NASA POWER](https://power.larc.nasa.gov/) | Chuva, temperatura mín./méd./máx., umidade | API REST (JSON) | `src/coleta/nasa_power.py` |
| [INMET](https://portal.inmet.gov.br/) | Estações automáticas mais próximas (validação do clima) | Download de arquivos (ZIP/CSV) | `src/coleta/inmet.py` |
| Yahoo Finance | Futuros do café (ICE, `KC=F`) e da soja (CBOT, `ZS=F`) | API (`yfinance`) | `src/coleta/mercado_internacional.py` |

Regiões e municípios representativos: **Sul de Minas** (Varginha), **Cerrado Mineiro** (Patrocínio) e
**Matas de Minas** (Manhuaçu).

## Estrutura

```
TrabalhoFinal/
├── .github/workflows/crawler.yml  # coleta diária automática (GitHub Actions)
├── src/
│   ├── config.py                  # caminhos, período, regiões, URLs, IDs de séries
│   ├── utils.py                   # HTTP ético (robots.txt, User-Agent, retry), parse de números BR
│   ├── pipeline.py                # orquestrador: coleta → tratamento → análise → modelagem
│   ├── coleta/                    # um módulo por fonte
│   ├── tratamento/                # limpeza, integração, features, qualidade
│   ├── analise/                   # estatística (P1–P6), gráficos, estilo
│   └── modelagem/                 # Regressão Linear e Random Forest
├── app/streamlit_app.py           # painel interativo
├── notebooks/                     # 01 coleta/qualidade, 02 EDA P1–P6, 03 modelagem
├── data/
│   ├── raw/                       # dados brutos, como coletados (nunca editados)
│   ├── interim/                   # cada fonte limpa e padronizada
│   └── processed/                 # base_integrada.csv, base_regional.csv, clima_diario.csv
├── reports/                       # figuras, tabelas, métricas e qualidade.md
├── tests/                         # pytest (parsers, features, ausência de vazamento)
├── docs/                          # pré-projeto, slides e enunciado
├── requirements.txt
└── Makefile
```

## Como executar

Requer Python 3.11+.

```bash
# 1. ambiente virtual
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # ou: make venv

# 2. coleta (APIs + crawler do dia + INMET)
python -m src.pipeline coleta            # --sem-inmet para pular os ZIPs do INMET (~centenas de MB)

# 3. histórico de preços desde 2020 (uma vez; ~3 h, pode ser interrompido e retomado)
python -m src.coleta.noticias_agricolas --backfill

# 4. tratamento, análise e modelos
python -m src.pipeline tratamento analise modelagem

# 5. painel
streamlit run app/streamlit_app.py
```

Ou tudo pelo `make`: `make coleta`, `make backfill`, `make tratamento analise modelagem`, `make painel`,
`make testes`, `make notebooks`.

### Passo manual opcional: planilhas do CEPEA

O site do CEPEA bloqueia downloads automatizados. Para validar o crawler com a fonte original:

1. Abra no navegador [café arábica](https://www.cepea.org.br/br/indicador/series/cafe.aspx?id=23) e
   [soja Paranaguá](https://www.cepea.org.br/br/indicador/series/soja.aspx?id=92) — o download começa automaticamente.
2. Salve os arquivos como `data/raw/cepea/cafe.xls` e `data/raw/cepea/soja.xls`.
3. Rode `python -m src.pipeline tratamento`. Quando presentes, os valores do CEPEA têm prioridade e o
   relatório `reports/qualidade.md` mostra a diferença entre as duas fontes.

## Tratamento e integração

1. **Padronização** (`limpeza.py`): datas em ISO, “R$ 1.234,56” → `1234.56`, sentinelas (-999 NASA,
   -9999 INMET) → NaN, futuros convertidos para US$/saca de 60 kg, INMET horário (UTC) → diário (Brasília).
2. **Integração** (`integracao.py`): índice = dias úteis. Janelas de clima calculadas no calendário diário
   completo; a chuva de fins de semana é somada ao próximo dia útil. Preços e dólar com *forward fill* de
   no máximo 3 dias.
3. **Ausentes e outliers** (`qualidade.py`): lacunas, outliers por IQR nas variações diárias, validação
   NASA × INMET e Notícias Agrícolas × CEPEA → `reports/qualidade.md`.
4. **Atributos** (`features.py`): chuva acumulada 30/90/180 dias, dias secos, menor mínima em 30 dias,
   anomalia de chuva, dólar defasado 1/5/20 dias úteis, variações % diária e mensal, médias móveis,
   mês/ano, período de safra, distância da geada de 2021.
5. **Deflação**: preços reais pelo IPCA (R$ do último mês disponível).

## Machine learning

Regressão Linear (padronizada) e Random Forest, treinadas separadamente para café e soja, com dois alvos
(nível de preço e variação em 21 dias úteis). Validação `TimeSeriesSplit` (5 folds), métricas MAE, RMSE e
R², baseline pela média. Saídas em `reports/modelos/`. O objetivo é **explicar** (comparar a importância de
câmbio × clima × sazonalidade), não prever preços — R² fora da amostra baixo é esperado.

## Ética e legalidade

- `robots.txt` consultado antes de cada acesso (`src/utils.py::pode_acessar`).
- User-Agent descritivo identificando o projeto (defina `CRAWLER_CONTATO` para incluir um e-mail).
- Intervalo de 3 s entre requisições (`CRAWLER_INTERVALO`).
- Se o site recusar o acesso (403/429/desafio anti-bot), o crawler para e registra o motivo — não há
  tentativa de contornar bloqueios.
- Os dados são cotações de mercado e meteorológicos, não pessoais (LGPD não se aplica). Fontes sempre citadas.

## Automação (GitHub Actions)

`.github/workflows/crawler.yml` roda o crawler e a API do BCB todo dia útil às 19h e faz commit dos CSVs.
O workflow só é executado quando esta pasta é a **raiz** de um repositório no GitHub (hoje ela está dentro
do repositório geral da faculdade). Para ativar: crie o repositório público do projeto, copie esta pasta
para a raiz e, opcionalmente, defina a variável `CRAWLER_CONTATO` em *Settings → Variables*.

## Diferenças em relação ao pré-projeto

- Código em `src/` (em vez de `crawler/`), separado por etapa.
- O histórico desde 2020 vem das páginas por data do Notícias Agrícolas (mesmo indicador Cepea/Esalq),
  porque o CEPEA bloqueia downloads automatizados; as planilhas do CEPEA ficam como validação opcional.
- Inclusão das cotações internacionais (ICE/CBOT) para comparar preço interno × bolsa × câmbio.
- Preço × dólar mostrado como índice base 100 em um único eixo, em vez de gráfico de eixo duplo
  (escalas duplas induzem a correlações visuais enganosas).

## Limitações

As relações encontradas indicam **correlação, não causalidade**: estoques mundiais, demanda internacional
e produção de outros países não estão no estudo. O clima vem de um ponto por região (NASA POWER, grade de
~50 km), validado com estações do INMET.
