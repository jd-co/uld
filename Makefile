.PHONY: help install install-dev lint format typecheck test test-cov clean build

help:
	@echo "ULD Development Commands"
	@echo "------------------------"
	@echo "install      Install package in editable mode"
	@echo "install-dev  Install with development dependencies"
	@echo "lint         Run linter (ruff)"
	@echo "format       Format code (ruff format)"
	@echo "typecheck    Run type checker (mypy)"
	@echo "test         Run tests"
	@echo "test-cov     Run tests with coverage"
	@echo "clean        Remove build artifacts"
	@echo "build        Build distribution packages"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,torrent]"
	pre-commit install

lint:
	ruff check src tests

format:
	ruff format src tests
	ruff check --fix src tests

typecheck:
	mypy src --ignore-missing-imports

test:
	pytest

test-cov:
	pytest --cov=src/uld --cov-report=html --cov-report=term-missing

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build: clean
	python -m build
