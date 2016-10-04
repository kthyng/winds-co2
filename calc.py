'''
Read in files, interpolate to points we want
'''

import requests
import netCDF4 as netCDF
import pandas as pd
import xarray as xr
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os


# load in Andrea's lat/lon/time data
filename = 'GoM_combined_data.txt'
# Ran the following once to get the nco2 value. This won't change unless this
# analysis is repeated in the future once the file has changed
# nco2 = len(open(filename).readlines()) - 1  # number of data rows (minus header)
nco2 = 651558
# reading in a chunk of rows at a time
# while (nco2)
nrows = 2
df = pd.read_table(filename, header=0, usecols=[3, 4, 5, 6],
                   parse_dates=[[0, 1]], index_col=[0], nrows=nrows)

fnamewlocs = 'windfilelocs.txt'
# if need the file names, search for them. Otherwise load names in from file.
if not os.path.exists(fnamewlocs.split('.')[0] + '.npz'):
    # open up and search for links on website
    wfiles = []  # initialize list of wind file addresses
    wtimes = []
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
                    for j in range(4):  # 4 times a day
                        wtimes.append(datetime(year, month, day, 6*j))
                else:  # don't save the monthly data file
                    continue
    np.savez(fnamewlocs.split('.')[0], wfiles=wfiles, wtimes=wtimes)
else:
    wfile = np.load(fnamewlocs.split('.')[0] + '.npz')
    wfiles = wfile['wfiles']
    wtimes = wfile['wtimes']
    wfile.close()


# loop through times to get files
for t, lat, lon in df.itertuples():  # iterates through rows with each row as a tuple
    print(t, lat, lon)
    it = np.where(wtimes<t)[0][-1]  # index in wind times that is just before co2 data
    fname = wfiles[int(it/4.)]  # file to use to get wind out for this co2 measurement
    # Find correct file to use
    # open and read file
    # loc = 'ftp://ftp2.remss.com/ccmp/v02.0/Y2000/M01/CCMP_Wind_Analysis_20000101_V02.0_L3.0_RSS.nc'
    # r = requests.get(loc)
    os.system('wget ' + fname)

    # read into xarray
    ccmp = xr.open_dataset(loc)

    #

# delete file
