#!/usr/bin/env python

import numpy as np

SLO_VALUE = 100

arr = np.loadtxt('data.txt', dtype=str)

y = arr[:, 0].astype(float)
ybin = (y <= SLO_VALUE).astype(int)

output = np.column_stack((ybin, arr[:, 1:-1]))
np.savetxt('data-class.txt', output, fmt='%s')

print("maximum y value = %d" % y.max())
print("minimum y value = %d" % y.min())
