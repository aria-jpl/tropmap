#!/usr/bin/python
################################################################################
# PROGRAM: tropwrap.py
################################################################################
'''
PROGRAM:
    tropwrap.py

PURPOSE:
    Construct a GPS-only or GPS+Weather combination troposphere map for
    a given interferogram.

DESCRIPTION:
    Given an interferogram and the two dates/times of acquisition, this
    program will construct a trop correction map and apply
    it to the interferogram

USAGE:
    tropwrap.py -igram <file> -latmin latmin -latmax latmax -lonmin lonmin -lonmax lonmax -resolution <xres>/<yres>
-date1 YYYY-MM-DD -hour1 HH -min1 MM  -date2 YYYY-MM-DD -hour2 HH -min2 MM -gps [gipsy|gamit] -Wx [namanl|rucanl|gfsanl|off] -interp [triang|IDW] [-output_dir <dir>] [-ISCE_DEM file] [-coords servlet|xml|llh] [-llh_dir <dir>] [-workdir <dir>] [-local_gipsy_dir <dir>] [-local_gamit_dir <dir>] [-download_only <dir>] [-pre_downloaded <dir>] [-png on|off] [-verbose on|off]

OPTIONS:
    -igram <file>
        file name of interferogram in GMT .grd format, units meters

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

    -date1 YYYY-MM-DD
        date in ISO form
 
    -hour1HH
        2-digit hour
    
    -min1MM
        2-digit minutes
    
    -date2 YYYY-MM-DD
        date in ISO form
 
    -hour2 HH
        2-digit hour
    
    -min2 MM
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
    tropwrap.py -igram geo_120928-121014-sim_HDR_8rlks.m.grd -resolution xres/yres -date1 2012-09-28 -hour1 04 -min1 07 -date2 2012-10-14 -hour2 04 -min2 07 -gps gipsy -Wx namanl -interp triang [-coords servlet|xml|llh] [-llh_dir dir]  [-output_dir dir] [-workdir dir] [-local_gipsy_dir dir] [-local_gamit_dir dir] [-local_xml_dir dir] [-download_only dir] [-pre_downloaded dir] [-png on] [-verbose on]

COPYRIGHT:
    Copyright 2011, by the California Institute of Technology. ALL RIGHTS 
RESERVED. United States Government Sponsorship acknowledged. Any commercial use 
must be negotiated with the Office of Technology Transfer at the California 
Institute of Technology.
 
AUTHORS:
    Jet Propulsion Laboratory
    California Institute of Technology
    Pasadena, CA, USA
'''

import os, sys, pydoc, numpy
from tropmap import *

__author__ = 'Angelyn Moore'
__date__    = '$Date: 2012-11-14 16:53:26 -0800 (Wed, 14 Nov 2012) $'[7:-21]
__version__ = '$Revision: 36433 $'[11:-2]

################################################################################
# FUNCTION: usage
################################################################################
def usage():
    '''
Generate a usage print statement.
    '''
    print '''
    tropwrap.py -igram geo_120928-121014-sim_HDR_8rlks.m.grd -resolution xres/yres -date1 2012-09-28 -hour1 04 -min1 07 -date2 2012-10-14 -hour2 04 -min2 07 -Wx namanl -interp triang [-coords servlet|xml|llh] [-llh_dir dir] [-output_dir dir] [-workdir dir] [-local_gipsy_dir dir] [-local_gamit_dir dir] [-local_xml_dir] [-download_only dir] [-pre_downloaded dir] [-png on] [-verbose on]
'''
    sys.exit(2)

def get_latlonrange(igram,fout):
   try:
       grdinfo=subprocess.Popen(['grdinfo',igram],stdout=subprocess.PIPE,stderr=fout).communicate()[0]
   except:
       print >>sys.stderr, ' '.join(['could not run grdinfo on',igram])       
       sys.exit(2)
       
   grdinfo=grdinfo[:-1] # remove empty line
   infolines=grdinfo.split("\n");
   for line in infolines:
       fields=line.split(' ')
       if fields[1] == 'x_min:':
           lonmin=fields[2]
           lonmax=fields[4]
           x_res=fields[6]
       if fields[1] == 'y_min:':
           latmin=fields[2]
           latmax=fields[4] 
           y_res=fields[6]
   return (float(latmin),float(latmax),float(lonmin),float(lonmax),x_res,y_res)
   
   

def tropwrap(clargs):
   tmpdir=setup_tmp(clargs)
   if clargs['verbose']=='on':
       fout=os.dup(1)
   else:
       fout=open(os.devnull,'w')
#   clargs['output_dir']=tmpdir
   #(clargs['latmin'],clargs['latmax'],clargs['lonmin'],clargs['lonmax'],x_res,y_res)=get_latlonrange(clargs['igram'],fout)
   clargs['date']=clargs['date1']
   clargs['hour']=clargs['hour1']
   clargs['min']=clargs['min1']
   clargs['output_file']=os.path.split(clargs['igram'])[1] + '_model_1'

#   clargs['output_dir']=tmpdir
   print(clargs)
   map1fn=tropmap(clargs)
   clargs['date']=clargs['date2']
   clargs['hour']=clargs['hour2']
   clargs['min']=clargs['min2']
   clargs['output_file']=os.path.split(clargs['igram'])[1] + '_model_2'
   
   map2fn=tropmap(clargs)
#  subtract to make diff, subtract mean
   igram_dir, igram_name = os.path.split(clargs['igram'])
   subprocess.Popen(['grdmath',map2fn,map1fn,'SUB','=','/'.join([tmpdir,'.'.join([igram_name,'correction.grd'])])]).wait()
   grdinfo=subprocess.Popen(['grdinfo','-L2','/'.join([tmpdir,'.'.join([igram_name,'correction.grd'])])],stdout=subprocess.PIPE,stderr=fout).communicate()[0]
   grdinfo=grdinfo[:-1] # remove empty line
   infolines=grdinfo.split("\n");
   for line in infolines:
       fields=line.split(' ')
       if fields[1] == 'mean:':
           mean=fields[2]
   correctionName = '/'.join([clargs['output_dir'],'.'.join([igram_name,'correction.grd'])])
   subprocess.Popen(['grdmath',map2fn,map1fn,'SUB',mean,'SUB','=',correctionName]).wait()
   import cPickle as cp
   fp = open('tropwrap.pck','w')
   cp.dump((correctionName,grdinfo),fp)
   fp.close()

   '''
   subprocess.Popen(['grdmath',clargs['igram'],'/'.join([clargs['output_dir'],'.'.join([igram_name,'correction.grd'])]),'SUB','=','/'.join([tmpdir,'.'.join([igram_name,'corrected.grd'])])]).wait()
   grdinfo=subprocess.Popen(['grdinfo','-L2','/'.join([tmpdir,'.'.join([igram_name,'corrected.grd'])])],stdout=subprocess.PIPE,stderr=fout).communicate()[0]
   grdinfo=grdinfo[:-1] # remove empty line
   infolines=grdinfo.split("\n");
   for line in infolines:
       fields=line.split(' ')
       if fields[1] == 'mean:':
           mean=fields[2]
   subprocess.Popen(['grdmath',clargs['igram'],'/'.join([tmpdir,'.'.join([igram_name,'correction.grd'])]),'SUB',mean,'SUB','=','/'.join([clargs['output_dir'],'.'.join([igram_name,'corrected.grd'])])])

   if clargs['png']=='on':
       create_correxpng(clargs)
    '''
def create_correxpng(clargs):
#  plot diff map
   igram_dir, igram_name = os.path.split(clargs['igram'])
   fullpath=os.path.abspath(os.path.dirname(sys.argv[0]))
   bbox='/'.join([''.join(['-R',str(clargs['lonmin'])]),str(clargs['lonmax']),str(clargs['latmin']),str(clargs['latmax'])])
   proj=''.join(['-Jkf',str((clargs['lonmin']+clargs['lonmax'])/2),'/10'])
   ps=open('/'.join([clargs['output_dir'],'.'.join([igram_name,'correction','ps'])]),'w') 
   subprocess.call(['grdimage',proj,bbox,''.join(['-C','/'.join([fullpath,'diffmap.cpt'])]),'/'.join([clargs['output_dir'], '.'.join([igram_name,'correction','grd'])]),'-K'],stdout=ps)
   subprocess.call(['pscoast',proj,bbox,'-Bg0/g0','-Di','-W','-O','-K'],stdout=ps)
   subprocess.call(['psscale','-D5.5/2/2.5/0.1','-B:,m:',''.join(['-C','/'.join([fullpath,'/diffmap.cpt'])]),'-B0.1','-E','-O'],stdout=ps)
   ps.close
   subprocess.call(['convert','-trim','-rotate','90','/'.join([clargs['output_dir'],'.'.join([igram_name,'correction','ps'])]),'/'.join([clargs['output_dir'],'.'.join([igram_name,'correction','png'])])])
#  plot corrected map
   ps=open('/'.join([clargs['output_dir'],'.'.join([igram_name,'corrected','ps'])]),'w') 
   subprocess.call(['grdimage',proj,bbox,''.join(['-C','/'.join([fullpath,'diffmap.cpt'])]), '/'.join([clargs['output_dir'],'.'.join([igram_name,'corrected','grd'])]),'-K'],stdout=ps)
   subprocess.call(['pscoast',proj,bbox,'-Bg0/g0','-Di','-W','-O','-K'],stdout=ps)
   subprocess.call(['psscale','-D5.5/2/2.5/0.1','-B:,m:',''.join(['-C','/'.join([fullpath,'/diffmap.cpt'])]),'-B0.1','-E','-O'],stdout=ps)
   ps.close
   subprocess.call(['convert','-trim','-rotate','90','/'.join([clargs['output_dir'],'.'.join([igram_name,'corrected','ps'])]),'/'.join([clargs['output_dir'],'.'.join([igram_name,'corrected','png'])])])


################################################################################
# FUNCTION: tropmapmain
################################################################################
def tropwrapmain():
    '''
Main program that interprets user-specified arguments and executes the necessary methods.
    '''

    # Define pointer to log file
    log_file = sys.__stdout__

    # Extract input arguments
    parser = argparse.ArgumentParser(description='Create a trop map for a given interferogram')
    parser.add_argument('-latmin',metavar='latmin',type=float,help='minimum latitude',required=True)
    parser.add_argument('-latmax',metavar='latmax',type=float,help='maximum latitude',required=True)
    parser.add_argument('-lonmin',metavar='lonmin',type=float,help='minimum longitude',required=True)
    parser.add_argument('-lonmax',metavar='lonmax',type=float,help='maximum longitude',required=True)
    parser.add_argument('-date1',metavar='YYYY-MM-DD',type=str,help='date in ISO format',required=True)
    parser.add_argument('-hour1',metavar='HH',type=str,help='2-digit hour',required=True)
    parser.add_argument('-min1',metavar='MM',type=str,help='2-digit minutes',required=True)
    parser.add_argument('-date2',metavar='YYYY-MM-DD',type=str,help='date in ISO format',required=True)
    parser.add_argument('-hour2',metavar='HH',type=str,help='2-digit hour',required=True)
    parser.add_argument('-min2',metavar='MM',type=str,help='2-digit minutes',required=True)
    parser.add_argument('-igram',metavar='igram',type=str,help='filename of input interferogram',required=True)
    parser.add_argument('-gps',metavar='gipsy|gamit',type=str,help='gipsy or gamit gps estimates',required=True,choices=['gipsy','gamit'])
    # NARR requires using external height field
#    parser.add_argument('-Wx',metavar='namanl|narr-a|rucanl|off',type=str,help='choose weather model, or gps only',required=True,choices=['namanl','narr-a','rucanl','off'])
#    parser.add_argument('-interp',metavar='triang|IDW',type=str,help='choose triangulation or inverse distance weighting',required=True,choices=['triang','IDW'])
    parser.add_argument('-Wx',metavar='namanl|rucanl|gfsanl|off',type=str,help='choose weather model, or gps only',required=True,choices=['namanl','rucanl','gfsanl','off'])
    parser.add_argument('-interp',metavar='triang|IDW',type=str,help='choose triangulation or inverse distance weighting',required=True,choices=['triang','IDW'])
    parser.add_argument('-workdir',metavar='dir',type=str,help='directory to save intermediate files in and attempt to read files from (default is to use /tmp and delete)')
    parser.add_argument('-coords',metavar='servlet|xml|llh',type=str,help='source for site coordinates',default='xml')
    parser.add_argument('-llh_dir',metavar='dir',type=str,help='Directory containing NominalPosition.List.llh file when using -coords llh')
    parser.add_argument('-resolution',metavar='xres/yres',type=str,help='resolution of correction map, specfied as xres/yres (meters)',default='6c')
    parser.add_argument('-output_dir',metavar='dir',type=str,help='directory in which the result map will be placed',default='.')
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

    retstatus=tropwrap(clargs)
    sys.exit(0)




################################################################################
# Main program if running as stand alone program
################################################################################
if __name__ == "__main__":
    tropwrapmain()

