.PHONY: install test demo serve

install:
	pip install -e ".[dev]"

test:
	pytest -q

demo:
	python -m baseline.demo

serve:
	python -m baseline.serve
