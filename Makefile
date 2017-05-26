.PHONY : docker-build docker-run

docker-build:
	sudo docker build -t hyperpilot/analyzer .

docker-run:
	sudo docker run -d -p 7781:7781 hyperpilot/analyzer

docker-rm:
	sudo docker rm -f $(shell sudo docker ps -q --filter ancestor=hyperpilot/analyzer)

post-dummyfile: 
	curl -X POST localhost:7781/prediction/testid2feature/$1 --data-binary @./analyzer/testing_requests/test_id.json
