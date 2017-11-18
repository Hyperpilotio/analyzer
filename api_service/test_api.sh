#!/bin/bash

# get all apps
curl -XGET localhost:5000/api/apps

# create 3 services
SERVICE_ID1=$(curl -XPOST -H "Content-Type: application/json" --data-binary "@workloads/goddd-service.json" localhost:5000/api/k8s_services | jq .data | cut -d"\"" -f2)
SERVICE_ID2=$(curl -XPOST -H "Content-Type: application/json" --data-binary "@workloads/mongo-service.json" localhost:5000/api/k8s_services | jq .data | cut -d"\"" -f2)
SERVICE_ID3=$(curl -XPOST -H "Content-Type: application/json" --data-binary "@workloads/pathfinder-service.json" localhost:5000/api/k8s_services | jq .data | cut -d"\"" -f2)

echo "goddd service created: $SERVICE_ID1"
echo "mongo service created: $SERVICE_ID2"
echo "pathfinder service created: $SERVICE_ID3"

# replace tech-demo-app service ids
sed "s/service-0001/$SERVICE_ID1/g" workloads/tech-demo-app.json > /tmp/tech-demo-app.json
sed -i -- "s/service-0002/$SERVICE_ID2/g" /tmp/tech-demo-app.json
sed -i -- "s/service-0003/$SERVICE_ID3/g" /tmp/tech-demo-app.json

# create app
APP_ID=$(curl -s  -H  "Content-Type: application/json" -X POST --data-binary "@/tmp/tech-demo-app.json" localhost:5000/api/apps | grep data | cut -d " " -f4  | cut -d "\"" -f2) ; echo "app_id in new app: $APP_ID"

# require type and name (this example has no type)
#curl -s  -H  "Content-Type: application/json" -X POST --data-binary "@workloads/tech-demo-bad-input.json" localhost:5000/api/apps

# get one app by id
#curl -XGET localhost:5000/api/apps/$APP_ID

# update an existing app
#curl -H "Content-Type: application/json" -X PUT localhost:5000/api/apps/$APP_ID --data-binary "@workloads/tech-demo-partial-update.json"

# delete an app by id
#curl -XDELETE localhost:5000/api/apps/$APP_ID

# add microservices to an app
#curl -H "Content-Type: application/json" -X POST localhost:5000/api/apps/$APP_ID/services --data-binary "@workloads/microservices.json"
