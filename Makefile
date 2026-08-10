PYTHON ?= poetry run python
ANALYSIS_INPUT ?= data/processed/wbes_eu27_analysis.csv
MAIN_CONFIG ?= configs/analysis.yml
MAIN_RESULTS ?= results/main
DEMO_INPUT ?= data/processed/demo_raw.csv
DEMO_CONFIG ?= configs/analysis.demo.yml
DEMO_RESULTS ?= results/demo

.PHONY: install lint typecheck test check validate-spec validate-data schema-audit validate-mapping check-harmonisation construct-diagnostics calibration-diagnostics demo run-demo run-main repro-demo clean

install:
	poetry install

lint:
	poetry run ruff check .

typecheck:
	poetry run mypy src tests

test:
	poetry run pytest --cov=euro_fsqca --cov-report=term-missing

check: lint typecheck test

validate-spec:
	$(PYTHON) -m euro_fsqca.cli validate-spec --spec configs/research_spec.yml

validate-data:
	$(PYTHON) -m euro_fsqca.cli validate-data --manifest data/manifest.csv --root data/raw

schema-audit:
	$(PYTHON) -m euro_fsqca.cli schema-audit --manifest data/manifest.csv --root data/raw --output outputs/data/schema_audit.csv

validate-mapping:
	$(PYTHON) -m euro_fsqca.cli validate-mapping --mapping configs/wbes_variable_map.yml --output outputs/data/mapping_coverage.csv

check-harmonisation:
	$(PYTHON) -m euro_fsqca.cli check-harmonisation --input $(ANALYSIS_INPUT)

construct-diagnostics:
	$(PYTHON) -m euro_fsqca.cli construct-diagnostics --input $(ANALYSIS_INPUT) --config $(MAIN_CONFIG)

calibration-diagnostics:
	$(PYTHON) -m euro_fsqca.cli calibration-diagnostics --input $(ANALYSIS_INPUT) --config $(MAIN_CONFIG)

demo:
	$(PYTHON) -m euro_fsqca.cli demo --output $(DEMO_INPUT) --n 6000 --seed 42

run-demo: demo
	$(PYTHON) -m euro_fsqca.cli run --input $(DEMO_INPUT) --config $(DEMO_CONFIG) --output-dir $(DEMO_RESULTS)

run-main:
	$(PYTHON) -m euro_fsqca.cli run --input $(ANALYSIS_INPUT) --config $(MAIN_CONFIG) --output-dir $(MAIN_RESULTS)

repro-demo: validate-spec run-demo check

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
