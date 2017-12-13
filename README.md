# Analyzer
Analyzer performs interference prediction and validation and visualizes the data.

#### Usage:
	
1. Build docker image

 		make docker-build
 	
2. Run server

		make docker-run
		
3. Test server 

		make docker-test
		
#### Configuration:
Configuration file is located in 'config.ini'

	
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


# Diagnosis
Diagnosis is our end-to-end node and container problem detection product.

#### Configuration:
Configuration file is located in 'config.ini'

#### Requirements:
1. Analyzer API and pipenv

- Follow instruction for setting up pipenv. (https://github.com/Hyperpilotio/analyzer/blob/master/api_service/README.md)

- After running
	`pipenv shell`

	run the API from the analyzer directory with
	`make dev` 

2. Influx

- Install influx and run the server using the command `influxd`.

- Install and configure aws. After installation, run
	`aws configure` and use the shared amazon s3 credentials here: (https://github.com/Hyperpilotio/hyperpilot-demo/wiki)

- From the hyperpilot-demo repo, run 
	`/hyperpilot_influx_restore.sh -n {name_of_backup_file}` to restore a snapshot uploaded to s3 to your local influx.

3. Mongo
- Install and run server with `mongod`.

- From the mongo_service directory, run `mongo create_user.js`. 

#### Running the analysis:
- From the analyzer directory (with the API, influxd, mongod and activated pipenv) run `python -u -m diagnosis.app_analyzer`
- Derived metrics and diagnosis results will be written to new influx databases. Problems and other diagnosis-related collections will be written to mongo. 
