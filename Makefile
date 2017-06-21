.PHONY : init test docker-build docker-run

PYTHON=python3
PYTHON_VERSION=$(shell $(PYTHON) --version)
PY_VERSION_OK=$(shell $(PYTHON) -c 'import sys; print(int(sys.version_info >= (3, 6, 1)))')
PIPENV=$(shell which pipenv)

init: init-python init-node

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

init-node:
ifneq (, $(shell which yarn))
	yarn install --dev
	yarn build
else
	npm install --dev
	npm run build
endif

test:
	$(PIPENV) run python -m unittest

docker-build:
	sudo docker build -t hyperpilot/analyzer .

docker-run:
	sudo docker run -it -p 7781:7781 hyperpilot/analyzer ./manage.py runserver 0.0.0.0:7781

docker-rm:
	sudo docker rm -f $(shell sudo docker ps -q --filter ancestor=hyperpilot/analyzer)
	
docker-test:
	sudo docker run -it hyperpilot/analyzer ./manage.py test

build-slo-form:
	docker build -t hyperpilot/analyzer:config -f Dockerfile.slo-config .

run-slo-form:
	docker run -d -p 5000:5000 hyperpilot/analyzer:config
