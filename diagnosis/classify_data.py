#!/usr/bin/env python

import numpy as np

SLO_VALUE = 100

arr = np.loadtxt('data.txt')

y = arr[:, 0]
ybin = y <= SLO_VALUE

output = np.column_stack((ybin, arr[:, 1:-1]))
np.savetxt('data-class.txt', output, fmt='%d')

print("maximum y value = %d" % y.max())
print("minimum y value = %d" % y.min())
