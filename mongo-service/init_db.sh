#!/bin/bash

MONGO_URL=`kubectl describe services mongo-publicport0 | grep elb | cut -d":" -f2 | xargs`:27017
echo mongodb service running at: $MONGO_URL
MONGO_USER=analyzer
MONGO_PWD=hyperpilot

echo Create new dbs and users
mongo $MONGO_URL create-dbuser.js

echo Create new collections and documents in configdb
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=configdb --collection=applications --type=json --file=application.json
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=configdb --collection=services --type=json --file=service.json
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=configdb --collection=loadtesters --type=json --file=load-tester.json
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=configdb --collection=qossensors --type=json --file=qos-sensor.json
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=configdb --collection=benchmarks --type=json --file=benchmark.json

echo Create new collections and documents in metricdb
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=metricdb --collection=calibration --type=json --file=calibration-test.json
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=metricdb --collection=profiling --type=json --file=profiling-test.json
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=metricdb --collection=validation --type=json --file=validation-test.json
