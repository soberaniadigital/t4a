.PHONY: setup setup-python setup-r analysis experiment-data

setup: setup-python setup-r

setup-python:
	python3 -m venv .venv
	.venv/bin/pip install -e ".[stats]"

setup-r:
	Rscript setup_r.R

experiment-data:
	python3 estatisticas/generate_experiment_csv.py

analysis: experiment-data
	Rscript estatisticas/analysis.R
