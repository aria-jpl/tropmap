import numpy as np

###########Completed 3D interpolation in geo coordinates############

# Class for bilinear interpolation at a certain level in a 3d cube

class Bilinear2DInterpolator:
    '''Bilinear interpolation in 2D. The code is modified from mpl_toolkits.basemap.interp and scipy.interpolate'''
    def __init__(self, xin, yin, datain,cube=False):
        '''Setting up the interpolator.

        .. Args:

            * xin     -> Monotonic array of x coordinates
            * yin     -> Monotonic array of y coordinates
            * datain  -> 2D array corresponding to (y,x) if cube=False, else 3D array corresponding to (nz,y,x)
        
        .. Kwargs:
            
            * cube    -> 2D array or 3D array cube.'''

        if cube:
            if xin.shape[0] != datain.shape[2]:
                raise ValueError('Shapes of datain and x do not match')

            if yin.shape[0] != datain.shape[1]:
                raise ValueError('Shapes of datain and y do not match')

        else:
            if xin.shape[0] != datain.shape[1]:
                raise ValueError('Shapes of datain and x do not match')

            if yin.shape[0] != datain.shape[0]:
                raise ValueError('Shapes of datain and y do not match')

        if xin[-1] < xin[0]:
            raise ValueError('Array x not sorted')

        if yin[-1] < yin[0]:
            raise ValueError('Array y not sorted')

        self.xin = xin.copy()
        self.yin = yin.copy()

        delx = xin[1:] - xin[0:-1]
        dely = yin[1:] - yin[0:-1]

        if max(delx)-min(delx) < 1.e-4 and max(dely)-min(dely) < 1.e-4:
            self.regular = True
        else:
            self.regular = False

        self.xinlist = self.xin.tolist()
        self.yinlist = self.yin.tolist()
        self.nx = len(self.xinlist)
        self.ny = len(self.yinlist)
        self.cube = cube
        self.zin = datain.copy()


    def __call__(self,xi,yi,iz=0):
        '''Function call to actually interpolate.'''
        if xi.shape != yi.shape:
            raise ValueError('xi and yi must have same shape.')

        if self.regular:
            xcoords = (self.nx-1)*(xi-self.xin[0])/(self.xin[-1]-self.xin[0])
            ycoords = (self.ny-1)*(yi-self.yin[0])/(self.yin[-1]-self.yin[0])
        else:
            xiflat = xi.flatten()
            yiflat = yi.flatten()
            ix = (np.searchsorted(self.xin,xiflat)-1).tolist()
            iy = (np.searchsorted(self.yin,yiflat)-1).tolist()
            xiflat = xiflat.tolist()
            yiflat = yiflat.tolist()

            xin = self.xinlist
            yin = self.yinlist
                
            xcoords = []
            ycoords = []
            for n,i in enumerate(ix):
                if i < 0:
                    xcoords.append(-1)
                elif i >= self.nx-1:
                    xcoords.append(self.nx)
                else:
                    xcoords.append(float(i)+(xiflat[n]-xin[i])/(xin[i+1]-xin[i]))
            for m,j in enumerate(iy):
                if j < 0:
                    ycoords.append(-1)
                elif j >= self.ny-1:
                    ycoords.append(self.ny)
                else:
                    ycoords.append(float(j)+(yiflat[m]-yin[j])/(yin[j+1]-yin[j]))

            xcoords = np.reshape(xcoords, xi.shape)
            ycoords = np.reshape(ycoords, yi.shape)

        xcoords = np.clip(xcoords,0,self.nx-1)
        ycoords = np.clip(ycoords,0,self.ny-1)

        xint = xcoords.astype(np.int32)
        yint = ycoords.astype(np.int32)
        xip1 = np.clip(xint+1,0,self.nx-1)
        yip1 = np.clip(yint+1,0,self.ny-1)

        delx = xcoords - xint.astype(np.float32)
        dely = ycoords - yint.astype(np.float32)

        zin = self.zin
        if self.cube:
            dataout = (1.-delx)*(1.-dely)*zin[iz,yint,xint] + \
                      delx*dely*zin[iz,yip1,xip1] + \
                      (1.-delx)*dely*zin[iz,yip1,xint] + \
                      delx*(1.-dely)*zin[iz,yint,xip1]
        else:
            dataout = (1.-delx)*(1.-dely)*zin[yint,xint] + \
                      delx*dely*zin[yip1,xip1] + \
                      (1.-delx)*dely*zin[yip1,xint] + \
                      delx*(1.-dely)*zin[yint,xip1]

        return dataout



        




############################################################
# Program is part of PyAPS                                 #
# Copyright 2012, by the California Institute of Technology#
# Contact: earthdef@gps.caltech.edu                        #
############################################################
