# analyzer
Analyzer performs interference prediction and validation and visualizes the data.

#### Usage:
	
1. Build docker image

 		make docker-build
 	
2. Run server

		make docker-run
		
3. Test server 

		make docker-test
		
#### Configuration:
configuration file is located in 'config.ini'

	
#### Prerequisite:
In order to connect to database, connecting to VPN is needed for now.

#### UI:
	make docker-build
	make docker-run
	
then connect to: [http://localhost:5000/api](http://localhost:5000/api)


### Setting up and running the app (without Docker)
- `make init`
- `make serve` (don't forget to connect to VPN first)

Please install Python 3.6.1 or later if you see the message from running `make init` saying that the Python version is outdated.



### Running correlation coefficient calculation from influxdb data

`pipenv shell`

[run mongod]

`cd mongo-service/`

#### initialize mongo:
`mongo -u admin -p hyperpilot create-dbuser.js` (Drop users in create-dbuser.js from databases if they already exist in mongo instance.)

`cd ../`
#### main driver:
`python3 -u -m diagnosis.metric_consumer`

Results will be written to the resultdb correlations collection in mongo. 
