# mesonetdownloader.py
#
# Abhiram Pamula (apamula@okstate.edu)
# Ben Rubinstein (brubinst@hawk.iit.edu)
#
# Some code based on nhdplusextractor by Mitchell Sawtelle
#   (https://github.com/Msawtelle/PyNHDPlus)
#
# last updated: 09/20/2022
#
# contains the MesonetDownloader class, which can be used to retrieve and
# manipulate source data from the Mesonet dataset online
import urllib.request
import os
import pandas as pd
import numpy as np
from datetime import timedelta, datetime
from shapefile import Reader
from pyproj import CRS, Transformer
from pandas.errors import EmptyDataError

class MesonetDownloader:
    '''
    The MesonetDownloader class contains methods to generate time series from
        the Oklahoma Mesonet climate dataset.
    '''

    def __init__(self, destination=None, verbose=False):
        '''
        init method for MesonetDownloader class

        arguments:
            destination (str): the path to where the user would like the
                Mesonet data to be stored if no argument is given the location
                of the file being run is used
            verbose (bool): if true write detailed debugging to stdout
        '''
        self.verbose = verbose
        # this is used for handling changing the rain column to differential
        self.errorcodes=[-994,-995,-996,-997,-998,-999]
        # if no destination given in init method set destination to current
        #   directory
        if destination is None:
            self.destination = os.path.dirname(__file__)
        else:
            self.destination = os.path.normpath(destination)

        try:
            if not os.path.isdir(self.destination): os.mkdir(self.destination)
        except PermissionError:
            errstr = ('The chosen destination folder does not exist and you do'
                      ' not have permission to create it.\n{}\nPlease set the'
                      ' destination argument to a different folder.')
            raise PermissionError(errstr.format(self.destination))

        # set up directory structure
        # mts_files holds the downloaded raw data from Mesonet
        # time_series holds saved dataframes as csvs
        self.mts_dir = '{}/{}'.format(self.destination,'mts_files')
        try:
            if not os.path.isdir(self.mts_dir): os.mkdir(self.mts_dir)
        except PermissionError:
            errstr = ('You do not have permission to create the required'
                      ' folders inside the destination directory.\n{}\nPlease'
                      ' change the permissions or choose a different'
                      ' destination folder.')
            raise PermissionError(errstr.format(self.mts_dir))

        # number of times to try in case of failed data retrieval
        self.TTL = 2

        # mesonet base url
        self.base_url = 'http://www.mesonet.org/index.php/'

        # attempt to read metadata from file
        self.metadata = pd.DataFrame()
        try:
            meta_file = 'geoinfo.csv'
            self.metadata = pd.read_csv('{}/{}'.format(self.destination,meta_file))
        except FileNotFoundError:
            if self.verbose:
                print('Metadata file not found locally. Attempting to download'
                      ' from Mesonet.')
        except Exception as e:
            if self.verbose:
                print('Failed to read metadata file locally due to:')
                print(e)
                print('Attempting to download from Mesonet.')
        finally:
            # if we failed to read the file locally, attempt to download
            if self.metadata.empty:
                meta_path = 'api/siteinfo/from_all_active_with_geo_fields/format/csv/'
                meta_url = '{}{}'.format(self.base_url,meta_path)
                attempt = 0
                while attempt < self.TTL:
                    try:
                        urllib.request.urlretrieve(meta_url,'{}/geoinfo.csv'.format(self.destination))
                        self.metadata = pd.read_csv('{}/{}'.format(self.destination,meta_file))
                        break
                    except Exception as e:
                        if self.verbose:
                            print('Attempt number {} to download metadata failed: {}'.format(attempt+1,meta_url))
                            print(e)
                    attempt += 1

        # raise an exception if the metadata file couldn't be read
        if self.metadata.empty:
            raise FileNotFoundError('Metadata file could not be found locally'
                                    ' or downloaded from Mesonet. Try setting'
                                    ' the verbose argument to True for more'
                                    ' details.')

        # convert the commission and decommision columns to datetime objects
        self.metadata['datc'] = pd.to_datetime(self.metadata['datc'],format='%Y%m%d')
        self.metadata['datd'] = pd.to_datetime(self.metadata['datd'],format='%Y%m%d')


    def get_station_ids(self):
        '''
        Returns a list of all the valid station IDs (STIDs) from the metadata file

        returns:
            str: a list of all the station IDs separated by spaces
        '''
        return ' '.join(self.metadata['stid'].values[1:])


    def get_station_coord(self,site_id):
        '''
        Returns the coordinates for a given station ID

        arguments:
            site_id (str): case-insensitive site ID as listed in the metadata
                file

        returns:
            tuple: lat/lon coordinates for the station
        '''
        # check if site id is valid
        if len(self.metadata[self.metadata['stid']==site_id.upper()]) == 0:
            if self.verbose:
                print('Error: invalid site ID. Valid site IDs are:')
                print(' '.join(self.metadata['stid'].values[1:]))
            return None
        lat = self.metadata.loc[self.metadata['stid'] == site_id.upper(),'nlat'].item()
        lon = self.metadata.loc[self.metadata['stid'] == site_id.upper(),'elon'].item()
        return (lat,lon)


    def download_station_data(self,site_id,start_date,end_date):
        '''
        Method to download data for a single station over a specified time period

        arguments:
            site_id (str): the ID for the station, IDs are in the metadata file
                case-insensitive
            start_date (datetime.date): first date to get data
            end_date (datetime.date): last date (inclusive) to get data

        returns:
            DataFrame: a pandas DataFrame containing the downloaded data sorted
                by datetime
        '''
        # note: site ids are in all caps in the metadata file but all lowercase
        #   in the URLs, this ensures that our code is case-insensitive
        site_id = site_id.lower()
        # check if site id is valid
        if len(self.metadata[self.metadata['stid']==site_id.upper()]) == 0:
            if self.verbose:
                print('Error: invalid site ID. Valid site IDs are:')
                print(' '.join(self.metadata['stid'].values[1:]))
            return None
        # check if station was active during the requested time period
        datc = self.metadata.loc[self.metadata['stid'] == site_id.upper(),'datc'].item()
        datd = self.metadata.loc[self.metadata['stid'] == site_id.upper(),'datd'].item()
        if start_date < datc.date():
            if self.verbose:
                print('Warning: the {} station was commissioned on {} which'
                      ' was after the requested start date of {}. It will be'
                      ' skipped.'.format(site_id.upper(),datc,start_date))
            return None
        if end_date > datd.date():
            if self.verbose:
                print('Warning: the {} station was decommissioned on {} which'
                      ' was before the requested end date of {}. It will be'
                      ' skipped.'.format(site_id.upper(),datd,end_date))
            return None
        dates_list = []
        # create list of dates to download
        delta = timedelta(days=1)
        while start_date <= end_date:
            dates_list.append(start_date.strftime('%Y%m%d'))
            start_date += delta
        df_list = []
        for i in dates_list:
            cur_df = pd.DataFrame()
            # attempt to read file locally
            try:
                cur_df = pd.read_csv('{}/{}{}.mts'.format(self.mts_dir,i,site_id),header=2,sep=r'\s+')
            except FileNotFoundError:
                if self.verbose:
                    print('File not found locally, attempting to download.')
                    print('{}/{}{}.mts'.format(self.mts_dir,i,site_id))
                attempt = 0
                while attempt < self.TTL:
                    try:
                        url = '{}dataMdfMts/dataController/getFile/{}{}/mts/DOWNLOAD/'.format(self.base_url,i,site_id)
                        urllib.request.urlretrieve(url,'{}/{}{}.mts'.format(self.mts_dir,i,site_id))
                        cur_df = pd.read_csv('{}/{}{}.mts'.format(self.mts_dir,i,site_id),header=2,sep=r'\s+')
                        break
                    except:
                        if self.verbose:
                            print('Failed to download data from {} on attempt {}.'.format(url,attempt+1))
                    attempt += 1
            except EmptyDataError:
                if self.verbose:
                    print('{}/{}{}.mts is an empty file.'.format(self.mts_dir,i,site_id))
                    print('This means that there is no data available for the'
                          ' {} on {}.'.format(site_id,i))
            if not cur_df.empty:
                date =  datetime.strptime(i, '%Y%m%d')
                cur_df['DATETIME'] = cur_df.apply(lambda x: date+timedelta(minutes = int(x['TIME'])), axis = 1)
                # change rain to differential instead of cumulative
                # make a copy of the rain column so we can track the errors
                cur_df['RAIN_BAK'] = cur_df['RAIN']
                                # replace the errors with nan
                for code in self.errorcodes:
                    cur_df['RAIN'].replace(str(code),np.nan,inplace=True)
                    cur_df['RAIN'].replace(code,np.nan,inplace=True)
                first_rain = cur_df.loc[0,'RAIN']
                second_rain = cur_df.loc[1,'RAIN']
                # there are cases where the last reading from the previous day
                # rolls over so we check for that and zero out the number
                if first_rain > second_rain:
                    first_rain = 0
                    cur_df.loc[0,'RAIN'] = first_rain
                cur_df['RAIN']=cur_df['RAIN'].diff()
                cur_df.loc[0,'RAIN'] = first_rain
                # copy error codes back into the rain column
                # TODO: fix the SettingWithCopyError warning
                pd.options.mode.chained_assignment = None
                for code in self.errorcodes:
                    cur_df['RAIN'].loc[cur_df['RAIN_BAK']==code] = code
                pd.options.mode.chained_assignment = 'warn'
                # drop some columns to save memory
                cur_df.drop(columns=['STNM','TIME','RAIN_BAK'],inplace=True)
                df_list.append(cur_df)
            elif self.verbose:
                print('No data available for {} on {}.'.format(site_id,i))
        if len(df_list) == 0:
            return None
        final_df = pd.concat(df_list)
        final_df = final_df.reset_index(drop=True)
        return final_df


    def download_bounding_box(self,bbox,start_date,end_date,padding=1):
        '''
        Downloads data for all the stations found within a bounding box.

        arguments:
            bbox (list): the bounding box to be searched; it expects the same format
                as used in pyshp, [low longitude, low latitude, highlon, highlat]
            start_date (datetime.date): first date to get data
            end_date (datetime.date): last date (inclusive) to get data
            padding (int): an optional parameter that increases or decreases
                the size of the bounding box, must be positive

        returns:
            dict: a dictionary with station IDs as keys and DataFrames holding
                the downloaded data as values
        '''
        # make bbox coordinates easier to work with
        lowlon = bbox[0]
        lowlat = bbox[1]
        highlon = bbox[2]
        highlat = bbox[3]
        if padding != 1 and padding > 0:
            lonpad = padding*(highlon-lowlon)/2
            latpad = padding*(highlat-lowlat)/2
            lowlon = lowlon - lonpad
            lowlat = lowlat - latpad
            highlon = highlon + lonpad
            highlat = highlat + latpad
        elif self.verbose and padding <= 0:
            print('Warning: The padding parameter must be positive. It will be'
                  ' ignored.')
        # find station IDs within the box
        station_ids = []
        for index, row in self.metadata.iterrows():
            lat = row.nlat
            lon = row.elon
            if lat > lowlat and lat < highlat and lon > lowlon and lon < highlon:
                station_ids.append(row.stid)
        if len(station_ids) == 0:
            if self.verbose:
                print('No stations found within the bounding box.')
                print(bbox)
                print('Try increasing the padding argument.')
            return None
        # download data for each station and save them in a dictionary
        station_dfs = dict()
        for stid in station_ids:
            station_df = self.download_station_data(stid, start_date, end_date)
            if station_df is not None:
                station_dfs[stid] = station_df
        return station_dfs


    def download_shape_object(self,shape,start_date,end_date,padding=1,prj_path=''):
        '''
        Reads a shape file from the specified path and downloads all data for
            all stations within its bounding box

        arguments:
            shape (shapefile.Shape or shapefile.Reader): the shape object to be
                searched for stations
            start_date (datetime.date): first date to get data
            end_date (datetime.date): last date (inclusive) to get data
            padding (int): an optional parameter that increases or decreases
                the size of the bounding box, must be positive
            prj_path (str): an optional parameter that points to the .prj file
                associated with the shape file; if this specified then the
                bounding box coordinates will be converted to EPSG:4269

        returns:
            dict: a dictionary with station IDs as keys and DataFrames holding
                the downloaded data as values
        '''
        bbox = shape.bbox
        # convert the coordinates to the correct CRS is the path to a
        #   projection file is specified
        if prj_path:
            bbox = self.change_crs(prj_path, bbox)
        # this is a quick check to see if the coordinates are in meters instead
        #   of latitude and longitude, this method isn't perfect but should
        #   catch most issues
        absbox = np.abs(bbox)
        if absbox[0]>180 or absbox[1]>90 or absbox[2]>180 or absbox[3]>90:
            if self.verbose:
                print('It appears that the bounding box {} is not in latitude'
                      ' longitude coordinates. Try specifing the prj_path'
                      ' argument when calling this function.'.format(bbox))
                return None
        df = self.download_bounding_box(bbox,start_date,end_date,padding)
        return df


    def download_shape_file(self,shape_path,start_date,end_date,padding=1,prj_path=''):
        '''
        Reads a shape file from the specified path and downloads all data for
            all stations within its bounding box

        arguments:
            shape_file (str): the path to the shape file to be used
            start_date (datetime.date): first date to get data
            end_date (datetime.date): last date (inclusive) to get data
            padding (int): an optional parameter that increases or decreases
                the size of the bounding box, must be positive
            prj_path (str): an optional parameter that points to the .prj file
                associated with the shape file; if this specified then the
                bounding box coordinates will be converted to EPSG:4269

        returns:
            dict: a dictionary with station IDs as keys and DataFrames holding
                the downloaded data as values
        '''
        # the whole method is wrapped in a try to make sure we release the
        #   shape file regardless of any exceptions
        try:
            # read the shape file and call the download method for shape objects
            sf = Reader(shape_path)
            df = self.download_shape_object(sf,start_date,end_date,padding,prj_path)
        except FileNotFoundError:
            if self.verbose:
                print('Error: the speficied shape file {} was not found.'.format(shape_path))
            return None
        except Exception as e:
            if self.verbose:
                print('Error: an exception occured attempting to download data'
                      ' for the shape file {}.'.format(shape_path))
                print(e)
                return None
        finally:
            sf.close()
        return df


    def change_crs(self, prj_path, bbox):
        '''
        Changes the CRS of a bounding box to EPSG:4269 used by Mesonet.

        arguments:
            crs_path (str): the path to the .prj file for the original box
            bbox (list): the bounding box to be converted; it expects the same format
                as used in pyshp, [low longitude, low latitude, highlon, highlat]

        returns:
            list: the converted bounding box coordinates
        '''
        # The coordinates for each station in the metadata file come from a
        #   shape file that uses EPSG:4269
        meso_crs = 'EPSG:4269'
        crs_str = ''
        # read the CRS string from the provided file
        try:
            crs_file = open(prj_path)
            crs_str = crs_file.read()
        except FileNotFoundError:
            if self.verbose:
                print('Error: the specified file {} was not found.'.format(prj_path))
                return bbox
        except Exception as e:
            if self.verbose:
                print('Error: unable to read the .prj file {}.'.format(prj_path))
                print(e)
                return bbox
        finally:
            crs_file.close()
        # Create a Transformer object, this is what actually transforms our
        #   coordinates to the proper CRS
        crs = CRS.from_user_input(crs_str)
        transformer = Transformer.from_crs(crs, meso_crs)
        if self.verbose:
            auth = crs.to_authority()
            code = '{}:{}'.format(auth[0],auth[1])
            print('Transforming bounding box from {} to {}.'.format(code,meso_crs))
        # The transformer can only work with points so we have to do each
        #   corner of the box separately
        corner1 = transformer.transform(bbox[0],bbox[1])
        corner2 = transformer.transform(bbox[2],bbox[3])
        return [corner1[1], corner1[0], corner2[1], corner2[0]]
