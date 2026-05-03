SHELL := /bin/bash

COMPOSE := docker compose

.PHONY: help up up-build up-d up-postgres down restart logs ps pull \
        ci ci-server ci-web test test-server test-web lint typecheck \
        openapi gen-types

help:
	@echo "Targets disponiveis:"
	@echo "  make up           - Sobe server + web (SQLite, foreground)"
	@echo "  make up-build     - Sobe com build forcado (SQLite, foreground)"
	@echo "  make up-d         - Sobe em background (SQLite)"
	@echo "  make up-postgres  - Sobe server + web + postgres (foreground)"
	@echo "  make down         - Derruba containers e remove orfaos"
	@echo "  make restart      - Reinicia stack local (SQLite)"
	@echo "  make logs         - Segue logs de todos os servicos"
	@echo "  make ps           - Lista status dos servicos"
	@echo "  make pull         - Atualiza imagens base"
	@echo ""
	@echo "  make ci           - Roda tudo o que CI roda (server + web)"
	@echo "  make ci-server    - ruff + mypy + pytest+cov + alembic smoke"
	@echo "  make ci-web       - tsc + vitest"
	@echo "  make test         - Atalho para pytest do server"
	@echo "  make lint         - ruff check em src/ + tests/"
	@echo "  make typecheck    - mypy --strict em src/"
	@echo "  make openapi      - Dump server/openapi.json a partir do FastAPI app"
	@echo "  make gen-types    - openapi.json -> web/src/types/api.gen.ts"

up:
	$(COMPOSE) up

up-build:
	$(COMPOSE) up --build

up-d:
	$(COMPOSE) up -d

up-postgres:
	$(COMPOSE) --profile postgres up

down:
	$(COMPOSE) down --remove-orphans

restart: down up

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

pull:
	$(COMPOSE) pull

# ── CI parity targets ───────────────────────────────────────────────────────
# Run the same checks GitHub Actions runs, locally. Useful before pushing.

ci: ci-server ci-web

ci-server:
	cd server && ruff check src tests
	cd server && mypy --strict src
	cd server && pytest --cov=agora --cov-report=term-missing
	cd server && DATABASE_URL=sqlite:///ci_alembic.db alembic upgrade head \
	         && DATABASE_URL=sqlite:///ci_alembic.db alembic downgrade base \
	         && rm -f server/ci_alembic.db

ci-web:
	cd web && npx tsc --noEmit -p .
	cd web && npm test -- --run

test: test-server

test-server:
	cd server && pytest

test-web:
	cd web && npm test -- --run

lint:
	cd server && ruff check src tests

typecheck:
	cd server && mypy --strict src

# ── OpenAPI codegen ─────────────────────────────────────────────────────────
# Dump the FastAPI app's schema to a local file the web can consume without
# needing a running server. Then regenerate the typed client mirror.

openapi:
	cd server && python -c "import json; from agora.interfaces.api.main import app; print(json.dumps(app.openapi(), indent=2))" > openapi.json
	@echo "Wrote server/openapi.json"

gen-types: openapi
	cd web && npm run gen:api
