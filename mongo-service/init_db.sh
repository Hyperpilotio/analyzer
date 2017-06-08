#!/bin/bash

MONGO_URL=internal-mongo-elb-624130134.us-east-1.elb.amazonaws.com:27017
DB_URL=${MONGO_URL}/admin
echo Create new dbs and users for mongodb at $MONGO_URL
mongo $DB_URL -u admin -p hyperpilot create-dbuser.js

MONGO_USER=analyzer
MONGO_PWD=hyperpilot

echo Create new collections and documents in configdb
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=configdb --collection=applications --type=json --file=application.json
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=configdb --collection=services --type=json --file=service.json
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=configdb --collection=loadtesters --type=json --file=load-tester.json
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=configdb --collection=qossensors --type=json --file=qos-sensor.json
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=configdb --collection=benchmarks --type=json --file=benchmarks.json

echo Create new collections and documents in metricdb
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=metricdb --collection=calibration --type=json --file=calibration-test.json
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=metricdb --collection=profiling --type=json --file=profiling-test.json
mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=metricdb --collection=validation --type=json --file=validation-test.json

ls -1 ./test_profiles/*.json | while read col; do 
    mongoimport -h $MONGO_URL -u $MONGO_USER -p $MONGO_PWD --db=metricdb --collection=profiling --type=json --file=$col; 
done
