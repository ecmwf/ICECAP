"""
This module contains all relevant information, to retrieve
data from the climate data store (CDS)
Only tested with seasonal data so far
"""

import os
import cdsapi
import xarray as xr

import utils
import dataobjects


def convert_step2time(_da_tmp):
    """ Convert step variable in grib file from MARS to time
    :param _da_tmp: xarray dataset
    :return: xarray dataset with time variable
    """
    da_in_tmp = _da_tmp.copy()
    da_in_tmp['step'] = da_in_tmp.step + da_in_tmp['starttime']
    da_in_tmp = da_in_tmp.rename({'step': 'time'})

    return da_in_tmp

class CdsRetrieval:
    """Defines a single CDS retrieval request"""


    @staticmethod
    def factory(kwargs):
        """return appropriate CDS retrieval  subclass"""
        if kwargs['fcastobj'].fcsystem == 'long-range':
            return _CdsSeasonalRetrieval(kwargs)

        raise NotImplementedError

    def __init__(self, kwargs):
        self.kwargs = {}
        self.kwargs['format'] = 'grib'
        self.kwargs['variable'] = 'sea_ice_cover'
        self.kwargs['originating_centre'] = kwargs['origin']
        self.kwargs['system'] = kwargs['fcastobj'].expname
        self.target = kwargs['tfile']
        self.data = None

    def pprint(self):
        """print CDS request"""
        print(f'CDS retrieval request for target file {os.path.basename(self.target)}:')
        for mkey,mval in self.kwargs.items():
            print(f'  {mkey} = {mval}')

    def execute(self,dryrun=False):
        """
        Execute CDS retrieval
        :param dryrun: if True print CDS request
        """

        if os.path.exists(self.target):
            print('INFO: not performing CDS retrieval, already have', self.target)
        else:
            if dryrun:
                self.pprint()
            else:
                if self.data is None:
                    raise ValueError('Data attribute needed to retrieve data from CDS')

                cds_client = cdsapi.Client()
                cds_client.retrieve(
                    self.data,
                    self.kwargs,
                    self.target
                )
                print('download', self.target)
                cds_client.download(self.target)




class _CdsSeasonalRetrieval(CdsRetrieval):
    """Defines CDS retrieval of CDS data for seasonal forecast"""

    def __init__(self, kwargs):
        super().__init__(kwargs)
        self.data = 'seasonal-original-single-levels'
        self.kwargs['year'] = kwargs['date'][:4]
        self.kwargs['month'] = kwargs['date'][4:6]
        self.kwargs['day'] = kwargs['date'][6:8]


        self.kwargs['leadtime_hour'] = [24*(n+1) for n in range(int(kwargs['ndays']))]


class CdsData(dataobjects.ForecastObject):
    """ Class for CDS data for retrieval and processing """

    def __init__(self, conf, args):
        super().__init__(conf, args)

        if args.startdate not in ['INIT', 'WIPE']:
            self.cycle = self.init_cycle(self.startdate)
            self.fccachedir = self.init_cachedir()
            self.ldmean = False
            self.linterp = True
            self.periodic = True

            self.tmptargetfile = f'{conf.tmpdir}/{self.source}/{self.modelname}/' \
                                 f'{args.expid}_{args.startdate}_{self.mode}/' \
                                 f'tmp_{args.expid}_{args.startdate}_{self.mode}.grb'
            utils.make_dir(os.path.dirname(self.tmptargetfile))

            factory_args = dict(
                date=self.startdate,
                fcastobj=self.fcast,
                tfile=self.tmptargetfile,
                ndays=self.ndays,
                origin=self.modelname
            )

            self.retrieval_request = CdsRetrieval.factory(factory_args)

    def get_from_tape(self, dryrun=False):
        """perform the CDS retrievals set up in init"""
        self.retrieval_request.execute(dryrun=dryrun)

    def make_filelist(self):
        """Generate a list of files which are expected to be staged"""
        filename = self._filenaming_convention('fc')
        files_list = []

        dates = [self.startdate]
        if self.mode == 'hc':
            dates = self.fcast.shcdates



        members = range(int(self.fcast.enssize))


        files = [filename.format(date, member, self.params, self.grid)
                 for date in dates
                 for member in members]


        _cachedir = self.fccachedir

        files_list += [_cachedir + '/' + file for file in files]

        return files_list

    def process(self):
        """Process retrieved CDS data and write to cache"""

        iname = 'siconc'
        for file in [self.tmptargetfile]:

            print(file)
            ds_in = xr.open_dataset(file, engine='cfgrib')

            da_in = ds_in[iname].rename(self.params)

            is_number = 'number' in da_in.dims
            is_step = 'step' in da_in.dims
            is_time = 'time' in da_in.dims


            # make it a 5d array
            if not is_number:
                da_in = da_in.expand_dims({'number': 1})
            if not is_step:
                da_in = da_in.expand_dims({'step': 1})
            if not is_time:
                da_in = da_in.expand_dims({'time': 1})



            da_in = da_in.transpose('number', 'time', 'step', 'latitude', 'longitude')
            da_in = da_in.rename({'time': 'starttime'})
            startdate = da_in.starttime.dt.strftime('%Y%m%d').values
            if len(startdate) > 1:
                raise ValueError(f'More than one startdate in file {file}')
            startdate = startdate[0]

            # split into list of files with one starttime
            files_pp = [da_in.sel(starttime=stime) for stime in da_in.starttime.values]

            # convert step to time
            files_pp = [convert_step2time(file) for file in files_pp]

            if self.ldmean:
                files_pp = [file.resample(time='1D').mean() for file in files_pp]



            if self.keep_native == "yes":
                for da_out_save in files_pp:
                    for number in da_out_save['number'].values:
                        da_out_save = da_out_save.isel(time=slice(self.ndays))
                        ofile = self._save_filename(date=startdate, number=number, grid='native')
                        da_out_save.sel(number=number).to_netcdf(ofile)



            if self.linterp:
                files_pp_interp = [self.interpolate(file) for file in files_pp]
                files_pp = files_pp_interp


            for da_out_save in files_pp:
                for number in da_out_save['number'].values:
                    da_out_save = da_out_save.isel(time=slice(self.ndays))
                    ofile = self._save_filename(date=startdate, number=number, grid=self.grid)
                    da_out_save.sel(number=number).to_netcdf(ofile)
