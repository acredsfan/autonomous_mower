# Makefile for autonomous mower project
# Provides convenient commands for development, testing, and code quality

.PHONY: help install install-dev test test-unit test-integration test-hardware test-all
.PHONY: lint format type-check security-check quality-check quality-fix
.PHONY: clean clean-cache clean-coverage clean-all
.PHONY: docs serve-docs
.PHONY: run run-simulation run-test
.PHONY: setup-hooks pre-commit

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "Installation:"
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo "  setup-hooks      Setup pre-commit hooks"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-hardware    Run hardware tests only"
	@echo "  test-simulation  Run simulation tests only"
	@echo "  test-coverage    Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run linting (flake8)"
	@echo "  format           Format code (black, isort)"
	@echo "  type-check       Run type checking (mypy)"
	@echo "  security-check   Run security analysis (bandit)"
	@echo "  quality-check    Run all quality checks"
	@echo "  quality-fix      Run quality checks and fix issues"
	@echo "  import-check     Check import dependencies"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean            Clean temporary files"
	@echo "  clean-cache      Clean Python cache files"
	@echo "  clean-coverage   Clean coverage reports"
	@echo "  clean-all        Clean everything"
	@echo ""
	@echo "Running:"
	@echo "  run              Run the mower system"
	@echo "  run-simulation   Run in simulation mode"
	@echo "  run-test         Run hardware diagnostics"

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e ".[dev,test]"
	pip install pre-commit pytest-cov pytest-mock pytest-asyncio pytest-timeout pytest-xdist

setup-hooks:
	pre-commit install
	pre-commit install --hook-type commit-msg

# Testing targets
test:
	python -m pytest tests/ -v

test-unit:
	python -m pytest tests/unit/ -v -m "unit"

test-integration:
	python -m pytest tests/integration/ -v -m "integration"

test-hardware:
	python -m pytest tests/hardware_integration/ -v -m "hardware"

test-simulation:
	python -m pytest tests/simulation/ -v -m "simulation"

test-coverage:
	python -m pytest tests/ --cov=src/mower --cov-report=html --cov-report=term-missing

test-integration:
	python scripts/run_integration_tests.py

test-system-startup:
	python scripts/run_integration_tests.py --suite startup

test-component-interactions:
	python scripts/run_integration_tests.py --suite interactions

test-hardware-simulation:
	python scripts/run_integration_tests.py --suite simulation

test-safety-integration:
	python scripts/run_integration_tests.py --suite safety

test-performance:
	python scripts/run_integration_tests.py --suite performance

test-all:
	python -m pytest tests/ -v --cov=src/mower --cov-report=html --cov-report=term-missing --durations=10

# Code quality targets
lint:
	python -m flake8 src/ tests/ --max-line-length=120 --extend-ignore=E203,W503,D100,D104

format:
	python -m black src/ tests/ --line-length=120
	python -m isort src/ tests/ --profile=black --line-length=120

type-check:
	python -m mypy src/

security-check:
	python -m bandit -r src/ -c pyproject.toml

quality-check:
	python scripts/run_code_quality_checks.py

quality-fix:
	python scripts/run_code_quality_checks.py --fix

import-check:
	python scripts/test_import_dependencies.py

pre-commit:
	pre-commit run --all-files

# Cleaning targets
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

clean-cache:
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-coverage:
	rm -rf htmlcov/
	rm -f .coverage
	rm -f coverage.xml

clean-all: clean clean-cache clean-coverage
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .tox/

# Documentation targets
docs:
	@echo "Documentation generation not yet implemented"

serve-docs:
	@echo "Documentation serving not yet implemented"

# Running targets
run:
	python -m mower.main_controller

run-simulation:
	SIMULATION_MODE=true python -m mower.main_controller

run-test:
	python -m mower.diagnostics.hardware_test

# Development helpers
check-deps:
	pip check

list-deps:
	pip list

freeze-deps:
	pip freeze > requirements-frozen.txt

# CI/CD helpers
ci-install:
	pip install -e ".[dev,test]"

ci-test:
	python -m pytest tests/ --cov=src/mower --cov-report=xml --junitxml=junit.xml

ci-quality:
	python scripts/run_code_quality_checks.py

# System service helpers (requires sudo)
install-service:
	sudo cp deployment/mower.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable mower

start-service:
	sudo systemctl start mower

stop-service:
	sudo systemctl stop mower

status-service:
	sudo systemctl status mower

logs-service:
	sudo journalctl -u mower -f