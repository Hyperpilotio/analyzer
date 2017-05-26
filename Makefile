docker-build:
	sudo docker build -t analyzer .
docker-run:
	sudo docker run -d -p 7781:7781 analyzer
run:
	python analyzer/manage.py runserver 0.0.0.0:7781
