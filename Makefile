.PHONY : docker-build docker-run

docker-build:
	sudo docker build -t hyperpilot/analyzer .

docker-run:
	sudo docker run -it -p 7781:7781 hyperpilot/analyzer ./manage.py runserver 0.0.0.0:7781

docker-rm:
	sudo docker rm -f $(shell sudo docker ps -q --filter ancestor=hyperpilot/analyzer)
	
docker-test:
	sudo docker run -it hyperpilot/analyzer ./manage.py test
