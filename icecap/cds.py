"""
This module contains all relevant information, to retrieve
data from the climate data store (CDS)
Only tested with seasonal data so far
"""

import os
import cdsapi
import xarray as xr
import numpy as np

import utils
import dataobjects


def convert_step2time(_da_tmp, offset_hour=0):
    """ Convert step variable in grib file from MARS to time
    :param _da_tmp: xarray dataset
    :param offset_hour: correction factor, needed e.g. for seasonal data with step=24 hours
    In those cases xarray will assign averaged sic conditions for day n to day n+1
    :return: xarray dataset with time variable
    """
    da_in_tmp = _da_tmp.copy()
    da_in_tmp['step'] = da_in_tmp.step + (da_in_tmp['starttime'] - np.timedelta64(offset_hour,'h'))
    da_in_tmp = da_in_tmp.rename({'step': 'time'})

    return da_in_tmp

class CdsRetrieval:
    """Defines a single CDS retrieval request"""


    @staticmethod
    def factory(kwargs):
        """return appropriate CDS retrieval  subclass"""
        if kwargs['fcsystem'] == 'long-range':
            return _CdsSeasonalRetrieval(kwargs)

        raise NotImplementedError

    def __init__(self, kwargs):
        self.kwargs = {}
        self.kwargs['format'] = 'grib'
        if kwargs['exptype'] == 'INIT':
            self.kwargs['variable'] = 'land_sea_mask'
        else:
            self.kwargs['variable'] = 'sea_ice_cover'
        self.kwargs['originating_centre'] = kwargs['origin']
        self.kwargs['system'] = kwargs['expname']
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
        if kwargs['exptype'] == 'INIT':
            self.kwargs['leadtime_hour'] = [0]

class CdsData(dataobjects.ForecastObject):
    """ Class for CDS data for retrieval and processing """

    def __init__(self, conf, args):
        super().__init__(conf, args)

        if args.exptype not in ['WIPE']:
            self.cycle = self.init_cycle(self.startdate)
            self.fccachedir = self.init_cachedir()
            self.ldmean = False
            self.linterp = True
            self.periodic = True
            self.lsm = True

            self.tmptargetfile = f'{conf.tmpdir}/{self.source}/{self.modelname}/' \
                                 f'{args.expid}_{args.startdate}_{args.exptype}_{self.mode}/' \
                                 f'tmp_{args.expid}_{args.startdate}_{self.mode}.grb'
            utils.make_dir(os.path.dirname(self.tmptargetfile))

            factory_args = dict(
                date=args.startdate,
                exptype=args.exptype,
                fcsystem=self.fcsystem,
                expname=self.expname,
                tfile=self.tmptargetfile,
                ndays=self.ndays,
                origin=self.modelname,
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
            dates = self.shcdates



        members = range(int(self.enssize))


        files = [filename.format(date, member, self.params, self.grid)
                 for date in dates
                 for member in members]


        _cachedir = self.fccachedir

        files_list += [_cachedir + '/' + file for file in files]

        return files_list

    def process_lsm(self, dryrun=False):
        """
        Retrieve land-sea-mask from tape if masking necessary for this dataset and save to disk
        :param dryrun: only sho mars request
        """
        if self.lsm and not os.path.isfile(f'{self.fccachedir}/lsm.nc'):
            self.retrieval_request.execute(dryrun=dryrun)
            if not dryrun:
                file = self.tmptargetfile
                ds_in = xr.open_dataset(file, engine='cfgrib')
                ds_lsm = xr.where(ds_in<=0.5,0,1)
                ds_lsm.to_netcdf(f'{self.fccachedir}/lsm.nc')
                print(f'{self.fccachedir}/lsm.nc')

    def process(self):
        """Process retrieved CDS data and write to cache"""

        iname = 'siconc'
        for file in [self.tmptargetfile]:

            print(file)
            ds_in = xr.open_dataset(file, engine='cfgrib')
            da_in = ds_in[iname].rename(self.params)



            # mask using the land-sea mask (if necessary for the respective dataset)
            if self.lsm:
                da_lsm = xr.open_dataarray(f'{self.fccachedir}/lsm.nc').isel(number=0)
                # drop coords not in dims as otherwise time is deleted from da_in after where command
                da_lsm = da_lsm.drop([i for i in da_lsm.coords if i not in da_lsm.dims])
                da_in = da_in.where(da_lsm == 0)
                da_in = da_in.astype(dtype=da_in.dtype, order='C')

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
            da_out = da_in.sel(starttime=startdate)


            # convert step to time
            da_out = convert_step2time(da_out, offset_hour=12)

            if self.ldmean:
                da_out = da_out.resample(time='1D').mean()


            if self.keep_native == "yes":
                for number in da_out['number'].values:
                    da_out_save = da_out.isel(time=slice(self.ndays))
                    ofile = self._save_filename(date=startdate, number=number, grid='native')
                    da_out_save.sel(number=number).to_netcdf(ofile)


            # save interpolated files if interpolation is necessary
            for number in da_out['number'].values:
                if self.linterp:
                    da_out_save = self.interpolate(da_out.sel(number=number))
                else:
                    da_out_save = da_out.sel(number=number)

                ofile = self._save_filename(date=startdate, number=number, grid=self.grid)
                da_out_save.to_netcdf(ofile)
                print(ofile)
