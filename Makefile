.PHONY: install run test lint seed docker-up docker-down

install:
	python -m pip install -r requirements-dev.txt

run:
	uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000

test:
	pytest

lint:
	ruff check app tests

seed:
	SEED_SAMPLE_DATA=true uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
