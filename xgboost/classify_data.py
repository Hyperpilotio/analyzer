#!/usr/bin/python

SLO_VALUE = 100
ymax = 0
ymin = 1000000

fout = open( 'data-class.txt', 'w' )

for lin in open( 'data.txt' ):
    arr = lin.split(' ')
    y = float(arr[0])
    ybin = 1 if y <= SLO_VALUE else 0
    
    fout.write( '%d' %ybin)
    for x in arr[1:-1]:
        fout.write( ' %s' %x )
    fout.write('\n')

    ymax = max(y, ymax)
    ymin = min(y, ymin)

print("maximum y value = %d" % ymax)
print("minimum y value = %d" % ymin)

fout.close()
