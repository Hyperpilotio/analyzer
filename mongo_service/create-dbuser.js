db = db.getSiblingDB('configdb');
db.createUser ( {
    user: "analyzer",
    pwd: "hyperpilot",
    roles: [
	     { role: "readWrite", db: "configdb" },
	     { role: "readWrite", db: "metricdb" },
	     { role: "readWrite", db: "resultdb" }
           ]
  }
);

db.createUser ( {
    user: "profiler",
    pwd: "hyperpilot",
    roles: [
	     { role: "readWrite", db: "configdb" },
	     { role: "readWrite", db: "metricdb" },
	     { role: "readWrite", db: "resultdb" }
           ]
  }
);

db = db.getSiblingDB('metricdb');
db.createUser ( {
    user: "analyzer",
    pwd: "hyperpilot",
    roles: [
	     { role: "readWrite", db: "configdb" },
	     { role: "readWrite", db: "metricdb" },
	     { role: "readWrite", db: "resultdb" }
           ]
  }
);

db.createUser ( {
    user: "profiler",
    pwd: "hyperpilot",
    roles: [
	     { role: "readWrite", db: "configdb" },
	     { role: "readWrite", db: "metricdb" },
	     { role: "readWrite", db: "resultdb" }
           ]
  }
);

db = db.getSiblingDB('resultdb');
db.createUser ( {
    user: "analyzer",
    pwd: "hyperpilot",
    roles: [
	     { role: "readWrite", db: "configdb" },
	     { role: "readWrite", db: "metricdb" },
	     { role: "readWrite", db: "resultdb" }
           ]
  }
);

db.createUser ( {
    user: "profiler",
    pwd: "hyperpilot",
    roles: [
	     { role: "readWrite", db: "configdb" },
	     { role: "readWrite", db: "metricdb" },
	     { role: "readWrite", db: "resultdb" }
           ]
  }
              );

db = db.getSiblingDB('jobdb');
db.createUser ( {
    user: "analyzer",
    pwd: "hyperpilot",
    roles: [
	     { role: "readWrite", db: "configdb" },
	     { role: "readWrite", db: "metricdb" },
	     { role: "readWrite", db: "resultdb" },
             { role: "readWrite", db: "jobdb" },
           ]
  }
);

db.createUser ( {
    user: "profiler",
    pwd: "hyperpilot",
    roles: [
	     { role: "readWrite", db: "configdb" },
	     { role: "readWrite", db: "metricdb" },
             { role: "readWrite", db: "resultdb" },
             { role: "readWrite", db: "jobdb" },
           ]
 });
