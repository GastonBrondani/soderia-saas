.PHONY: help install dev test contract snapshot tenant migrate migrate-check revision lint

help:
	@echo "make install         instalar dependencias"
	@echo "make dev             levantar la API con reload"
	@echo "make test            correr todos los tests"
	@echo "make contract        verificar que la API no cambio"
	@echo "make snapshot        regenerar el contrato de la API"
	@echo "make tenant C=solmar R='Sodería Sol del Mar'   dar de alta una sodería"
	@echo "make migrate-check   ver que version tiene cada base"
	@echo "make migrate         aplicar migraciones a todas las bases"
	@echo "make revision M='descripcion'                  generar migracion"

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -q

contract:
	pytest tests/test_api_contract.py -v

snapshot:
	python scripts/snapshot_openapi.py

tenant:
	@test -n "$(C)" || (echo "Falta C=<codigo>"; exit 1)
	@test -n "$(R)" || (echo "Falta R='<razon social>'"; exit 1)
	python scripts/crear_tenant.py --codigo $(C) --razon-social "$(R)"

migrate-check:
	python scripts/migrate_all_tenants.py --dry-run

migrate:
	python scripts/migrate_all_tenants.py

revision:
	@test -n "$(M)" || (echo "Falta M='<descripcion>'"; exit 1)
	@test -n "$(ALEMBIC_TARGET_URL)" || (echo "Falta ALEMBIC_TARGET_URL"; exit 1)
	alembic revision --autogenerate -m "$(M)"

lint:
	ruff check app scripts tests
