.PHONY: install lint typecheck test check demo run-demo clean

install:
	poetry install

lint:
	poetry run ruff check src tests

typecheck:
	poetry run mypy src

test:
	poetry run pytest --cov=euro_fsqca --cov-report=term-missing

check: lint typecheck test

demo:
	PYTHONPATH=src python -m euro_fsqca.cli demo --output data/processed/demo_raw.csv --n 6000 --seed 42

run-demo: demo
	PYTHONPATH=src python -m euro_fsqca.cli run --input data/processed/demo_raw.csv --config configs/analysis.demo.yml --output-dir results/demo

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
