#!/usr/bin/env python
import sys
import numpy as np
from sklearn.model_selection import train_test_split

if len(sys.argv) < 3:
    print ('Usage:<filename> <k> [nfold = 5]')
    exit(0)

fname = sys.argv[1]
k = int( sys.argv[2] )
if len(sys.argv) > 3:
    nfold = int( sys.argv[3] )
else:
    nfold = 5

with open(fname, 'r') as f:
    train, test = train_test_split(f.readlines(), test_size=1 / nfold, random_state=10)

with open(fname + '.train', 'w') as train_f:
    train_f.write(''.join(train))
with open(fname + '.test', 'w') as test_f:
    test_f.write(''.join(test))
