# analyzer
Analyzer performs interference prediction and validation

Usage:
	
1. Build docker image

 		make docker-build
 	
2. Run server

		make docker-run
		
3. Send request (post a json to analyzer)

		make post-dummyfile
		
		#expected response: {"dummy": "yummy"}