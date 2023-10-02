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
        self.verif_modelname = utils.csv_to_list(conf.plotsets[name].modelname)
        self.verif_expname = utils.csv_to_list(conf.plotsets[name].verif_expname)
        self.verif_mode = utils.csv_to_list(conf.plotsets[name].verif_mode)

        self.verif_fcsystem = utils.csv_to_list(conf.plotsets[name].verif_fcsystem)
        self.verif_source = utils.csv_to_list(conf.plotsets[name].verif_source)
        self.verif_dates = utils.plotdates_to_list(conf.plotsets[name].verif_dates)
        self.conf_verif_dates = conf.plotsets[name].verif_dates
        self.verif_fromyear = conf.plotsets[name].verif_fromyear
        self.verif_toyear = conf.plotsets[name].verif_toyear
        self.verif_refyear = conf.plotsets[name].verif_refdate





        self.verif_enssize = utils.csv_to_list(conf.plotsets[name].verif_enssize)
        if len(self.verif_enssize) == 1:
            self.verif_enssize = [self.verif_enssize[0] for n in range(len(self.verif_dates))]
        elif len(self.verif_enssize) != len(self.verif_dates):
            raise ValueError('enssize can be either length 1 (all dates/systems with same ensemble size)'
                             'or must have the same length as dates')


        # initialize calibration forecasts
        self.calib = False
        if conf.plotsets[name].calib_dates is not None:
            self.calib = True
            self.calib_modelname = self.verif_modelname
            self.calib_expname = self.verif_expname
            self.calib_mode = utils.csv_to_list(conf.plotsets[name].calib_mode)
            self.calib_source = self.verif_source
            self.calib_fcsystem = self.verif_fcsystem
            self.calib_dates = utils.plotdates_to_list(conf.plotsets[name].calib_dates)
            self.conf_calib_dates = conf.plotsets[name].calib_dates
            self.calib_fromyear = conf.plotsets[name].calib_fromyear
            self.calib_toyear = conf.plotsets[name].calib_toyear
            self.calib_refyear = conf.plotsets[name].calib_refdate
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



    def _init_fc(self, name):
        """ Initialize forecast sets either for calibration or verification data
        :param name: eitehr verif or calib
        :return: dictionary with entries related to forecasts
        """
        fcsets = {}
        for ifc, date in enumerate(getattr(self,f'{name}_dates')):
            fcsets[date] = {}
            _dtfromdate = [dt.datetime.strptime(getattr(self,f'{name}_fromyear') +
                                               date, '%Y%m%d')]
            _dttodate = [dt.datetime.strptime(getattr(self,f'{name}_toyear') + date, '%Y%m%d')]
            _dates = utils.make_hc_datelist(_dtfromdate, _dttodate)

            fcsets[date]['sdates'] = [d.strftime('%Y%m%d') for d in _dates]

            cycledate = getattr(self,f'{name}_fromyear') + date

            # for hc refdate can be either a YYYY string or YYYYMMDD string
            # for the former add MMDD from date variable
            if 'hc' in getattr(self,f'{name}_mode'):
                cycledate = getattr(self,f'{name}_refyear')
                if len(cycledate) == 4:
                    cycledate += date


            kwargs = {
                'source': getattr(self,f'{name}_source')[0],
                'fcsystem': getattr(self,f'{name}_fcsystem')[0],
                'expname': getattr(self,f'{name}_expname')[0],
                'modelname': getattr(self,f'{name}_modelname')[0],
                'mode': getattr(self,f'{name}_mode')[0],
                'thisdate': cycledate
            }
            cycle = forecast_info.get_cycle(**kwargs)

            kwargs = {
                'cacherootdir': self.cacherootdir,
                'fcsystem': getattr(self,f'{name}_fcsystem')[0],
                'expname': getattr(self,f'{name}_expname')[0],
                'refdate': date,
                'source': getattr(self,f'{name}_source')[0],
                'mode': getattr(self,f'{name}_mode')[0],
                'modelname': getattr(self, f'{name}_modelname')[0],
                'cycle': cycle
            }

            fcsets[date]['cachedir'] = dataobjects.define_fccachedir(**kwargs)
            fcsets[date]['enssize'] = getattr(self,f'{name}_enssize')[ifc]

        return fcsets




    def _load_verif(self, fcset):
        """ load verification data """

        filename = self._filenaming_convention('verif')
        _all_list = []
        _inits = []

        for fcname in fcset:
            _inits.append(fcname)
            _da_date_list = []
            _fcdates = fcset[fcname]['sdates']


            for _date in _fcdates:
                _dtdate = [utils.string_to_datetime(_date)]
                _dtseldates = utils.create_list_target_verif(self.target, _dtdate)
                _seldates = [utils.datetime_to_string(dtdate) for dtdate in _dtseldates]

                _da_seldate_list = []
                for _seldate in _seldates:
                    _members = range(1)
                    _da_ensmem_list = []
                    for _member in _members:
                        _filename = f"{self.obscachedir}/" \
                                    f"{filename.format(_seldate, self.params, self.grid)}"

                        if self.use_dask:
                            _da_ensmem_list.append(xr.open_dataarray(_filename, chunks='auto'))
                        else:
                            _da_ensmem_list.append(xr.open_dataarray(_filename))
                    _ensdim = xr.DataArray(_members, dims='member', name='member')
                    _da_member = xr.concat(_da_ensmem_list, dim=_ensdim)
                    _da_seldate_list.append(_da_member)

                _da_date = xr.concat(_da_seldate_list, dim='time')
                _da_date = self.convert_time_to_lead(_da_date)

                _da_date_list.append(_da_date)

            _date_dim = xr.DataArray(range(len(_fcdates)), dims='date', name='date')
            da_fc = xr.concat(_da_date_list, dim=_date_dim)
            _all_list.append(da_fc.sortby(da_fc.date))

        _init_dim = xr.DataArray(_inits, dims='inidate', name='inidate')
        da_init = xr.concat(_all_list, dim=_init_dim)

        # set nan values to zero in obs files
        da_init = da_init.where(~da_init.isnull(), 0)

        return da_init

    def load_verif_fc(self, name, grid=None):
        """ load forecast data for verification"""
        return self._load_forecasts(getattr(self,f'fc{name}sets'), grid=grid)

    def load_verif_data(self, name):
        """ load verification data """
        return self._load_verif(getattr(self,f'fc{name}sets'))

    def _load_forecasts(self, fcset, grid=None,):
        """ load forecast data """

        if grid is None:
            grid = self.grid

        filename = self._filenaming_convention('fc')
        _all_list = []
        _inits = []
        for fcname in fcset:
            _inits.append(fcname)
            _da_date_list = []
            _fcdates = fcset[fcname]['sdates']

            for _date in _fcdates:

                _members = range(int(fcset[fcname]['enssize']))
                _da_ensmem_list = []
                for _member in _members:

                    _filename = f"{fcset[fcname]['cachedir']}/" \
                                f"{filename.format(_date, _member, self.params,grid)}"
                    #print(_filename)
                    _dtdate = [utils.string_to_datetime(_date)]
                    _dtseldates = utils.create_list_target_verif(self.target,_dtdate)
                    _seldates = [utils.datetime_to_string(dtdate) for dtdate in _dtseldates]

                    _da_file = self.load_data(_filename, _seldates)
                    _da_file = self.convert_time_to_lead(_da_file)

                    _da_ensmem_list.append(_da_file)
                _ensdim = xr.DataArray(_members, dims='member', name='member')
                _da_date = xr.concat(_da_ensmem_list, dim=_ensdim)
                _da_date_list.append(_da_date)

            _date_dim = xr.DataArray(range(len(_fcdates)), dims='date', name='date')
            da_fc = xr.concat(_da_date_list, dim=_date_dim)
            _all_list.append(da_fc.sortby(da_fc.date))

        _init_dim = xr.DataArray(_inits, dims='inidate', name='inidate')
        da_init = xr.concat(_all_list, dim=_init_dim)

        return da_init


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
        result.to_netcdf(_ofile)
    def gettype(self):
        """ Determine typ of plot (timeseries or mapplot) """
        dims_list = [dim[:2] for dim in self.result.dims]
        if 'xc' in dims_list or 'longitude' in self.result.dims:
            return 'map'
        else:
            return 'ts'

    def convert_time_to_lead(self,_da=None):
        """ Convert time variable to steps"""
        target_as_list = utils.create_list_target_verif(self.target, as_list=True)
        _da = _da.assign_coords(time=target_as_list)
        return _da




    def load_data(self, _file,_seldate):
        """
        load single xarray data file and select specific timestep
        Use dask if selected
        :param _file: filename
        :param _seldate: timestep(s) to load
        :return: xarray DataArray
        """


        if self.use_dask:
            _da_file = xr.open_dataarray(_file, chunks='auto')
        else:
            _da_file = xr.open_dataarray(_file)
        return _da_file.sel(time=_da_file.time.dt.strftime("%Y%m%d").isin(_seldate))
