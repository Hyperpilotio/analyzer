# Using local mongo
1. Restore dump file to local mongo 
	
		cd ./dump
		mongorestore .
	


2. Re-routing the db in config.init file

	```
	[MONGODB]
	HOST = localhost
	PORT = 27017
	USERNAME = analyzer
	PASSWORD = hyperpilot
	# Change LOGLEVEL to DEBUG to see show logs when performing Mongo queries
	LOGLEVEL = INFO
	```

