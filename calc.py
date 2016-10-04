'''
Read in files, interpolate to points we want
'''

import requests
import netCDF4 as netCDF
import pandas as pd
# import xarray as xr
import netCDF4 as netCDF
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
import bisect
import pyproj
from scipy.ndimage import map_coordinates
import matplotlib.pyplot as plt
import cmocean.cm as cmo
import numpy as np
import scipy.interpolate


# load in Andrea's lat/lon/time data
filename = 'GoM_combined_data.txt'
# Ran the following once to get the nco2 value. This won't change unless this
# analysis is repeated in the future once the file has changed
# nco2 = len(open(filename).readlines()) - 1  # number of data rows (minus header)
# nco2 = 651558
# reading in a chunk of rows at a time
# while (nco2)
# nrows = 2
# df = pd.read_table(filename, header=0, usecols=[3, 4, 5, 6],
#                    parse_dates=[[0, 1]], index_col=[0], nrows=nrows)

# read in from file
dates = []
lats = []
lons = []
lines = open(filename).readlines()
for i, line in enumerate(lines[1:]):
    # print(line)
    year = int(line.split('\t')[3].split('/')[2])
    if year < 20:
        year += 2000
    elif year > 60:
        year += 1900
    month = int(line.split('\t')[3].split('/')[0])
    day = int(line.split('\t')[3].split('/')[1])
    # ht = line.split('\t')[4].split(':')[0]
    # if np.isnan(float(ht)):
    #     print(i, year, month, day, ht)
    #     print(line)
    #     break
    #
    # minute = int(line.split('\t')[4].split(':')[1])
    # second = int(line.split('\t')[4].split(':')[2])
    lat = float(line.split('\t')[5])
    lon = float(line.split('\t')[6])
    dates.append(datetime(year, month, day))
    lats.append(lat)
    lons.append(lon)
isort = np.argsort(dates)
dates = np.asarray(dates)[isort]
lons = np.asarray(lons)[isort]
lats = np.asarray(lats)[isort]

fnamewlocs = 'windfilelocs.txt'
# if need the file names, search for them. Otherwise load names in from file.
if not os.path.exists(fnamewlocs.split('.')[0] + '.npz'):
    # open up and search for links on website
    wfiles = []  # initialize list of wind file addresses
    wdates = []
    # baseloc = 'ftp://ftp2.remss.com/ccmp/v02.0/'
    baseloc = 'http://data.remss.com/ccmp/v02.0/'
    # directory of years
    # returns a "response" object from the website, then give the text content of that response
    restext = requests.get(baseloc).text
    soup = BeautifulSoup(restext, "lxml")  # interprets the text from the website
    yearrows = soup.findAll('a')[1:]
    for yearrow in yearrows:
        year = int(yearrow.string[1:])  # year as a number
        yearloc = baseloc + yearrow.string
        # directory of months for a year
        restext = requests.get(yearloc).text  # access text on new website
        soup = BeautifulSoup(restext, "lxml")  # open up page for a day
        monthrows = soup.findAll('a')[1:]

        for monthrow in monthrows:
            month = int(monthrow.string[1:])  # month as a number
            monthloc = yearloc + '/' + monthrow.string
            # directory of days for a month for a year
            restext = requests.get(monthloc).text  # access text on new website
            soup = BeautifulSoup(restext, "lxml")  # open up page for a day
            dayrows = soup.findAll('a')[1:]

            for dayrow in dayrows:
                dayloc = monthloc + '/' + dayrow.string
                if len(dayrow.string.split('_')[3]) > 6:
                    day = int(dayrow.string.split('_')[3][6:])  # day as a number
                    wfiles.append(dayloc)
                    # for j in range(4):  # 4 times a day
                    wdates.append(datetime(year, month, day))
                else:  # don't save the monthly data file
                    continue
    np.savez(fnamewlocs.split('.')[0], wfiles=wfiles, wdates=wdates)
else:
    wfile = np.load(fnamewlocs.split('.')[0] + '.npz')
    wfiles = wfile['wfiles']
    wdates = wfile['wdates']
    wfile.close()

lonmin = -99
lonmax = -79
latmin = 17
latmax = 33
projinputs = {'proj': 'lcc', 'llcrnrlon': lonmin, 'llcrnrlat': latmin,
          'urcrnrlon': lonmax, 'urcrnrlat': latmax, 'lat_0': 30,
          'lon_0': -94, 'resolution': 'i', 'area_thresh': 0.}
proj = pyproj.Proj(projinputs)

# loop through times to get files
winds = []
# for t, lat, lon in df.itertuples():  # iterates through rows with each row as a tuple
for i, (date, lat, lon) in enumerate(zip(dates[:2], lats[:2], lons[:2])):
    xp, yp = proj(lon, lat)  # data point, where we want to calculate wind
    if i == 0:
        # keep a date around that only bumps up when the data date changes
        datesave = date
        it = bisect.bisect_left(wdates, date)  # index in wind times that equals co2 data time
        fname = wfiles[it]  # file to use to get wind out for this co2 measurement
        # download file
        # os.system('wget ' + fname)
        # read in file
        ccmp = netCDF.Dataset(fname.split('/')[-1])
        # Since this is the first file, deal with projecting the lat/lon values
        longitude = ccmp['longitude'][:] - 180
        ilon = np.where((lonmin < longitude) * (longitude < lonmax))[0]
        longitude = longitude[ilon]
        latitude = ccmp['latitude'][:]
        ilat = np.where((latmin < latitude) * (latitude < latmax))[0]
        latitude = latitude[ilat]
        Lon, Lat = np.meshgrid(longitude, latitude)
        X, Y = proj(Lon, Lat)  # wind locations
        # get array of indices
        iLon, iLat = np.meshgrid(ilon, ilat)
        # average the winds over the day
        uwnd = ccmp['uwnd'][:].mean(axis=0)
        uwnd = uwnd[iLat, iLon]
        vwnd = ccmp['vwnd'][:].mean(axis=0)
        vwnd = vwnd[iLat, iLon]
        # set up interpolators
        fu = scipy.interpolate.interp2d(X, Y, uwnd)
        fv = scipy.interpolate.interp2d(X, Y, vwnd)
        plt.pcolormesh(longitude, latitude, vwnd, cmap=cmo.speed)

    else:
        # compare with datesave to see if a new file is needed
        if date == datesave:
            # use file from before
            pass
        else:
            import pdb; pdb.set_trace()

            # close old file
            ccmp.close()
            # delete old file
            os.system('rm ' + fname)
            # update datesave
            datesave = date
            # read in and use new file
            it = bisect.bisect_left(wdates, date)  # index in wind times that equals co2 data time
            fname = wfiles[it]  # file to use to get wind out for this co2 measurement
            # download file
            os.system('wget ' + fname)
            # read in file
            ccmp = netCDF.Dataset(fname.split('/')[-1])
            # average the winds over the day
            uwnd = ccmp['uwnd'][:].mean(axis=0)
            uwnd = uwnd[iLat, iLon]
            vwnd = ccmp['vwnd'][:].mean(axis=0)
            vwnd = vwnd[iLat, iLon]
            # set up interpolators
            fu = scipy.interpolate.interp2d(X, Y, uwnd)
            fv = scipy.interpolate.interp2d(X, Y, vwnd)

    # do interpolation
    wu = fu(xp, yp)
    wv = fv(xp, yp)
    winds.extend(np.sqrt(wu**2 + wv**2))

    # check: new winds entry should look right when overlaid on wind data
    plt.scatter(lon, lat, s=100, c=wv, cmap=cmo.speed, vmin=vwnd.min(), vmax=vwnd.max())
    import pdb; pdb.set_trace()
