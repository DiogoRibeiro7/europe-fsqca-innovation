PYTHON ?= poetry run python
ANALYSIS_INPUT ?= data/processed/wbes_eu27_analysis.csv
RAW_TABLE ?= data/interim/wbes_eu27_raw.parquet
INGEST_SPEC ?= configs/wbes_ingestion.yml
MAIN_CONFIG ?= configs/analysis.yml
MAIN_RESULTS ?= results/main
DEMO_INPUT ?= data/processed/demo_raw.csv
DEMO_CONFIG ?= configs/analysis.demo.yml
DEMO_RESULTS ?= results/demo
R_SCRIPT ?= Rscript
R_INPUT ?= results/main/calibrated_memberships.csv
R_OUTCOME ?= INN
R_OUTPUT ?= results/main/r_validation/europe

.PHONY: install lint typecheck test check ingest readiness validate-spec validate-data schema-audit variable-audit validate-mapping check-harmonisation construct-diagnostics calibration-diagnostics r-check-env r-setup r-crosscheck parity demo run-demo run-main repro-demo clean

install:
	poetry install

lint:
	poetry run ruff check .

typecheck:
	poetry run mypy src tests

test:
	poetry run pytest --cov=euro_fsqca --cov-report=term-missing

check: lint typecheck test

ingest:
	$(PYTHON) scripts/build_analysis_table.py --manifest data/manifest.csv --raw-root data/raw --spec $(INGEST_SPEC) --output $(RAW_TABLE)

readiness:
	$(PYTHON) -m euro_fsqca.cli readiness --config $(MAIN_CONFIG) --mapping configs/wbes_variable_map.yml --manifest data/manifest.csv --root data/raw

validate-spec:
	$(PYTHON) -m euro_fsqca.cli validate-spec --spec configs/research_spec.yml

validate-data:
	$(PYTHON) -m euro_fsqca.cli validate-data --manifest data/manifest.csv --root data/raw

schema-audit:
	$(PYTHON) -m euro_fsqca.cli schema-audit --manifest data/manifest.csv --root data/raw --output outputs/data/schema_audit.csv

variable-audit:
	$(PYTHON) -m euro_fsqca.cli variable-audit --manifest data/manifest.csv --root data/raw --output outputs/data/variable_coverage.csv

validate-mapping:
	$(PYTHON) -m euro_fsqca.cli validate-mapping --mapping configs/wbes_variable_map.yml --output outputs/data/mapping_coverage.csv

check-harmonisation:
	$(PYTHON) -m euro_fsqca.cli check-harmonisation --input $(ANALYSIS_INPUT)

construct-diagnostics:
	$(PYTHON) -m euro_fsqca.cli construct-diagnostics --input $(ANALYSIS_INPUT) --config $(MAIN_CONFIG)

calibration-diagnostics:
	$(PYTHON) -m euro_fsqca.cli calibration-diagnostics --input $(ANALYSIS_INPUT) --config $(MAIN_CONFIG)

r-check-env:
	$(R_SCRIPT) r/setup_renv.R

r-setup:
	$(R_SCRIPT) r/setup_renv.R --install

r-crosscheck:
	$(R_SCRIPT) r/qca_crosscheck.R $(R_INPUT) $(MAIN_CONFIG) $(R_OUTPUT) $(R_OUTCOME)

parity:
	$(PYTHON) scripts/run_parity.py --results $(MAIN_RESULTS) --config $(MAIN_CONFIG) --output outputs/validation/python_r_parity.csv

demo:
	$(PYTHON) -m euro_fsqca.cli demo --output $(DEMO_INPUT) --n 6000 --seed 42

# The synthetic demo is a software smoke test, so it must declare itself as one.
run-demo: demo
	$(PYTHON) -m euro_fsqca.cli run --input $(DEMO_INPUT) --config $(DEMO_CONFIG) --output-dir $(DEMO_RESULTS) --unsafe-development-run

run-main:
	$(PYTHON) -m euro_fsqca.cli run --input $(ANALYSIS_INPUT) --config $(MAIN_CONFIG) --output-dir $(MAIN_RESULTS)

repro-demo: validate-spec run-demo check

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
