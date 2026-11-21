PY := .venv/bin/python

.PHONY: venv coleta backfill tratamento analise modelagem tudo painel testes notebooks limpar

venv:            ## cria o ambiente virtual e instala as dependencias
	python3 -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

coleta:          ## coleta todas as fontes (sem o backfill historico)
	$(PY) -m src.pipeline coleta

backfill:        ## historico do Noticias Agricolas desde 2020 (~3 h, retomavel)
	$(PY) -m src.coleta.noticias_agricolas --backfill

tratamento:      ## limpeza, integracao, features e relatorio de qualidade
	$(PY) -m src.pipeline tratamento

analise:         ## graficos e tabelas P1-P6
	$(PY) -m src.pipeline analise

modelagem:       ## Regressao Linear e Random Forest
	$(PY) -m src.pipeline modelagem

tudo: coleta tratamento analise modelagem

painel:          ## painel Streamlit
	.venv/bin/streamlit run app/streamlit_app.py

testes:
	.venv/bin/pytest -q

notebooks:       ## executa os notebooks e salva as saidas
	.venv/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb

limpar:          ## remove dados derivados (mantem data/raw)
	rm -rf data/interim/* data/processed/* reports/figures/* reports/modelos/* reports/tabelas/*
