.PHONY: test dev db-up db-down migrate migrate-down

test:
	pytest -v

dev:
	uvicorn app.main:app --reload

db-up:
	docker-compose -f ../08-devops/docker-compose.yml up -d

db-down:
	docker-compose -f ../08-devops/docker-compose.yml down

migrate:
	alembic upgrade head

migrate-down:
	alembic downgrade -1
