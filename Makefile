.PHONY: install dev test lint typecheck migrate

install:
	pip install -e ".[dev]"

dev:
	uvicorn app.main:app --reload --port 8000

test:
	pytest

test-cov:
	pytest --cov=app --cov-report=term-missing

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .

typecheck:
	mypy app/

check: lint typecheck

migrate:
	alembic upgrade head

migration:
	@read -p "Migration message: " msg; alembic revision --autogenerate -m "$$msg"

setup-db:
	mkdir -p data
	alembic upgrade head
