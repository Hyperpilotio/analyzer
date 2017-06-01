db = connect('internal-mongo-elb-624130134.us-east-1.elb.amazonaws.com/admin');
db.auth( "admin", "hyperpilot" );
//db.updateUser("admin", 
//	 { "roles" : [
//		{ "root", "admin" },
//		"readWriteAnyDatabase"
//	   ] 
//	 }
//);

db = db.getSiblingDB('configdb');
db.createUser ( {
    user: "analyzer",
    pwd: "hyperpilot",
    roles: [ 
	     { role: "readWrite", db: "configdb" },
	     { role: "readWrite", db: "metricdb" }
           ]
  }
);

db = db.getSiblingDB('metricdb');
db.createUser ( {
    user: "analyzer",
    pwd: "hyperpilot",
    roles: [ 
	     { role: "readWrite", db: "configdb" },
	     { role: "readWrite", db: "metricdb" }
           ]
  }
);
