.PHONY : init test docker-build docker-run

ANALYZER_IMAGE ?= hyperpilot/analyzer
SLO_CONFIG_IMAGE ?= hyperpilot/analyzer:config

PYTHON = python3
PYTHON_VERSION = $(shell $(PYTHON) --version)
PY_VERSION_OK = $(shell $(PYTHON) -c 'import sys; print(int(sys.version_info >= (3, 6, 1)))')
PIPENV = $(shell which pipenv)

init: init-python init-js

init-python:
	@if [ $(PY_VERSION_OK) = 0 ]; then\
		echo Your Python version is $(PYTHON_VERSION);\
		echo "Please install Python 3.6.1 or later";\
	else\
		echo "Python version check passed!";\
		if [ "$(PIPENV)" = "" ]; then\
			echo "pipenv not found, installing...";\
			curl -L raw.github.com/kennethreitz/pipenv/master/get-pipenv.py | $(PYTHON);\
		else\
			echo "Pipenv installed!";\
		fi;\
		echo "Initialising pipenv";\
		pipenv install --three;\
	fi

init-js:
ifneq (, $(shell which yarn))
	cd frontend && yarn install
else
	cd frontend && npm install
endif

build-js:
ifneq (, $(shell which yarn))
	cd frontend && yarn build
else
	cd frontend && npm run build
endif

test:
	$(PIPENV) check
	$(PIPENV) run python -m unittest

serve: build-js
	$(PIPENV) run gunicorn main:application --access-logfile - --workers 4 --bind 0.0.0.0:5000

docker-build:
	docker build -t $(ANALYZER_IMAGE) .

docker-run: PORT ?= 5000
docker-run:
	docker run -d -p $(PORT):5000 $(ANALYZER_IMAGE)

docker-rm:
	docker rm -f $(shell docker ps -a -q --filter ancestor=$(ANALYZER_IMAGE))
	
docker-test:
	docker run -it $(ANALYZER_IMAGE) python -m unittest

build-slo-form:
	docker build -t $(SLO_CONFIG_IMAGE) -f slo_config/Dockerfile .

run-slo-form: PORT ?= 5000
run-slo-form:
	docker run -d -p $(PORT):5000 $(SLO_CONFIG_IMAGE)
