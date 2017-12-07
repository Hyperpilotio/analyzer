#!/bin/bash

#check jq is available
if  ! type jq > /dev/null; then
  echo "jq is required for test, Install first"
  return
fi

# get all apps
echo "get all apps: "
curl -XGET localhost:5000/api/apps

# create 3 services
SERVICE_ID1=$(curl -s -XPOST -H "Content-Type: application/json" --data-binary "@workloads/goddd-service.json" localhost:5000/api/k8s_services | jq .data | cut -d"\"" -f2)
SERVICE_ID2=$(curl -s -XPOST -H "Content-Type: application/json" --data-binary "@workloads/mongo-service.json" localhost:5000/api/k8s_services | jq .data | cut -d"\"" -f2)
SERVICE_ID3=$(curl -s -XPOST -H "Content-Type: application/json" --data-binary "@workloads/pathfinder-service.json" localhost:5000/api/k8s_services | jq .data | cut -d"\"" -f2)

echo "goddd service created: $SERVICE_ID1"
echo "mongo service created: $SERVICE_ID2"
echo "pathfinder service created: $SERVICE_ID3"

# replace tech-demo-app service ids
sed "s/service-0001/$SERVICE_ID1/g" workloads/tech-demo-app-wo-slo.json > /tmp/tech-demo-app.json
sed -i -- "s/service-0002/$SERVICE_ID2/g" /tmp/tech-demo-app.json
sed -i -- "s/service-0003/$SERVICE_ID3/g" /tmp/tech-demo-app.json

# create app
APP_ID=$(curl -s  -H  "Content-Type: application/json" -X POST --data-binary "@/tmp/tech-demo-app.json" localhost:5000/api/apps  |grep app_id |cut -d ":" -f2 |grep -o '"[^"]\+"' | sed 's/"//g'
)
echo "app_id in new app: $APP_ID"

APP_NAME=$(curl -s -X GET localhost:5000/api/apps/${APP_ID}| jq .data.name|sed 's/"//g')
echo "app name in new app: $APP_NAME"

echo
echo
echo "=============="
echo "test state API"
echo "=============="
echo
# get app state
APP_STATE=$(curl -s   -H "Content-Type: application/json" -X GET  http://127.0.0.1:5000/api/apps/${APP_ID}/state | grep state | cut -d ":" -f2 | grep -o '"[^"]\+"' | sed 's/"//g')
echo "app state of ${APP_ID} : $APP_STATE"
# update app state
echo "update state to Unregistered: "
NEW_APP_STATE=$(curl -s -X PUT -d '{"state":"Unregistered"}' -H "Content-Type: application/json"  http://127.0.0.1:5000/api/apps/${APP_ID}/state  |grep state |cut -d ":" -f2 | grep -o '"[^"]\+"' | sed 's/"//g')
echo "new app state of ${APP_ID} : ${NEW_APP_STATE}"
# update invalid state
echo "update a invalid state: should be error"
curl -s -X PUT -d '{"state":"unregistered"}' -H "Content-Type: application/json"  http://127.0.0.1:5000/api/apps/${APP_ID}/state



echo
echo "=============="
echo "test slo API"
echo "=============="
echo
# get un-exist slo
echo "get slo BEFORE SLO created: should be error"
curl -s  -H "Content-Type: application/json" -X GET  http://127.0.0.1:5000/api/apps/${APP_ID}/slo

# get un-exist slo by name
echo "get slo BEFORE SLO created by name: should be error too"
curl -s  -H "Content-Type: application/json" -X GET  http://127.0.0.1:5000/api/apps/info/${APP_NAME}/slo

# update un-exist slo
echo "update slo before SLO created: should be error too"
curl -X PUT -d @workloads/new_slo.json  -H "Content-Type: application/json"  http://127.0.0.1:5000/api/apps/${APP_ID}/slo


# add app slo
echo "add new slo: return whole application.json"
curl -X POST -d @workloads/app-slo.json  -H "Content-Type: application/json"  http://127.0.0.1:5000/api/apps/${APP_ID}/slo

# get slo again
echo "get slo AFTER SLO created: "
curl -s  -H "Content-Type: application/json" -X GET  http://127.0.0.1:5000/api/apps/${APP_ID}/slo
echo "get slo by name AFTER SLO created: "
curl -s  -H "Content-Type: application/json" -X GET  http://127.0.0.1:5000/api/apps/info/${APP_NAME}/slo

# update app slo
echo "update SLO: return whole application.json"
curl -X PUT -d @workloads/new_slo.json  -H "Content-Type: application/json"  http://127.0.0.1:5000/api/apps/${APP_ID}/slo
echo "get slo  AFTER SLO updated: "
curl -s  -H "Content-Type: application/json" -X GET  http://127.0.0.1:5000/api/apps/${APP_ID}/slo
echo "get slo by name AFTER SLO update: "
curl -s  -H "Content-Type: application/json" -X GET  http://127.0.0.1:5000/api/apps/info/${APP_NAME}/slo


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
