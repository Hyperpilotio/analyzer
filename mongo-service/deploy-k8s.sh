#!/usr/bin/env bash

DEPLOYER_URL="internal-deployer-605796188.us-east-1.elb.amazonaws.com"
#DEPLOYER_URL="localhost"

curl -XPOST $DEPLOYER_URL:7777/v1/deployments --data-binary @deploy-k8s.json

echo "Please check progress of your deployment at http://$DEPLOYER_URL:7777/ui"
