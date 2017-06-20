# analyzer
Analyzer performs interference prediction and validation and visualizes the data.

## # Running the api service app

### Requirements:
- Python **3.6.1**
- pipenv

### Setup:
- Install Python 3.6.1 (`brew install python3` on Mac)
- Install pipenv (`curl raw.github.com/kennethreitz/pipenv/master/get-pipenv.py | python3`)
- `pipenv install --three`

### Running
Don't forget to open your VPN first!
- `pipenv shell`
- `FLASK_APP=api_service/app.py flask run`

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
