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
        self.verif_expname = utils.convert_to_list(conf.plotsets[name].verif_expname)
        self.verif_mode = utils.convert_to_list(conf.plotsets[name].verif_mode)
        self.verif_fromdate = utils.convert_to_list(conf.plotsets[name].verif_fromdate)
        self.verif_todate = utils.convert_to_list(conf.plotsets[name].verif_todate)
        self.verif_enssize = utils.convert_to_list(conf.plotsets[name].verif_enssize)
        self.verif_fcsystem = utils.convert_to_list(conf.plotsets[name].verif_fcsystem)
        self.verif_refdate = utils.convert_to_list(conf.plotsets[name].verif_refdate)

        # initialize calibration forecasts
        # this is just a dummy hers it will be implemented at a later stage
        self.calib_expname = None


        self.use_metric_name = False
        self.result = None

        # combine verification and (potentially) calibration forecasts
        self.combine_expname = None
        self.combine_mode = None
        self.combine_fromdate = None
        self.combine_todate = None
        self.combine_enssize = None
        self.combine_fcsystem = None
        self.combine_refdate = None

        forecast_atts = ['expname','mode','fromdate','todate','enssize','fcsystem','refdate']
        for att in forecast_atts:
            setattr(self, f'combine_{att}', getattr(self,f'verif_{att}'))

        if self.calib_expname is not None:
            for att in forecast_atts:
                setattr(self, f'combine_{att}',
                        getattr(self, f'combine_{att}')+getattr(self, f'calib_{att}'))

        self._init_forecasts()


    def _init_forecasts(self):
        self.fcsets = dict()
        for ifc, fcname in enumerate(self.combine_expname):

            kwargs = {
                'cacherootdir': self.cacherootdir,
                'fcsystem': self.combine_fcsystem[ifc],
                'expname': fcname,
                'refdate': self.combine_refdate[ifc],
                'mode': self.combine_mode[ifc]
            }
            self.fcsets[ifc] = dict()
            self.fcsets[ifc]['cachedir'] = dataobjects.define_fccachedir(**kwargs)

            # create dates
            _dtfromdate = [dt.datetime.strptime(self.combine_fromdate[ifc], '%Y%m%d')]
            _dttodate = [dt.datetime.strptime(self.combine_todate[ifc], '%Y%m%d')]
            _dates = utils.make_hc_datelist(_dtfromdate, _dttodate)
            self.fcsets[ifc]['sdates'] = [d.strftime('%Y%m%d') for d in _dates]




    def load_verif(self):
        """ load verification data """

        filename = self._filenaming_convention('verif')
        _all_list = []
        for fcname in self.fcsets:
            _da_date_list = []
            _fcdates = self.fcsets[fcname]['sdates']

            for _date in _fcdates:
                _dtdate = [utils.string_to_datetime(_date)]
                _dtseldates = utils.create_list_target_verif(self.target, _dtdate)
                _seldates = [utils.datetime_to_string(dtdate) for dtdate in _dtseldates]

                _da_seldate_list = []
                for _seldate in _seldates:
                    _members = range(1)
                    _da_ensmem_list = []
                    for _member in _members:
                        _filename = self.obscachedir+'/'+filename.format(_seldate, self.params, self.grid)
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

        if len(_all_list) == 1:
            _all_list = _all_list[0]

        return _all_list

    def load_forecasts(self, grid=None):
        """ load forecast data """

        if grid is None:
            grid = self.grid

        filename = self._filenaming_convention('fc')
        _all_list = []
        for fcname in self.fcsets:
            _da_date_list = []
            _fcdates = self.fcsets[fcname]['sdates']

            for _date in _fcdates:
                _members = range(int(self.combine_enssize[fcname]))
                _da_ensmem_list = []
                for _member in _members:
                    _filename = self.fcsets[fcname]['cachedir']+'/'+ filename.format(_date, _member, self.params, grid)
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

        if len(_all_list) == 1:
            _all_list = _all_list[0]
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
