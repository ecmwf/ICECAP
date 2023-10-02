"""Module with parent classes with attributes linked
to forecasts and verification data for staging and for config"""

import os
import glob
import datetime as dt
import shutil

import xesmf as xe
import xarray as xr

import utils
import forecast_info

class DataObject:
    """ Parent data object, with attributes valid
    for both forecasts and verification data"""

    def __init__(self, conf):
        self.params = conf.params
        self.filelist = None
        self.verif_name = conf.verdata
        self.cacherootdir = conf.cachedir
        self.obscachedir = f'{conf.cachedir}/{conf.verdata.replace("-grid","")}/'
        self.salldates = conf.salldates
        self.linterp = False
        self.regridder = None
        self.grid = self.verif_name.replace("-grid","")
        self.keep_native = conf.keep_native
        self.files_to_retrieve = []
        self.tmptargetfile = None
        self.periodic = None
        self.ndays = None

    def check_cache(self, check_level=2, verbose=False):
        """
        Check if files already exist in cachedir
        :param check_level: check only if file exists (1)
                            check if timesteps are correct (2)
        :param verbose: switch on debugging output
        """

        # for obs there is one datafile per date, whereas for fc it's one
        # file per startdate (with ndays timesteps)
        # thus chekcs for length are only possible for fc data
        if self.ndays is None and check_level>1:
            raise ValueError("Class attribute ndays can't be set to None for"
                             "check_level > 1")

        files_to_check = self.make_filelist()

        self.files_to_retrieve = []
        if verbose:
            print(f'files to check {files_to_check}')

        for file in files_to_check:
            # quick check if exist
            if not os.path.exists(f'{file}'):
                if verbose:
                    print(f'Not all files are found in cache {file}')
                self.files_to_retrieve.append(file)
            else:
                if check_level > 1:
                    ds_in = xr.open_dataset(f'{file}')
                    if len(ds_in.time) < self.ndays:
                        if verbose:
                            print(f'Not all timesteps needed found in {file}')
                        self.files_to_retrieve.append(file)


        if self.files_to_retrieve:
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
        if self.periodic is None:
            raise ValueError("Class attribute periodic used in interpolate can't be set to None")

        if 'grid' in self.verif_name:
            ref_file = f'{self.obscachedir}/{self.verif_name}.nc'
        else:
            ref_file = f'{self.obscachedir}/' \
                       f'{self._filenaming_convention("verif").format(self.salldates[0],self.params)}'
        ds_ref = xr.open_dataarray(ref_file)

        if self.regridder is None:
            utils.print_info('Computing weights')
            self.regridder = xe.Regridder(ds_raw.rename({'longitude': 'lon', 'latitude': 'lat'}),
                                          ds_ref.rename({'longitude': 'lon', 'latitude': 'lat'}),
                                          "bilinear", periodic=self.periodic)


        ds_out = self.regridder(ds_raw.rename({'longitude': 'lon', 'latitude': 'lat'}))

        # make sure interpolated fields have same xc and yc values as ref
        ds_out['xc'] = ds_ref['xc'].values
        ds_out['yc'] = ds_ref['yc'].values
        ds_out.rename({'lon':'longitude','lat':'latitude'})

        # copy projection information if needed
        for proj_param in ['projection', 'central_longitude', 'central_latitude',
                           'true_scale_latitude']:
            if proj_param in ds_ref.attrs:
                ds_out.attrs[proj_param] = getattr(ds_ref,proj_param)
        ds_ref.close()

        return ds_out

    def clean_up(self):
        """ Remove temporary files"""
        if self.tmptargetfile is not None:
            shutil.rmtree(os.path.dirname(self.tmptargetfile))



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
        self.startdate = args.startdate
        self.fcast = conf.fcsets[args.expid]
        self.expname = self.fcast.expname
        self.enssize = self.fcast.enssize
        self.mode = self.fcast.mode
        self.source = self.fcast.source
        self.ndays = int(self.fcast.ndays)
        self.modelname = self.fcast.modelname


        self.fcsdates = self.fcast.salldates

        if self.mode == 'hc':
            self.refdate = utils.csv_to_list(self.fcast.hcrefdate)
        else:
            self.refdate = utils.csv_to_list(self.fcast.dates)

    def create_folders(self):
        """ Create forecast directories in cachedir"""

        utils.print_info('Setting up folders for forecast retrieval')
        directory_list = []
        for date in self.refdate:
            self.cycle = self.init_cycle(date)
            _fccachedir = self.init_cachedir()
            directory_list.append(_fccachedir)

        for directory in list(set(directory_list)):
            utils.make_dir(directory)

    def remove_native_files(self):
        """ Remove native grid files after interpolation checks"""
        if self.keep_native:
            utils.print_info('SRemoving native grid files')
            file_list = []
            for date in self.refdate:
                self.cycle = self.init_cycle(date)
                _fccachedir = self.init_cachedir()
                files_to_add =  glob.glob(f'{_fccachedir}/*_native.nc')
                file_list += files_to_add

            for file in file_list:
                os.remove(file)

    def init_cycle(self, date):
        """
        return cycle name
        :param date: date of forecast
        :return: cycle as string
        """


        kwargs = {
            'source': self.source,
            'fcsystem': self.fcast.fcsystem,
            'expname': self.expname,
            'modelname' : self.modelname,
            'mode' : self.mode,
            'thisdate' : date
        }
        return forecast_info.get_cycle(**kwargs)




    def init_cachedir(self):
        """ create cachedir string """

        kwargs = {
            'cacherootdir': self.cacherootdir,
            'fcsystem': self.fcast.fcsystem,
            'expname': self.expname,
            'source': self.source,
            'cycle' : self.cycle,
            'mode' : self.mode,
            'modelname':self.modelname
        }
        return define_fccachedir(**kwargs)


    def _save_filename(self, date, number, grid):
        """
        Create cache file name
        :param date: date of forecast
        :param number: ensemble member number
        :param grid: grid information)
        :return: outfile name as string
        """

        filename = self._filenaming_convention('fc')
        _cachedir = self.init_cachedir()
        return f'{_cachedir}/' + \
               filename.format(date,
                               number,
                               self.params,
                               grid)

    @staticmethod
    def get_cycle(date):
        """
        Gets cycle information. This is usually set to latest but
        can be overriden for specific forecast objects, as done for e.g.
        ecmwf forecasts which need cycle information depending on the date of the forecast
        at ECMWF, cycle only depends on date, which might be similar for other centres so it is kept also
        in this generic function of get_cycle
        :param kwargs: can be anything
        :return: cycle information as string
        """
        cycle = "latest"
        return cycle


def define_fccachedir(**kwargs):
    """
    Retrive forecast cache directory
    :param kwargs: keywords needed to define cache-directory of forecast
    cacherootdir: root cachedir given in config
    fcsystem: forecast system type of teh experiment
    expname: experiment ID
    refdate: experiment reference date
    mode : hindcast (hc) or forecast (fc)
    cycle : model version
    :return: cache directory (str) for the specific forecast
    """
    if kwargs["modelname"] is None:
        kwargs["modelname"] = kwargs["source"]

    _fccachedir = f'{kwargs["cacherootdir"]}/{kwargs["source"]}/{kwargs["fcsystem"]}/' \
                  f'{kwargs["modelname"]}/{kwargs["expname"]}/{kwargs["cycle"]}/{kwargs["mode"]}'
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
        self.source = kwargs['source']
        self.modelname = kwargs['modelname']


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
        self.verif_fromyear = kwargs['verif_fromyear']
        self.verif_toyear = kwargs['verif_toyear']
        self.target = kwargs['target']
        self.verif_enssize = kwargs['verif_enssize']
        self.verif_fcsystem = kwargs['verif_fcsystem']
        self.verif_refdate = kwargs['verif_refdate']
        self.projection = kwargs['projection']
        self.proj_options = kwargs['proj_options']
        self.circle_border = kwargs['circle_border']
        self.plot_extent = kwargs['plot_extent']
        self.cmap = kwargs['cmap']
        self.verif_source = kwargs['source']
        self.verif_dates = kwargs['verif_dates']
        self.calib_dates = kwargs['calib_dates']
        self.calib_mode = kwargs['calib_mode']
        self.calib_fromyear = kwargs['calib_fromyear']
        self.calib_toyear = kwargs['calib_toyear']
        self.calib_refdate = kwargs['calib_refdate']
        self.calib_enssize = kwargs['calib_enssize']
        self.ofile = kwargs['ofile']
        self.points = kwargs['points']
        self.add_verdata = kwargs['add_verdata']
        self.modelname = kwargs['modelname']
