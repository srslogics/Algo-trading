.PHONY: install migrate run test lint
install:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements.lock
	.venv/bin/python -m pip install --no-deps -e .
migrate:
	.venv/bin/alembic upgrade head
run: migrate
	.venv/bin/uvicorn optionlab.api.app:create_app --factory --host 127.0.0.1 --port 8000 --no-proxy-headers
test:
	.venv/bin/pytest -q
lint:
	.venv/bin/ruff check src tests scripts
