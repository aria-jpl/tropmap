#!/usr/bin/env python
from __future__ import print_function
import isce
import subprocess
import sys
import os
import numpy as np
from array import array
from bilin import Bilinear2DInterpolator as BI


def readImage(filename,dt,width):
    arr = np.fromfile(filename,dt)
    return np.reshape(arr,(arr.shape[0]/width,width))


# filename: filename containing the data to extract
# dt: data type numpy style
def extract(filename,dt):
    arr = np.fromfile(filename,dt)
    return np.reshape(arr,(arr.shape[0]/2,2))[:,1]

# filename: filename where to save the data
# arr: python array to be saved
# dt: data type python array style
def save(filename,arr,dt):
    fp = open(filename,'w')
    arrDump = array(dt,arr)
    arrDump.tofile(fp)
    fp.close()

# Extract the phase from a complex image and save it.
# filein: input file containing the magnitude and  phase data
# fileout: outpu filename where the phase is saved
def extractPhase(filein,fileout):
    save(fileout,extract(filein,'<f'),'f')


# Grid an input image
# filein: the input geoimage
# fileout: the output geoimage gridded
# corners: [lonmin,lonmax,latmin,latmax]
# deltas: [deltalon,deltalat]
def gridImage(filein,fileout,corners,deltas):
    command = 'xyz2grd -V -R' + str(corners[0]) + '/' + str(corners[1]) + '/' + str(corners[2]) + '/' + str(corners[3]) \
            + ' -I' +  str(deltas[0]) + '/' +  str(deltas[1]) + ' ' + filein +  ' -F -ZTLf -N0.0 -Ddegres/degres/radians/=/=/unwrapped_phase/ -G' + fileout 
    print(command)
    subprocess.call(command,shell = True)


def phaseToMeters(filein,fileout):
    command = 'grdmath ' + filein +' 2 DIV 3.14159 DIV 0.015 MUL = ' + fileout
    print(command)
    subprocess.call(command,shell = True)

#filein : input interferogram (just used to create the name)
#datetime1 : datetime instance of the first acquisition
#datetime2 : datetime instance of the second acquisition
#demxml : dem xml file adopted
def tropoCorrection(filein,datetime1,datetime2,demxml):
    from iscesys.Parsers.FileParserFactory import createFileParser
    parser = createFileParser('xml')
    prop,fact,misc = parser.parse(demxml)
    dem = demxml.replace('.xml','')
    latstart = prop['Coordinate2']['startingvalue']
    latdelta = prop['Coordinate2']['delta']
    length = prop['Coordinate2']['size']
    lonstart = prop['Coordinate1']['startingvalue']
    londelta = prop['Coordinate1']['delta']
    width = prop['Coordinate1']['size']
    latend = latstart + latdelta*length
    lonend = lonstart + londelta*width
    latmin = min(latstart,latend)
    latmax = max(latstart,latend)
    lonmin = min(lonstart,lonend)
    lonmax = max(lonstart,lonend)
    date1 = datetime1.date().isoformat()
    date2 = datetime2.date().isoformat()
    time1 = datetime1.time()
    time2 = datetime2.time()
    hour1 = time1.hour
    hour2 = time2.hour
    min1 = time1.minute
    min2 = time2.minute
    
    command = 'tropwrap.py -igram ' + filein + ' -resolution ' + str(width) + '+/' + str(length) + '+' +   ' -latmin ' + str(latmin) +' -latmax ' + str(latmax) + ' -lonmin ' + str(lonmin) \
              + ' -lonmax ' + str(lonmax) + ' -date1 ' + str(date1) + \
              ' -date2 ' + str(date2)  + ' -hour1 ' + str(hour1) + ' -min1 '+ str(min1) + ' -hour2 ' + \
              str(hour2) + ' -min2 ' + str(min2) + ' -gps gipsy -Wx off -interp triang -png on -ISCE_DEM ' + dem
    subprocess.call(command,shell = True)

#waveLength : radar wavelegth
#ifgName : interferogram name
#fileLat : latitude file from isce (lat.rdr)
#fileLon : longitude file from isce (lon.rdr)
#fileLos : line of sight file from isce 
#ifgCorrectedName : filename for the output corrected interferogram
def wrapCorrection(waveLength,ifgName,fileLat,fileLon,fileLos,ifgCorrectedName):
    import cPickle as cp
    from iscesys.Parsers.FileParserFactory import createFileParser
    parser = createFileParser('xml')
    prop,fact,misc = parser.parse(ifgName +'.xml')
    width = prop['Coordinate1']['size']
    fp = open('tropwrap.pck')
    dataIn = cp.load(fp)
    fp.close()
    correctionName = dataIn[0]
    grdinfo = dataIn[1]
    correctionXyzName = correctionName[:-3] + 'xyz'
    command = 'grd2xyz -Zf ' + correctionName + ' > ' + correctionXyzName
    subprocess.call(command,shell=True)
    # hate to do that but the grdinfo is a string and needs to be parsed
    grdinfoSp = grdinfo.split(' ')
    lonMin = float(grdinfoSp[grdinfoSp.index('x_min:') + 1])
    lonDelta = float(grdinfoSp[grdinfoSp.index('x_inc:') + 1])
    lonN = int(grdinfoSp[grdinfoSp.index('nx:') + 1].split()[0])
    latMax = float(grdinfoSp[grdinfoSp.index('y_max:') + 1])
    latDelta = float(grdinfoSp[grdinfoSp.index('y_inc:') + 1])
    latN = int(grdinfoSp[grdinfoSp.index('ny:') + 1].split()[0])
    lon = lonMin + lonDelta*np.arange(lonN) 
    lat = latMax - latDelta*np.arange(latN)
    datain = readImage(correctionXyzName,'<f',lonN)
    indxBad = np.where(np.isnan(datain))
    datain[indxBad[0],indxBad[1]] = 0
    latOut = readImage(fileLat,'<f',width) 
    lonOut = readImage(fileLon,'<f',width)
    #read as same width as lanOut or lonOut, but then skip every other line when looping
    losOut = readImage(fileLos,'<f',width)
    bi = BI(lon,-lat,datain)
    geoCorrection = np.zeros(latOut.shape)
    for i in xrange(latOut.shape[0]):
        geoCorrection[i,:] = -bi(lonOut[i,:],-latOut[i,:]) *(4*np.pi/waveLength)/np.cos(np.radians(losOut[i*2,:]))
    #free memory
    del latOut
    del lonOut
    ifg = readImage(ifgName,'<f',2*width) 
    ifg = np.reshape(ifg,(ifg.shape[0],width,2))
    dim = geoCorrection.shape
    geoCorrection.astype(np.float32).tofile('uwcorr.unw')
    #save('test.geo',np.reshape(geoCorrection,dim[0]*dim[1]),'f')
    fp = open(ifgCorrectedName,'w')
    line = np.zeros((width,2))
    for i in xrange(ifg.shape[0]):
        cpx = (ifg[i,:,0] + np.complex64(1.0j)*ifg[i,:,1])*(np.exp(np.complex64(1.0j)*geoCorrection[i,:]))
        line[:,0] = np.real(cpx) 
        line[:,1] = np.imag(cpx)
        arrayOut = array('f',np.reshape(line,2*width))
        arrayOut.tofile(fp)
    fp.close()
def main(argv):
    
    #test extractPhase
    #extractPhase(argv[0],argv[1])

    #test gridImage
    '''
    width = 1215
    length = 2048
    delta = 0.0008333333333
    latmin = 30.951666667
    lonmin = -115.490833333
    latmax = latmin + delta*length
    lonmax = lonmin + delta*width
    gridImage(argv[0],argv[0] + '.grd',[lonmin,lonmax,latmin,latmax],[delta,delta])
    '''
    #test phaseToMeters
    #phaseToMeters(argv[0] + '.grd',argv[0] + '.grd.m')
    #tested wrapCorrections by creating synthetic corrections of constant wvl/(4pi) so the correction 
    # should be one. It works
    wrapCorrection(0.0312283810417,'topophase.flat','lat.rdr','lon.rdr','los.rdr','testCorrections.out')
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
