import math

def latlondist(latA,latB,lonA,lonB):
    a = math.sin(float(latB)*math.pi/360-float(latA)*math.pi/360)**2+math.cos(float(latA)*math.pi/180)*math.cos(float(latB)*math.pi/180)*math.sin(float(lonB)*math.pi/360-float(lonA)*math.pi/360)**2;
    dist = 2*6371*math.atan2(math.sqrt(a),math.sqrt(1-a));
    return dist

def d2r(d):
    return d*3.14159265/180

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * atan2(math.sqrt(a), math.sqrt(1-a))
    m = 1000*6367 * c
    return m

