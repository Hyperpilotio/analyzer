#!/bin/bash

#check jq is available
if  ! type jq > /dev/null; then
  echo "jq is required for test, Install first"
  return
fi

if  ! type mongoimport > /dev/null; then
  echo "mongoimport is required for test, Install first"
  return
fi

# get all apps
echo "get all apps: "
curl -s -XGET localhost:5000/api/v1/apps | jq -c .

# create 3 services
SERVICE_ID1=$(curl -s -XPOST -H "Content-Type: application/json" --data-binary "@workloads/goddd-service.json" localhost:5000/api/v1/k8s_services | jq .data | cut -d"\"" -f2)
SERVICE_ID2=$(curl -s -XPOST -H "Content-Type: application/json" --data-binary "@workloads/mongo-service.json" localhost:5000/api/v1/k8s_services | jq .data | cut -d"\"" -f2)
SERVICE_ID3=$(curl -s -XPOST -H "Content-Type: application/json" --data-binary "@workloads/pathfinder-service.json" localhost:5000/api/v1/k8s_services | jq .data | cut -d"\"" -f2)

echo "goddd service created: $SERVICE_ID1"
echo "mongo service created: $SERVICE_ID2"
echo "pathfinder service created: $SERVICE_ID3"

# replace tech-demo-app service ids
sed "s/service-0001/$SERVICE_ID1/g" workloads/tech-demo-app-wo-slo-wo-features.json > /tmp/tech-demo-app.json
sed -i -- "s/service-0002/$SERVICE_ID2/g" /tmp/tech-demo-app.json
sed -i -- "s/service-0003/$SERVICE_ID3/g" /tmp/tech-demo-app.json

# create app
APP_ID=$(curl -s  -H  "Content-Type: application/json" -X POST --data-binary "@/tmp/tech-demo-app.json" localhost:5000/api/v1/apps  |grep app_id |cut -d ":" -f2 |grep -o '"[^"]\+"' | sed 's/"//g'
)
echo "app_id in new app: $APP_ID"

APP_NAME=$(curl -s -X GET localhost:5000/api/v1/apps/${APP_ID}| jq .data.name|sed 's/"//g')
echo "app name in new app: $APP_NAME"

echo
echo
echo "=============="
echo "test state API"
echo "=============="
echo

echo "get app state"
curl -s   -H "Content-Type: application/json" -X GET  http://127.0.0.1:5000/api/v1/apps/${APP_ID}/state | jq -c .
echo "update app state to Unregistered"
curl -s -X PUT -d '{"state":"Unregistered"}' -H "Content-Type: application/json"  http://127.0.0.1:5000/api/v1/apps/${APP_ID}/state | jq -c .
# update invalid state
echo "update a invalid state: should be error"
curl -s -X PUT -d '{"state":"unregistered"}' -H "Content-Type: application/json"  http://127.0.0.1:5000/api/v1/apps/${APP_ID}/state | jq -c .



echo
echo "=============="
echo "test slo API"
echo "=============="
echo
# get un-exist slo
echo "get slo BEFORE SLO created: should be error"
curl -s  -H "Content-Type: application/json" -X GET  http://127.0.0.1:5000/api/v1/apps/${APP_ID}/slo | jq -c .

# get un-exist slo by name
echo "get slo BEFORE SLO created by name: should be error too"
curl -s  -H "Content-Type: application/json" -X GET  http://127.0.0.1:5000/api/v1/apps/info/${APP_NAME}/slo | jq -c .

# update un-exist slo
echo "update slo before SLO created: should be error too"
curl -s -X PUT -d @workloads/new_slo.json  -H "Content-Type: application/json"  http://127.0.0.1:5000/api/v1/apps/${APP_ID}/slo | jq -c .


# add app slo
echo "add new slo: return whole application.json"
curl -s -X POST -d @workloads/app-slo.json  -H "Content-Type: application/json"  http://127.0.0.1:5000/api/v1/apps/${APP_ID}/slo | jq -c .

# get slo again
echo "get slo AFTER SLO created: "
curl -s  -H "Content-Type: application/json" -X GET  http://127.0.0.1:5000/api/v1/apps/${APP_ID}/slo | jq -c .
echo "get slo by name AFTER SLO created: "
curl -s  -H "Content-Type: application/json" -X GET  http://127.0.0.1:5000/api/v1/apps/info/${APP_NAME}/slo | jq -c .

# update app slo
echo "update SLO: return whole application.json"
curl -s -X PUT -d @workloads/new_slo.json  -H "Content-Type: application/json"  http://127.0.0.1:5000/api/v1/apps/${APP_ID}/slo | jq -c .
echo "get slo  AFTER SLO updated: "
curl -s  -H "Content-Type: application/json" -X GET  http://127.0.0.1:5000/api/v1/apps/${APP_ID}/slo | jq -c .
echo "get slo by name AFTER SLO update: "
curl -s  -H "Content-Type: application/json" -X GET  http://127.0.0.1:5000/api/v1/apps/info/${APP_NAME}/slo | jq -c .


echo
echo "======================"
echo "test incidents GET API"
echo "======================"
echo
echo "app_name is not in query json: should be error"
curl -s -X GET -d '{"app":"tech-demo"}' -H  "Content-Type: application/json"  localhost:5000/api/v1/incidents | jq -c .
echo "incidents is not added: should be error"
curl -s -X GET -d '{"app_name":"tech-demo"}' -H  "Content-Type: application/json"  localhost:5000/api/v1/incidents | jq -c .
echo "add 2 incidents, timestamps are 1511980860000000000 and 1611980860000000000: should return timestamp 1611980860000000000"
mongoimport --db resultdb --collection incidents --drop --file ./workloads/incident.json
curl -s -X GET -d '{"app_name":"tech-demo"}' -H  "Content-Type: application/json"  localhost:5000/api/v1/incidents | jq -c .


echo
echo "======================"
echo "test problems GET API"
echo "======================"
echo
echo "problem is not added: should be error"
curl -s -X GET -d '{"app":"tech-demo"}' -H  "Content-Type: application/json"  localhost:5000/api/v1/problems/problem-0001 | jq -c .
echo "add 3 problems: timestamp are 1510000000000000000 & 1520000000000000000 & 1530000000000000000"
echo "equal to 2017/11/6/12:26:40 GMT-08:00 & 2018/3/2/06:13:20 GMT-08:00 & 2018/6/26/01:00:00 GMT-07:00"
mongoimport --db resultdb --collection problems --drop --file ./workloads/3-problems.json
echo "get problem-0001 after 3 problems are added"
curl -s -X GET -d '{"app":"tech-demo"}' -H  "Content-Type: application/json"  localhost:5000/api/v1/problems/problem-0001 | jq -c .

FIVEMINAGO=$(date -v-5M "+%Y-%m-%d  %H:%M:%S")
CURRENT=$(date  "+%Y-%m-%d  %H:%M:%S")
echo "get problems using default interval current (${CURRENT}) and pass 5 min (${FIVEMINAGO})"
curl -s -X GET  localhost:5000/api/problems | jq -c .
curl -s -X GET -d '{"start_time":1510000000000000000}' -H  "Content-Type: application/json" localhost:5000/apiv1/problems | jq -c .
echo "get problems using interval 1510000000000000000 and 1520000000000000000"
curl -s -X GET -d '{"start_time":1510000000000000000, "end_time":1520000000000000000}' -H  "Content-Type: application/json" localhost:5000/api/v1/problems | jq -c .

echo
echo "======================"
echo "test diagnosis GET API"
echo "======================"
echo
echo "app_name is not in query json: should be error"
curl -s -X GET -d '{"state":"unregistered"}' -H "Content-Type: application/json"  http://127.0.0.1:5000/api/v1/diagnoses | jq -c .
echo "BEFORE add documents:  "
echo "get by name find most recent one,  return error if no result"
curl -s -X GET -d '{"app_name":"tech-demo"}' -H "Content-Type: application/json"  http://127.0.0.1:5000/api/v1/diagnoses | jq -c .
echo "get by name & incident_id, return error if no result"
curl -s -X GET -d '{"app_name":"tech-demo", "incident_id":"incident-0002"}' -H "Content-Type: application/json"  http://127.0.0.1:5000/api/v1/diagnoses | jq -c .
echo "get by name & interval, return empty array if no result"
curl -s -X GET -d '{"app_name":"tech-demo", "start_time":1511980830000000000, "end_time":1511980850000000000}' -H "Content-Type: application/json"  http://127.0.0.1:5000/api/v1/diagnoses | jq -c .

mongoimport --db resultdb --collection diagnoses --drop --file ./workloads/diagnoses.json
echo "after add 2 document"
echo "get by name: find most recent one"
curl -s -X GET -d '{"app_name":"tech-demo"}' -H "Content-Type: application/json"  http://127.0.0.1:5000/api/v1/diagnoses | jq -c .
echo "get criteria app_name=tech-demo, incident_id=incident-0002"
curl -s -X GET -d '{"app_name":"tech-demo", "incident_id":"incident-0002"}' -H "Content-Type: application/json"  http://127.0.0.1:5000/api/v1/diagnoses | jq -c .
echo "get by name & interval"
curl -s -X GET -d '{"app_name":"tech-demo", "start_time":1511980830000000000, "end_time":1511980850000000000}' -H "Content-Type: application/json"  http://127.0.0.1:5000/api/v1/diagnoses | jq -c .


echo
echo "================================"
echo "test features management Add API"
echo "================================"
echo
echo "add new feature"
curl -s -X POST -d @workloads/2-features.json  -H "Content-Type: application/json" localhost:5000/api/v1/apps/${APP_ID}/management_features | jq -c .
echo "add feature again: should be error"
curl -s -X POST -d @workloads/2-features.json  -H "Content-Type: application/json" localhost:5000/api/v1/apps/${APP_ID}/management_features | jq -c .


echo
echo "================================"
echo "test features management GET API"
echo "================================"
echo
echo "get all management_features"
curl -s -X GET    localhost:5000/api/v1/apps/${APP_ID}/management_features | jq -c .
echo "get invalid feature: should be error"
curl -s -X GET  localhost:5000/api/v1/apps/${APP_ID}/management_features/efficiency | jq -c .
echo "get not exist efficiency_management: should be error"
curl -s -X GET  localhost:5000/api/v1/apps/${APP_ID}/management_features/efficiency_management | jq -c .
echo "get bottleneck_management"
curl -s -X GET  localhost:5000/api/v1/apps/${APP_ID}/management_features/bottleneck_management | jq -c .
echo "get interference_management"
curl -s -X GET  localhost:5000/api/v1/apps/${APP_ID}/management_features/interference_management | jq -c .

echo
echo "================================"
echo "test features management update API"
echo "================================"
echo
echo "new data has no name field: should be error"
curl -s -X PUT -d '{"status":"good"}' -H  "Content-Type: application/json"  localhost:5000/api/v1/apps/${APP_ID}/management_features/efficiency_management | jq -c .
echo "new & old feature are not the same type : should be error"
curl -s -X PUT -d @workloads/bottleneck_management_feature.json  -H  "Content-Type: application/json"  localhost:5000/api/v1/apps/${APP_ID}/management_features/efficiency_management | jq -c .
echo "append efficiency_management"
curl -s -X PUT -d @workloads/efficiency_management_feature.json  -H  "Content-Type: application/json"  localhost:5000/api/v1/apps/${APP_ID}/management_features/efficiency_management | jq -c .
echo "update bottleneck_management"
curl -s -X PUT -d @workloads/bottleneck_management_feature.json  -H  "Content-Type: application/json"  localhost:5000/api/v1/apps/${APP_ID}/management_features/bottleneck_management | jq -c .
echo "update interference_management"
curl -s -X PUT -d @workloads/interference_management_feature.json -H  "Content-Type: application/json"  localhost:5000/api/v1/apps/${APP_ID}/management_features/interference_management | jq -c .

# require type and name (this example has no type)
#curl -s  -H  "Content-Type: application/json" -X POST --data-binary "@workloads/tech-demo-bad-input.json" localhost:5000/api/v1/apps

# get one app by id
#curl -XGET localhost:5000/api/v1/apps/$APP_ID

# update an existing app
#curl -H "Content-Type: application/json" -X PUT localhost:5000/api/v1/apps/$APP_ID --data-binary "@workloads/tech-demo-partial-update.json"

# delete an app by id
#curl -XDELETE localhost:5000/api/v1/apps/$APP_ID

# add microservices to an app
#curl -H "Content-Type: application/json" -X POST localhost:5000/api/v1/apps/$APP_ID/services --data-binary "@workloads/microservices.json"

echo
echo "================================"
echo "test get pod API"
echo "================================"
echo
echo "get all names of pods associated with an app."
curl -s -H "Content-Type: application/json" -X GET localhost:5000/api/v1/apps/$APP_ID/pods | jq -c .
