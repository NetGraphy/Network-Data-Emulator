.PHONY: up down build migrate seed test logs shell

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m snep.seed

test:
	docker compose exec api pytest tests/ -v

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

logs-ssh:
	docker compose logs -f ssh

logs-snmp:
	docker compose logs -f snmp

shell:
	docker compose exec api bash

db-shell:
	docker compose exec postgres psql -U snep -d snep

reset-db:
	docker compose exec api alembic downgrade base
	docker compose exec api alembic upgrade head
	docker compose exec api python -m snep.seed

format:
	cd backend && ruff format snep/ tests/
	cd backend && ruff check --fix snep/ tests/
