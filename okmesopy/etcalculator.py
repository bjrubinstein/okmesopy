# etcalculator.py
#
# Abhiram Pamula (apamula@okstate.edu)
# Ben Rubinstein (brubinst@hawk.iit.edu)
#
# adapted from PyHSPF by David Lampert (https://github.com/djlampert/PyHSPF)
#
# last updated: 03/20/2023
#
# contains methods to calculate reference evapotranspiration

import datetime
import numpy as np

class ETCalculator:
    '''
    The ETCalculator class contains methods to calculate reference
        evapotranspiration using the Penman-Monteith Equation
        https://www.fao.org/3/x0490e/x0490e06.htm
    '''

    def __init__(self, verbose=False, timestep=60):
        '''
        Init method for ETCalculator class
        
        arguments:
            verbose (bool): if true write detailed debugging to stdout
            timestep (int or str): the time interval to use in minutes; must be
                hourly, daily, or a multiple of 5 AND factor of 60. Hourly or
                daily timesteps can be entered as 'hourly' or 60 or 'daily' or
                1440
        '''
        self.verbose = verbose

        # validate the step size
        if timestep == 'daily' or timestep == 1440: timestep = 1440
        elif timestep == 'hourly' or timestep == 60: timestep = 60
        elif timestep < 5:
            if self.verbose:
                print('{} was given as step size but it must be at least 5'
                      ' minutes. A step size of 5 minutes will be used'
                      ' instead'.format(timestep))
            timestep = 5
        elif timestep%5 != 0 and 60%timestep != 0:
            if self.verbose:
                msg = ('Error: step size was given as {}. Valid time steps are'
                       ' hourly, daily, or a factor of 60 that is also a'
                       ' multiple of 5.')
                raise ValueError(msg)
        self.timestep = timestep

        # Dictionary to hold required climate data, varies depending of if we
        # are working with hourly/fractional hourly or daily data
        if timestep == 1440:
            self.data = {
                'tmin':        None,
                'tmax':        None,
                'dewpoint':    None,
                'wind':        None,
                'solar':       None,
                }
        else:
            self.data = {
                'temperature': None,
                'dewpoint':    None,
                'wind':        None,
                'solar':       None,
                }

        # location
        self.longitude = None
        self.latitude  = None
        self.elevation = None


    def add_location(self, latitude, longitude, elevation):
        '''
        Adds location information, required for some calculations
        
        arguments:
            longitude (float): longitude in degrees
            latitude (float): latitude in degrees
            elevation (float): elevation in meters
        '''

        self.longitude = longitude
        self.latitude  = latitude
        self.elevation = elevation


    def add_timeseries(self, tstype, timestep, start, values):
        '''
        Adds a timeseries to use for ET calculations
        
        arguments:
            tstype (str): the type of data being given, must match one of the
                keys in the self.data dictionary
                (temperature, dewpoint, humidity, wind, solar, RET)
            timestep (int or str): the interval in minutes between datapoints,
                must match the one given when initializing ETCalculator
            start (datetime): the datetime for the first datapoint in the
                timeseries
            values (list): a list of values for the measured data
        '''
        if timestep == 'daily': timestep = 1440
        elif timestep == 'hourly': timestep = 60
        # validate the timestep
        if not timestep == self.timestep:
            print('Warning: the timestep for this series ({}) does not match'
                  ' the timestep of this calculator ({}). The timeseries will'
                  ' not be added.'.format(timestep,self.timestep))
            return

        # validate the type of timeseries
        if tstype not in self.data:
            print('Warning: unknown time series type {} specified'.format(tstype))
            print('valid choices are ' + ', '.join(self.data) + '. The'
                  ' timeseries will not be added.')
            return

        self.data[tstype] = start, values


    def rad(self, d): 
        '''
        Converts degrees to radians

        arguments:
            d (float): angle in degrees

        returns:
            float: angle in radians
        '''

        return (np.pi / 180 * d)


    def atmosphere_pressure(self):
        '''
        Estimates the atmospheric pressure (kPa) from the elevation (m) using a 
            simplified ideal gas law.

        returns:
            float: estimate atmospheric pressure in kPa
        '''

        if self.elevation is None:
            raise RuntimeError('Elevation not specified. Use add_location()'
                               ' to define the location.')

        return 101.3 * ((293.0 - 0.0065 * self.elevation) / 293.0)**5.26


    def vapor_pressure(self, temp):
        '''
        Estimates the water vapor pressure (kPa) at a given temperature (C).

        arguments:
            T (float): temperature in C

        returns:
            float: water vapor pressure in kPa
        '''

        return 0.6108 * np.exp((17.27 * temp) / (temp + 237.3))


    def wind_correction(self, u1, z = 10):
        '''
        Estimates the wind speed at z = 2 m from the wind speed at height z 
            Mesonet records wind speed at both 2 and 10 meters, this allows the
            user to choose which to use

        arguments:
            u1 (float): wind speed at z meters in m/s
            z (float): height of the measurement in meters

        returns:
            float: estimated wind speed at 2 meters
        '''

        # note that at z = 2 the multiplier is 1.000 ~ 1
        return u1 * 4.87 / np.log(67.8 * z - 5.42)


    def get_soil(self, times, Gday, Gnight):
        '''
        Provides an array of the values of the soil heat flux if a list is 
        provided, otherwise just provides the appropriate day or night value.

        arguments:
            times (list): list of datetime.datetime instances
            Gday (float): soil heat flux during the day in MJ/m2/hour
            Gnight (float): soil heat flux during the night in MJ/m2/hour

        returns:
            list(float): list of heat flux values
        '''

        Gd = np.array([Gday if t else Gnight 
                          for t in self.is_daytime(times)])

        return Gd


    def get_Cd(self, times, Cday, Cnight):
        '''
        Provides an array of the values denominator coefficient if a list is 
        provided, otherwise just provides the appropriate day or night value.

        arguments:
            times (list): list of datetime.datetime instances
            Cday (float): daytime denominator coefficient
            Cnight (float): nighttime denominator coefficient

        returns:
            list(float): list of heat flux values
        '''

        Cd = np.array([Cday if t else Cnight 
                          for t in self.is_daytime(times)])
        return Cd


    def time_round(self, d):
        """Rounds a datetime.datetime instance to the nearest hour."""

        yr, mo, da, hr, mi = d.timetuple()[:5]

        if 30 <= d.minute:  # round to the next hour

            r = (datetime.datetime(yr, mo, da, hr) + 
                 datetime.timedelta(hours = 1))

        else:

            r = datetime.datetime(yr, mo, da, hr)

        return r


    def sun(self, time, zenith = 90.83, nearest_hour = False):
        '''
        Estimates the sunrise and sunset time for a given latitude, longitude,
            and date and optionally rounds it to the nearest hour. Algorithm
            is derived from "Almanac for Computers," 1990, Nautical Almanac,
            Office United States Naval Observatory, Washington DC 20392.

        arguments:
            time (datetime): the date to check sunrise and sunset for
            zenith (float): sun's zenith distance at a certain time, 90°50' for
                sunrise/sunset (see p. B6 of the reference)
            nearest_hour (bool): whether or not to round the times to the
                nearest hour

        returns:
            tuple (datetime): a pair of datetime.datetime objects in the form
                (sunrise, sunset)
        '''

        # calculate day of the year

        N = time.timetuple().tm_yday

        # convert longitude to hour value and calculate approximate time

        hour = self.longitude / 15

        # rise

        t = N + (6 - hour) / 24

        # calculate mean anomaly

        M = (360 / 365.25 * t) - 3.289

        # calculate sun's true longitude

        L = (M + 1.916 * np.sin(self.rad(M)) + 
             (0.02 * np.sin(2 * self.rad(M))) + 282.634)

        # adjust into 0, 360 range

        if L < 0:   L+=360
        if L > 360: L-=360
             
        # calculate right ascension

        RA = 180 / np.pi * np.arctan(0.91764 * np.tan(self.rad(L)))

        # ensure RA is in the same quadrant as L

        Lquadrant  = (np.floor(L  / 90)) * 90
        RAquadrant = (np.floor(RA / 90)) * 90

        RA = RA + (Lquadrant - RAquadrant)

        # convert to hours

        RA = RA / 15

        # calculate the solar declination

        sinDec = 0.39782 * np.sin(self.rad(L))
        cosDec = np.cos(np.arcsin(sinDec))

        # calculate the solar local hour angle

        cosH = ((np.cos(self.rad(zenith)) - sinDec * 
                 np.sin(self.rad(self.latitude))) / 
                (cosDec * np.cos(self.rad(self.latitude))))

        # rise

        H = 360 - 180 / np.pi * np.arccos(cosH)

        H = H / 15

        # calculate local mean time of rising

        T = H + RA - 0.06571 * t - 6.622

        # adjust back to UTC

        UT = T - hour

        # adjust to local time zone (this is not super accurate, but for the 
        # purposes of ET estimation really doesn't warrant detailed estimation)

        offset = round(self.longitude / 15)

        # daily saving time

        if time.month < 3 or 10 < time.month: offset -= 1

        localT = UT + offset

        # adjust to [0, 24] as needed

        if localT < 0:  localT += 24
        if localT > 24: localT -= 24
            
        t = datetime.timedelta(hours = localT)

        sunrise = ':'.join(str(t).split(':')[:2])

        sunrise = datetime.datetime(*time.timetuple()[:3]) + t

        # now do sunset

        t = N + (18 - hour) / 24

        # calculate mean anomaly

        M = (360 / 365.25 * t) - 3.289

        # calculate sun's true longitude

        L = (M + 1.916 * np.sin(self.rad(M)) + 
             (0.02 * np.sin(2 * self.rad(M))) + 282.634)

        # adjust into 0, 360 range

        if L < 0:   L+=360
        if L > 360: L-=360
             
        # calculate right ascension

        RA = 180 / np.pi * np.arctan(0.91764 * np.tan(self.rad(L)))

        # ensure RA is in the same quadrant as L

        Lquadrant  = (np.floor(L  / 90)) * 90
        RAquadrant = (np.floor(RA / 90)) * 90

        RA = RA + (Lquadrant - RAquadrant)

        # convert to hours

        RA = RA / 15

        # calculate the solar declination

        sinDec = 0.39782 * np.sin(self.rad(L))
        cosDec = np.cos(np.arcsin(sinDec))

        # calculate the solar local hour angle

        cosH = ((np.cos(self.rad(zenith)) - sinDec * 
                 np.sin(self.rad(self.latitude))) / 
                (cosDec * np.cos(self.rad(self.latitude))))

        # set

        H = 180 / np.pi * np.arccos(cosH) / 15

        # calculate local mean time of rising

        T = H + RA - 0.06571 * t - 6.622

        # adjust back to UTC

        UT = T - hour

        # adjust to local time zone

        localT = UT + offset

        # adjust to [0, 24] as needed

        if localT < 0:  localT += 24
        if localT > 24: localT -= 24
            
        t = datetime.timedelta(hours = localT)

        sunset = ':'.join(str(t).split(':')[:2])

        sunset = datetime.datetime(*time.timetuple()[:3]) + t

        if nearest_hour: 
            
            sunrise, sunset = self.time_round(sunrise), self.time_round(sunset)

        return sunrise, sunset


    def is_daytime(self, times):
        '''
        Determines whether the sun is up or not for each values in "times"

        arguments:
            times (list): list of datetime.datetime instances to check

        returns:
            list (bool): a list of boolean values where true means the sun is
                up
        '''

        sunrise, sunset = zip(*[self.sun(t) for t in times])

        return [r <= t and t < s for t, r, s in zip(times, sunrise, sunset)]


    def daily_radiation(self, times, solar, Tmin, Tmax, Pv, albedo = 0.23,
                        sigma = 4.903e-9,):
        '''
        Estimates the net radiation (MJ/m2/day) from the measured downwelling
            radiation, min/max temperature, and vapor pressure

        arguments:
            times (list): list of datetime.datetime instances
            solar (list): measured solar radiation in MJ/m2/hour (as floats);
                R_s in the ASCE document
            Tmin (float): daily minimium temperature in K
            Tmax (float): daily maximum temperature in K
            Pv (float): vapor pressure in kPa
            albedo (float): assumed value typical for grass
            sigma (float): Boltzmann constant in MJ/m2/day

        returns:
            list (float): time series of net solar radiation
        '''

        # make sure the location has been supplied

        location = self.longitude, self.latitude, self.elevation

        if any([l is None for l in location]):
            print('error: location has not been specified\n')
            raise

        # convert the dates to julian days

        julian = np.array([t.timetuple().tm_yday for t in times])

        # calculate the solar declination (rad)

        sd = 23.45 * self.rad(np.cos(2 * np.pi / 365 * (julian - 172)))

        # calculate the inverse relative distance Earth-Sun

        irl = 1 + 0.033 * np.cos(2 * np.pi / 365 * julian)

        # calculate the hour angle at sunset (rad)

        sha = np.arccos(-np.tan(self.rad(self.latitude)) *
                           np.tan(sd))

        # calculate the extraterrestrial radiation

        et_rad = 37.59 * irl * (sha *
                                np.sin(self.rad(self.latitude))
                                * np.sin(sd) +
                                np.cos(self.rad(self.latitude)) *
                                np.cos(sd) * np.sin(sha))

        # calculate the clear day solar radiation

        clear = (0.00002 * self.elevation + 0.75) * et_rad

        # shortwave radiation

        Rns = solar * (1 - albedo)

        # longwave radiation

        Rnl = (sigma * 0.5 * (Tmin**4 + Tmax**4) *
               (0.34 - 0.139 * np.sqrt(Pv)) *
               (1.35 * solar / clear - 0.35))

        return Rns - Rnl


    def hourly_radiation(self, times, solar, T, Pv, albedo = 0.23,
                         sigma = 2.042e-10, Gsc = 4.92):
        '''
        Estimates the net radiation (MJ/m2/hour) from the measured downwelling
            radiation, temperature, and vapor pressure

        arguments:
            times (list): list of datetime.datetime instances
            solar (list): measured solar radiation in MJ/m2/hour (as floats);
                R_s in the ASCE document
            T (float): average temperature in K
            Pv (float): vapor pressure in kPa
            albedo (float): assumed value typical for grass
            sigma (float): Boltzmann constant in MJ/m2/hour
            Gsc (float): solar constant in MJ/m2/hour

        returns:
            list (float): time series of net solar radiation
        '''

        # time step in hours
        t1 = self.timestep / 60

        # convert dates to julian days

        julian  = np.array([t.timetuple().tm_yday for t in times])
        ts      = np.array([t.timetuple().tm_hour for t in times])
        tm      = np.array([t.timetuple().tm_min for t in times])

        # calculate the solar declination (rad)

        d = self.rad(0.409 * np.cos(2 * np.pi / 365 * julian - 1.39))

        # calculate the inverse relative distance factor

        dr = 1 + 0.033 * np.cos(2 * np.pi / 365 * julian)

        # calculate the seasonal correction for solar time

        b  = 2 * np.pi * (julian - 81) / 364
        Sc = (0.1645 * np.sin(2 * b) - 0.1255 * np.cos(b) - 
              0.025 * np.sin(b))

        # convert the latitude to radians

        p = self.rad(self.latitude)

        # calculate the longitude at the center of the time zone

        Lm = self.longitude
        Lz = 15 * round(self.longitude / 15)

        # calculate the sunset hour angle

        ws = np.arccos(-1 * np.tan(p) * np.tan(d))

        # calculate the solar time angle at the midpoint of the time interval

        w = np.pi / 12 * ((ts + tm/60 + t1/2 + (Lm - Lz) / 15 + Sc) - 12)

        # calculate the solar time angles

        w1 = w - np.pi * t1 / 24
        w2 = w + np.pi * t1 / 24
        # overwrite the values if the sun is down

        w1[w1 < -ws] = -ws[w1 < -ws]
        w2[w2 < -ws] = -ws[w2 < -ws]
        w1[w2 < -ws] =  ws[w2 < -ws]
        w2[w2 >  ws] =  ws[w2 >  ws]
        w1[w1 >  w2] =  w2[w1 >  w2]

        # calculate the extraterrestrial radiation for the hour

        c = 12 / np.pi * Gsc * dr
        Ra = c * ((w2 - w1) * np.sin(p) * np.sin(d) +
                  np.cos(p) * np.cos(d) * (np.sin(w2) - np.sin(w1)))

        # calculate the clear day solar radiation

        Rso = (0.00002 * self.elevation + 0.75) * Ra

        # calculate the angle of the sun above the horizon at the midpoint
        # of the hour period

        B = np.arcsin(np.sin(p) * np.sin(d) + 
                         np.cos(p) * np.cos(d) * np.cos(w))

        # calculate ratio of the clear sky radiation to the actual radiation

        fcd = np.array([1.35 * (s / c) - 0.35 
                           if 0 < c and 0.3 < s / c and 17 < a 
                           else 0.05
                           for s, c, a in zip(solar, Rso, B)])

        Rns = solar * (1 - albedo)
        Rnl = sigma * 0.5 * T**4 * (0.34 - 0.139 * np.sqrt(Pv)) * fcd

        return Rns - Rnl


    def calculate_ret(self, start, end, albedo = 0.23, Cn = None, Cday = 0.24,
                      Cnight = 0.96, Cd = 0.34, Gday = 0.1, Gnight = 0.5,
                      Gd = 0, wheight = 2):
        '''
        Calculates the potential evapotransporation (PET) in mm for an hourly
        timeseries using the Penman-Monteith equation. Equations from:
        
        American Society of Civil Engineers (ASCE)
        Task Committee on Standardization of Reference Evapotranspiration
        Environmental and Water Resources Institute
        THE ASCE Standardized Reference Evapotranspiration Equation
        January 2005 Final Report

        https://xwww.mesonet.org/images/site/ASCE_Evapotranspiration_Formula.pdf

        arguments:
        start (datetime): the first day to calculate RET for
        end (datetime): the last day, exclusive
        albedo (float): i.e. canopy coefficient; ASCE recommends using a fixed
            value of 0.23
        Cn (float): numerator coefficient, varies depending on short or tall
            crop reference and hourly or daily time step; if not specified the
            correct Cn for short reference will be chosen based on timestep
            see Table 1 in the ASCE document
        Cday (float): daytime denominator coefficient; used for non-daily
            calculations, by default the short crop reference value is used
        Cnight (float): nighttime denominator coefficient
        Cd (float): daily denominator coefficient; by default the short crop
            reference value is used
        Gday (float): ground heat flux coefficient during the day; by default
            the short crop reference value is used; see eqns. 65a - 66b
        Gnight (float): ground heat coefficient flux during the night
        Gd (float): daily soil heat flux density; 0 by default, see eqn. 30
        wheight (float): the actual height wind measurements were taken at;
            used to correct the wind speed to 2m; should be 2 if WS2M is used
            and 10 if WSPD or WMAX is used
        '''

        if self.verbose:
            print('Calculating reference evapotranspiration...\n')

        # check the location has been supplied

        location = self.longitude, self.latitude, self.elevation

        if any([v is None for v in location]):
            print('Warning: location must be specified. Use the add_location()'
                  ' method.')
            return
        
        # check that all the time series are present

        required = [*self.data]

        if any([self.data[ts] is None for ts in required]):
            for ts in required:
                if self.data[ts] is None:
                    print('Warning: {} data unavailable. Add the required data'
                          ' with the add_timeseries() method.'.format(ts))
            return

        # make a list of times to use to calculate values

        times = [start + datetime.timedelta(minutes = self.timestep) * i 
                 for i in range(int((end-start).days * 1440/self.timestep))]

        # create a dictionary of numpy arrays for the requested period

        data = {}

        for ts in required:

            s, d = self.data[ts]

            # find the index of the requested start and end times

            i = int((start - s).days * 1440 / self.timestep)
            j = int((end - s).days * 1440 / self.timestep)

            # make the time series (if the data are available)

            try:
                data[ts] = np.array(d[i:j])
            except:
                print('Warning: {} data unavailable '.format(ts) +
                      'for requested period {} -- {}\n'.format(start, end))
                return

        # check and replace dewpoints higher than tmin/temperature
        #   (physically impossible)
        # convert solar from watt/m2 to MJ/m2/(hour or day)
        # calculate average temp for daily time step
        if self.timestep == 1440:
            dewpoint = np.minimum(data['tmin'], data['dewpoint'])
            solar = data['solar'] * 86400 / 10**6
            data['temperature'] = (data['tmin']+data['tmax'])/2
        else:
            dewpoint = np.minimum(data['temperature'], data['dewpoint'])
            solar = data['solar'] * 3600 / 10**6

        # set the numerator coefficient if it hasn't been provided
        if Cn is None:
            if self.timestep == 1440: Cn = 900
            else: Cn = 37

        # correct windspeed height (note the correction is essentially 1 if z
        # is 2 meters)

        u2 = self.wind_correction(data['wind'], z = wheight)

        # estimate the atmospheric pressure at the given elevation

        P = self.atmosphere_pressure()

        # estimate the average saturation vapor pressure (kPa)

        Ps = self.vapor_pressure(data['temperature'])

        # estimate the vapor pressure (kPa) from the dew point

        Pv = self.vapor_pressure(dewpoint)

        # estimate the vapor pressure curve slope (kPa C-1) at mean temperature

        d = (4098 * self.vapor_pressure(data['temperature']) / 
             (data['temperature'] + 237.3)**2)

        # convert C to K

        T = data['temperature'] + 273.15

        # adjust values based on the timestep
        if self.timestep == 1440:
            # daily soil heat flux is 0 by default
            soil = Gd
            # C_d coefficient is constant for daily estimation
            C_d = Cd
            Tmin = data['tmin'] + 273.15
            Tmax = data['tmax'] + 273.15
            rnet = self.daily_radiation(times, solar, Tmin, Tmax, Pv)
        else:
            rnet = self.hourly_radiation(times, solar, T, Pv)
            # hourly soil heat flux varies based on night/day
            soil = rnet * self.get_soil(times, Gday, Gnight)
            # C_d varies depending on night/day
            C_d = self.get_Cd(times, Cday, Cnight)
        
        # estimate the psychrometric constant (kPa C-1)
        # equation is gamma = cp(T) * P * MWair / latent_heat / MWwater
        # this uses cp for water at T = 20 C

        g = 0.000665 * P

        # estimate the reference evapotranspiration
        if self.timestep == 1140:
            RET = (0.408*d*(rnet-soil)+g*Cn/T*u2*(Ps-Pv))/(d+g*(1+Cd*u2))
        else:
            RET = ((0.408 * (rnet - soil) * d  + Cn * u2 / T * (Ps - Pv) * g) / 
                  (d + (g * (1 + C_d * u2)))) * (60 / self.timestep) 

        self.data['RET'] = start, RET

        if self.verbose: 

            print('Finished calculating reference evapotranspiration\n')
