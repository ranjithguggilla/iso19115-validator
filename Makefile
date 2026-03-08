.PHONY: help install dev lint test test-cov check suggest fair serve sample clean

PYTHON  := python3
PIP     := pip
PYTEST  := pytest

help:
	@echo "iso19115-validator — make targets"
	@echo ""
	@echo "  install     pip install (production)"
	@echo "  dev         pip install -e '.[dev]'"
	@echo "  lint        ruff check"
	@echo "  test        pytest"
	@echo "  test-cov    pytest with coverage report"
	@echo "  check       validate example metadata"
	@echo "  suggest     show suggestions for example metadata"
	@echo "  fair        compute FAIR score for example metadata"
	@echo "  serve       start the web UI"
	@echo "  sample      generate sample reports for docs"
	@echo "  clean       remove build artifacts"

install:
	$(PIP) install .

dev:
	$(PIP) install -e ".[dev]"

lint:
	ruff check isolint/ tests/

test:
	$(PYTEST) tests/

test-cov:
	$(PYTEST) --cov=isolint --cov-report=term-missing --cov-report=html tests/

check:
	isolint check examples/valid_metadata.xml
	@echo ""
	isolint check examples/incomplete_metadata.xml || true

suggest:
	isolint suggest examples/valid_metadata.xml

fair:
	isolint fair examples/valid_metadata.xml

serve:
	isolint serve

sample:
	$(PYTHON) scripts/generate_sample_report.py

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ htmlcov/ .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
