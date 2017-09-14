#!/bin/bash

MY_XGBOOST=~/go/src/github.com/xgboost/xgboost
NUM_ROUNDS=8
MODEL_NAME=000$NUM_ROUNDS.model
echo $MODEL_NAME

# map the data to features. For convenience we only use 7 original attributes and encode them as features in a trivial way 
#python mapfeat.py
# split train and test
python mknfold.py data.txt 1

# training and output the models
$MY_XGBOOST model.conf num_round=$NUM_ROUNDS

# output predictions of test data - TODO: need to fix crash
$MY_XGBOOST model.conf task=pred model_in=$MODEL_NAME

# print the boosters of last model in dump.raw.txt
$MY_XGBOOST model.conf task=dump model_in=$MODEL_NAME name_dump=dump.raw.txt
# cat the result
echo "Estimated decision tree model:"
cat dump.raw.txt

# print the boosters of 0002.model in dump.nice.txt with feature map - TODO: fix featmap.txt format
#$MY_XGBOOST model.conf task=dump model_in=$MODEL_NAME fmap=featmap.txt name_dump=dump.nice.txt
#cat dump.nice.txt
