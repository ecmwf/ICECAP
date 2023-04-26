"""Module with parent classes with attributes linked
to forecasts and verification data for staging and for config"""

import os
import datetime as dt
import uuid
import xesmf as xe
import xarray as xr

import utils

class DataObject:
    """ Parent data object, with attributes valid
    for both forecasts and verification data"""

    def __init__(self, conf):
        self.params = conf.params
        self.cachedir = None
        self.ndays = conf.ndays
        self.filelist = None
        self.verif_name = conf.verdata
        self.cacherootdir = conf.cachedir
        self.obscachedir = f'{conf.cachedir}/{conf.verdata}/'
        self.salldates = conf.salldates
        self.linterp = False
        self.regridder = None
        self.regridder_name = f'weights_{uuid.uuid4().hex}.nc'
        self.grid = self.verif_name
        self.keep_native = conf.keep_native

    def check_cache(self, check_level=2, verbose=False):
        """
        Check if files already exist in cachedir
        :param check_level: check only if file exists (1)
                            check if timesteps are correct (2)
        :param verbose: switch on debugging output
        """

        files_to_check = self.make_filelist()
        if verbose:
            print(f'files to check {files_to_check}')

        for file in files_to_check:
            # quick check if exist
            if not os.path.exists(f'{file}'):
                if verbose:
                    print(f'Not all files are found in cache {self.cachedir}/{file}')
                return False

        if check_level > 1:

            for file in files_to_check:
                ds_in = xr.open_dataset(f'{file}')
                if len(ds_in.time) < self.ndays:
                    if verbose:
                        print(f'Not all timesteps needed found in {self.cachedir}/{file}')
                    return False
        return True

    def make_filelist(self):
        """
        Create list of files to be saved in cachedir
        This depends on the forecast/verification object and is thus
        overriden by the respective class
        """
        self.filelist = []
        return self.filelist

    def interpolate(self, ds_raw):
        """
        Interpolate forecast to observation grid
        :param ds_raw: raw forecast xarray object
        :return: interpolated field as xarray object
        """

        ref_file = f'{self.obscachedir}/' \
                   f'{self._filenaming_convention("verif").format(self.salldates[0],self.params)}'
        ds_ref = xr.open_dataarray(ref_file)

        self.regridder = xe.Regridder(ds_raw.rename({'longitude': 'lon', 'latitude': 'lat'}),
                                      ds_ref.rename({'longitude': 'lon', 'latitude': 'lat'}),
                                      "bilinear", periodic=True, reuse_weights=True,
                                      filename=self.regridder_name)
        ds_out = self.regridder(ds_raw.rename({'longitude': 'lon', 'latitude': 'lat'}))

        # make sure interpolated fields have same xc and yc values as ref
        ds_out['xc'] = ds_ref['xc'].values
        ds_out['yc'] = ds_ref['yc'].values
        ds_out.rename({'lon':'longitude','lat':'latitude'})
        return ds_out



    @staticmethod
    def _filenaming_convention(args):
        """
        Naming convention for verification and forecast cache files
        :param args: fc for forecast data and verif for verification data
        """
        if args == 'fc':
            return '{}_mem-{:03d}_{}_{}.nc'
        if args == 'verif':
            return '{}_{}.nc'

        raise f'Argument {args} not supported'

class ForecastObject(DataObject):
    """ Generic ForecastObject used for staging """

    def __init__(self, conf, args):
        super().__init__(conf)

        self.machine = conf.machine
        self.fcast = conf.fcsets[args.expid]
        self.enssize = self.fcast.enssize
        self.mode = self.fcast.mode

        self.fcsdates = self.fcast.salldates

        if self.mode == 'hc':
            self.refdate = self.fcast.hcrefdate
        else:
            self.refdate = self.fcast.dates

        kwargs = {
            'cacherootdir': self.cacherootdir,
            'fcsystem': self.fcast.fcsystem,
            'expname': self.fcast.expname,
            'refdate': self.refdate,
            'mode': self.mode
        }
        self.fccachedir = define_fccachedir(**kwargs)
        utils.make_dir(self.fccachedir)

def define_fccachedir(**kwargs):
    """
    Retrive forecast cache directory
    :param kwargs: keywords needed to define cache-directory of forecast
    cacherootdir: root cachedir given in config
    fcsystem: forecast system type of teh experiment
    expname: experiment ID
    refdate: experiment reference date
    mode : hindcast (hc) or forecast (fc)
    :return: cache directory (str) for the specific forecast
    """
    _fccachedir = f'{kwargs["cacherootdir"]}/{kwargs["fcsystem"]}/' \
                  f'{kwargs["expname"]}/{kwargs["refdate"]}/{kwargs["mode"]}/'
    return _fccachedir


class ForecastConfigObject:
    """A forecast config object corresponds to a single numerical experiment (used in config.py)."""
# dates : config dates
# sdates : string dates
# dtdates: datetime dates

    def __init__(self, **kwargs):
        self.fcsystem = kwargs['fcsystem']
        self.expname = kwargs['expname']
        self.enssize = int(kwargs['enssize'])
        self.mode = kwargs['mode']  # hindcast mode (affects start dates)
        self.dates = kwargs['dates']
        self.hcrefdate = kwargs['hcrefdate']
        self.hcfromdate = kwargs['hcfromdate']
        self.hctodate = kwargs['hctodate']
        self.ref = kwargs['ref']
        self.ndays = kwargs['ndays']

        if self.mode  == 'fc':
            _dates_list = utils.csv_to_list(self.dates)
            self.dtdates = [dt.datetime.strptime(d, '%Y%m%d') for d in _dates_list]
            self.sdates = [d.strftime('%Y%m%d') for d in self.dtdates]
            self.dtalldates = utils.make_days_datelist(self.dtdates, self.ndays)



        elif self.mode == 'hc':
            _dates_list_ref  = utils.csv_to_list(self.hcrefdate)
            self.dthcrefdate = [dt.datetime.strptime(d, '%Y%m%d') for d in _dates_list_ref]
            self.shcrefdate = [d.strftime('%Y%m%d') for d in self.dthcrefdate]

            _dates_hc_from_list = utils.csv_to_list(self.hcfromdate)
            self.dthcfromdate = [dt.datetime.strptime(d, '%Y%m%d') for d in _dates_hc_from_list]
            _dates_hc_to_list = utils.csv_to_list(self.hctodate)
            self.dthctodate = [dt.datetime.strptime(d, '%Y%m%d') for d in _dates_hc_to_list]

            self.hcdates = utils.make_hc_datelist(self.dthcfromdate, self.dthctodate)
            self.shcdates = [d.strftime('%Y%m%d') for d in self.hcdates]
            self.dtalldates = utils.make_days_datelist(self.hcdates, self.ndays)

        self.salldates = sorted(list(dict.fromkeys([d.strftime('%Y%m%d')
                                                    for d in self.dtalldates])))

class PlotConfigObject:
    """A plot config object corresponds to a single numerical plotID (used in config.py)."""
    def __init__(self, **kwargs):
        self.verif_expname = kwargs['verif_expname']
        self.plottype = kwargs['plottype']
        self.verif_mode = kwargs['verif_mode']
        self.verif_fromdate = kwargs['verif_fromdate']
        self.verif_todate = kwargs['verif_todate']
        self.target = kwargs['target']
        self.verif_enssize = kwargs['verif_enssize']
        self.verif_fcsystem = kwargs['verif_fcsystem']
        self.verif_refdate = kwargs['verif_refdate']
