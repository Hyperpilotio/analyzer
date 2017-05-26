.PHONY : docker-build docker-run

docker-build:
	sudo docker build -t analyzer .

docker-run:
	sudo docker run -d -p 7781:7781 analyzer

docker-rm:
	sudo docker rm -f $(shell sudo docker ps -q --filter ancestor=analyzer)

post-dummyfile: 
	curl -X POST localhost:7781/prediction/predict/$1 --data-binary @./analyzer/test_request/test.json
