'''
Read in files, interpolate to points we want
'''

# import requests
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
          'urcrnrlon': lonmax, 'urcrnrlat': latmax, 'lat_0': latmin,
          'lon_0': lonmin, 'resolution': 'i', 'area_thresh': 0.}
proj = pyproj.Proj(projinputs)

# loop through times to get files
windsfilename = 'winds.npz'
if not os.path.exists(windsfilename):
    winds = []
    # for t, lat, lon in df.itertuples():  # iterates through rows with each row as a tuple
    for i, (date, lat, lon) in enumerate(zip(dates, lats, lons)):
        xp, yp = proj(lon, lat)  # data point, where we want to calculate wind
        if i == 0:
            # keep a date around that only bumps up when the data date changes
            datesave = date
            it = bisect.bisect_left(wdates, date)  # index in wind times that equals co2 data time
            fname = wfiles[it]  # file to use to get wind out for this co2 measurement
            print('\n' + str(i) + ': ' + fname.split('/')[-1] + '\n')
            # download file
            if not os.path.exists(fname.split('/')[-1]):
                os.system('wget ' + fname)
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
            dx = X.max() - X.min()
            dy = Y.max() - Y.min()
            # get array of indices
            iLon, iLat = np.meshgrid(ilon, ilat)
            # average the winds over the day
            uwnd = ccmp['uwnd'][:].mean(axis=0)
            uwnd = uwnd[iLat, iLon]
            vwnd = ccmp['vwnd'][:].mean(axis=0)
            vwnd = vwnd[iLat, iLon]
            # plt.pcolormesh(longitude, latitude, uwnd, cmap=cmo.speed); plt.colorbar()
            # plt.pcolormesh(longitude, latitude, vwnd, cmap=cmo.speed); plt.colorbar()

        else:
            # compare with datesave to see if a new file is needed
            if date == datesave:
                # use file from before
                pass
            else:
                # import pdb; pdb.set_trace()

                # close old file
                ccmp.close()
                # delete old file
                os.system('rm ' + fname.split('/')[-1])
                # update datesave
                datesave = date
                # read in and use new file
                it = bisect.bisect_left(wdates, date)  # index in wind times that equals co2 data time
                fname = wfiles[it]  # file to use to get wind out for this co2 measurement
                print('\n' + str(i) + ': ' + fname.split('/')[-1] + '\n')
                np.savetxt('winds.txt', winds)
                # download file
                if not os.path.exists(fname.split('/')[-1]):
                    os.system('wget ' + fname)
                # read in file
                ccmp = netCDF.Dataset(fname.split('/')[-1])
                # average the winds over the day
                uwnd = ccmp['uwnd'][:].mean(axis=0)
                uwnd = uwnd[iLat, iLon]
                vwnd = ccmp['vwnd'][:].mean(axis=0)
                vwnd = vwnd[iLat, iLon]

        # do interpolation
        # xp/yp locations in grid space for map_coordinates function
        xg = (xp/dx)*X.shape[1]
        yg = (yp/dy)*Y.shape[0]
        wu = map_coordinates(uwnd, np.array([[yg, xg]]).T)
        wv = map_coordinates(vwnd, np.array([[yg, xg]]).T)
        winds.extend(np.sqrt(wu**2 + wv**2))
        # np.savez('winds.npz', winds=winds)
        # print( xg, yg, wu, wv, winds[i])

        # check: new winds entry should look right when overlaid on wind data
        # plt.scatter(lon, lat, s=100, c=wu, cmap=cmo.speed, vmin=uwnd.min(), vmax=uwnd.max())
        # plt.scatter(lon, lat, s=100, c=wv, cmap=cmo.speed, vmin=vwnd.min(), vmax=vwnd.max(),
        #             edgecolors=None)
    # plt.savefig('uwnd.png', bbox_inches='tight')
    # plt.savefig('vwnd.png', bbox_inches='tight')
        # import pdb; pdb.set_trace()
    np.savez(windsfilename, winds=winds)
else:
    winds = np.load(windsfilename)['winds']



# Write winds back to original file in the correct order
fin = open(filename, 'r')
fout = open(filename.split('.')[0] + '_winds.txt', 'w')
lines = fin.readlines()
# loop over sorting indices to get the columns in the right row together
for i, isor in enumerate(isort):
    isor += 1  # need to shift by the header line
# for i, line in enumerate(lines):
    if i == 0:
        fout.write(lines[0])
    else:
        # need to use isort indices for lines but not for winds since winds are
        # already sorted by time
        towrite = lines[isor].split('\t')[:18]
        towrite.append(str(winds[i]))
        towrite.extend(lines[isor].split('\t')[19:])
        towrite = '\t'.join(towrite)
        # print(towrite)
        fout.write(towrite)
        # fout.write(lines[isor].split('\t')[:18], winds[i-1], lines[isor].split('\t')[19:])
fout.close()
fin.close()
