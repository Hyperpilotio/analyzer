#!/bin/bash

DEPLOYER_URL="internal-deployer-605796188.us-east-1.elb.amazonaws.com"
curl ${DEPLOYER_URL}:7777/v1/deployments/$1/kubeconfig > ~/.kube/kubeconfig

#echo Creating a kubernetes-dashboard
kubectl create -f $GOPATH/src/github.com/hyperpilotio/hyperpilot-demo/workloads/tech-demo/kubernetes-dashboard.yaml

MONGO_POD=`kubectl get pods | grep mongo | cut -d" " -f1 | xargs`
MONGO_URL=`kubectl describe services mongo-publicport0 | grep elb | cut -d":" -f2 | xargs`:27017

echo "mongodb pod name: " $MONGO_POD
echo "mongodb service running at: " $MONGO_URL

echo Connecting to mongodb server
mongo $MONGO_URL/admin -u admin -p hyperpilot
