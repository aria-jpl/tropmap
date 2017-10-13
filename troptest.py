#!/usr/bin/env python
import sys
import isce
import tropoUtils as tu
from iscesys.Parsers.FileParserFactory import createFileParser
from datetime import datetime

def main():
    date1 = datetime(2010,1,15,6,11,42)
    date2 = datetime(2010,4,17,6,11,8)
    tu.tropoCorrection('test.int',date1,date2,sys.argv[1])

if __name__ == '__main__':
    sys.exit(main())
            
