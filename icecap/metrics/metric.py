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
        self.verif_mode = utils.csv_to_list(conf.plotsets[name].verif_mode)
        self.verif_fromdate = utils.csv_to_list(conf.plotsets[name].verif_fromdate)
        self.verif_todate = utils.csv_to_list(conf.plotsets[name].verif_todate)
        self.verif_enssize = utils.csv_to_list(conf.plotsets[name].verif_enssize)
        self.verif_fcsystem = utils.csv_to_list(conf.plotsets[name].verif_fcsystem)
        self.verif_dates = utils.csv_to_list(conf.plotsets[name].verif_dates)
        self.verif_source = utils.csv_to_list(conf.plotsets[name].verif_source)


        # initialize calibration forecasts
        # this is just a dummy hers it will be implemented at a later stage
        self.calib_expname = None


        self.use_metric_name = False
        self.result = None
        self.default_cmap = None


        self._init_fcverif()


    def _init_fcverif(self):
        self.fcverifsets = dict()
        for ifc, date in enumerate(self.verif_dates):
            kwargs = {
                'source': self.verif_source[0],
                'fcsystem': self.verif_fcsystem[0],
                'expname': self.verif_expname[0],
                'thisdate': date
            }
            cycle = dataobjects.get_cycle(**kwargs)
            kwargs = {
                'cacherootdir': self.cacherootdir,
                'fcsystem': self.verif_fcsystem[0],
                'expname': self.verif_expname[0],
                'refdate': date,
                'source': self.verif_source[0],
                'mode' : self.verif_mode[0],
                'cycle' : cycle
            }

            self.fcverifsets[ifc] = dict()
            self.fcverifsets[ifc]['cachedir'] = dataobjects.define_fccachedir(**kwargs)
            self.fcverifsets[ifc]['enssize'] = self.verif_enssize[ifc]

            # create dates

            _dtfromdate = [dt.datetime.strptime(self.verif_fromdate[ifc], '%Y%m%d')]
            _dttodate = [dt.datetime.strptime(self.verif_todate[ifc], '%Y%m%d')]
            _dates = utils.make_hc_datelist(_dtfromdate, _dttodate)

            self.fcverifsets[ifc]['sdates'] = [d.strftime('%Y%m%d') for d in _dates]



    def _load_verif(self, fcset):
        """ load verification data """

        filename = self._filenaming_convention('verif')
        _all_list = []
        for fcname in fcset:
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

                        _da_ensmem_list.append(xr.open_dataarray(_filename))
                    _ensdim = xr.DataArray(_members, dims='member', name='member')
                    _da_member = xr.concat(_da_ensmem_list, dim=_ensdim)
                    _da_seldate_list.append(_da_member)

                _da_date = xr.concat(_da_seldate_list, dim='time')
                _da_date = self.convert_time_to_lead(_da_date)

                _da_date_list.append(_da_date)

            _date_dim = xr.DataArray(_fcdates, dims='date', name='date')
            da_fc = xr.concat(_da_date_list, dim=_date_dim)
            _all_list.append(da_fc.sortby(da_fc.date))


        return _all_list

    def load_verif_fc(self, grid=None):
        """ load forecast data for verification"""
        return self._load_forecasts(self.fcverifsets, grid=grid)

    def load_verif_data(self):
        """ load verification data """
        return self._load_verif(self.fcverifsets)

    def _load_forecasts(self, fcset, grid=None,):
        """ load forecast data """

        if grid is None:
            grid = self.grid

        filename = self._filenaming_convention('fc')
        _all_list = []
        for fcname in fcset:
            _da_date_list = []
            _fcdates = fcset[fcname]['sdates']

            for _date in _fcdates:
                _members = range(int(fcset[fcname]['enssize']))
                _da_ensmem_list = []
                for _member in _members:

                    _filename = f"{fcset[fcname]['cachedir']}/" \
                                f"{filename.format(_date, _member, self.params,grid)}"
                    _dtdate = [utils.string_to_datetime(_date)]
                    _dtseldates = utils.create_list_target_verif(self.target,_dtdate)
                    _seldates = [utils.datetime_to_string(dtdate) for dtdate in _dtseldates]

                    _da_file = self.load_data(_filename, _seldates)
                    _da_file = self.convert_time_to_lead(_da_file)

                    _da_ensmem_list.append(_da_file)
                _ensdim = xr.DataArray(_members, dims='member', name='member')
                _da_date = xr.concat(_da_ensmem_list, dim=_ensdim)
                _da_date_list.append(_da_date)

            _date_dim = xr.DataArray(_fcdates, dims='date', name='date')
            da_fc = xr.concat(_da_date_list, dim=_date_dim)
            _all_list.append(da_fc.sortby(da_fc.date))


        return _all_list

    def get_filename_metric(self):
        """ Create filename for saved metricfile """
        if self.use_metric_name:
            oname = f'{self.metricname}.nc'
            return f'{self.metricdir}/{self.metricname}/{oname}'
        raise 'Only use_metric_name = True implemented so far'

    def save(self):
        """ Save metric to metricdir """
        _ofile = self.get_filename_metric()
        utils.make_dir(os.path.dirname(_ofile))

        result = self.result
        result.to_netcdf(_ofile)

    def convert_time_to_lead(self,_da=None):
        """ Convert time variable to steps"""
        target_as_list = utils.create_list_target_verif(self.target, as_list=True)
        _da = _da.assign_coords(time=target_as_list)
        return _da



    @staticmethod
    def load_data(_file,_seldate):
        """ load single xarray data file and select specific timestep """
        _da_file = xr.open_dataarray(_file)
        return _da_file.sel(time=_da_file.time.dt.strftime("%Y%m%d").isin(_seldate))
