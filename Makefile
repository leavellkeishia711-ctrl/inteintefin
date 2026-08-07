.PHONY: up down prod-gate

up:
	docker compose -f 08-devops/docker-compose.yml up -d --build

down:
	docker compose -f 08-devops/docker-compose.yml down

prod-gate:
	docker compose -f 08-devops/docker-compose.ci.yml up -d --build
	# Wait for db to be healthy
	echo "Waiting for stack..."
	sleep 10
	docker compose -f 08-devops/docker-compose.ci.yml exec -T api alembic upgrade head
	# We can add more smoke tests here if needed
