SHELL := /bin/bash

COMPOSE := docker compose

.PHONY: help up up-build up-d up-postgres down restart logs ps pull

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
