db = connect('af640dca0423a11e797230e306c4e9ed-596311498.us-east-1.elb.amazonaws.com:27017/admin');
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
