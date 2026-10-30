.PHONY: up down logs test seed check backup
up:
	docker compose up --build -d
down:
	docker compose down
logs:
	docker compose logs -f web
test:
	docker compose exec web python manage.py test exchange -v 2
check:
	docker compose exec web python manage.py check --deploy
seed:
	docker compose exec web python manage.py seed_demo
backup:
	@echo 'Use pg_dump with appropriate credentials and encrypted external storage.'
