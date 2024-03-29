# mesonettools.py
#
# Abhiram Pamula (apamula@okstate.edu)
# Ben Rubinstein (brubinst@hawk.iit.edu)
#
# last updated: 03/20/2023
#
# contains the MesonetTools class
import os, re
import pandas as pd
import numpy as np
import missingno as msno
from .mesonetdownloader import MesonetDownloader
from .etcalculator import ETCalculator
from geopy import distance

class MesonetTools:
    '''
    The MesonetTools class contains methods to assist with processing time
        series generated by the MesonetDownloader class.
    '''

    def __init__(self, verbose=False):
        '''
        init method for the MesonetTools class

        arguments:
            verbose (bool): if true write detailed debugging to stdout
        '''
        self.verbose=verbose
        # these are used internally when replacing data
        self.nondatcols=['STID']
        self.calculatedcols=['TDEW','EVAP']
        # columns that should be summed instead of averaged when resampling
        self.sumcols=['RAIN','EVAP']
        self.errorcodes=[-994,-995,-996,-997,-998,-999]


    def replace_errors(self,df,code=1,column=None):
        '''
        Replace error codes in the dataset with NaN.

        Description of error codes:
            -999 - flagged bad by QA routines
            -998 - sensor not installed
            -997 - missing calibration coefficients
            -996 - station did not report
            -995 - data not reported on this time interval
            -994 - value is too wide to fit in column
        arguments:
            df (DataFrame or dict): the dataframe or dictionary of dataframes
                to be manipulated
            code (int): the specific error code to be replaced, the default 1
                replaces all error codes
            column (str): optional parameter that when specified changes only
                a single column

        returns:
            DataFrame or dict: the modified df object
        '''
        df = df.copy()
        # check if we've been given a dict or dataframe
        if self.__is_dict(df)==-1:
            if self.verbose:
                print('Warning: replace_errors() expects a DataFrame or dict'
                      ' not a {}. No actions performed.'.format(type(df)))
        # check that the error code argument is valid
        elif code != 1 and code not in self.errorcodes:
            if self.verbose:
                print('Warning: {} is not a valid error code. Nothing will'
                      ' be replaced. Use 1 or do not pass in a code argument'
                      ' to replace all error codes or enter one of the'
                      ' following: {}.'.format(code,self.errorcodes))
                print('help(MesonetTools.replace_errors) will give a'
                      ' description of the error codes.')
        # if df is a dictionary, recursively call this function for each of its keys
        elif self.__is_dict(df)==1:
            for key in df:
                df[key] = self.replace_errors(df[key],code,column)
        # if df is a dataframe
        elif self.__is_dict(df)==0:
            if code==1:
                # replace all error codes with NaN
                if column is None:
                    # replace for all columns
                    df = df.replace(self.errorcodes,np.nan)
                else:
                    # check if the column exists
                    if column in df.columns:
                        # replace for a single column
                        df[column] = df[column].replace(self.errorcodes,np.nan)
                    elif self.verbose:
                        print('Warning: there is no column named {}'
                              ' in the dataframe. No actions will be'
                              ' taken.'.format(column))
            # check if code is a valid error code
            else:
                if column is None:
                    # replace for all columns
                    df = df.replace(code,np.nan)
                else:
                    # check if the column exists
                    if column in df.columns:
                        # replace for a single column
                        df[column] = df[column].replace(code,np.nan)
                    elif self.verbose:
                        print('Warning: there is no column named {}'
                              ' in the dataframe. No actions will be'
                              ' taken.'.format(column))
        return df


    def interpolate_missing(self,df,codes=[],column=None):
        '''
        Fills missing data with simple linear interpolation between known
            values
        
        This method will automatically ignore the following columns:
            'STID', 'DATETIME'

        arguments:
            df (DataFrame or dict): the dataframe or dictionary of dataframes
                to be manipulated
            codes (list): optional parameter that when specified interpolates
                only for the specified codes
            column (str): optional parameter that when specified changes only
                a single column

        returns:
            DataFrame or dict: the modified df object
        '''
        # check if we've been given a dict or dataframe
        if self.__is_dict(df)==-1:
            if self.verbose:
                print('Warning: interpolate_missing() expects a DataFrame or'
                      ' dict not a {}. No actions performed.'.format(type(df)))
        # check that at least one error code in the list is valid
        elif codes and all(i not in self.errorcodes for i in codes):
            if self.verbose:
                print('Warning: No valid error codes were entered: {}. No'
                      ' changes will be made. Use an empty list or do not pass'
                      ' in the codes argument to replace all error codes or'
                      ' enter at least one of the following valid error codes:'
                      ' {}'.format(codes,self.errorcodes))
                print('help(MesonetTools.replace_errors) will give a'
                      ' description of the error codes.')
        # if df is a dictionary, recursively call this function for each of its keys
        elif self.__is_dict(df)==1:
            for key in df:
                df[key] = self.interpolate_missing(df[key],codes,column)
        else:
            backup = pd.DataFrame()
            if codes:
                # store a backup so we can recovery error codes that shouldn't
                #   be replaced
                backup = df
            # replace all error codes
            df = self.replace_errors(df,column=column)
            if column is None:
                for ncolumn in df.columns:
                    if ncolumn not in self.nondatcols:
                        df[ncolumn] = df[ncolumn].interpolate()
            else:
                df[column] = df[column].interpolate()
            # if there were specific error codes provided, recover the others
            if codes:
                df = self.__copy_errors(df,backup,codes,column)
        return df


    def fill_neighbor_data(self,df,downloader,codes=[],column=None):
        '''
        Fills missing data with the value from the geographically closest
            station that has the missing observation
        
        This method will automatically ignore -995 error codes and the
            following columns: 'STID', 'DATETIME'

        arguments:
            df (DataFrame or dict): the dataframe or dictionary of dataframes
                to be manipulated
            downloader (MesonetDownloader): a MesonetDownloader object is
                required to calculate distances and download new data
            codes (list): optional parameter that when specified interpolates
                only for the specified codes
            column (str): optional parameter that when specified changes only
                a single column

        returns:
            DataFrame or dict: the modified df object
        '''
        # make sure that downloader is a MesonetDownloader object
        if not isinstance(downloader, MesonetDownloader):
            if self.verbose:
                print('Warning: downloader must be an okmesopy.MesonetDownloader'
                      ' object not a {}. No changes will be made.'.format(type(downloader)))
        # check if we've been given a dict or dataframe
        elif self.__is_dict(df)==-1:
            if self.verbose:
                print('Warning: fill_neighbor_data() expects a DataFrame or'
                      ' dict not a {}. No actions performed.'.format(type(df)))
        # check that at least one error code in the list is valid
        elif codes and all(i not in self.errorcodes for i in codes):
            if self.verbose:
                print('Warning: No valid error codes were entered: {}. No'
                      ' changes will be made. Use an empty list or do not pass'
                      ' in the codes argument to replace all error codes or'
                      ' enter at least one of the following valid error codes:'
                      ' {}'.format(codes,self.errorcodes))
                print('help(MesonetTools.replace_errors) will give a'
                      ' description of the error codes.')
        # if df is a dictionary, recursively call this function for each of its keys
        elif self.__is_dict(df)==1:
            for key in df:
                df[key] = self.fill_neighbor_data(df[key],downloader,codes,column)
        else:
            stid = df.loc[df.index[0],'STID']
            if not codes:
                codes = self.errorcodes.copy()
            # skip -995, no stations will have data on the not sampled intervals
            if -995 in codes: codes.remove(-995)
            for code in codes:
                df = self.replace_errors(df,code,column)
            # create a list of stations sorted by distance
            target_coord = downloader.get_station_coord(stid)
            coord_tuple = list(downloader.metadata.loc[:,['nlat','elon']].itertuples(index = False, name = None))
            for i in coord_tuple:
                if i == target_coord:
                    coord_tuple.remove(i)
            req_loc = downloader.metadata['stid'].loc[downloader.metadata['stid']!=stid]
            station_list=[]
            for i,j in zip(req_loc,coord_tuple):
                station_list.append([i,distance.distance(target_coord,j).miles])
            station_list = sorted(station_list, key = lambda x:(x[1], x[0]))
            stids = [i[0] for i in station_list]
            # we need to deal with nans in calculated columns since no station
            # will have those; first replace them with a placeholder value
            for col in self.calculatedcols:
                if col in df.columns: df[col] = df[col].replace(np.nan,-1000)
            for station in stids:
                # break when all data has been filled
                if column is None:
                    if df.isnull().sum().sum()==0: break
                else:
                    if df[column].isnull().sum()==0: break
                df = self.__download_neighbor(df,downloader,station)
            # add the nans back into the calculated columns
            for col in self.calculatedcols:
                if col in df.columns: df[col] = df[col].replace(-1000,np.nan)
        return df


    def summarize_missing(self,df,graph=False):
        '''
        Summarizes error codes in the provided dataframe

        arguments:
            df (DataFrame): the dataframe with missing data to be summarized
            graph (bool): an optional arugument that if true will generate
                visualization of the missing data using the missingno library
        '''
        # Generate a new dataframe that will hold the error info
        cols = df.columns.to_list()
        for col in self.nondatcols: cols.remove(col)
        errors = pd.DataFrame()
        # loop through each column
        for col in cols:
            # count the error codes
            counts = df.groupby(col).size()
            for error in self.errorcodes:
                # populate the error dataframe
                try:
                    count = counts[error]
                    errors.loc[col,error]=count
                except:
                    # a key value error here means there were none of this
                    # error code in this column
                    errors.loc[col,error]=0
            # add a total value for each column
            errors.loc[col,'TOTAL']=errors.loc[col,:].sum()
        # add a total for the error codes as well
        for col in errors.columns:
            errors.loc['TOTAL',col]=errors.loc[:,col].sum()
        # total values, the bottom right cell has the overall total
        total = errors.iloc[-1,-1]
        total_corrected = total - errors.loc[errors.index[-1],-995]
        # print a summary of the missing data
        print('Missing data summary for {} station:'.format(df.loc[df.index[0],'STID']))
        print('-----------------------')
        print('To see a description of each error code run help(MesonetTools.replace_errors)')
        print('Note: the -995 error code is used when data is not collected'
              ' on an interval. This code is generally normal and expected.')
        print('There are {} total missing data points and {} missing data'
              ' data points excluding -995 codes'.format(int(total),int(total_corrected)))
        print('The following chart displays the number of each kind of error'
              ' code found in each column of the DataFrame.\n')
        print(errors.astype(int))
        # graphically display errors if the chart arguement is true
        if graph:
            # prepare a dataframe for the missingno library, we need to
            # actually replace all the error codes with NaN so missingno can
            # recognize them
            rep_df = self.replace_errors(df)
            # also remove non data columns
            for col in self.nondatcols:
                rep_df.drop(col,axis=1,inplace=True)
            msno.matrix(rep_df,freq='5M')


    def save_timeseries(self,df,column,step=5,get_min=False,get_max=False):
        '''
        Saves the a data for a single variable for a single station as a
            PyHSPF readable timeseries. If a set of stations is provided,
            the arithmetic mean is used instead

        arguments:
            df (DataFrame or dict): the DataFrame to create a series from; if
                a dictionary is passed in, the arithmetic mean of all contained
                DataFrames is used
            column (str): the variable to create a time series for
            step (int or str): the time interval to use in minutes; must be at
                least 5 and divisible by 5; the closest multiple of 5 will be
                least instead if not; the strings 'hourly' and 'daily' are also
                valid
            get_min (bool): If true, returns the minimum value instead of mean
                or sum when resampling
            get_max (bool): If true, returns the maximum value instead of mean
                or sum when resampling

        returns:
            tuple (int,datetime,list): the timeseries object in the form
                (step size,start date,data)
        '''
        column = column.upper()
        # validate the step size
        if step == 'hourly': step = 60
        elif step == 'daily': step = 1440
        elif step < 5:
            if self.verbose:
                print('{} was given as step size but it must be at least 5'
                      ' minutes. A step size of 5 minutes will be used'
                      ' instead'.format(step))
            step = 5
        elif step%5 != 0:
            if self.verbose:
                print('Step size must be a multiple of 5. The given step size'
                      ', {}, will be rounded up to {}.'.format(step,step + 5 - step%5))
            step = step + 5 - step%5
        # if a dictionary has been given, generate the average
        tempdf = pd.DataFrame()
        if self.__is_dict(df):
            # concatenate all the DataFrames together, using only the relevant
            #   column to save memory
            for key in df:
                start = df[key].index[0]
                # make sure the column exists
                if not column in df[key].columns:
                    print('Error: the column {} was not found in the dataframe'
                          ' for the {} station.'.format(column,key))
                    return None
                tempdf = pd.concat((tempdf,df[key].copy(column)))
            # remove all error codes so they don't throw off the averages
            tempdf = self.replace_errors(tempdf)
            # make df the mean
            df = tempdf.groupby(tempdf.index).mean(numeric_only=True)
        else:
            # get the start date and time
            start = df.index[0]
        # easiest case we just use every data point
        if step == 5:
            data = df[column].replace(self.errorcodes,np.nan).tolist()
        else:
            # check what kind of resampling we need to do
            if get_min and not get_max:
                data = df[column].replace(self.errorcodes,np.nan).resample(str(step)+'Min').min().tolist()
            elif get_max and not get_min:
                data = df[column].replace(self.errorcodes,np.nan).resample(str(step)+'Min').max().tolist()
            elif get_min and get_max:
                print('Error: both get_min and get_max were set to True. Only'
                      ' one can be true.')
                return 
            elif column in self.sumcols:
                data = df[column].replace(self.errorcodes,np.nan).resample(str(step)+'Min').sum().tolist()
            else:
                data = df[column].replace(self.errorcodes,np.nan).resample(str(step)+'Min').mean().tolist()
        ts = step, start, data
        return ts


    def save_csv(self,df,path,force=False,filename=''):
        '''
        Saves a downloaded dataset as a CSV file.

        arguments:
            df (DataFrame or dict): the DataFrame or dictionary of DataFrames
                to be saved
            path (str): the directory to save the file to
            force (bool): if set to true will overwrite existing files
            filename (str): optional name of the csv file; filenames must be
                alphanumeric characters, hyphens, underscores, and periods only
        '''
        path = os.path.normpath(path)
        try:
            if not os.path.isdir(path): os.mkdir(path)
        except PermissionError:
            errstr = ('The specified directory {} does not exist and you do not'
                      ' have permission to create it. Please try a different'
                      ' directory.')
            raise PermissionError(errstr.format(path))
        # check if the filename is valid
        if re.search(r'[^A-Za-z0-9\._\-\\]',filename):
            print('Warning: Filenames can only contain alphanumeric characters'
                  ', hyphens, underscores, and periods. Enter a new filename'
                  ' or leave the argument blank to use an autogenerated name.')
            return
        # if we have a dictionary, concatenate all the DataFrames together
        if self.__is_dict(df):
            concat_df = pd.DataFrame()
            for key in df:
                concat_df = pd.concat((concat_df,df[key]))
                # generate the file name
                if not filename:
                    start = df[key].index[0].strftime('%m%d%y')
                    end = df[key].index[-1].strftime('%m%d%y')
                    filename = '{}_and-{}-more_{}-{}.csv'.format(key,len(df)-1,start,end)
            # if file exists check if the force argument is true
            if os.path.exists('{}/{}'.format(path,filename)) and not force:
                print('Warning: The file {} already exists in the directory {}.'
                      ' Please choose a new filename or directory or set the force'
                      ' argument to true to overwrite the existing file.'.format(filename,path))
                return
            concat_df.to_csv('{}/{}'.format(path,filename))
        else:
            if not filename:
                stid = df.loc[df.index[0],'STID']
                start = df.index[0].strftime('%m%d%y')
                end = df.index[-1].strftime('%m%d%y')
                filename = '{}_{}-{}.csv'.format(stid,start,end)
            # if file exists check if the force argument is true
            if os.path.exists('{}/{}'.format(path,filename)) and not force:
                print('Warning: The file {} already exists in the directory {}.'
                      ' Please choose a new filename or directory or set the force'
                      ' argument to true to overwrite the existing file.'.format(filename,path))
                return
            df.to_csv('{}/{}'.format(path,filename))


    def calculate_dewpoint(self, df, a=17.625, b=243.04):
        '''
        Calculates the dewpoint temperatures from temperature and relative
        humidity using the Magnus-Tetens formula
        DOI:10.1175/BAMS-86-2-225
        
        arguments:
            df (DataFrame or dict): the dataframe or dictionary of dataframes
                to calculate dewpoints for
            a, b (float): the Magnus coefficients, by default the ones given by
                Alduchov and Eskridge are used:
                DOI:10.1175/1520-0450(1996)035<0601:IMFAOS>2.0.CO;2
        '''
        # make sure we have been given a dataframe or dictionary
        if self.__is_dict(df)==-1:
            if self.verbose:
                print('Warning: calculate_dewpoint() expects a DataFrame or'
                      ' dict not a {}. No actions performed.'.format(type(df)))
        # if df is a dictionary, recursively call this function for each of its keys
        elif self.__is_dict(df)==1:
            for key in df:
                df[key] = self.calculate_dewpoint(df[key],a,b)
        # if df is a dataframe we can find the dewpoint
        elif self.__is_dict(df)==0:
            # replace errors in RELH and TAIR to ensure we get nans where data
            # is missing
            rep_df = self.replace_errors(df,column='TAIR')
            rep_df = self.replace_errors(rep_df,column='RELH')
            alpha = np.log(rep_df["RELH"]/100) + (a*rep_df["TAIR"]/(b+rep_df["TAIR"]))
            df["TDEW"] = (b * alpha) / (a - alpha)
        return df


    def calculate_ret(self,df,start,end,downloader,timestep=60,wind='WS2M',
                      error_handling='nan',return_calc=False):
        '''
        Calculates the reference evapotranspiration using the Penman-Monteith
            equation. This method sets everything up using a MesonetDownloader
            dataframe and the actual calculations are done in the ETCalculator
            class.
        
        arguments:
            df (DataFrame): the dataframe to calculate reference ET for
            start (datetime.datetime): first date to get data
            end (datetime.datetime): last date (inclusive) to get data
            downloader (MesonetDownloader): a MesonetDownloader object is
                required to get the station location data
            timestep (int): time step to use in minutes; acceptable values are
                60, 1440, or a factor of 60 that is also a multiple of 5
            wind (str): which column to use for wind speed data; acceptable
                values are 'WS2M','WSPD', and 'WMAX' which are wind speed at 2
                meters, 10 meters, and max wind speed at 10 meters respectively
                it is recommended to use the default 'WS2M' so that no
                correction needs to be done
            error_handling (str): tells the function how to deal with error
                codes in the data; acceptable values are 'nan', 'interpolate',
                and 'neighbor'. 'nan' is the default and simply replaces error
                codes with nan. This will result in nans in the ET time series.
                'interpolate' and 'neighbor' use the interpolate_missing and
                fill_neighbor_data methods respectively to fill in missing data
            return_calc (bool): if true returns the calculator object instead
                of just the RET time series

        returns:
            tuple (int,datetime,list): step size in minutes, start time
                of the series, reference evapotranspiration in mm
            or
            ETCalculator: returned instead if the return_calc argument is true
        '''
        # validate the timestep
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
        # prepare the dataframe
        if error_handling == 'nan':
            df = self.replace_errors(df)
        elif error_handling == 'interpolate':
            df = self.interpolate_missing(df,column='TAIR')
            df = self.interpolate_missing(df,column='RELH')
            df = self.interpolate_missing(df,column=wind)
            df = self.interpolate_missing(df,column='SRAD')
        elif error_handling == 'neighbor':
            df = self.fill_neighbor_data(df, downloader,column='TAIR')
            df = self.fill_neighbor_data(df, downloader,column='RELH')
            df = self.fill_neighbor_data(df, downloader,column=wind)
            df = self.fill_neighbor_data(df, downloader,column='SRAD')
        else:
            print('Invalid error code handling method was given. Acceptable'
                  ' values for the error_handling parameter are \'nan\','
                  ' \'interpolate\', and \'neighbor\'.')
            return None
        df = self.calculate_dewpoint(df)
        # initialize the ETCalculator object
        calc = ETCalculator(timestep=timestep)
        # add location data to the calculator
        stid = df.iloc[0,0]
        calc.add_location(*downloader.get_location(stid))
        # add the required time series to the calculator
        if timestep == 1440:
            # daily calculations use min/max temperatures insetad of average
            calc.add_timeseries('tmin',*self.save_timeseries(df,'TAIR',timestep,get_min=True))
            calc.add_timeseries('tmax',*self.save_timeseries(df,'TAIR',timestep,get_max=True))
            calc.add_timeseries('dewpoint',*self.save_timeseries(df,'TDEW',timestep))
            calc.add_timeseries('wind',*self.save_timeseries(df,wind,timestep))
            calc.add_timeseries('solar',*self.save_timeseries(df,'SRAD',timestep))
        else:
            # hourly and fractional hourly calculations are done the same way
            calc.add_timeseries('temperature',*self.save_timeseries(df,'TAIR',timestep))
            calc.add_timeseries('dewpoint',*self.save_timeseries(df,'TDEW',timestep))
            calc.add_timeseries('wind',*self.save_timeseries(df,wind,timestep))
            calc.add_timeseries('solar',*self.save_timeseries(df,'SRAD',timestep))
        # calculate RET and return the time series
        calc.calculate_ret(start,end)
        if return_calc:
            return calc
        else:
            return (timestep, *calc.data['RET'])


    def __download_neighbor(self,df,downloader,station_id):
        '''
        Helper function that downloads and fills data from a neighboring station

        arguments:
            df (DataFrame): the dataframe with missing data to be filled 
            downloader (MesonetDownloader): a MesonetDownloader object is
                required to download new data
            station_id (str): the station ID for the neighboring station

        returns:
            DataFrame: the modified df object
        '''
        # get a list of dates with missing data
        missing_dates = []
        for dt in pd.Series([d.date() for d in df[df.isna().any(axis=1)].index]).unique():
            if dt not in missing_dates: missing_dates.append(dt)
        # download data for each of the missing dates
        for miss_date in missing_dates:
            date = pd.to_datetime(miss_date)
            neighbor_df = downloader.download_station_data(station_id,date,date)
            if neighbor_df is not None:
                # we don't want to copy over any error codes so replace all of them
                neighbor_df = self.replace_errors(neighbor_df)
                # fill in data
                df = df.fillna(neighbor_df)
        return df


    def __copy_errors(self,df,backup,codes,column=None):
        '''
        Helper function that copies error codes back into a dataframe

        arguments:
            df (DataFrame): the dataframe to be manipulated
            backup (DataFrame): a copy of df with error codes still in place 
            codes (list): a list of codes to copy back into df
            column (str): optional parameter that when specified changes only
                a single column

        returns:
            DataFrame: the modified df object
        '''
        # TODO: fix the SettingWithCopyError?
        pd.options.mode.chained_assignment = None
        for code in self.errorcodes:
            if code not in codes:
                if column is not None:
                    # these commands cause a SettingWithCopyError. I think it
                    #   is a false positive but I'm not fully sure I
                    #   understand the error properly
                    df[column].loc[backup[column]==code] = code
                else:
                    for ncolumn in df.columns:
                        df[ncolumn].loc[backup[ncolumn]==code] = code
        pd.options.mode.chained_assignment = 'warn'
        return df


    def __is_dict(self,df):
        '''
        MesonetDownloader creates single dataframes and dictionaries of
            dataframes. Returns 1 for dict, 0 for dataframe, and -1 as an
            error code for anything else

        arguments:
            df (DataFrame or dict): the object to type check

        returns:
            int: 1 for a dictionary, 0 for a DataFrame, -1 otherwise
        '''
        if isinstance(df,dict):
            return 1
        elif isinstance(df,pd.DataFrame):
            return 0
        else:
            return -1
