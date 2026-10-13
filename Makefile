PORT ?= 8000

.DEFAULT_GOAL := help
.PHONY: help build serve test test-live icons data fetch douban enrich clean

help: ## list the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

build: ## rebuild site/index.html from the template and data (seconds, offline)
	cd pipeline && python3 build.py

serve: build ## build, then serve site/ at http://localhost:8000 (change with PORT=)
	@echo "Serving http://localhost:$(PORT)  (Ctrl-C to stop)"
	python3 -m http.server $(PORT) -d site

test: build ## easter eggs, links, rating imports and release checks in headless Chrome (offline)
	node pipeline/tests/eggs.mjs
	OFFLINE=1 node pipeline/tests/ratings.mjs
	node pipeline/tests/site.mjs

test-live: build ## the same, plus the Douban bookmarklet on a public profile (needs network)
	node pipeline/tests/eggs.mjs
	node pipeline/tests/ratings.mjs
	node pipeline/tests/site.mjs

icons: ## redraw the favicons, touch icon and social card from pipeline/brand/ (needs network for fonts)
	cd pipeline && node brand.mjs

# The data steps live in pipeline/local/ (not in the repository) and reuse everything already cached; README's "Caches and refreshing ratings" says what to delete first.
data: ## full data refresh: fetch, douban, enrich, build (slow, needs network)
	$(MAKE) fetch
	$(MAKE) douban
	$(MAKE) enrich
	$(MAKE) build

fetch: ## titles, dates and posters from Wikipedia and Wikidata
	cd pipeline && python3 local/fetch.py

douban: ## match new titles on Douban by IMDb id (headless Chrome, paced)
	cd pipeline && python3 local/douban/add_jobs.py && node local/douban/subj.mjs && node local/douban/m.mjs && node local/douban/check.mjs

enrich: ## ratings, runtimes and seasons; writes pipeline/report.txt (REFRESH_RT=1 refetches Rotten Tomatoes)
	cd pipeline && python3 local/enrich.py

clean: ## remove test screenshots and Python bytecode (caches stay)
	rm -f pipeline/tests/*.png
	rm -rf pipeline/__pycache__
