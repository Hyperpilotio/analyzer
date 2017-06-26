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
	
then connect to: [http://localhost:5000](http://localhost:5000)


### Setting up and running the app (without Docker)
- `make init`
- `make serve` (don't forget to connect to VPN first)

Please install Python 3.6.1 or later if you see the message from running `make init` saying that the Python version is outdated.
