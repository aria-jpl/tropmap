#!/usr/bin/env python
################################################################################
# PROGRAM: tropmap.py
################################################################################
'''
PROGRAM:
    tropmap.py

PURPOSE:
    Construct a GPS-only or GPS+Weather combination troposphere map

DESCRIPTION:
    Given a lat/lon bounding box and a time/date, this program will
    make a trop map.

USAGE:
    tropmap.py -latmin latmin -latmax latmax -lonmin lonmin -lonmax lonmax -resolution <xres>/<yres> -date YYYY-MM-DD -hour HH -min MM -gps [gipsy|gamit] -Wx [namanl|rucanl|gfsanl|off] -interp [triang|IDW] [-output_dir <dir>] [-output_file <file>] [-coords servlet|xml|llh] [-llh_dir <dir>] [-workdir <dir>] [-ISCE_DEM file] [-local_gipsy_dir <dir>] [-local_gamit_dir <dir>] [-download_only <dir>] [-pre_downloaded <dir>] [-png on|off] [-verbose on|off]

OPTIONS:
    -latmin latmin
        minimum latitude

    -latmax latmax
        maximum latitude

    -lonmin lonmin
        minimum longitude

    -lonmax lonmax
        maximum longitude

    -resolution <xres>/<yres>
        number of samples in the x/y direction of the DEM file
    
    -date YYYY-MM-DD
        date in ISO form
 
    -hour HH
        2-digit hour
    
    -min MM
        2-digit minutes
    
    -gps [gipsy|gamit]
        which GPS estimates

    -Wx [namanl,rucanl,gfsanl,off]
        choose weather model, or none

    -interp [triang|IDW]
        choose triangulation or inverse distance weighting

    -coords [servlet|xml|llh] 
        choose method for getting site coordinates.  Default = servlet


    -llh_dir [dir] [optional]
        location of NominalPosition.List.llh file if using -coords llh

    -output_dir (optional)
        set a directory for the output correction map.  Default = cwd

    -output_file (optional)
        set a filename for the output .grd map

    -workdir dir  (optional)
        set a directory to save in and attempt to read input files from
        (default is to work under /tmp and then delete)

    -ISCE_DEM file (optional)
        specify an input DEM file from ISCE.  Output .grd file will match
        this DEM in range and resolution.

    -local_gipsy_dir dir (optional)
        local directory (above yearly directories) for gipsy .trop files
        (default is to ftp from SIO)

    -local_gamit_dir dir (optional)
        local directory (above regional/ and global/) for gamit ofiles
        (default is to ftp from SIO)

    -local_xml_dir dir (optional)
        local directory for xml file
        (default is to ftp from SIO)

    -download_only dir (optional)
        acquire needed GPS, weather, and DEM data to this dir, then exit.
        Useful if you are going to farm out the calculations to nodes.

    -pre_downloaded dir (optional)
        GPS, weather, and DEM data has already been downloaded to this dir
        with the download_only flag

    -png [on,off] (optional)
        will create a png preview. default=off

    -verbose on (optional)
        see diagnostic output 

EXAMPLE:
    tropmap.py -latmin 30.5 -latmax 34.5 -lonmin -121.5 -lonmax -118.5 -resolution 3600+/2400+ 3600+/2400+ 3600+/2400+ -date 2010-01-01 -hour 06 -min 00 -gps gipsy -Wx namanl -interp triang [-coords servlet|xml|llh] [-llh_dir dir]  [-output_dir dir] [-output_file file] [-workdir dir] [-ISCE_DEM file] [-local_gipsy_dir dir] [-local_gamit_dir dir] [-local_xml_dir dir] [-download_only dir] [-pre_downloaded dir] [-png on] [-verbose on]

COPYRIGHT:
    Copyright 2011, by the California Institute of Technology. ALL RIGHTS 
RESERVED. United States Government Sponsorship acknowledged. Any commercial use 
must be negotiated with the Office of Technology Transfer at the California 
Institute of Technology.
 
EXPORT CLASIFICATION:
    This software is subject to U.S. export control laws and regulations and 
has been classified as EAR99.  By accepting this software, the user agrees to 
comply with all applicable U.S. export laws and regulations.  User has the 
responsibility to obtain export licenses, or other export authority as may be 
required before exporting such information to foreign countries or providing 
access to foreign persons."

AUTHORS:
    Jet Propulsion Laboratory
    California Institute of Technology
    Pasadena, CA, USA
'''

Hscale=7400
Wscale=3000
# for no scaling to sea level exp(x/99999) is essentially 1
#Hscale=99999
#Wscale=99999

import os, sys, pydoc, pdb, fnmatch, ftplib, gzip, types,calendar,time
import argparse, subprocess, numpy, urllib2, math
import datetime, tarfile, zipfile, tempfile, shutil, re
from PyNIO import Nio
from wxfunctions import *
from spatialfunc import *

__author__ = 'Angelyn Moore'
__date__    = '$Date: 2011-11-14 16:53:26 -0800 (Mon, 14 Nov 2011) $'[7:-21]
__version__ = '$Revision: 36433 $'[11:-2]

################################################################################
# FUNCTION: usage
################################################################################
def usage():
    '''
Generate a usage print statement.
    '''
    print '''
    tropmap.py -latmin latmin -latmax latmax -lonmin lonmin -lonmax lonmax -date YYYY-MM-DD -hour HH -min 00 -Wx namanl -interp triang [-coords servlet|xml|llh] [-llh_dir dir]  [-output_file file] [-output_dir dir] [-workdir dir] [-ISCE_DEM file] [-local_gipsy_dir dir] [-local_gamit_dir dir] [-local_xml_dir] [-download_only dir] [-pre_downloaded dir] [-png on] [-verbose on]
'''
    sys.exit(2)

def setup_tmp(clargs):
    if type(clargs['workdir']) is types.NoneType:
        tmpdir=os.path.abspath(tempfile.mkdtemp(dir='.'))
        return tmpdir
    else:
      if os.path.isdir(clargs['workdir']):
        return clargs['workdir']
      else:
        try:
          os.mkdir(clargs['workdir'])
          return(clargs['workdir'])
        except:
          print >>sys.stderr, ' '.join(['could not create',clargs['workdir']])
          sys.exit(2)

def cleanup(clargs,tmpdir):
    if type(clargs['workdir']) is types.NoneType:
      shutil.rmtree(tmpdir)

def findwxhr(date,hr):
    [yyyy,mm,dd]=date.split('-')
    date=date.replace('-','')
    wxhr="%02d" % int(round(float(hr)/6)*6)
    if int(wxhr)==24:
        d=datetime.datetime(year=int(yyyy), month=int(mm), day=int(dd))+datetime.timedelta(days=1)
        date=''.join([str(d.year),str("%02d" % d.month),str("%02d" % d.day)])
        wxhr='00'
    wxhr=''.join([wxhr,'00']) 
    return date,wxhr
    
def get_grib(clargs,tmpdir,fout):
    fullpath=os.path.abspath(os.path.dirname(sys.argv[0]))
    (yyyymmdd,hhmm)=findwxhr(clargs['date'],clargs['hour'])
    yyyymm=yyyymmdd[:-2]
    datehr=''.join([yyyymmdd,hhmm[:-2]])
    latmin=clargs['latmin']-1.0
    latmax=clargs['latmax']+1.0
    lonmin=clargs['lonmin']-1.0
    lonmax=clargs['lonmax']+1.0
    
    wxFilePrefix={}
    wxGrid={}
    latvar={}
    lonvar={}
    wxFilePrefix['namanl']='namanl'
    wxGrid['namanl']='218'
    latvar['namanl']='gridlat'
    lonvar['namanl']='gridlon'
    # NARR requires external height field
    wxFilePrefix['narr-a']='narr-a'
    wxGrid['narr-a']='221'
    latvar['gfsanl']='lat'
    lonvar['gfsanl']='lon'
    wxFilePrefix['rucanl']='ruc2anl'
    wxGrid['rucanl']='252'
    latvar['rucanl']='gridlat'
    lonvar['rucanl']='gridlon'
    wxFilePrefix['gfsanl']='gfsanl'
    wxGrid['gfsanl']='3'
    latvar['gfsanl']='lat'
    lonvar['gfsanl']='lon'

    if type(clargs['pre_downloaded']) is not types.NoneType:
        wxdir=clargs['pre_downloaded']
    elif type(clargs['download_only']) is not types.NoneType:
        wxdir=clargs['download_only']
    else:
        wxdir=tmpdir

    #generalize to other wx models here
    if clargs['Wx'] != 'off':
        wxfn='_'.join([wxFilePrefix[clargs['Wx']],wxGrid[clargs['Wx']],yyyymmdd,hhmm,'000.sub.grb'])
        target_grb_fn="/".join([wxdir,clargs['Wx'],yyyymm,wxfn])
        if not os.path.exists(target_grb_fn):
    
        #    Get the grib file from noaa
#            print >>sys.stderr, "Getting GRIB"
            subprocess.call(['get-httpsubset.pl',datehr,datehr,'PRES-HGT-PWAT-TMP','ATM-SFC','/'.join([wxdir,clargs['Wx']]),clargs['Wx']],stdout=fout)
        
         
            if not os.path.exists("/".join([wxdir,clargs['Wx'],yyyymm,wxfn])):
                # may need to get entire grb and subset by hand
                print >>sys.stderr, ' '.join(["Could not get Wx inventory for",yyyymmdd,"(not fatal)"])
                try:
                    # get full grb
                    wxbasefn='_'.join([wxFilePrefix[clargs['Wx']],wxGrid[clargs['Wx']],yyyymmdd,hhmm,'000'])
                    url='/'.join(['http://nomads.ncdc.noaa.gov/data/',clargs['Wx'],yyyymm,yyyymmdd,''.join([wxbasefn,'.grb'])])
                    print >>sys.stderr, ''.join(['Trying to create inventory from ',url," (May take a few minutes)"])
                    if not os.path.exists("/".join([wxdir,clargs['Wx'],yyyymm])):
                        os.mkdir("/".join([wxdir,clargs['Wx'],yyyymm]))
                    response=urllib2.urlopen(url)
                    html=response.read()
                    out=open('/'.join([wxdir,clargs['Wx'],yyyymm,''.join([wxbasefn,'.grb'])]),'w')
                    out.write(html)
                    out.close()
            
                    # wgrib -s to get inv
                    wgrib=subprocess.Popen(['wgrib','-s','/'.join([wxdir,clargs['Wx'],yyyymm,''.join([wxbasefn,'.grb'])])],stdout=subprocess.PIPE,stderr=fout).communicate()[0]
                    out=open('/'.join([wxdir,clargs['Wx'],yyyymm,''.join([wxbasefn,'.inv'])]),'w')
                    out.write(wgrib)
                    out.close()
                    # get_inv.manual to add range
                    invrange=subprocess.Popen(['get_inv.manual.pl','/'.join([wxdir,clargs['Wx'],yyyymm,''.join([wxbasefn,'.inv'])])],stdout=subprocess.PIPE,stderr=fout).communicate()[0]
                    out=open('/'.join([wxdir,clargs['Wx'],yyyymm,''.join([wxbasefn,'.range.inv'])]),'w')
                    out.write(invrange)
                    out.close()
                    # grep :PRES|PWAT|HGT|TMP:ATM|SFC | get_grib
            
                    grepproc=subprocess.Popen(['grep','-Pi',':(PRES|PWAT|HGT|TMP):(ATM|SFC)','/'.join([wxdir,clargs['Wx'],yyyymm,''.join([wxbasefn,'.range.inv'])])],stdout=subprocess.PIPE,stderr=fout)
                    grepop=grepproc.communicate()[0]
                    gribproc=subprocess.Popen(['get_grib.pl',url,'/'.join([wxdir,clargs['Wx'],yyyymm,''.join([wxbasefn,'.sub.grb'])])],stdin=subprocess.PIPE,stderr=fout)
                    gribproc.communicate(grepop)
            
                    os.remove('/'.join([wxdir,clargs['Wx'],yyyymm,''.join([wxbasefn,'.grb'])]))
                except: 
                    print >>sys.stderr, ' '.join(["Could not get Wx data for",yyyymmdd])
                    cleanup(clargs,tmpdir)
                    sys.exit(2)
    
    if type(clargs['download_only']) is types.NoneType:
        outHsl=open('/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'WxZHDm.sl.xy'])]),'w')
        outWsl=open('/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'WxZWDm.sl.xy'])]),'w')
        if clargs['Wx'] != 'off':
            try:  
                Wx=Nio.open_file("/".join([wxdir,clargs['Wx'],yyyymm,wxfn]),"r")
            except:
                print >>sys.stderr, ' '.join([wxfn,"could not be opened with Nio"])
                cleanup(clargs,tmpdir)
                sys.exit(2)
         
            if clargs['Wx'] == 'narr-a':
               narrfix=Nio.open_file('/'.join([fullpath,'AWIP32-fixed.grb']),"r")
               Wxlat_all=numpy.ravel(narrfix.variables['gridlat_221'])
               Wxlon_all=numpy.ravel(narrfix.variables['gridlon_221'])
            else:
              Wxlat_all=numpy.ravel(Wx.variables['_'.join([latvar[clargs['Wx']],wxGrid[clargs['Wx']]])])
              Wxlon_all=numpy.ravel(Wx.variables['_'.join([lonvar[clargs['Wx']],wxGrid[clargs['Wx']]])])
            
            if clargs['Wx'] == 'gfsanl':
                Wxlon_all-=360
                Wxlat_all=numpy.repeat(Wxlat_all,360)
                Wxlon_all=numpy.tile(Wxlon_all,181)
                # vars inside gfsanl have '_10' appended
                suffix='_10'
            else:
                suffix=''

            Wxlat=Wxlat_all[(Wxlat_all<=latmax) & (Wxlat_all>=latmin) & (Wxlon_all<=lonmax) & (Wxlon_all>=lonmin)]
            Wxlon=Wxlon_all[(Wxlat_all<=latmax) & (Wxlat_all>=latmin) & (Wxlon_all<=lonmax) & (Wxlon_all>=lonmin)]
            # vars have _10 postpended for gfs
            Wxtemp=numpy.ravel(Wx.variables[''.join(['_'.join(['TMP',wxGrid[clargs['Wx']],'SFC']),suffix])])[(Wxlat_all<=latmax) & (Wxlat_all>=latmin) & (Wxlon_all<=lonmax) & (Wxlon_all>=lonmin)]
            Wxpw=numpy.ravel(Wx.variables[''.join(['_'.join(['P_WAT',wxGrid[clargs['Wx']],'EATM']),suffix])])[(Wxlat_all<=latmax) & (Wxlat_all>=latmin) & (Wxlon_all<=lonmax) & (Wxlon_all>=lonmin)]/10
            Wxpres=numpy.ravel(Wx.variables[''.join(['_'.join(['PRES',wxGrid[clargs['Wx']],'SFC']),suffix])])[(Wxlat_all<=latmax) & (Wxlat_all>=latmin) & (Wxlon_all<=lonmax) & (Wxlon_all>=lonmin)]/100
            if clargs['Wx'] == 'narr-a':
               Wxhgt=numpy.ravel(narrfix.variables['HGT_221_SFC'])[(Wxlat_all<=latmax) & (Wxlat_all>=latmin) & (Wxlon_all<=lonmax) & (Wxlon_all>=lonmin)]/1000
            else:
               Wxhgt=numpy.ravel(Wx.variables[''.join(['_'.join(['HGT',wxGrid[clargs['Wx']],'SFC']),suffix])])[(Wxlat_all<=latmax) & (Wxlat_all>=latmin) & (Wxlon_all<=lonmax) & (Wxlon_all>=lonmin)]/1000
    
            # now have ht(km) pressure(mbar) pwat(cm)
            for i in range(len(Wxlat)-1):  
                Wxzhd=zhdsaasta(Wxpres[i],Wxlat[i],Wxhgt[i]*1000)/100
                Wxzwd=pw2zwd(Wxpw[i],Wxtemp[i])/100
                Wxzwdm=movepw(pw2zwd(Wxpw[i],Wxtemp[i]),Wxhgt[i]*1000,0,Wscale)/100
                Wxzhdm=movepres(zhdsaasta(Wxpres[i],Wxlat[i],Wxhgt[i]*1000),Wxhgt[i],0,Hscale)/100
                # write out for GMT use
                outHsl.write(' '.join([str(Wxlon[i]),str(Wxlat[i]),str(Wxzhdm),'\n']))
                outWsl.write(' '.join([str(Wxlon[i]),str(Wxlat[i]),str(Wxzwdm),'\n']))
        else:
            # For gps only, force wx = 0
            Wxzhdm=0.00
            Wxzwdm=0.00
            for lati in range(0,10):  
                for loni in range(0,10):
                    lat=latmin+lati*(latmax-latmin)/10
                    lon=lonmin+loni*(lonmax-lonmin)/10
                    outHsl.write(' '.join([str(lon),str(lat),str(Wxzhdm),'\n']))
                    outWsl.write(' '.join([str(lon),str(lat),str(Wxzwdm),'\n']))
        
        outHsl.close()
        outWsl.close()
        endtuple=os.times()
        end=endtuple[2]+endtuple[3]
        
        latgrid=(latmax-latmin)/100
        longrid=(lonmax-lonmin)/100
        
        subprocess.call(['triangulate',''.join(['-R','/'.join([str(clargs['lonmin']-1.0),str(clargs['lonmax']+1.0),str(clargs['latmin']-1.0),str(clargs['latmax']+1.0)])]),''.join(['-I','/'.join([str(longrid),str(latgrid)])]),'-F','/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'WxZWDm.sl.xy'])]),''.join(['-G','/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'WxZWDm.sl.grd'])])])],stdout=fout)
        subprocess.call(['triangulate',''.join(['-R','/'.join([str(clargs['lonmin']-1.0),str(clargs['lonmax']+1.0),str(clargs['latmin']-1.0),str(clargs['latmax']+1.0)])]),''.join(['-I','/'.join([str(longrid),str(latgrid)])]),'-F','/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'WxZHDm.sl.xy'])]),''.join(['-G','/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'WxZHDm.sl.grd'])])])],stdout=fout)

def urlget_tdp(url, tdpdir, yyyy, doy):
    password_mgr=urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None,url,'anonymous','awmoore@jpl.nasa.gov')
    handler=urllib2.HTTPBasicAuthHandler(password_mgr)
    opener=urllib2.build_opener(handler)
    urllib2.install_opener(opener)
    html=urllib2.urlopen(url).read().splitlines()
   
    linepats=r'(\d{4}\-\d{2}\-\d{2}.trop.tar.\w+)'
    for line in html:
      if 'trop.tar' in line:
        trop_file=re.search(linepats,line).group(0)
        url='/'.join([url,trop_file])
        response=urllib2.urlopen(url)
        html=response.read()
        if not os.path.exists('/'.join([tdpdir,yyyy])):
          os.mkdir('/'.join([tdpdir,yyyy]))
        trop_dir='/'.join([tdpdir,yyyy,doy])
        if not os.path.exists(trop_dir):
          os.mkdir(trop_dir)
        trop_path = '/'.join([trop_dir,trop_file])
        out=open(trop_path,'w')
        out.write(html)
        out.close()
        return trop_dir, trop_file
 
def acquire_tdp(clargs,tmpdir):
    if type(clargs['pre_downloaded']) is not types.NoneType:
        tdpdir=clargs['pre_downloaded']
    elif type(clargs['download_only']) is not types.NoneType:
        tdpdir=clargs['download_only']
    else:
        tdpdir=tmpdir
    yyyymmdd=clargs['date'].replace('-','')
    yymmdd=yyyymmdd[2:]
    yyyy=yyyymmdd[:-4]
    dd=yyyymmdd[6:]
    mm=yyyymmdd[4:6]
    ddd=datetime.date.toordinal(datetime.date(int(yyyy),int(mm),int(dd)))-datetime.date.toordinal(datetime.date(int(yyyy),1,1))+1
    doy="%03d" % (ddd)
    try:
        os.mkdir('/'.join([tdpdir,yyyy]))
    except OSError:
        pass
    try:
        os.mkdir('/'.join([tdpdir,yyyy,doy]))
    except OSError:
        pass
    trop_file=''.join([clargs['date'],'.trop.tar.gz'])
    trop_dir='/'.join([tdpdir,yyyy,doy])
    if not os.path.exists(trop_dir):
      os.mkdir(trop_dir)
    trop_path = '/'.join([trop_dir,trop_file])
    # get trop file
    if type(clargs['local_gipsy_dir']) is types.NoneType:
      if os.path.exists('/'.join([tdpdir,yyyy,doy,trop_file])): #look in workdir
        pass
      else: #ftp
#        print >>sys.stderr, "Getting trop"
#        try:
          url='/'.join(['http://garner.ucsd.edu/pub/solutions/gipsy/trop/',str(yyyy),str(doy)])
          try:
            (trop_dir,trop_file)=urlget_tdp(url, tdpdir, yyyy, doy)
  
          except:
            print >>sys.stderr, "Unable to retrieve trop file from  SIO"
            cleanup(clargs,tmpdir)
            sys.exit(2)
          
          
    elif os.path.exists('/'.join([clargs['local_gipsy_dir'],str(yyyy),str(doy),trop_file])):
            if clargs['verbose']=='on':
                print >>sys.stderr, "found local trop file"
            shutil.copy('/'.join([clargs['local_gipsy_dir'],str(yyyy),str(doy),trop_file]),'/'.join([tmpdir,str(yyyy),str(doy)]))
    else:
        print >>sys.stderr, "Unable to find local trop files"
        cleanup(clargs,tmpdir)
        sys.exit(2)
    
    try:
      if trop_file.endswith(".gz"):
        troptar=tarfile.open('/'.join([trop_dir,trop_file]),'r:gz')
      elif trop_file.endswith(".Z"):
        os.popen('gunzip -S .Z -f '+'/'.join([trop_dir,trop_file]))
        trop_tar=trop_file.split('.Z')[0]
        troptar=tarfile.open('/'.join([trop_dir,trop_tar]),'r:')
      troptar.extractall(path=''.join([trop_dir,'/']))
      troptar.close()
    except: 
      print >>sys.stderr, "Unable to untar trop file"
      cleanup(clargs,tmpdir)
      sys.exit(2)
          
    
    if type(clargs['download_only']) is types.NoneType:
        troplist=[]
        try:
            for file in os.listdir('/'.join([tdpdir,yyyy,doy])):
                if fnmatch.fnmatch(file,'*.trop'):
                    #troplist=''.join([troplist,file.split('.')[0],' '])
                    troplist.append(file.split('.')[0])
        except OSError:
            print "No dir %s" % ('/'.join([tdpdir,yyyy,doy]))
        # remove trailing space
    #    troplist=troplist[:-1]
        return troplist
    else:
       return None


def download_f(block):
    file.write(block)

def acquire_gamit(clargs,tmpdir):
    if type(clargs['pre_downloaded']) is not types.NoneType:
        gamdir=clargs['pre_downloaded']
    elif type(clargs['download_only']) is not types.NoneType:
        gamdir=clargs['download_only']
    else:
        gamdir=tmpdir
    yyyymmdd=clargs['date'].replace('-','')
    yymmdd=yyyymmdd[2:]
    yyyy=yyyymmdd[:-4]
    dd=yyyymmdd[6:]
    mm=yyyymmdd[4:6]
    ddd=datetime.date.toordinal(datetime.date(int(yyyy),int(mm),int(dd)))-datetime.date.toordinal(datetime.date(int(yyyy),1,1))+1
    doy="%03d" % (ddd)
    troplist=""
    tropfile={}
    try:
        os.mkdir('/'.join([gamdir,yyyy]))
        os.mkdir('/'.join([gamdir,yyyy,doy]))
    except OSError:
        pass
    
    if type(clargs['local_gamit_dir']) is types.NoneType:
        ftp=ftplib.FTP('garner.ucsd.edu')
        ftp.login('anonymous','awmoore@jpl.nasa.gov')
        # get ofiles
        ftp.cwd('/'.join(['/pub/solutions/global',str(yyyy),doy])) 
        ftpfiles=ftp.nlst()
        for file in ftpfiles:
            if fnmatch.fnmatch(file,"o????a.???.Z"):
                 dlfile=open('/'.join([gamdir,yyyy,doy,file]),"wb")
                 ftp.retrbinary('RETR '+file,dlfile.write)
                 dlfile.close()
        ftp.cwd('/'.join(['/pub/solutions/regional',yyyy])) 
        daydirs=ftp.nlst()
        for daydir in daydirs:
            if fnmatch.fnmatch(daydir,doy+"?"):
                ftp.cwd('/'.join(["/pub/solutions/regional",yyyy,daydir]))
                ftpfiles=ftp.nlst()
                for file in ftpfiles:
                    if fnmatch.fnmatch(file,"o????a.???.Z"):
                        dlfile=open('/'.join([gamdir,yyyy,doy,file]),"wb")
                        ftp.retrbinary('RETR '+file,dlfile.write)
                        dlfile.close()
        if type(clargs['download_only']) is not types.NoneType:
            return (None,None)
    
    elif os.path.exists('/'.join([clargs['local_gamit_dir'],'global'])):
            if clargs['verbose']=='on':
                print >>sys.stderr, "found local ofiles"
            for file in os.listdir('/'.join([clargs['local_gamit_dir'],'global',yyyy,doy])):
                if fnmatch.fnmatch(file,"o????a.???.Z"):
                    shutil.copy('/'.join([clargs['local_gamit_dir'],'global',yyyy,doy,file]),'/'.join([tmpdir,yyyy,doy,file]))
            for dirname,dirnames, filenames in os.walk('/'.join([clargs['local_gamit_dir'],'regional',yyyy])):
                for subdirname in dirnames:
                    if fnmatch.fnmatch(subdirname,doy+"?"):
                        for file in os.listdir('/'.join([clargs['local_gamit_dir'],'regional',yyyy,subdirname])):
                            if fnmatch.fnmatch(file,"o????a.???.Z"):
                                shutil.copy('/'.join([clargs['local_gamit_dir'],'regional',yyyy,subdirname,file]),'/'.join([tmpdir,yyyy,doy,file]))
    
    else:
        print >>sys.stderr, "Unable to find local trop files"
        cleanup(clargs,tmpdir)
        sys.exit(2)
                     
    
    for file in os.listdir('/'.join([tmpdir,yyyy,doy])):
         if fnmatch.fnmatch(file,"o????a.???.Z"):
             os.popen('gunzip -S .Z -f '+'/'.join([tmpdir,yyyy,doy,file]))
             (troplist,tropfile)=ofile_inventory(tmpdir,yyyy,doy,file.split('.Z')[0],troplist,tropfile)
    
    return (troplist,tropfile)

def acquire_xml(clargs,tmpdir):
    
    if ((type(clargs['local_xml_dir']) is not types.NoneType) and (os.path.exists('/'.join([clargs['local_xml_dir'],'globalProcMetadataInput.xml'])))): 
        if (clargs['verbose'])=='on':
            print >>sys.stderr, "found local xml file"
        shutil.copy('globalProcMetadataInput.xml',tmpdir)
    else:
        # get xml file
        url='http://garner.ucsd.edu/pub/gamit/setup/globalProcMetadataInput.xml'
        password_mgr=urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None,url,'anonymous','awmoore@jpl.nasa.gov')
        handler=urllib2.HTTPBasicAuthHandler(password_mgr)
        opener=urllib2.build_opener(handler)
        urllib2.install_opener(opener)
        response=urllib2.urlopen(url)
        html=response.read()
        out=open('/'.join([tmpdir,'globalProcMetadataInput.xml']),'w')
        out.write(html)
        out.close()
        endtuple=os.times()
    
def get_gpstrop(clargs,tmpdir,fout):

    yymmdd=clargs['date'][2:].replace('-','')
    ll={}
    h={}
    dryztrop={}
    wetztrop={}
    gpszhd_sl=[]
    gpszwd_sl=[]
    sitesInBox=[]
    lonlat=[]
    gpslon=[]
    gpslat=[]
    sites=[]
    # get tdp files in yymmdd subdir 
     
    if clargs['gps']=='gipsy':
        troplist=acquire_tdp(clargs,tmpdir)
    elif clargs['gps']=='gamit':
        (troplist,tropfile)=acquire_gamit(clargs,tmpdir)
    if type(clargs['download_only']) is not types.NoneType:
        return(None,None,None,None,None,None)
       
    
    else:
        boxsites=[]
        [yyyy,mm,dd]=clargs['date'].split('-')
        sec=calendar.timegm(time.strptime(' '.join([yyyy,mm,dd,clargs['hour'],clargs['min']]),"%Y %m %d %H %M"))-calendar.timegm(time.strptime("2000 01 01 12 00", "%Y %m %d %H %M" ))
      
        tdpHout=open('/'.join([tmpdir,'gpsH.sl.xy']),'w')
        tdpWout=open('/'.join([tmpdir,'gpsW.sl.xy']),'w')
    
        
        if clargs['gps'] == 'gipsy':
            source='jpl_ats'
        elif clargs['gps'] == 'gamit':
            source='sopac_ats'
        minLonPos=str(clargs['lonmin']-1.0)
        maxLonPos=str(clargs['lonmax']+1.0)
        if clargs['coords'] == 'servlet':
            response=urllib2.urlopen(''.join(['http://geoapp02.ucsd.edu:8080/gpseDB/coord?op=getXYZ&date=',clargs['date'],'&minLat=',str(clargs['latmin']-1.0),'&maxLat=',str(clargs['latmax']+1.0),'&minLon=',minLonPos,'&maxLon=',maxLonPos,'&source=',source]))
            sitesInBox=response.read().split("\n")
            # remove empty last line
            sitesInBox=sitesInBox[:-1]
            # remove header lines
            sitesInBox=sitesInBox[2:]
        elif clargs['coords'] == 'xml':
            acquire_xml(clargs,tmpdir)
            tropliststr=' '.join(troplist)    

            sitesInBox=subprocess.Popen(['xmlpos.oneday.pl','--date1',clargs['date'],'--lat1',str(clargs['latmin']-1.0),'--lat2',str(clargs['latmax']+1.0),'--lon1',minLonPos,'--lon2',maxLonPos,'-d',tmpdir,'-i','/'.join([tmpdir,'globalProcMetadataInput.xml']),'-s',tropliststr],stdout=subprocess.PIPE,stderr=fout).communicate()[0]
            sitesInBox=sitesInBox.split("\n")
            # remove empty last line
            sitesInBox=sitesInBox[:-1]
        else:
            llh=open('/'.join([clargs['llh_dir'],'NominalPosition.List.llh']),'r')
            for line in llh:
                [site4,lat,lon,ht]=line.split(' ')
                if (float(lat)>=clargs['latmin']-1.0) & (float(lat)<=clargs['latmax']+1.0) & (float(lon)>=clargs['lonmin']-1.0) & (float(lon)<=clargs['lonmax']+1.0): 
                    sitesInBox.append(line)
            llh.close()

            
        for line in sitesInBox:
            if clargs['coords'] == 'servlet':
                [site4,sitenm,decyr,x,y,z,xs,ys,zs,lat,lon,ht,lats,lons,hts,blank]=line.split(';')
            elif clargs['coords'] == 'xml':
                [site4,lon,lat,ht]=line.split(' ')
                lon=str(float(lon)-360)
            else:
                [site4,lat,lon,ht]=line.split(' ')

            site4=site4.upper()
            if site4 in troplist:
                try:
                    if clargs['gps']=='gipsy':
                        (dryztrop[site4],wetztrop[site4])=read_tdp(clargs,site4,tmpdir,yymmdd,sec) 
                    elif clargs['gps']=='gamit':
                        (dryztrop[site4],wetztrop[site4])=read_ofile(site4,tmpdir,yymmdd,file,sec,tropfile[site4],clargs['date'],int(clargs['hour']),clargs['min'],ht) 
                
                    ll[site4]=' '.join([lon,lat]);
                    h[site4]=float(ht);
                    dryztrop_sl=movepres(float(dryztrop[site4]),h[site4],0,Hscale)
                    wetztrop_sl=movepw(float(wetztrop[site4]),h[site4],0,Wscale)
                    gpszhd_sl.append(movepres(float(dryztrop[site4]),h[site4],0,Hscale))
                    gpszwd_sl.append(movepw(float(wetztrop[site4]),h[site4],0,Wscale))
                    sites.append(site4)
                    lonlat.append(ll[site4])
                    gpslon.append(ll[site4].split()[0])
                    gpslat.append(ll[site4].split()[1])
                    tdpHout.write(' '.join([ll[site4],str(dryztrop_sl),'\n']))
                    tdpWout.write(' '.join([ll[site4],str(wetztrop_sl),'\n']))
                except KeyError:
                        pass
        tdpHout.close()
        tdpWout.close()
        return(gpszhd_sl,gpszwd_sl,lonlat,sites,gpslon,gpslat)

def ofile_inventory(tmpdir,yyyy,doy,ofilenm,troplist,tropfile):
    ofile=open('/'.join([tmpdir,yyyy,doy,ofilenm])) 
    for line in ofile:
        if 'FIXED' in line: break
    for line in ofile:
        if 'ATM_ZEN' in line:
            site=line.split(' ')[2]
            if site not in troplist:
                troplist=' '.join([troplist,site])
                tropfile[site]=ofilenm 
    ofile.close()
    return (troplist,tropfile)

def read_ofile(site4,tmpdir,yymmdd,file,sec,tropfile,date,hour,min,ht):
    yyyymmdd=date.replace('-','')
    yymmdd=yyyymmdd[2:]
    yyyy=yyyymmdd[:-4]
    dd=yyyymmdd[6:]
    mm=yyyymmdd[4:6]
    ddd=datetime.date.toordinal(datetime.date(int(yyyy),int(mm),int(dd)))-datetime.date.toordinal(datetime.date(int(yyyy),1,1))+1
    doy="%03d" % (ddd)
    day=int(date.split('-')[2]) 
    dryztrop={}
    wetztrop={}
    if min>30:
        hour=hour+1
        if hour==24:
          hour=0
          day=day+1
  
    ofile=open("/".join([tmpdir,yyyy,doy,tropfile]),"r")
    for line in ofile:
        if 'FIXED' in line: break
    for line in ofile:
        if "ATM_ZEN X " in line and "+-" in line:
            if (int(line.split()[6])==day and int(line.split()[7])==hour):
                ztd=line.split()[12]
    # STD ATM for pressure; 
                dryztrop[site4]=1.013+2.27*math.exp(-.116e-3*float(ht))
                wetztrop[site4]=float(ztd)-dryztrop[site4]
    ofile.close()

    return (dryztrop[site4],wetztrop[site4])

def read_tdp(clargs,site4,tmpdir,yymmdd,sec):
    yyyymmdd=clargs['date'].replace('-','')
    yymmdd=yyyymmdd[2:]
    yyyy=yyyymmdd[:-4]
    dd=yyyymmdd[6:]
    mm=yyyymmdd[4:6]
    ddd=datetime.date.toordinal(datetime.date(int(yyyy),int(mm),int(dd)))-datetime.date.toordinal(datetime.date(int(yyyy),1,1))+1
    doy="%03d" % (ddd)
    dryztrop={}
    wetztrop={}
    file=site4+'.trop'

        #print "%s %s" % (site4,file)
  
    tdp=open("/".join([tmpdir,yyyy,doy,file]),"r")
    L=tdp.readlines()
    for line in L:
      if "DRYZTROP" in line:
        if float(line.strip('#').split()[0]) < float(sec):
          dryztrop[site4]=line.strip('#').split()[2] 
      elif "WETZTROP" in line:
        if "#" not in line:
          time=line.split()[0]
          if (abs(float(time)-float(sec))<150):
            #print "%s %s" % (time,sec)
            wetztrop[site4]=line.split()[2]
    tdp.close()     
    return (dryztrop[site4],wetztrop[site4])

def get_dem(clargs,tmpdir,fout):
    if type(clargs['pre_downloaded']) is not types.NoneType:
        demdir=clargs['pre_downloaded']
    elif type(clargs['download_only']) is not types.NoneType:
        demdir=clargs['download_only']
    else:
        demdir=tmpdir

    try:
        os.mkdir('/'.join([demdir,'DEMfiles']))
    except OSError:
        pass
    if type(clargs['ISCE_DEM']) is not types.NoneType:
       print "%s" % ' '.join(['xyz2grd',''.join(['-R','/'.join([str(clargs['lonmin']),str(clargs['lonmax']),str(clargs['latmin']),str(clargs['latmax'])])]),''.join(['-I',clargs['resolution']]),'-Zh',clargs['ISCE_DEM'],'-N-10000',''.join(['-G','/'.join([tmpdir,'DEMfiles','DEM-mapres.grd'])])])
       try: 
           subprocess.Popen(['xyz2grd',''.join(['-R','/'.join([str(clargs['lonmin']),str(clargs['lonmax']),str(clargs['latmin']),str(clargs['latmax'])])]),''.join(['-I',clargs['resolution']]),'-Zh',clargs['ISCE_DEM'],'-N-10000',''.join(['-G','/'.join([tmpdir,'DEMfiles','DEM-mapres.grd'])])])
       except:
           print >>sys.stderr, ' '.join(['could not run xyz2grd on',clargs['ISCE_DEM']])
           cleanup(clargs,tmpdir)
           sys.exit(2)

    else:
        # Get SRTM files
        if os.path.exists('DEM-mapres.grd'):
            shutil.copy('DEM-mapres.grd','/'.join([tmpdir,'DEMfiles']))
            return
        
        else:
            # Determine integer degrees in the bbox
            # there is a sprintf ("%03d") issue with longitudes
            minintlat=int(math.floor(clargs['latmin']))
            maxintlat=int(math.ceil(clargs['latmax']))
            minintlon=int(math.floor(clargs['lonmin']))
            maxintlon=int(math.ceil(clargs['lonmax']))
    
            # see http://dds.cr.usgs.gov/srtm/version2_1/SRTM1/Region_definition.jpg
            if minintlat>=37 and maxintlat<=50 and minintlon>=-125 and maxintlon<=-111:
                region='Region_01'
            elif minintlat>=37 and maxintlat<=50 and minintlon>=-111 and maxintlon<=-97:
                region='Region_02'
            elif minintlat>=37 and maxintlat<=50 and minintlon>=-98 and maxintlon<=-84:
                region='Region_03'
            elif minintlat>=27 and maxintlat<=37 and minintlon>=-124 and maxintlon<=-100:
                region='Region_04'
            elif minintlat>=26 and maxintlat<=37 and minintlon>=-101 and maxintlon<=-98:
                region='Region_05'
            elif minintlat>=16 and maxintlat<=48 and minintlon>=-71 and maxintlon<=-64:
                region='Region_06'
            # Region 07 definition is actually stranger
            elif minintlat>=-1 and maxintlat<=60 and minintlon>=-166 and maxintlon<=-130:
                region='Region_07'
            else:
                print >>sys.stderr, "Error: Range specified is not contained within an SRTM DEM region"
                sys.exit(2)
        
            if type(clargs['download_only']) is not types.NoneType:
                try:
                    os.mkdir('/'.join([demdir,'DEMfiles']))
                except OSError:
                    pass
            else:
                blend=open('/'.join([demdir,'DEMfiles','blend.job']),'w')
            for lat in range (minintlat,maxintlat):
                for lon in range (minintlon,maxintlon):
                    # expects positive W lat
                    fn=''.join(['N',str(lat),'W',str(lon)[1:],'.hgt.zip'])
                    bn=fn[:-4]
                    gn='.'.join([bn,'grd'])
                    if not os.path.exists('/'.join([demdir,'DEMfiles',gn])):
    #                    print >>sys.stderr, "Getting DEM"
    #                    url='/'.join(['http://dds.cr.usgs.gov/srtm/version2_1/SRTM3','North_America',fn])
                        url='/'.join(['http://dds.cr.usgs.gov/srtm/version2_1/SRTM1',region,fn])
                        try:
                            response=urllib2.urlopen(url)
                        except urllib2.HTTPError:
                            continue
                        html=response.read()
                        out=open('/'.join([demdir,'DEMfiles',fn]),'w')
                        out.write(html)
                        out.close()
                   
                        # unzip
                        DEM=zipfile.ZipFile('/'.join([demdir,'DEMfiles',fn]))
                        DEM.extractall('/'.join([demdir,'DEMfiles']))
                        DEM.close()
                       
                        # gdal_translate to .grd
                        subprocess.call(['gdal_translate','-of','GMT','/'.join([demdir,'DEMfiles',bn]),'/'.join([demdir,'DEMfiles',gn])],stdout=fout)
    
                    if type(clargs['download_only']) is types.NoneType:
                        blend.write(' '.join(['/'.join([demdir,'DEMfiles',gn]),''.join(['-R','/'.join([str(lon),str(lon+1),str(lat),str(lat+1)])]),'1','\n']))
    
            if type(clargs['download_only']) is types.NoneType:
                blend.close()
                # Check how this resolution is specified. Should be in arcsec?
                blendjob=subprocess.call(['grdblend',''.join(['-R','/'.join([str(clargs['lonmin']),str(clargs['lonmax']),str(clargs['latmin']),str(clargs['latmax'])])]),''.join(['-I','/'.join(['0.000277778','0.000277778'])]),'/'.join([tmpdir,'DEMfiles/blend.job']),''.join(['-G','/'.join([tmpdir,'DEMfiles','DEM1.grd'])])],stdout=fout)
    #            print "%s" % ' '.join(['grdblend',''.join(['-R','/'.join([str(clargs['lonmin']),str(clargs['lonmax']),str(clargs['latmin']),str(clargs['latmax'])])]),''.join(['-I','/'.join(['0.000833333','0.000833333'])]),'/'.join([tmpdir,'DEMfiles/blend.job']),''.join(['-G','/'.join([tmpdir,'DEMfiles','DEM1.grd'])])])
    #            blendjob=subprocess.call(['grdblend',''.join(['-R','/'.join([str(clargs['lonmin']),str(clargs['lonmax']),str(clargs['latmin']),str(clargs['latmax'])])]),''.join(['-I','/'.join(['3c','3c'])]),'/'.join([tmpdir,'DEMfiles/blend.job']),''.join(['-G','/'.join([tmpdir,'DEMfiles','DEM1.grd'])])],stdout=fout)
                subprocess.call(['grdmath','/'.join([tmpdir,'DEMfiles','DEM1.grd']),'-100','GT','0','NAN','=','/'.join([tmpdir,'DEMfiles','DEMmask.grd'])],stdout=fout)
                subprocess.call(['grdmath','/'.join([tmpdir,'DEMfiles','DEM1.grd']),'/'.join([tmpdir,'DEMfiles','DEMmask.grd']),'MUL','=','/'.join([tmpdir,'DEMfiles','DEM.grd'])],stdout=fout)
                subprocess.call(['grdsample','/'.join([tmpdir,'DEMfiles','DEM.grd']),''.join(['-G','/'.join([tmpdir,'DEMfiles','DEM-mapres.grd'])]),''.join(['-I',str(clargs['resolution'])])])
             
def gpsWxdiffs(clargs,gpszhd_sl,gpszwd_sl,ll,sites,gpslon,gpslat,tmpdir):
    (yyyymmdd,hhmm)=findwxhr(clargs['date'],clargs['hour'])
#    wx=netcdf('/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'WxZWDm.sl.grd'])]),"r")
    wx=Nio.open_file('/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'WxZWDm.sl.grd'])]),"r",format='netcdf')
    Wx100W=wx.variables['z'][::1].copy()
    wx.close()
#    wx=netcdf('/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'WxZHDm.sl.grd'])]),"r")
    wx=Nio.open_file('/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'WxZHDm.sl.grd'])]),"r",format='netcdf')
    Wx100H=wx.variables['z'][::1].copy()
    wx.close()

    # Find the 100x100 grid point of each GPS station

    lonDiff=(clargs['lonmax']-clargs['lonmin']+2*1.0)*numpy.ones((numpy.size(sites)))
    latDiff=(clargs['latmax']-clargs['latmin']+2*1.0)*numpy.ones((numpy.size(sites)))
    ind1=numpy.empty(numpy.size(sites),dtype=int)
    ind2=numpy.empty(numpy.size(sites),dtype=int)
    ((numpy.array(gpslon,dtype=float)-clargs['lonmin']+1.0)/lonDiff*(99)).round(out=ind1)
    ((numpy.array(gpslat,dtype=float)-clargs['latmin']+1.0)/latDiff*(99)).round(out=ind2)
    linInd=numpy.empty(numpy.size(gpslon))
    linInd=ind1+ind2*numpy.shape(Wx100H)[0]

    Wx100W_flat=Wx100W.flatten()[linInd]
    Wx100H_flat=Wx100H.flatten()[linInd]
   
    stnHdiff=(gpszhd_sl-Wx100H_flat)
    stnWdiff=(gpszwd_sl-Wx100W_flat)

    return(stnHdiff,stnWdiff,Wx100H,Wx100W)

def triang(clargs,gpszhd_sl,gpszwd_sl,ll,sites,gpslon,gpslat,tmpdir,fout):
    (wxdate,wxhr)=findwxhr(clargs['date'],clargs['hour'])
    yyyymmdd=clargs['date'].replace('-','')
    hhmm=''.join([clargs['hour'],clargs['min']])
    (stnHdiff,stnWdiff,Wx100H,Wx100W)=gpsWxdiffs(clargs,gpszhd_sl,gpszwd_sl,ll,sites,gpslon,gpslat,tmpdir)
    outHsl=open('/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'gpsZHD.sl.xy'])]),'w')
    outWsl=open('/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'gpsZWD.sl.xy'])]),'w')
    for i in range(len(stnWdiff)):
        [lonGPS,latGPS]=ll[i].split()
        outHsl.write(' '.join([lonGPS,latGPS,str(stnHdiff[i]),'\n']))
        outWsl.write(' '.join([lonGPS,latGPS,str(stnWdiff[i]),'\n']))
    outHsl.close()
    outWsl.close()

    #triangulate diffs 
    latgrid=(clargs['latmax']-clargs['latmin']+2*1.0)/100
    longrid=(clargs['lonmax']-clargs['lonmin']+2*1.0)/100
    subprocess.call(['triangulate',''.join(['-R','/'.join([str(clargs['lonmin']-1.0),str(clargs['lonmax']+1.0),str(clargs['latmin']-1.0),str(clargs['latmax']+1.0)])]),''.join(['-I','/'.join([str(longrid),str(latgrid)])]),'-F','/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'gpsZHD.sl.xy'])]),''.join(['-G','/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'gpsZHD.sl.grd'])])])],stdout=fout)
    subprocess.call(['triangulate',''.join(['-R','/'.join([str(clargs['lonmin']-1.0),str(clargs['lonmax']+1.0),str(clargs['latmin']-1.0),str(clargs['latmax']+1.0)])]),''.join(['-I','/'.join([str(longrid),str(latgrid)])]),'-F','/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'gpsZWD.sl.xy'])]),''.join(['-G','/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'gpsZWD.sl.grd'])])])],stdout=fout)

    # add diff surfaces to WxZHDm.sl.grd, WxZWDm.sl.grd

    subprocess.call(['grdmath','/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'gpsZHD.sl.grd'])]),'/'.join([tmpdir,'.'.join([wxdate,wxhr,'WxZHDm.sl.grd'])]),'ADD','=','/'.join([tmpdir,'comboH.sl.grd'])],stdout=fout)
    subprocess.call(['grdmath','/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'gpsZWD.sl.grd'])]),'/'.join([tmpdir,'.'.join([wxdate,wxhr,'WxZWDm.sl.grd'])]),'ADD','=','/'.join([tmpdir,'comboW.sl.grd'])],stdout=fout)


def IDW(clargs,gpszhd_sl,gpszwd_sl,ll,sites,gpslon,gpslat,tmpdir,fout):
    (wxdate,wxhr)=findwxhr(clargs['date'],clargs['hour'])
    yyyymmdd=clargs['date'].replace('-','')
    hhmm=''.join([clargs['hour'],clargs['min']])
    dMax=200
    dist=numpy.zeros(shape=(101,101,len(ll)))
    f=numpy.zeros(shape=(101,101,len(ll)))
    gpszhd_idw=numpy.zeros(shape=(101,101))
    gpszwd_idw=numpy.zeros(shape=(101,101))

    (stnHdiff,stnWdiff,Wx100H,Wx100W)=gpsWxdiffs(clargs,gpszhd_sl,gpszwd_sl,ll,sites,gpslon,gpslat,tmpdir)

    for lati in range(0,100):
      lat=clargs['latmin']-1.0+lati*(clargs['latmax']-clargs['latmin']+2*1.0)/100
      for loni in range(0,100):
        lon=clargs['lonmin']-1.0+loni*(clargs['lonmax']-clargs['lonmin']+2*1.0)/100
        for i in range(len(ll)):
          [lonGPS,latGPS]=ll[i].split()
          dist[lati][loni][i]=latlondist(latGPS,lat,lonGPS,lon)
          if (dist[lati][loni][i]<dMax):
            f[lati,loni,i]=1/dist[lati][loni][i]**2
#            f[lati,loni,i]=1/dist[lati][loni][i]
          else:
            f[lati,loni,i]=0.
    
    outH=open('/'.join([tmpdir,'comboH.txt']),'w')
    outW=open('/'.join([tmpdir,'comboW.txt']),'w')
    diffH=open('/'.join([tmpdir,'diffH.txt']),'w')
    diffW=open('/'.join([tmpdir,'diffW.txt']),'w')
    for lati in range(0,100):
      lat=clargs['latmin']-1.0+lati*(clargs['latmax']-clargs['latmin']+2*1.0)/100
      for loni in range(0,100):
        lon=clargs['lonmin']-1.0+loni*(clargs['lonmax']-clargs['lonmin']+2*1.0)/100
        dcopy=list(dist[lati,loni,:])
        dcopy.sort()
        nmax=dcopy[9]
    
        f[lati,loni,numpy.nonzero(dist[lati,loni,:]>nmax)]=0.
        fsum=0
        for i in range(len(ll)):
          #if (d[lati,loni,i]<nmax):
            #f[lati,loni,i]=0.
            if (f[lati,loni,i]!=0.):
              try:
                gpszhd_idw[lati,loni]+=f[lati,loni,i]*float(stnHdiff[i])
                gpszwd_idw[lati,loni]+=f[lati,loni,i]*float(stnWdiff[i])
                fsum+=f[lati][loni][i]
              except KeyError:
                pass
        diffH.write(' '.join([str(lon),str(lat),str(gpszhd_idw[lati][loni]),'\n']))
        diffW.write(' '.join([str(lon),str(lat),str(gpszwd_idw[lati][loni]),'\n']))
        gpszhd_idw[lati][loni]=gpszhd_idw[lati][loni]/fsum
        gpszwd_idw[lati][loni]=gpszwd_idw[lati][loni]/fsum
    

        #add Wx to difference surface
        zhd_idw_sl=gpszhd_idw[lati][loni]+Wx100H[lati][loni]
        zwd_idw_sl=gpszwd_idw[lati][loni]+Wx100W[lati][loni]

        outH.write(' '.join([str(lon),str(lat),str(zhd_idw_sl),'\n']))
        outW.write(' '.join([str(lon),str(lat),str(zwd_idw_sl),'\n']))
    outH.close()
    outW.close()
    diffH.close()
    diffW.close()

#   grd
    subprocess.call(['xyz2grd',''.join(['-R','/'.join([tmpdir,'.'.join([wxdate,wxhr,'WxZHDm.sl.grd'])])]),'-F','/'.join([tmpdir,'comboH.txt']),''.join(['-G','/'.join([tmpdir,'comboH.sl.grd'])])],stdout=fout)
    subprocess.call(['xyz2grd',''.join(['-R','/'.join([tmpdir,'.'.join([wxdate,wxhr,'WxZWDm.sl.grd'])])]),'-F','/'.join([tmpdir,'comboW.txt']),''.join(['-G','/'.join([tmpdir,'comboW.sl.grd'])])],stdout=fout)


def gotomapres(clargs,tmpdir,fout):
#   resample to final resolution
    yyyymmdd=clargs['date'].replace('-','')
    hhmm=''.join([clargs['hour'],clargs['min']])

    subprocess.call(['grdsample',''.join(['-R','/'.join([str(clargs['lonmin']),str(clargs['lonmax']),str(clargs['latmin']),str(clargs['latmax'])])]),''.join(['-I',str(clargs['resolution'])]),'-F','/'.join([tmpdir,'comboH.sl.grd']),''.join(['-G','/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'comboH.sl.mapres.grd'])])])],stdout=fout)
    subprocess.call(['grdsample',''.join(['-R','/'.join([str(clargs['lonmin']),str(clargs['lonmax']),str(clargs['latmin']),str(clargs['latmax'])])]),''.join(['-I',str(clargs['resolution'])]),'-F','/'.join([tmpdir,'comboW.sl.grd']),''.join(['-G','/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'comboW.sl.mapres.grd'])])])],stdout=fout)

def gototopo(clargs,tmpdir,fout): 
#   goto topo
    yyyymmdd=clargs['date'].replace('-','')
    hhmm=''.join([clargs['hour'],clargs['min']])

    subprocess.call(['grdmath','/'.join([tmpdir,'DEMfiles','DEM-mapres.grd']),'-1','MUL',str(Hscale),'DIV','EXP','/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'comboH.sl.mapres.grd'])]),'MUL','=','/'.join([tmpdir,'comboH.grd'])],stdout=fout)
    subprocess.call(['grdmath','/'.join([tmpdir,'DEMfiles','DEM-mapres.grd']),'-1','MUL',str(Wscale),'DIV','EXP','/'.join([tmpdir,'.'.join([yyyymmdd,hhmm,'comboW.sl.mapres.grd'])]),'MUL','=','/'.join([tmpdir,'comboW.grd'])],stdout=fout)

#   add for ZTD

    if type(clargs['output_file']) is types.NoneType:
        fn={}
        if clargs['Wx']!='off':
          fn['Wx']=clargs['Wx']
        else:
          fn['Wx']='gpsonly'
        finalfn='/'.join([clargs['output_dir'],'.'.join([yyyymmdd,hhmm,clargs['gps'],fn['Wx'],clargs['interp'],'.grd'] )])
    else:
        finalfn='/'.join([clargs['output_dir'],clargs['output_file']])
    subprocess.call(['grdmath','/'.join([tmpdir,'comboH.grd']),'/'.join([tmpdir,'comboW.grd']),'ADD','=',finalfn],stdout=fout)
    if clargs['png']=='on':
       create_png(clargs,finalfn)
    return finalfn

def create_png(clargs,finalfnbase):
       fullpath=os.path.abspath(os.path.dirname(sys.argv[0]))
       bbox='/'.join([''.join(['-R',str(clargs['lonmin'])]),str(clargs['lonmax']),str(clargs['latmin']),str(clargs['latmax'])])
       proj=''.join(['-Jkf',str((clargs['lonmin']+clargs['lonmax'])/2),'/5'])
       ps=open('.'.join([finalfnbase,'ps']),'w')
       subprocess.call(['grdimage',proj,bbox,''.join(['-C',fullpath,'/tropmap.cpt']), finalfnbase,'-K'],stdout=ps)
       subprocess.call(['pscoast',proj,bbox,'-Bg0/g0','-Di','-W','-O','-K'],stdout=ps)
       subprocess.call(['psscale','-D5.5/2/2.5/0.1','-B:,m:',''.join(['-C',fullpath,'/tropmap.cpt']),'-B1','-E','-O'],stdout=ps)
       ps.close
       subprocess.call(['convert','-trim','-rotate','90','.'.join([finalfnbase,'ps']),'.'.join([finalfnbase,'png'])])


def tropmap(clargs):
   tmpdir=setup_tmp(clargs)
   if clargs['verbose']=='on':
       fout=os.dup(1)
   else:
       fout=open(os.devnull,'w')
   get_grib(clargs,tmpdir,fout)
   (gpszhd_sl,gpszwd_sl,ll,sites,gpslon,gpslat)=get_gpstrop(clargs,tmpdir,fout)
   get_dem(clargs,tmpdir,fout)
   if type(clargs['download_only']) is types.NoneType:
       if clargs['interp']=='triang':
           triang(clargs,gpszhd_sl,gpszwd_sl,ll,sites,gpslon,gpslat,tmpdir,fout)
       elif clargs['interp']=='IDW':
           IDW(clargs,gpszhd_sl,gpszwd_sl,ll,sites,gpslon,gpslat,tmpdir,fout)
       gotomapres(clargs,tmpdir,fout)
       finalfn=gototopo(clargs,tmpdir,fout)
       cleanup(clargs,tmpdir)
       return finalfn
#   ZTD()
################################################################################
# FUNCTION: tropmapmain
################################################################################
def tropmapmain():
    '''
Main program that interprets user-specified arguments and executes the necessary methods.
    '''

    # Define pointer to log file
    log_file = sys.__stdout__

    # Extract input arguments
    parser = argparse.ArgumentParser(description='Create a trop map.')
    parser.add_argument('-latmin',metavar='latmin',type=float,help='minimum latitude',required=True)
    parser.add_argument('-latmax',metavar='latmax',type=float,help='maximum latitude',required=True)
    parser.add_argument('-lonmin',metavar='lonmin',type=float,help='minimum longitude',required=True)
    parser.add_argument('-lonmax',metavar='lonmax',type=float,help='maximum longitude',required=True)
    parser.add_argument('-date',metavar='YYYY-MM-DD',type=str,help='date in ISO format',required=True)
    parser.add_argument('-hour',metavar='HH',type=str,help='2-digit hour',required=True)
    parser.add_argument('-min',metavar='MM',type=str,help='2-digit minutes',required=True)
    parser.add_argument('-gps',metavar='gipsy|gamit',type=str,help='gipsy or gamit gps estimates',required=True,choices=['gipsy','gamit'])
    parser.add_argument('-Wx',metavar='namanl|narr-a|rucanl|gfsanl|off',type=str,help='choose weather model, or gps only',required=True,choices=['namanl','narr-a','rucanl','gfsanl','off'])
    parser.add_argument('-interp',metavar='triang|IDW',type=str,help='choose triangulation or inverse distance weighting',required=True,choices=['triang','IDW'])
    parser.add_argument('-workdir',metavar='dir',type=str,help='directory to save intermediate files in and attempt to read files from (default is to use /tmp and delete)')
    parser.add_argument('-coords',metavar='servlet|xml|llh',type=str,help='source for site coordinates',default='xml')
    parser.add_argument('-llh_dir',metavar='dir',type=str,help='Directory containing NominalPosition.List.llh file when using -coords llh')
    parser.add_argument('-resolution',metavar='xres/yres',type=str,help='resolution of correction map, specfied as xres/yres (meters)',default='6c')
    parser.add_argument('-output_dir',metavar='dir',type=str,help='directory in which the result map will be placed',default='.')
    parser.add_argument('-output_file',metavar='file',type=str,help='output filename for the .grd product',default='output')
    parser.add_argument('-ISCE_DEM',metavar='file',type=str,help='ISCE DEM file specifying range and resolution for product file')
    parser.add_argument('-local_gipsy_dir',metavar='dir',type=str,help='directory (above yearly directories) for gipsy .trop.tar files')
    parser.add_argument('-local_gamit_dir',metavar='dir',type=str,help='directory (above global/ and regional/) for gamit ofiles')
    parser.add_argument('-local_xml_dir',metavar='dir',type=str,help='directory for xml files')
    parser.add_argument('-download_only',metavar='dir',type=str,help='download needed input data to this dir, then exit')
    parser.add_argument('-pre_downloaded',metavar='dir',type=str,help='needed input data has been downloaded to this dir with -download_only')
    parser.add_argument('-png',metavar='on',type=str,help='create png preview',choices=['on'],default='off')
    parser.add_argument('-verbose',metavar='on',type=str,help='more diagnostic messages',choices=['on'],default='off')
    args=parser.parse_args()
    clargs=vars(args)
    # Add type checking, min<max, etc here

    retstatus=tropmap(clargs)
    sys.exit(0)




################################################################################
# Main program if running as stand alone program
################################################################################
if __name__ == "__main__":
    tropmapmain()


