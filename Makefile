PY := python3

.PHONY: all build beautiful clean site

all: build beautiful

build:
	$(PY) src/run_01_build.py

beautiful:
	$(PY) src/run_02_beautiful.py

# Regenerate the GitHub Pages page from README.md. Needs `pip install markdown`.
site:
	$(PY) tools/site.py

clean:
	rm -f figures/*.png output/*.csv data/processed/*
