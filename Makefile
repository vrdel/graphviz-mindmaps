.PHONY: clean wheel-devel

clean:
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache \) -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
	rm -rf build dist *.egg-info

wheel-devel:
	python3 tools/build_wheel_devel.py
