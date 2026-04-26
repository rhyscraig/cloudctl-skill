.PHONY: help install test test-cov test-security lint format clean docs install-dev

help:
	@echo "CloudctlSkill Development Commands"
	@echo "==================================="
	@echo ""
	@echo "Installation:"
	@echo "  make install          - Install cloudctl-skill in development mode"
	@echo "  make install-dev      - Install with all dev dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test             - Run all tests"
	@echo "  make test-cov         - Run tests with coverage report"
	@echo "  make test-security    - Run security tests only"
	@echo "  make test-unit        - Run unit tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             - Run linting checks"
	@echo "  make format           - Format code with black"
	@echo "  make type-check       - Run type checking with mypy"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs             - Build documentation"
	@echo "  make docs-serve       - Build and serve docs locally"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            - Remove build artifacts and cache"
	@echo "  make clean-all        - Remove all generated files"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v

test-cov:
	python -m pytest tests/ --cov=cloudctl_skill --cov-report=html --cov-report=term

test-security:
	python -m pytest tests/test_security.py -v

test-unit:
	python -m pytest tests/test_cloudctl_skill.py -v

test-integration:
	python -m pytest tests/ -v -m integration

lint:
	ruff check src/ tests/

format:
	black src/ tests/
	ruff check --fix src/ tests/

type-check:
	mypy src/

docs:
	cd docs && make html

docs-serve:
	cd docs && make html && python -m http.server --directory _build/html

clean:
	rm -rf build/ dist/ *.egg-info __pycache__ .pytest_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-all: clean
	rm -rf docs/_build/
	rm -rf .mypy_cache/

.DEFAULT_GOAL := help
