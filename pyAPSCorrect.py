#!/usr/bin/env python
# Author : Piyush Agram
# Date   : Dec 3, 2013
#
# Use PyAPS to correct the flattened interferograms before/after unwrapping
import tsinsar as ts
import pyaps
import os
import datetime as dt
import numpy as np
import sys
import cPickle as cp
import isce
import isceobj.Image as IF
from utils.contextUtils import toContext
####Exit error codes for pyAPScorrect 
ErrorCodes = {
        'Download Not Available Master' : 10,
        'Download Not Available Slave' : 20,
        'Master Delay Estimation Failed' : 11,
        'Slave Delay Estimation Failed' : 21,
        'Picke Load Error' : 30,
        'Write Error' : 31,
        'Memmap Error' : 32,
        'NaN Present' : 33
        }

#####Time interval between successive model outputs
Interval = {'ECMWF' : 6,
            'NARR'  : 3,
            'ERA'   : 6,
            'MERRA' : 6}

#######Download utilities
Downloader = {'ECMWF' : pyaps.ECMWFdload,
              'NARR'  : pyaps.NARRdload,
              'ERA'   : pyaps.ERAdload,
              'MERRA' : pyaps.MERRAdload}

process = 'pyAPSCorrect'

####Pickle loader
def load_pickle(fname='insar.cpk'):
    '''
    Loads the pickle file from insarApp runs.
    '''
    import cPickle
    import isce
    import isceobj

    try:
        insarObj = cPickle.load(open(fname, 'rb'))
    except Exception as e:
        print(e)
        toContext(process,ErrorCodes['Pickle Load Error'],str(e))
        sys.exit(ErrorCodes['Pickle Load Error'])
        
    return insarObj

#####Main object
class PyapsInfo(object):
    '''Relevant information for PyAPS.'''

    def __init__(self, geoflag=False,pickleFile='insar.cpk'):
        '''Construct all the required geometry information from the pickled
        insarProc object.'''
        self.insar = load_pickle(pickleFile) 
        iobj = self.insar._insar
        self.pickle = pickleFile
        topo = iobj.getTopo()
        dem = iobj._demImage
        self.ifg = iobj.topophaseFlatFilename
        ifgImage = IF.createImage()
        ifgImage.load(self.ifg + '.xml')
        ####Processing in radar coordinates
        if not geoflag:
            print 'Processing in radar coordinates'
            self.lat = topo.latFilename
            self.lon = topo.lonFilename
            self.hgt = topo.heightRFilename
            self.width  = ifgImage.width
            self.length = ifgImage.length
            self.minlat = topo.minimumLatitude
            self.maxlat = topo.maximumLatitude
            self.minlon = topo.minimumLongitude
            self.maxlon = topo.maximumLongitude
            self.daz = topo.azimuthSpacing
            self.drg = topo.slantRangePixelSpacing
            self.geo = geoflag
        else:
        #### Processing in geo coordinates
            print 'Processing geo coordinates'
            self.lat = None
            self.lon = None
            self.hgt = dem.filename
            self.width = dem.width
            self.length = dem.length
            self.maxlat = dem.firstLatitude
            self.minlon = dem.firstLongitude
            self.minlat = self.maxlat + dem.deltaLatitude*self.length
            self.maxlon = self.minlon + dem.deltaLongitude*self.width
            self.daz = 30.0
            self.drg = 30.0
            self.geo = geoflag

        rad = topo.planetLocalRadius
        hgt = topo.spacecraftHeight
        rng = topo.rangeFirstSample + 0.5*self.width*self.drg
        theta = np.pi - np.arccos(((rng*rng) + (rad*rad) - ((rad+hgt)*(rad+hgt))) / (2.*rng*rad))

        #####Change this to pixel-by-pixel LOS in future 
        #####If really needed
        self.inc = 180.0*theta/np.pi
        print 'Incidence angle in degrees: ', self.inc 
        self.wvl = iobj.radarWavelength
        #self.ifg = iobj._insar.getTopophaseFlatFilename()

        self.unw = iobj.getUnwrappedIntFilename()

        self.masterdate= iobj.getMasterFrame().sensingMid
        self.slavedate = iobj.getSlaveFrame().sensingMid

        self.flist = []
        self.model = None
        self.outfile = None

    def download(self, model=None, dirname=None):
        '''Download weather model data. If files already exist, data is not downloaded.'''

        self.model = model.upper()

        #If directory doesn't exist create it
        if not os.path.isdir(dirname):
            os.mkdir(dirname)


        for utc,which  in zip([self.masterdate, self.slavedate],['Master','Slave']):
            datestr, hr = utc2datehour(utc, model=self.model)
            try:
                fname = Downloader[model]([datestr], "{0:02d}".format(hr), dirname)
            except Exception as e:
                print(e)
                toContext(process,ErrorCodes['Download Not Available' + ' ' + which ],str(e))
                sys.exit(ErrorCodes['Download Not Available' + ' ' + which ])

            self.flist.append(fname[0])

    def createRsc(self):
        '''Creates a ROI-PAC style RSC for the height file with dimensions.'''

        from collections import OrderedDict

        rdict = OrderedDict()

        #####For processing radar coordinates
        if not self.geo:
            rdict['LAT_REF1'] = self.minlat
            rdict['LON_REF1'] = self.minlon
            rdict['LAT_REF2'] = self.minlat
            rdict['LON_REF2'] = self.maxlon
            rdict['LAT_REF3'] = self.maxlat
            rdict['LON_REF3'] = self.maxlon
            rdict['LAT_REF4'] = self.maxlat
            rdict['LON_REF4'] = self.minlon
        else:
        #####For processing in geo coordinates
            rdict['X_FIRST'] = self.minlon
            rdict['Y_FIRST'] = self.maxlat
            rdict['Y_STEP'] = (self.minlat - self.maxlat)/(1.0*self.length)
            rdict['X_STEP'] = (self.maxlon - self.minlon)/(1.0*self.length)

        rdict['WIDTH'] = self.width
        rdict['FILE_LENGTH'] = self.length
        rdict['RANGE_PIXEL_SIZE'] = self.drg
        rdict['AZIMUTH_PIXEL_SIZE'] = self.daz
        rscname = '{0}.rsc'.format(self.hgt)
        try:
            ts.write_rsc(rdict, rscname)
        except Exception as e:
            toContext(process,ErrorCodes['Write Error'],str(e))
            print(e)
            sys.exit(ErrorCodes['Write Error'])

    def estimateDelay(self):
        '''Estimate the delay using PyAPS.'''

        self.outfile = 'corrections_pyAPS_%s'%(self.model)
        print('Processing master delay')
        delay = np.zeros((self.length, self.width), dtype=np.float32)

        ######Processing in radar coordinates
        if not self.geo:
            try:
                atmobj = pyaps.PyAPS_rdr(self.flist[0],self.hgt,grib=self.model,demfmt='HGT')
                atmobj.getgeodelay(delay, lat=self.lat, lon=self.lon, inc=self.inc,wvl=self.wvl) 
            except Exception as e:
                toContext(process,ErrorCodes['Master Delay Estimation Failed'],str(e))
                print(e)
                sys.exit(ErrorCodes['Master Delay Estimation Failed'])
        else:
        #######Processing in geo coordinates
            try:
                atmobj = pyaps.PyAPS_geo(self.flist[0], self.hgt, grib=self.model,demfmt='HGT')
                atmobj.getdelay(delay, inc=self.inc,wvl=sel.wvl)
            except Exception as e:
                toContext(process,ErrorCodes['Master Delay Estimation Failed'],str(e))
                print(e)
                sys.exit(ErrorCodes['Master Delay Estimation Failed'])

        del atmobj
        
        if(np.isnan(np.sum(delay))):
            print("pyAPSCorrect.py estimateDelay: found NaN. Aborting") 
            toContext(process,ErrorCodes['NaN Present'],"pyAPSCorrect.py estimateDelay: found NaN. Aborting")
            sys.exit(ErrorCodes['NaN Present'])

        
        print('Processing slave delay')
        delay_slav = np.zeros((self.length, self.width), dtype=np.float32)
        if not self.geo:
            try:
                atmobj = pyaps.PyAPS_rdr(self.flist[1],self.hgt,grib=self.model,demfmt='HGT')
                atmobj.getgeodelay(delay_slav, lat=self.lat, lon=self.lon, inc=self.inc,wvl=self.wvl)
            except Exception as e:
                print(e)
                toContext(process,ErrorCodes['Slave Delay Estimation Failed'],str(e))
                sys.exit(ErrorCodes['Slave Delay Estimation Failed'])
        else:
            try:
                atmobj = pyaps.PyAPS_geo(self.flist[1], self.hgt,grib=self.model,demfmt='HGT')
                atmobj.getdelay(delay_slav, inc=self.inc,wvl=self.wvl)
            except Exception as e:
                toContext(process,ErrorCodes['Slave Delay Estimation Failed'],str(e))
                print(e)
                sys.exit(ErrorCodes['Slave Delay Estimation Failed'])

        del atmobj

        if(np.isnan(np.sum(delay_slav))):
            print("pyAPSCorrect.py estimateDelay: found NaN. Aborting") 
            toContext(process,ErrorCodes['NaN Present'],"pyAPSCorrect.py estimateDelay: found NaN. Aborting")
            sys.exit(ErrorCodes['NaN'])
        delay -= delay_slav
        del delay_slav

        try:
            #import pdb
            #pdb.set_trace()
            self.insar._insar.correctionsFilename = self.outfile+'.rdr'
            delay.astype(np.float32).tofile(self.insar._insar.correctionsFilename)
            ifImage = IF.createImage()
            accessMode = 'read'
            dataType = 'FLOAT'
            ifImage.initImage(self.insar._insar.correctionsFilename,accessMode,self.width,dataType)
            descr = 'Troposheric corrections'
            ifImage.setImageType('sbi')
            ifImage.addDescription(descr)
            ifImage.renderHdr()
        except Exception as e:
            toContext(process,ErrorCodes['Write Error'],str(e))
            print(e)
            sys.exit(ErrorCodes['Write Error'])
        
        cJ = np.complex64(1.0j)
        delay = np.exp(cJ*(delay))
        try:
            delay.tofile(self.outfile+'.mph')
        except Exception as e:
            toContext(process,ErrorCodes['Write Error'],str(e))
            print(e)
            sys.exit(ErrorCodes['Write Error'])
        #since some time this is the only stage executed dump the pickle
        #if there are other stages they'll be overwritten
        fp = open(self.pickle,'w')
        cp.dump(self.insar,fp)
        fp.close()
        toContext(process,0,'pyAPSCorrections delay created')

    def correctIfg(self, prefix):
        '''
        Correct the wrapped flattened interferogram using the estimated delay map.
        '''
        try:
            Oifg = ts.load_mmap(self.ifg, self.width, self.length, datatype=np.complex64, quiet=True)
        except Exception as e:
            toContext(process,ErrorCodes['Memmap Error'],str(e))
            print(e)
            sys.exit(ErrorCodes['Memmap Error'])

        try:
            Aifg = ts.load_mmap(self.outfile+'.mph', self.width, self.length, datatype=np.complex64, quiet=True)
        except Exception as e:
            toContext(process,ErrorCodes['Memmap Error'],str(e))
            print(e)
            sys.exit(ErrorCodes['Memmap Error'])

        corrname = '{0}_{1}'.format(prefix, self.ifg)

        try:
            fout = open(corrname, 'w')
            for kk in xrange(self.length):
                dat = Oifg[kk,:] * Aifg[kk,:]
                dat.tofile(fout)
        except Exception as e:
            toContext(process,ErrorCodes['Write Error'],str(e))
            print(e)
            sys.exit(ErrorCodes['Write Error'])

        fout.close()
        ifImage = IF.createImage()
        accessMode = 'read'
        dataType = 'CFLOAT'
        ifImage.initImage(corrname,accessMode,self.width,dataType)
        descr = 'Troposheric corrected flattened interferogram'
        ifImage.setImageType('cpx')
        ifImage.addDescription(descr)
        ifImage.renderHdr()
        
        self.insar._insar.correctedTopophaseFilename = corrname
        fp = open(self.pickle,'w')
        cp.dump(self.insar,fp)
        fp.close()
        toContext(process,0,'pyAPSCorrections applied')

    def correctUnw(self, prefix):
        '''
        Correct the unwrapped interferogram using the estimated delay map.
        '''
        try:
            Oamp = ts.load_mmap(self.unw, self.width, self.length, map='BIL', nchannels=2, channel=1,datatype=np.float32, quiet=True)
            Oifg = ts.load_mmap(self.unw, self.width, self.length, map='BIL', nchannels=2, channel=1,datatype=np.float32, quiet=True)
        except Exception as e:
            toContext(process,ErrorCodes['Memmap Error'],str(e))
            print(e)
            sys.exit(ErrorCodes['Memmap Error'])

        try:
            Aifg = ts.load_mmap(self.outfile+'.rdr', self.width, self.length, datatype=np.float32,quiet=True)
        except Exception as e:
            toContext(process,ErrorCodes['Memmap Error'],str(e))
            print(e)
            sys.exit(ErrorCodes['Memmap Error'])

        corrname = '{0}_{1}'.format(prefix, self.unw)

        try:
            fout = open(corrname, 'w')
            for kk in xrange(self.length):
                dat = Oifg[kk,:] * Aifg[kk,:]
                amp = Omap[kk,:]
                amp.tofile(fout)
                dat.tofile(fout)
        except Exception as e:
            toContext(process,ErrorCodes['Write Error'],str(e))
            print(e)
            sys.exit(ErrorCodes['Write Error'])

        fout.close()
        ifImage = IF.createImage()
        accessMode = 'read'
        dataType = 'CFLOAT'
        ifImage.initImage(corrname,accessMode,self.width,dataType)
        descr = 'Troposheric corrected unwrapped flattened interferogram'
        ifImage.setImageType('cpx')
        ifImage.addDescription(descr)
        ifImage.renderHdr()
        self.insar._insar.correctedTopophaseFilename = corrname
        fp = open(self.pickle,'w')
        cp.dump(self.insar,fp)
        fp.close()
        toContext(process,0,'pyAPSCorrections applied')






def utc2datehour(utc, model=None):
    '''Convert utc to nearest interval.'''

    temp = utc - dt.datetime.combine(utc.date(), dt.time(0))
    secs = temp.total_seconds()

    period = Interval[model.upper()]
    hr = np.int(period*np.round(secs/(period*3600.0)))

    addday = np.int(np.floor(hr/24))
    if addday:
        datestr = (utc + dt.timedelta(days=1)).strftime('%Y%m%d')
    else:
        datestr = utc.strftime('%Y%m%d')

    hr = hr%24

    return datestr, hr



def parse():
    '''Command line parsing.'''

    import argparse
    parser = argparse.ArgumentParser(
            description='Reads in wrapped interferograms and corrects using PyAPS',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
            )

    parser.add_argument('--model', action='store', default='ECMWF', dest='model',
            help='Weather model to use.', type=str)

    parser.add_argument('--prefix', action='store',default='corrections', dest='prefix',
            help='Prefix for the corrected interferogram.', type=str)

    parser.add_argument('--dir', action='store', default='.', dest='dirname',
            help='Directory to store the downloaded atmospheric model data.', type=str)

    parser.add_argument('--geo', action='store_true', default=False, dest='geo',
            help = 'Use the dem in geo coordinates instead of lat,lon,hgt in radar coordinates.')

    parser.add_argument('--unw', action='store_true', default=False, dest='unw',
            help= 'Correct the unwrapped interferogram instead of the wrapped flattened interferogram.')

    parser.add_argument('--pickle', action='store', default='insar.cpk', dest='pickle',
            help= 'Input pickle file with the insar object.',type=str)
    inps = parser.parse_args()

    inps.model = inps.model.upper()
    if inps.model not in ['ECMWF', 'ERA', 'NARR', 'MERRA']:
        raise Exception('Input model should be among ECMWF/ERA/NARR/MERRA')

    return inps


if __name__ == '__main__':
    '''The main driver script.'''

    #Parse input arguments
    opts = parse()

    #PyAPS information
    pyapsObj = PyapsInfo(geoflag=opts.geo,pickleFile=opts.pickle)

    pyapsObj.download(model=opts.model, dirname=opts.dirname)

    pyapsObj.createRsc()
    pyapsObj.estimateDelay()
    if not opts.unw:
        pyapsObj.correctIfg(opts.prefix)
    else:
        pyapsObj.correctUnw(opts.prefix)

    sys.exit(0)
