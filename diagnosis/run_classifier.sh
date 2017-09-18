#!/bin/bash

MY_XGBOOST=~/go/src/github.com/xgboost/xgboost
NUM_ROUNDS=3
MODEL_NAME=000$NUM_ROUNDS.model
MODEL_TYPE=model-class.conf

# map the data to features. For convenience we only use 7 original attributes and encode them as features in a trivial way 
#python mapfeat.py

# convert regression data to classification data
python classify_data.py

# split data into train set and test set
python mknfold.py data-class.txt 1

# training and output the models
$MY_XGBOOST $MODEL_TYPE num_round=$NUM_ROUNDS

# output predictions of test data - TODO: need to fix crash
$MY_XGBOOST $MODEL_TYPE task=pred model_in=$MODEL_NAME

# print the structure of the last model in dump.raw.txt
$MY_XGBOOST $MODEL_TYPE task=dump model_in=$MODEL_NAME name_dump=dump.raw.txt
echo "Estimated raw decision tree model:"
cat dump.raw.txt

# print the structure of the last model in dump.nice.txt with feature map
$MY_XGBOOST $MODEL_TYPE task=dump model_in=$MODEL_NAME fmap=xgboost_keys.txt name_dump=dump.nice.txt
echo "Estimated decision tree model with feature names:"
cat dump.nice.txt
