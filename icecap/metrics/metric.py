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
import pandas as pd

import metrics.metric_utils as mutils
import dataobjects
import utils
import forecast_info

class BaseMetric(dataobjects.DataObject):
    """Generic Metric Object inherited by each specific metric"""

    def __init__(self, name, conf):
        super().__init__(conf)



        self.metricname = name
        if conf.plotsets[name].verif_ref is not None:
            self.verif_name = conf.plotsets[name].verif_ref

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



        self.use_metric_name = False
        self.result = None
        self.default_cmap = None

        # initialize metric arguments important for plotting
        self.clip = False
        self.ofile = conf.plotsets[name].ofile

        self.use_dask = False

        self.points = None

        self.add_verdata = conf.plotsets[name].add_verdata
        self.add_verdata_nomask = conf.plotsets[name].add_verdata_nomask

        if self.add_verdata_nomask == 'yes' and self.plottype != 'ice_extent':
            utils.print_info('Setting add_verdata_nomask is only possible for ice_extent')
            self.add_verdata_nomask = 'no'

        self.area_statistic_conf = conf.plotsets[name].area_statistic
        self.area_statistic = None
        self.area_statistic_function = None
        self.area_statistic_unit = None
        self.area_statistic_kind = None

        self.region_extent = conf.plotsets[name].region_extent
        self.nsidc_region = conf.plotsets[name].nsidc_region
        self.plot_shading = conf.plotsets[name].plot_shading
        self.inset_position = conf.plotsets[name].inset_position
        self.additonal_mask = conf.plotsets[name].additonal_mask

        self.etcdir = conf.etcdir

        self.ticks = None
        self.ticklabels = None
        self.norm = None

        self.time_average = None

        # copy attributes from entry
        if conf.plotsets[name].copy_id is not None:
            copy_metric = BaseMetric(conf.plotsets[name].copy_id, conf)


            for key,value in self.__dict__.items():
                if value is None or value == [None]:
                    setattr(self, key, getattr(copy_metric, key))
                elif value == 'None':
                    setattr(self, key, None)



        if len(self.verif_enssize) != 1:
            raise ValueError('enssize can be either length 1 (all dates/systems with same ensemble size)')

        # initialize calibration forecasts
        self.calib = False
        self.calib_method = conf.plotsets[name].calib_method
        if self.calib_method is not None:
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

        if conf.plotsets[name].points is not None:
            tmp_points = utils.csv_to_list(conf.plotsets[name].points, ';')
            self.points = [list(map(float,utils.csv_to_list(point,','))) for point in tmp_points]


        if self.area_statistic_conf is not None:
            self.area_statistic_function = 'mean'
            self.area_statistic_unit = 'fraction'

            self.area_statistic = self.area_statistic_conf.split(':')
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
        else:
            self.area_statistic = None
            self.area_statistic_function = None
            self.area_statistic_unit = None
            self.area_statistic_kind = None

        self.fcverifsets = self._init_fc(name='verif')






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
            if 'hc' in getattr(self, f'{name}_mode'):
                _refdates = getattr(self, f'{name}_refdate')
                _cycles = [forecast_info.get_cycle(**kwargs, thisdate=_date) for _date in _refdates]
            else:
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

                fcsets[date] = {}
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
        Load the dummy verification file (specific date for obs))
        :return: xr DataArray
        """
        if self.verif_name in ['osi-cdr', 'osi-401-b']:
            filename = self._filenaming_convention('verif')
            _filename = f"{self.obscachedir}/" \
                        f"{filename.format('20171130', self.params, self.grid)}"
            da = xr.open_dataarray(_filename)
            da = da.expand_dims(dim={"member": [1], "date": [1], "inidate": [1]})
            da['time'] = ['dummy']
        else:
            raise NotImplementedError(f'No dummy observations specified for {self.verif_name}')


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
                if sorted(_seldates) != _seldates:
                    raise ValueError('Target needs to be sorted')


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
                            if os.path.isfile(_filename):
                                _da_file = self._load_file(_filename)
                            else:
                                if not _da_seldate_list:
                                    utils.print_info('No verification data found')
                                    return None
                                else:
                                    _da_file = xr.full_like(_da_seldate_list[0],
                                                            np.nan)
                                    _da_file['time'] = [pd.to_datetime(_seldate).to_numpy()]

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
                file.load().to_netcdf(_ofile.replace('.nc',f'_{fi}.nc'))
        else:
            utils.print_info(f'Saving metric file {_ofile}')
            result.load().to_netcdf(_ofile)
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


    def calc_area_statistics(self, datalist, ds_mask, statistic='mean'):
        """
        Calculate area statistics (mean/sum) for verif and fc using a combined land-sea-mask from both datasets
        :param datalist: list of xarray objects for verif and fc
        :param ds_mask: combined land-sea-mask from fc and verif (using mask_lsm function)
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

            datalist = [mutils.area_cut(d, lon1,lon2,lat1,lat2) for d in datalist]
            ds_mask_reg = mutils.area_cut(ds_mask, lon1,lon2,lat1,lat2)
        elif self.nsidc_region:

            utils.print_info('Selecting NSIDC region')
            ifile = f"{self.etcdir}/nsidc_{self.verif_name.replace('-grid','')}.nc"
            try:
                ds_nsidc = xr.open_dataarray(ifile)
            except:
                raise FileNotFoundError(f'NSIDC region file {ifile} not found ')

            region_number = mutils.get_nsidc_region(ds_nsidc, self.nsidc_region)
            ds_mask_reg = xr.where(ds_nsidc == region_number,ds_mask,float('nan'))
            ds_mask_reg = ds_mask_reg.drop([i for i in ds_mask_reg.coords if i not in ds_mask_reg.dims])
            datalist = [d.where(~np.isnan(ds_mask_reg)) for d in datalist]

        else:
            ds_mask_reg = ds_mask
            datalist = [d.where(~np.isnan(ds_mask_reg)) for d in datalist]

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
            datalist_out = [d.sum(dim=('xc', 'yc'), skipna=True, min_count=1)*cell_area for d in datalist_mask]
        elif statistic == 'median':
            datalist_out = [d.median(dim=('xc', 'yc'), skipna=True) for d in datalist_mask]
        else:
            raise ValueError(f'statistic can be either mean or sum not {statistic}')



        return datalist_out, ds_mask_reg.rename('lsm')


    def mask_lsm(self, datalist):
        """ Create land-sea mask from two datasets (usually observations and fc)
        :param datalist: list of dataArrays (first two will be used to generate combined lsm)
        :return: list masked dataArrays from datalist
        """
        ds_mask = mutils.create_combined_mask(datalist[0],
                                             datalist[1])

        if self.additonal_mask:
            utils.print_info('APPLYING ADDITIONAL MASK')
            ds_additonal_mask = xr.open_dataarray(self.additonal_mask)

            #datalist = [d.where(~np.isnan(ds_additonal_mask)) for d in datalist]
            ds_mask = ds_mask.where(~np.isnan(ds_additonal_mask))

        datalist_mask = [d.where(~np.isnan(ds_mask)) for d in datalist]

        fcdata = datalist_mask[0]
        for d in ['member','date']:
            if d not in fcdata.dims:
                fcdata = fcdata.expand_dims(d)
        fcdata = fcdata.isel(member=0, date=0)

        len1 = len(np.argwhere(~np.isnan(datalist_mask[1].isel(time=0).values)))
        len2 = len(np.argwhere(~np.isnan(datalist_mask[1].isel(time=0).values)))
        if len1 != len2:
            raise ValueError(f'Masking produces observations and forecasts with different number of'
                             f'NaN cells {len1} {len2}')

        return datalist_mask, ds_mask.rename('lsm-full')

    def mask_lsm_new(self, ds_obs, ds_fc):
        """ Create land-sea mask from two datasets (usually observations and fc)
        :param datalist: list of dataArrays (first two will be used to generate combined lsm)
        :return: list masked dataArrays from datalist
        """
        alldims = ['member', 'date', 'inidate']

        # remove unnecessary dimensions
        fc_dims = {d:0 for d in alldims if d in ds_fc.dims}
        fc_dims['time'] = [0]
        ds_fc = ds_fc.isel(fc_dims)
        obs_dims = {d: 0 for d in alldims if d in ds_obs.dims}
        obs_dims['time'] = [0]
        ds_obs = ds_obs.isel(obs_dims)

        ds_mask = mutils.create_combined_mask(ds_obs,
                                             ds_fc)

        if self.additonal_mask:
            utils.print_info('APPLYING ADDITIONAL MASK')
            ds_additonal_mask = xr.open_dataarray(self.additonal_mask)

            #datalist = [d.where(~np.isnan(ds_additonal_mask)) for d in datalist]
            ds_mask = ds_mask.where(~np.isnan(ds_additonal_mask))

        return ds_mask.rename('lsm-full'), ds_obs


    def process_data_for_metric(self, average_dims,
                                persistence=False,
                                sice_threshold=None):
        """
        Process forecast/observation data for metric (load data, calibrate forecast etc)
        :param average_dims: dimesnions over which to average when loading data
        :return: dictionary of forecast/observation data
        """

        dict_out = {}

        # read verdata/fc data for verif
        da_fc_verif = self.load_fc_data('verif',
                                        average_dim=average_dims)
        da_verdata_verif_raw = self.load_verif_data('verif',
                                                average_dim=average_dims)

        if da_verdata_verif_raw is None:
            da_verdata_verif_raw = self._load_verif_dummy(average_dim=average_dims)
            if self.add_verdata == 'yes':
                utils.print_info('No verification data found --> add_verdata set to no')
                self.add_verdata = 'no'

        data = [da_fc_verif, da_verdata_verif_raw.copy(deep=True)]

        # read verdata/fc data for calib
        if self.calib:
            da_fc_calib = self.load_fc_data('calib', average_dim=average_dims)
            da_verdata_calib = self.load_verif_data('calib', average_dim=['member'])
            data.append(da_fc_calib)
            data.append(da_verdata_calib)

        if persistence:
            da_persistence = self.load_verif_data('verif', target='i:0').isel(member=0, time=0)
            data.append(da_persistence)

        lsm_full, da_coords = self.mask_lsm_new(da_verdata_verif_raw, da_fc_verif)
        data = [d.where(~np.isnan(lsm_full)) for d in data]
        dict_out['lsm_full'] = lsm_full

        # assign back to xarray objects
        da_fc_verif = data[0]
        da_verdata_verif = data[1]



        if persistence:
            da_persistence = data[2]


        if sice_threshold is not None:
            # 1. calibrate first for each grid cell and add to datalist
            # 2. add persistence to datalist
            # 3. set values to 1
            # 3. average all data in list

            datalist = [da_fc_verif, da_verdata_verif]
            # now calibrate if desired
            if self.calib:
                da_fc_calib = data[2]
                da_verdata_calib = data[3]
                da_fc_verif_bc = self.calibrate(da_verdata_calib, da_fc_calib,
                                                da_fc_verif,
                                                method=self.calib_method)

                datalist += [da_fc_calib, da_verdata_calib, da_fc_verif_bc]


            if persistence:
                datalist.append(da_persistence)

            # 2nd step
            utils.print_info(f'Setting all grid cells with sea ice > {sice_threshold} to 1')
            datalist_thresh = [xr.where(d > sice_threshold, 1, 0) for d in datalist]
            datalist = [datalist_thresh[d].where(~np.isnan(datalist[d])) for d in range(len(datalist))]




            if 'edge' in self.plottype:
                utils.print_info('Edge detection algorithm')
                da_verdata_verif_ice_edge = mutils.detect_edge(da_verdata_verif, None)
                da_verdata_verif_ice_ext_edge = mutils.detect_extended_edge(da_verdata_verif_ice_edge)
                datalist = [d.where(da_verdata_verif_ice_ext_edge == 1) for d in datalist]


            # 3rd
            if self.area_statistic_kind == 'data':
                datalist, lsm = self.calc_area_statistics(datalist, lsm_full,
                                                      statistic=self.area_statistic_function)
                dict_out['lsm'] = lsm


            dict_out['da_fc_verif'] = datalist[0]
            dict_out['da_verdata_verif'] = datalist[1]

            if self.calib:
                dict_out['da_fc_calib'] = datalist[2]
                dict_out['da_verdata_calib'] = datalist[3]
                dict_out['da_fc_verif_bc'] = datalist[4]


            if persistence:
                dict_out['da_verdata_persistence'] = datalist[-1]
                if self.plottype == 'ice_extent':
                    dict_out['da_verdata_verif_raw'] = datalist[-2]

            if self.plottype == 'ice_extent':
                da_verdata_verif_raw_thresh = xr.where(da_verdata_verif_raw > sice_threshold, 1, 0)
                da_verdata_verif_raw_thresh = da_verdata_verif_raw_thresh.where(~np.isnan(da_verdata_verif_raw))
                lsm_obs, _ = self.mask_lsm_new(da_verdata_verif_raw, da_verdata_verif_raw)
                data_raw, _ = self.calc_area_statistics([da_verdata_verif_raw_thresh], lsm_obs,
                                                          statistic=self.area_statistic_function)
                dict_out['da_verdata_verif_raw'] = data_raw[0]

        else:
            # 1. use datalist directly
            # 2. average all data in list
            # 2. calibrate

            datalist = data

            if 'edge' in self.plottype:
                utils.print_info('Edge detection algorithm')
                da_verdata_verif_ice_edge = mutils.detect_edge(da_verdata_verif)
                da_verdata_verif_ice_ext_edge = mutils.detect_extended_edge(da_verdata_verif_ice_edge)
                datalist = [d.where(da_verdata_verif_ice_ext_edge == 1) for d in datalist]


            # derive area statistics if desired for data itself
            if self.area_statistic_kind == 'data':
                datalist, lsm = self.calc_area_statistics(datalist, lsm_full,
                                                      statistic=self.area_statistic_function)
                dict_out['lsm'] = lsm

            # reassign data list items to individual xarray objects
            da_fc_verif = datalist[0]
            da_verdata_verif = datalist[1]
            dict_out['da_verdata_verif'] = da_verdata_verif
            dict_out['da_fc_verif'] = da_fc_verif

            # now calibrate if desired
            if self.calib:
                da_fc_calib = datalist[2]
                da_verdata_calib = datalist[3]
                da_fc_verif_bc = self.calibrate(da_verdata_calib, da_fc_calib,
                                                da_fc_verif,
                                                method=self.calib_method)

                dict_out['da_fc_verif_bc'] = da_fc_verif_bc
                dict_out['da_verdata_calib'] = da_verdata_calib
                dict_out['da_fc_calib'] = da_fc_calib



            if persistence:
                dict_out['da_verdata_persistence'] = datalist[-1]

        # return this array as it definitely still has all attributes needed for plotting
        dict_out['da_coords'] = da_coords

        return dict_out


    def calibrate(self, da_verdata_calib, da_fc_calib, da_fc_verif, method=None):
        """
        Apply calibration to forecast to be verified
        :param da_verdata_calib: calibration observation data
        :param da_fc_calib: calibration forecast data
        :param da_fc_verif: forecast data to be calibrated
        :param method: method used for calibration
        :return: calibrated forecast
        """
        utils.print_info(f'Calibrating using method: {method}')
        allowed_methods = ['mean', 'mean+trend','anom']
        if method not in allowed_methods:
            raise ValueError(f'Method calibration needs to be one of {allowed_methods}')

        if method == 'mean' or method == 'anom':
            for dim in ['inidate', 'date','member']:
                if dim in da_fc_calib.dims:
                    da_fc_calib = da_fc_calib.mean(dim=dim)
                if dim in da_verdata_calib.dims:
                    da_verdata_calib = da_verdata_calib.mean(dim=dim)

            if method == 'mean':
                utils.print_info('Calibration mean')
                bias_calib = da_fc_calib - da_verdata_calib
                fc_verif_bc = da_fc_verif - bias_calib
            elif method == 'anom':
                utils.print_info('Calibration anomalies')
                fc_verif_bc = da_fc_verif - da_fc_calib

            return fc_verif_bc


        if method == 'mean+trend':
            utils.print_info('Calibration mean+trend')
            for dim in ['inidate', 'member']:
                if dim in da_fc_calib.dims:
                    da_fc_calib = da_fc_calib.mean(dim=dim)
                if dim in da_verdata_calib.dims:
                    da_verdata_calib = da_verdata_calib.mean(dim=dim)

            bias_calib = da_fc_calib - da_verdata_calib

            if 'xc' not in bias_calib.dims:
                bias_calib = bias_calib.expand_dims(['xc', 'yc'])


            da_slope, da_intercept, da_pvalue = mutils.compute_linreg(bias_calib)

            years_calib = np.arange(int(self.calib_fromyear), int(self.calib_toyear) + 100)


            if self.verif_fromyear is not None:
                years_verif = np.arange(int(self.verif_fromyear), int(self.verif_toyear)+1)
            else:
                verif_year = self.verif_dates[0][:4]
                years_verif = np.arange(int(verif_year), int(verif_year) + 1)
            years_verif_int = np.intersect1d(years_verif, years_calib, return_indices=True)[2]

            orgdates = da_fc_verif['date'].values[:]
            da_fc_verif['date'] = years_verif_int

            correction = da_slope*da_fc_verif['date'] + da_intercept
            fc_verif_bc = da_fc_verif - correction
            fc_verif_bc['date'] = orgdates
            fc_verif_bc = fc_verif_bc.squeeze()

            return fc_verif_bc
