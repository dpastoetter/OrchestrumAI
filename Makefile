.PHONY: dev dev-backend dev-frontend install test build-frontend

PYTHONPATH := backend:agents:.
export PYTHONPATH
export ORCHESTRUMAI_STUB_RUN ?= 1

install:
	pip install -e ".[dev]"
	cd frontend && npm install

dev-backend:
	uvicorn orchestrumai.app:create_app --factory --host 127.0.0.1 --port 8000 --reload --reload-dir backend --reload-dir agents

dev-frontend:
	cd frontend && npm run dev

dev:
	@echo "Run 'make dev-backend' and 'make dev-frontend' in separate terminals"

build-frontend:
	cd frontend && npm run build

test:
	ORCHESTRUMAI_STUB_RUN=1 pytest backend/tests -q
