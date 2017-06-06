# analyzer
Analyzer performs interference prediction and validation

#### Usage:
	
1. Build docker image

 		make docker-build
 	
2. Run server

		make docker-run
		
3. Test server 

		make docker-test
		
#### Configuration:
configuration file is located in 'config.json'

	
#### Prerequisite:
In order to connect to database, connecting to VPN is needed for now.

#### UI:
	
	make docker-build
	make docker-run
then connect to: [http://localhost:7781](http://localhost:7781)