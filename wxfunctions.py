from math import *

def gpspwv(zwd,zhd,p,pmeasht,t,tmeasht,kappa,lat,gpshtm):
    newzwd=zwd+zhd-2.2768e-3*movepres(p,pmeasht,gpshtm)/(1-0.00266*cos(2*d2r(lat))-0.00000028*gpshtm)
    iwv=1000*newzwd/kappa(t,tmeasht,gpshtm)
    return iwv

def kappa(t,tmeashtm,gpshtm):
    return 1/(1e-5*(3.776e5/(70.2+0.72*movetemp(t,tmeashtm,gpshtm))+17)*461.518)

def zhdsaasta(pmbar,lat,hgtm):
    #zhd is in cm
    return 0.22765*pmbar/(1-0.00266*cos(2*radians(lat))-0.00000028*hgtm)

def pw2zwd(iwv,t):
    return iwv/kappa(t,0,0);

def d2r(d):
    return d*3.14159265/180

def movepres(p,pmeashtm,newhtm,Hscale):
    return p*exp((pmeashtm-newhtm)/Hscale)

def movetemp(t,tmeashtm,newhtm):
    return t-(tmeashtm-newhtm)*.0065

def movepw(pw,pwmeashtm,newhtm,Wscale):
    return pw*exp((pwmeashtm-newhtm)/Wscale)

