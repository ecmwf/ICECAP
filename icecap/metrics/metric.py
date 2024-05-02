"""
Definition of metrics.

It is intended to use the create (factory) function to instantiate
a specific metric. The specific metric definition contains only the
essentials, and relies on methods and init of its parent. This makes
addition of new metrics as easy as possible.
"""

import os.path
import datetime as dt
import xarray as xr
import numpy as np


import dataobjects
import utils
import forecast_info

class BaseMetric(dataobjects.DataObject):
    """Generic Metric Object inherited by each specific metric"""

    def __init__(self, name, conf):
        super().__init__(conf)
        self.metricname = name
        self.target = conf.plotsets[name].target
        self.plottype = conf.plotsets[name].plottype
        self.metricdir = conf.metricdir


        #initialise verification attributes

        self.verif_expname = utils.csv_to_list(conf.plotsets[name].verif_expname)
        self.verif_modelname = utils.csv_to_list(conf.plotsets[name].verif_modelname)

        self.verif_mode = utils.csv_to_list(conf.plotsets[name].verif_mode)

        self.verif_fcsystem = utils.csv_to_list(conf.plotsets[name].verif_fcsystem)
        self.verif_source = utils.csv_to_list(conf.plotsets[name].verif_source)

        self.verif_dates = utils.confdates_to_list(conf.plotsets[name].verif_dates)
        self.conf_verif_dates = conf.plotsets[name].verif_dates
        self.verif_fromyear = conf.plotsets[name].verif_fromyear
        self.verif_toyear = conf.plotsets[name].verif_toyear
        self.verif_refdate = utils.confdates_to_list(conf.plotsets[name].verif_refdate)

        self.verif_enssize = utils.csv_to_list(conf.plotsets[name].verif_enssize)

        if len(self.verif_enssize) != 1:
            raise ValueError('enssize can be either length 1 (all dates/systems with same ensemble size)')

        # initialize calibration forecasts
        self.calib = False
        if conf.plotsets[name].calib_dates is not None:
            self.calib = True
            self.calib_modelname = self.verif_modelname
            self.calib_expname = self.verif_expname
            self.calib_mode = utils.csv_to_list(conf.plotsets[name].calib_mode)
            self.calib_source = self.verif_source
            self.calib_fcsystem = self.verif_fcsystem
            self.calib_dates = utils.confdates_to_list(conf.plotsets[name].calib_dates)
            self.conf_calib_dates = conf.plotsets[name].calib_dates
            self.calib_fromyear = conf.plotsets[name].calib_fromyear
            self.calib_toyear = conf.plotsets[name].calib_toyear
            self.calib_refdate = utils.confdates_to_list(conf.plotsets[name].calib_refdate)
            self.calib_enssize = utils.csv_to_list(conf.plotsets[name].calib_enssize)
            self.fccalibsets = self._init_fc(name='calib')

        self.use_metric_name = False
        self.result = None
        self.default_cmap = None


        self.fcverifsets = self._init_fc(name='verif')

        # initialize metric arguments important for plotting
        self.clip = False
        self.ofile = conf.plotsets[name].ofile

        self.use_dask = False

        self.points = None
        if conf.plotsets[name].points is not None:
            tmp_points = utils.csv_to_list(conf.plotsets[name].points, ';')
            self.points = [list(map(float,utils.csv_to_list(point,','))) for point in tmp_points]

        self.add_verdata = conf.plotsets[name].add_verdata

        self.area_statistic = None
        self.area_statistic_function = None
        self.area_statistic_unit = None
        self.area_statistic_minvalue = None
        self.area_statistic_kind = None

        if conf.plotsets[name].area_statistic is not None:
            self.area_statistic_function = 'mean'
            self.area_statistic_unit = 'fraction'

            self.area_statistic = conf.plotsets[name].area_statistic.split(':')
            self.area_statistic_kind = self.area_statistic[0]
            if self.area_statistic_kind not in ['data', 'score']:
                raise ValueError('area_statistic need to provide information if statistic '
                                 'is calculated over data or score')
            if len(self.area_statistic)>1:
                self.area_statistic_function = self.area_statistic[1]
                if self.area_statistic_function not in ['mean', 'sum', 'median']:
                    raise ValueError('2nd argument of area_statistic need to be either'
                                     'mean, median or sum')

            if len(self.area_statistic)>2:
                self.area_statistic_unit = self.area_statistic[2]
                if self.area_statistic_unit not in ['total','fraction','percent']:
                    raise ValueError('3rd argument of area_statistic (unit)'
                                     'needs to be either total, fraction, percent')
                if self.area_statistic_unit == 'fraction' and self.area_statistic_function == 'sum':
                    utils.print_info('Setting the unit of area_statistics to fraction has no effect when using sum as function')
                    self.area_statistic_unit = 'total'

            if len(self.area_statistic)>3:
                self.area_statistic_minvalue = float(self.area_statistic[3])
                if self.area_statistic_minvalue <0 or self.area_statistic_minvalue>1:
                    raise ValueError('4th argument of area_statistic (minimum sic value)'
                                     'needs to be between 0 and 1')

        self.region_extent = conf.plotsets[name].region_extent
        self.plot_shading = conf.plotsets[name].plot_shading
        self.inset_position = conf.plotsets[name].inset_position
        self.additonal_mask = conf.plotsets[name].additonal_mask

        self.ticks = None
        self.ticklabels = None
        self.norm = None

        self.time_average = None


    def _init_fc(self, name):
        """ Initialize forecast sets either for calibration or verification data
        :param name: either verif or calib
        :return: dictionary with entries related to forecasts
        """
        fcsets = {}

        # first option: dates are given as YYYYMMDD so we can put them all in one forecast set
        if len(getattr(self,f'{name}_dates')[0]) == 8:

            # set fromyear toyear to None if set in config
            if getattr(self,f'{name}_fromyear') or getattr(self,f'{name}_toyear'):
                utils.print_info('Dates are given as YYYYMMDD so _fromyear and _toyear is ignored')
                setattr(self,f'{name}_fromyear', None)
                setattr(self, f'{name}_toyear', None)

            date = 'all'
            fcsets[date] = {}
            fcsets[date]['sdates'] = getattr(self,f'{name}_dates')

            # get cycle information for all dates
            kwargs = {
                'source': getattr(self, f'{name}_source')[0],
                'fcsystem': getattr(self, f'{name}_fcsystem')[0],
                'expname': getattr(self, f'{name}_expname')[0],
                'modelname': getattr(self, f'{name}_modelname')[0],
                'mode': getattr(self, f'{name}_mode')[0]
            }
            _cycles = [forecast_info.get_cycle(**kwargs, thisdate=_date) for _date in fcsets[date]['sdates']]
            if len(set(_cycles)) != 1:
                raise ValueError('Forecast dates are pooled from different model cycles')

            kwargs = {
                'cacherootdir': self.cacherootdir,
                'fcsystem': getattr(self, f'{name}_fcsystem')[0],
                'expname': getattr(self, f'{name}_expname')[0],
                'source': getattr(self, f'{name}_source')[0],
                'mode': getattr(self, f'{name}_mode')[0],
                'modelname': getattr(self, f'{name}_modelname')[0],
                'cycle': _cycles[0]
            }

            fcsets[date]['cachedir'] = dataobjects.define_fccachedir(**kwargs)
            fcsets[date]['enssize'] = getattr(self, f'{name}_enssize')[0]


        # second option: dates are given as MMDD and fromyear toyear is given so we construct all dates here
        # and have one forecast set for each initialization date MM/DD
        else:
            for date in getattr(self,f'{name}_dates'):

                _dates_tmp = [f'{_year}{date}' for _year in range(int(getattr(self,f'{name}_fromyear')),
                                                        int(getattr(self,f'{name}_toyear')) + 1)]

                # remove dates which are not defined, e.g. 29.2 for non-leap years
                _dates = []
                for d in _dates_tmp:
                    try:
                        _dates.append(dt.datetime.strptime(d, '%Y%m%d'))
                    except:
                        pass
                if _dates:
                    fcsets[date] = {}
                else:
                    utils.print_info(f'No forecasts for Date {date}')

                fcsets[date]['sdates'] = [d.strftime('%Y%m%d') for d in _dates]

                # get cycle information for all dates
                kwargs = {
                    'source': getattr(self, f'{name}_source')[0],
                    'fcsystem': getattr(self, f'{name}_fcsystem')[0],
                    'expname': getattr(self, f'{name}_expname')[0],
                    'modelname': getattr(self, f'{name}_modelname')[0],
                    'mode': getattr(self, f'{name}_mode')[0]
                }

                if 'fc' in getattr(self,f'{name}_mode'):
                    _cycles = [forecast_info.get_cycle(**kwargs, thisdate=_date) for _date in fcsets[date]['sdates']]
                elif 'hc' in getattr(self,f'{name}_mode'):
                    _refdates = getattr(self, f'{name}_refdate')
                    _cycles = [forecast_info.get_cycle(**kwargs, thisdate=_date) for _date in _refdates]

                if len(set(_cycles)) != 1:
                    raise ValueError('Forecast dates are pooled from different model cycles')

                kwargs = {
                    'cacherootdir': self.cacherootdir,
                    'fcsystem': getattr(self, f'{name}_fcsystem')[0],
                    'expname': getattr(self, f'{name}_expname')[0],
                    'source': getattr(self, f'{name}_source')[0],
                    'mode': getattr(self, f'{name}_mode')[0],
                    'modelname': getattr(self, f'{name}_modelname')[0],
                    'cycle': _cycles[0]
                }

                fcsets[date]['cachedir'] = dataobjects.define_fccachedir(**kwargs)
                fcsets[date]['enssize'] = getattr(self, f'{name}_enssize')[0]

        return fcsets



    def _load_verif_dummy(self, average_dim=None):
        """
        Load the dummy verification file in case dates are not available for forecast
        :return: xr DataArray
        """

        _filename = f'{self.obscachedir}/{self.verif_name}.nc'
        da = xr.open_dataarray(_filename)
        da = da.expand_dims(dim={"member": 1, "date":1, "inidate":1})

        if None not in average_dim :
            for d in average_dim:
                da = da.mean(dim=d)
        return da

    def _load_data(self, fcset, datatype, grid=None,
                   average_dim=None, target=None):
        """ load forecast or verification data
        :param fcset: forecast sets created in _init_fc
        :param datatype: fc or verif
        :param grid: 'native' or None
        :param average_dim: list of dimensions to average when loading data
        :param target: target days to be selected (usually determined by neamlist), but can be
        set to 'i:0' for persistence
        :return:
        """
        if target is None:
            target = self.target
        elif target != 'i:0':
            raise ValueError('Target can be either None or i:0')

        if grid is None:
            grid = self.grid

        filename = self._filenaming_convention(datatype)

        _all_list = []
        _inits = []
        for fcname in fcset:
            _inits.append(fcname)
            _da_date_list = []
            _fcdates = fcset[fcname]['sdates']
            for _date in _fcdates:
                _dtdate = [utils.string_to_datetime(_date)]
                _dtseldates = utils.create_list_target_verif(target, _dtdate)
                _seldates = [utils.datetime_to_string(dtdate) for dtdate in _dtseldates]

                if datatype == 'fc':
                    _members = range(int(fcset[fcname]['enssize']))
                else:
                    _members = range(1)

                _da_ensmem_list = []
                for _member in _members:

                    if datatype == 'verif':
                        _da_seldate_list = []
                        for _seldate in _seldates:
                            _filename = f"{self.obscachedir}/" \
                                        f"{filename.format(_seldate, self.params, self.grid)}"
                            _da_file = self._load_file(_filename)
                            _da_seldate_list.append(_da_file)
                        _da_file = xr.concat(_da_seldate_list, dim='time')

                    elif datatype == 'fc':
                        _filename = f"{fcset[fcname]['cachedir']}/" \
                                    f"{filename.format(_date, _member, self.params, grid)}"

                        _da_file = self._load_file(_filename, _seldates)




                    # utils.print_info('CAUTION TEMPORARY IMPLEMENTATION')
                    # self.time_average = 'QS-DEC'
                    #
                    # if self.time_average is not None:
                    #     _da_file = _da_file.resample(time=self.time_average).mean(dim="time")

                    _da_file = self.convert_time_to_lead(_da_file, target=target)

                    _da_ensmem_list.append(_da_file)
                    _ensdim = xr.DataArray(_members, dims='member', name='member')
                _da_date = xr.concat(_da_ensmem_list, dim=_ensdim)
                if 'member' in average_dim:
                    _da_date = _da_date.mean(dim='member')
                    _da_date = _da_date.load()
                _da_date_list.append(_da_date)


            _date_dim = xr.DataArray(range(len(_fcdates)), dims='date', name='date')
            da_fc = xr.concat(_da_date_list, dim=_date_dim)
            if 'date' in average_dim:
                da_fc = da_fc.mean(dim='date')
                _all_list.append(da_fc)
            else:
                _all_list.append(da_fc.sortby(da_fc.date))

        _init_dim = xr.DataArray(_inits, dims='inidate', name='inidate')
        da_init = xr.concat(_all_list, dim=_init_dim)
        if 'inidate' in average_dim:
            da_init = da_init.mean(dim='inidate')

        return da_init






    def load_fc_data(self, name, grid=None, average_dim=None):
        """
        load forecast data
        :param name: calib or verif
        :param grid: 'native' or None
        :param average_dim: list of dimensions to average when loading data
        :return: xarray dataArray
        """
        utils.print_info(f"READING FC DATA FOR {name}")
        average_dim = [average_dim] if not(isinstance(average_dim, list)) else average_dim
        return self._load_data(getattr(self, f'fc{name}sets'), datatype='fc', grid=grid,
                               average_dim=average_dim)

    def load_verif_data(self, name, average_dim=None, target=None):
        """
        load verification data
        :param name: calib or verif
        :param average_dim: list of dimensions to average when loading data
        :param target: target days to be selected (usually determined by neamlist), but can be
        set to 'i:0' for persistence
        :return: xarray dataArray
        """
        utils.print_info(f"READING OBSERVATION DATA FOR {name}")
        average_dim = [average_dim] if not (isinstance(average_dim, list)) else average_dim
        if 'grid' in self.verif_name and name != 'calib':
            return self._load_verif_dummy(average_dim)

        return self._load_data(getattr(self,f'fc{name}sets'), datatype='verif',
                               average_dim=average_dim, target=target)




    def get_filename_metric(self):
        """ Create filename for saved metricfile """
        if self.use_metric_name:
            oname = f'{self.metricname}.nc'
            return f'{self.metricdir}/{self.metricname}/{oname}'
        raise ValueError('Only use_metric_name = True implemented so far')


    def save(self):
        """ Save metric to metricdir """
        _ofile = self.get_filename_metric()
        utils.make_dir(os.path.dirname(_ofile))

        result = self.result


        if isinstance(result, list):
            for fi, file in enumerate(result):
                utils.print_info(f'Saving metric file {_ofile.replace(".nc",f"_{fi}.nc")}')
                file.to_netcdf(_ofile.replace('.nc',f'_{fi}.nc'))
        else:
            utils.print_info(f'Saving metric file {_ofile}')
            result.to_netcdf(_ofile)
    def gettype(self):
        """ Determine typ of plot (timeseries or mapplot) """
        if self.area_statistic or self.plottype in ['ice_distance']:
            return 'ts'
        else:
            return 'map'


    def convert_time_to_lead(self,_da=None, target=None):
        """
        Convert time variable to steps
        :param _da: xr DataArray
        :return: xr DataArray
        """
        if self.time_average is None:
            target_as_list = utils.create_list_target_verif(target, as_list=True)
            _da = _da.assign_coords(time=target_as_list)
        elif 'QS' in self.time_average:
            _da = _da.assign_coords(time=_da.time.dt.month.values+1)
        elif 'MS' in self.time_average:
            _da = _da.assign_coords(time=_da.time.dt.month.values)
        else:
            _da = _da.assign_coords(time=range(len(_da.time.values)))
        return _da

    def _load_file(self, _file,_seldate=None):
        """
        load single xarray data file and select specific timestep if needed
        Use dask if selected
        :param _file: filename
        :param _seldate: timestep(s) to load
        :return: xarray DataArray
        """


        if self.use_dask:
            #_da_file = xr.open_dataarray(_file, chunks={'time':1, 'xc':50}) #chunks='auto')
            _da_file = xr.open_dataarray(_file, chunks='auto')
        else:
            _da_file = xr.open_dataarray(_file)

        if _seldate:
            _da_file = _da_file.sel(time=_da_file.time.dt.strftime("%Y%m%d").isin(_seldate))

        return _da_file

    @staticmethod
    def area_cut(ds, lon1, lon2, lat1, lat2):
        """
        Set values outside lon/lat regions specified here to NaN values
        :param ds: input xarray DataArray
        :param lon1: east longitude
        :param lon2: west longitude
        :param lat1: south latitude
        :param lat2: north latitude
        :return: maksed dataArray
        """

        if 'longitude' in ds.coords:
            lon_name = 'longitude'
            lat_name = 'latitude'
        else:
            lon_name = 'lon'
            lat_name = 'lat'

        if lon1 > lon2:
            data_masked1 = ds.where((ds[lat_name] > lat1) & (ds[lat_name] <= lat2)
                                     & (ds[lon_name] > lon1) & (ds[lon_name] < 180))
            data_masked2 = ds.where((ds[lat_name] > lat1) & (ds[lat_name] <= lat2)
                                     & (ds[lon_name] >= -180) & (ds[lon_name] < lon2))

            combined_mask = np.logical_or(~np.isnan(data_masked1), ~np.isnan(data_masked2))
            _data = xr.where(combined_mask, ds, float('nan'))
        else:
            _data = ds.where((ds[lat_name] >= lat1) & (ds[lat_name] <= lat2)
                             & (ds[lon_name] >= lon1) & (ds[lon_name] <= lon2))

        return _data
    def calc_area_statistics(self, datalist, ds_mask, minimum_value=0, statistic='mean'):
        """
        Calculate area statistics (mean/sum) for verif and fc using a combined land-sea-mask from both datasets
        :param datalist: list of xarray objects for verif and fc
        :param ds_mask: combined land-sea-mask from fc and verif (using mask_lsm function)
        :param minimum_value: only count grid cells with sea-ice larger than this value
        :param statistic: derive mean or sum
        :return: list of xarray objects (verif and fc) for which statistic has been applied to
        """


        # mask region of interest if selected
        if self.region_extent:
            _region_bounds = utils.csv_to_list(self.region_extent)
            _region_bounds = [float(r) for r in _region_bounds]
            lon1 = _region_bounds[0]
            lon2 = _region_bounds[1]
            lat1 = _region_bounds[2]
            lat2 = _region_bounds[3]

            datalist = [self.area_cut(d, lon1,lon2,lat1,lat2) for d in datalist]
            ds_mask_reg  =self.area_cut(ds_mask, lon1,lon2,lat1,lat2)
        else:
            ds_mask_reg = ds_mask


        if minimum_value:
            utils.print_info(f'Setting grid cells with sic>{minimum_value} to 1')
            datalist_mask = [xr.where(d > minimum_value, 1, 0) for d in datalist]
        else:
            datalist_mask = datalist


        # CELL AREA
        xdiff = np.unique(np.diff(datalist_mask[0]['xc'].values))
        ydiff = np.unique(np.diff(datalist_mask[0]['yc'].values))
        if len(xdiff) > 1 or len(ydiff) > 1:
            raise ValueError('XC or YC coordinates are not evenly spaced')

        xdiff = np.abs(xdiff[0] / 1000)
        ydiff = np.abs(ydiff[0] / 1000)
        cell_area = xdiff * ydiff

        if statistic == 'mean':
            datalist_out = [d.mean(dim=('xc', 'yc'), skipna=True) for d in datalist_mask]
            if self.area_statistic_unit == 'total':
                datalist_out = [d*cell_area for d in datalist_out]
        elif statistic == 'sum':
            datalist_out = [d.sum(dim=('xc', 'yc'), skipna=True)*cell_area for d in datalist_mask]
        elif statistic == 'median':
            datalist_out = [d.median(dim=('xc', 'yc'), skipna=True) for d in datalist_mask]
        else:
            raise ValueError(f'statistic can be either mean or sum not {statistic}')



        return datalist_out, ds_mask_reg.rename('lsm')


    def mask_lsm(self, datalist):
        """ Create land-sea mask from two datasets (usually observatiosn and fc)
        :param datalist: list of dataArrays (first two will be used to generate combined lsm)
        :return: list masked dataArrays from datalist
        """
        ds_mask = self._create_combined_mask(datalist[0],
                                             datalist[1])

        if self.additonal_mask:
            utils.print_info('APPLYING ADDITIONAL MASK')
            ds_additonal_mask = xr.open_dataarray(self.additonal_mask)

            #datalist = [d.where(~np.isnan(ds_additonal_mask)) for d in datalist]
            ds_mask = ds_mask.where(~np.isnan(ds_additonal_mask))

        datalist_mask = [d.where(~np.isnan(ds_mask)) for d in datalist]

        if 'member' in datalist_mask[0].dims:
            len1 = len(np.argwhere(~np.isnan(datalist_mask[0].isel(member=0, time=0).values)))
        else:
            len1 = len(np.argwhere(~np.isnan(datalist_mask[0].isel(time=0).values)))
        len2 = len(np.argwhere(~np.isnan(datalist_mask[1].isel(time=0).values)))
        if len1 != len2:
            raise ValueError(f'Masking produces observations and forecasts with different number of'
                             f'NaN cells {len1} {len2}')

        return datalist_mask, ds_mask.rename('lsm-full')

    @staticmethod
    def _create_combined_mask(_ds_verif, _ds_fc):
        """
        Create a mask for cells which are set to NaN in verification or forecast data
        :param _ds_verif: verification xarray dataarray
        :param _ds_fc: forecast xarray dataarray
        :return: combined mask as xarray (boolean array)
        """

        for dim in ['inidate','date']:
            if dim in _ds_fc.dims:
                _ds_fc = _ds_fc.isel({dim:0})
            if dim in _ds_verif.dims:
                _ds_verif = _ds_verif.isel({dim:0})


        _ds_verif_tmp = xr.where(np.isnan(_ds_verif), 1, 0)


        if 'member' in _ds_verif_tmp.dims:
            _ds_verif_tmp = _ds_verif_tmp.sum(dim='member')
        _ds_verif_mask = xr.where(_ds_verif_tmp.sum(dim='time') == 0, True, False)


        _ds_fc_tmp = xr.where(np.isnan(_ds_fc), 1, 0)
        if 'member' in _ds_fc_tmp.dims:
            _ds_fc_tmp = _ds_fc_tmp.sum(dim='member')
        _ds_fc_mask = xr.where(_ds_fc_tmp.sum(dim='time') == 0, True, False)

        combined_mask = np.logical_and(_ds_verif_mask == 1, _ds_fc_mask == 1)
        combined_mask = xr.where(combined_mask,1,float('nan'))

        return combined_mask
