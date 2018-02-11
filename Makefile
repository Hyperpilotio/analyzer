.PHONY : init test docker-build docker-run

ANALYZER_IMAGE ?= hyperpilot/analyzer
TAG ?= latest
SLO_CONFIG_IMAGE ?= hyperpilot/analyzer:config

PYTHON = python3
PYTHON_VERSION = $(shell $(PYTHON) --version)
PY_VERSION_OK = $(shell $(PYTHON) -c 'import sys; print(int(sys.version_info >= (3, 6, 1)))')
PIPENV = $(shell which pipenv)

GUNICORN_ARGS = api_service.wsgi:app --access-logfile - --error-logfile - -k gevent --bind 0.0.0.0:5000 --log-level debug --workers=1

init:
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

test:
	$(PIPENV) check
	$(PIPENV) run python -m unittest

serve:
	$(PIPENV) run gunicorn $(GUNICORN_ARGS)

run-server: serve

dev:
	$(PIPENV) run gunicorn $(GUNICORN_ARGS) --reload

dev-py: dev

docker-build:
	docker build -t $(ANALYZER_IMAGE):${TAG} .

docker-run: PORT ?= 5000
docker-run:
	docker run -d -p $(PORT):5000 $(ANALYZER_IMAGE)

docker-rm:
	docker rm -f $(shell docker ps -a -q --filter ancestor=$(ANALYZER_IMAGE))

docker-test:
	docker run -it $(ANALYZER_IMAGE):${TAG} pipenv run python -m unittest

docker-push:
	docker push $(ANALYZER_IMAGE):${TAG}

build-slo-form:
	docker build --no-cache -t $(SLO_CONFIG_IMAGE):${TAG} -f slo_config/Dockerfile .

run-slo-form: PORT ?= 5000
run-slo-form:
	docker run -d -p $(PORT):5000 $(SLO_CONFIG_IMAGE)
