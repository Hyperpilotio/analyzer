#!/bin/bash

# create app
APP_ID=$(curl -s  -H  "Content-Type: application/json" -X POST -d '{"path":"workloads/tech-demo-app.json"}' localhost:5000/api/apps | grep app | cut -d " " -f4  | cut -d "\"" -f2) ; echo $APP_ID

# require type and name (this example has no type)
curl -s  -H  "Content-Type: application/json" -X POST -d '{"path":"workloads/tech-demo-bad-input.json"}' localhost:5000/api/apps

# get one app by id
curl -XGET localhost:5000/api/apps/$APP_ID

# modify app
curl -XPUT localhost:5000/api/apps/$APP_ID

# get all apps
curl -XGET localhost:5000/api/apps

# delete an app by id 
curl -XDELETE localhost:5000/api/apps/$APP_ID
