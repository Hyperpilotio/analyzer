#!/bin/bash

# get all apps
curl -XGET localhost:5000/api/apps

# create 3 services
SERVICE_ID1=$(curl -XPOST -H "Content-Type: application/json" --data-binary "@workloads/goddd-service.json" localhost:5000/api/k8s_services)
SERVICE_ID2=$(curl -XPOST -H "Content-Type: application/json" --data-binary "@workloads/mongo-service.json" localhost:5000/api/k8s_services)
SERVICE_ID3=$(curl -XPOST -H "Content-Type: application/json" --data-binary "@workloads/pathfinder-service.json" localhost:5000/api/k8s_services)

# replace tech-demo-app service ids
sed -i -- "s/%SERVICE_ID1%/$SERVICE_ID1/g" workloads/tech-demo-app.json
sed -i -- "s/%SERVICE_ID2%/$SERVICE_ID2/g" workloads/tech-demo-app.json
sed -i -- "s/%SERVICE_ID3%/$SERVICE_ID3/g" workloads/tech-demo-app.json

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
