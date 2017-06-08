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

db = db.getSiblingDB('configdb');
db.createUser ( {
    user: "profiler",
    pwd: "hyperpilot",
    roles: [ 
	     { role: "readWrite", db: "configdb" },
	     { role: "readWrite", db: "metricdb" }
           ]
  }
);
