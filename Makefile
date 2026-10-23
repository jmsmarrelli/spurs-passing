# Pipeline stages share generated inputs and must run in order.
.NOTPARALLEL:
PY ?= python3

.PHONY: all build beautiful clean site

all: verify-data build beautiful

build:
	$(PY) src/run_01_build.py

beautiful:
	$(PY) src/run_02_beautiful.py

# Regenerate the GitHub Pages page from README.md. Needs `pip install -r requirements.txt`.
site:
	$(PY) tools/site.py

clean:
	rm -f figures/*.png output/*.csv data/processed/*

.PHONY: fetch-data verify-data
fetch-data:
	$(PY) tools/fetch_data.py

verify-data:
	$(PY) tools/fetch_data.py --check

.PHONY: report
report:
	$(PY) tools/report.py
