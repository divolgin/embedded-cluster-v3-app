.DEFAULT_GOAL := generate
PYTHON ?= python3
HELM ?= helm
REPLICATED ?= replicated
export HELM REPLICATED

.PHONY: generate lint release clean
generate:
	$(PYTHON) scripts/manifests.py generate

lint: generate
	$(PYTHON) scripts/manifests.py lint
	REPLICATED_RELEASE_VALIDATION_V2=1 $(REPLICATED) release lint --fail-on error

release: lint
	$(REPLICATED) release create --yaml-dir manifests

clean:
	rm -rf manifests .build charts/alpine-sleeper/charts
