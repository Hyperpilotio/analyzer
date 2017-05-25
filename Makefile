docker-build:
	sudo docker build -t analyzer .
docker-start:
	sudo docker run -d -p 7781:7781 analyzer
start:
	python analyzer/manage.py runserver 0.0.0.0:7781