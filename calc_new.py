'''
Read in files, interpolate to points we want
'''

import requests
# import netCDF4 as netCDF
# import pandas as pd
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
# import scipy.interpolate


# load in Andrea's lat/lon/time data
# filename = 'GoM_combined_data.txt'  # this was the original file
# Ran the following once to get the nco2 value. This won't change unless this
# analysis is repeated in the future once the file has changed
# nco2 = len(open(filename).readlines()) - 1  # number of data rows (minus header)
# nco2 = 651558
# reading in a chunk of rows at a time
# while (nco2)
# nrows = 2
# df = pd.read_table(filename, header=0, usecols=[3, 4, 5, 6],
#                    parse_dates=[[0, 1]], index_col=[0], nrows=nrows)

# # Use the following to update through 2018
# filename = 'For_kristen.txt'
# df = pd.read_table('For_kristen.txt', parse_dates=[[0,1,2,3,4,5]], index_col=0)
# index = [pd.Timestamp.strptime(df.index[i], '%Y %m %d %H %M %S') for i in range(len(df))]
# df.index = index
# df.index.rename('Dates', inplace=True)

# Use the following to update through 2018
filename = 'all_t_lat_lon.csv'
df = pd.read_csv(filename, parse_dates=True, index_col=0)

fnamewlocs = 'windfilelocs_all'
# if need the file names, search for them. Otherwise load names in from file.
if not os.path.exists(fnamewlocs + '.npz'):
    # open up and search for links on website
    wfiles = []  # initialize list of wind file addresses
    wdates = []
    baseloc = 'http://data.remss.com/ccmp/v02.0/'
    # directory of years
    # returns a "response" object from the website, then give the text content of that response
    restext = requests.get(baseloc).text
    soup = BeautifulSoup(restext, "lxml")  # interprets the text from the website
    yearrows = soup.findAll('a')[1:]
    for yearrow in yearrows:
        if len(yearrow.string) > 5:
            continue
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
          'urcrnrlon': lonmax, 'urcrnrlat': latmax, 'lat_0': latmin,
          'lon_0': lonmin, 'resolution': 'i', 'area_thresh': 0.}
proj = pyproj.Proj(projinputs)

# link wind file dates and file names togetherin this dataframe
windfiles = pd.DataFrame(index=wdates, data={'wfiles': wfiles})

# loop through times to get files
windsfilename = 'winds_all'#.npz'
df['mean wind for day [m/s]'] = np.nan
if not os.path.exists(windsfilename + '.csv'):
    nloops = 0
    # loop over just the days since there is a file per day
    # treat all rows from a single day as the same since averaging over the
    # winds for the day
    for day in df.index.normalize().unique().sort_values():

        fname = windfiles.loc[day,'wfiles']

        # print file name to use this loop (1 day of dates)
        print('\n' + fname.split('/')[-1] + '\n')

        # retrieve file
        os.system('wget ' + fname)

        # read in file
        ccmp = netCDF.Dataset(fname.split('/')[-1])

        if nloops == 0:
            # Since this is the first file, deal with projecting the lat/lon values
            longitude = ccmp['longitude'][:] - 180
            ilon = np.where((lonmin < longitude) * (longitude < lonmax))[0]
            longitude = longitude[ilon]
            latitude = ccmp['latitude'][:]
            ilat = np.where((latmin < latitude) * (latitude < latmax))[0]
            latitude = latitude[ilat]
            Lon, Lat = np.meshgrid(longitude, latitude)
            X, Y = proj(Lon, Lat)  # wind locations
            dx = X.max() - X.min()
            dy = Y.max() - Y.min()
            # get array of indices
            iLon, iLat = np.meshgrid(ilon, ilat)
            nloops += 1

        # average the winds over the day
        uwnd = abs(ccmp['uwnd'][:]).mean(axis=0)
        uwnd = uwnd[iLat, iLon]
        vwnd = abs(ccmp['vwnd'][:]).mean(axis=0)
        vwnd = vwnd[iLat, iLon]

        # pull out lat/lon for each row that is today
        rows = df.index.normalize()==day
        lons = df[rows]['LONG_DEC_DEGREE']
        lats = df[rows]['LAT_DEC_DEGREE']

        # do interpolation
        # xp/yp locations in grid space for map_coordinates function
        xp, yp = proj(lons.values, lats.values)  # data point, where we want to calculate wind
        xg = (xp/dx)*X.shape[1]
        yg = (yp/dy)*Y.shape[0]
        wu = map_coordinates(uwnd, np.array([yg.flatten(), xg.flatten()]))
        wv = map_coordinates(vwnd, np.array([yg.flatten(), xg.flatten()]))
        df.loc[rows,'mean wind for day [m/s]'] = np.sqrt(wu**2 + wv**2)

        # close old file
        ccmp.close()
        # delete old file
        os.system('rm ' + fname.split('/')[-1])

    df.to_csv(windsfilename + '.csv')
