.PHONY: up down logs test lint format

# Start development environment
up:
	docker-compose -f docker-compose.dev.yml up -d

# Stop development environment
down:
	docker-compose -f docker-compose.dev.yml down

# View logs
logs:
	docker-compose -f docker-compose.dev.yml logs -f

# Run tests
test:
	docker-compose -f docker-compose.dev.yml run --rm app pytest

# Run linting
lint:
	docker-compose -f docker-compose.dev.yml run --rm app flake8 .
	docker-compose -f docker-compose.dev.yml run --rm app black . --check
	docker-compose -f docker-compose.dev.yml run --rm app isort . --check-only

# Format code
format:
	docker-compose -f docker-compose.dev.yml run --rm app black .
	docker-compose -f docker-compose.dev.yml run --rm app isort .

# Create initial database
init-db:
	docker-compose -f docker-compose.dev.yml run --rm app python -m app.db.init_db

# Create test data
seed-db:
	docker-compose -f docker-compose.dev.yml run --rm app python -m app.db.seed_db

# Clean all data
clean:
	docker-compose -f docker-compose.dev.yml down -v
