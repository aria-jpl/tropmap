#!/usr/bin/env python
from __future__ import print_function
import sys
import numpy as np
from array import array
def extract(filename,dt):
    arr = np.fromfile(filename,dt)
    return np.reshape(arr,(arr.shape[0]/2,2))[:,1]
def save(filename,arr,dt):
    fp = open(filename,'w')
    arrDump = array(dt,arr)
    arrDump.tofile(fp)
    fp.close()
def extractPhase(filein,fileout):
    save(fileout,extract(filein,'<f'),'f')

def main(argv):
    if not len(argv) == 2:
        print('Usage: extractPhase.py filein fileout')
        sys.exit(1)
    extractPhase(argv[0],argv[1])
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
