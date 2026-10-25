install:
	pip install -r requirements.txt

run:
	python -m src.main

test:
	pytest tests/ -v

lint:
	flake8 src/ tests/