#!/bin/bash

# get all apps
curl -XGET localhost:5000/api/apps

# create app
APP_ID=$(curl -s  -H  "Content-Type: application/json" -X POST --data-binary "@workloads/tech-demo-app.json" localhost:5000/api/apps | grep data | cut -d " " -f4  | cut -d "\"" -f2) ; echo "app_id in new app: $APP_ID"

# require type and name (this example has no type)
curl -s  -H  "Content-Type: application/json" -X POST --data-binary "@workloads/tech-demo-bad-input.json" localhost:5000/api/apps

# get one app by id
curl -XGET localhost:5000/api/apps/$APP_ID

# update an existing app
curl -H "Content-Type: application/json" -X PUT localhost:5000/api/apps/$APP_ID --data-binary "@workloads/tech-demo-partial-update.json"

# delete an app by id 
curl -XDELETE localhost:5000/api/apps/$APP_ID

# add microservices to an app
curl -H "Content-Type: application/json" -X POST localhost:5000/api/apps/$APP_ID/services --data-binary "@workloads/microservices.json"
