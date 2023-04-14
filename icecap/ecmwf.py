"""
This module should contain all ecmwf specific relevant information, e.g.
mars retrieval, ecmwf retrieval flow
"""
import os
import subprocess
import flow
import setup_icecap

xr = None  # This is a lazy import. Loading xarray is slow and we don't always need it.

params_ecmwf = {
    'sic' : {
        'grib_code' : '31.128',
        'xr_code' : 'siconc'
    }
}


class EcmwfTree(flow.ProcessTree):
    """
    Specific ECMWF flow
    """
    def __init__(self, conf):
        super().__init__(conf)
        # self.add_attr(['variable:EXEHOST;hpc-batch'], f'global')
        site = 'hpc'
        self.add_attr([f'variable:ECF_JOB_CMD;troika submit -o %ECF_JOBOUT% {site} %ECF_JOB%',
                       f'variable:ECF_KILL_CMD;troika kill {site} %ECF_JOB%',
                       f'variable:ECF_STATUS_CMD;troika monitor {site} %ECF_JOB%',
                       'variable:EXEHOST;hpc-batch'], 'global')

        for expid in conf.fcsets.keys():
            if conf.fcsets[expid].mode in ['fc', 'both']:
                self.add_attr(['variable:MODE;fc',
                               'repeat:DATES;{}'.format(self.fcsets[expid].sdates)],
                              f'retrieval:{expid}:fc')
                if conf.fcsets[expid].fcsystem in ['extended-range', 'medium-range']:
                    self.add_attr(['task:ecmwf_retrieve;mars',
                                   'variable:TYPE;cf'], f'retrieval:{expid}:fc:cf')
                    self.add_attr(['task:ecmwf_retrieve;mars',
                                   'variable:TYPE;pf'], f'retrieval:{expid}:fc:pf')

            if conf.fcsets[expid].mode in ['hc', 'both']:
                self.add_attr(['variable:MODE;hc',
                               'repeat:DATES;{}'.format(self.fcsets[expid].shcrefdate)],
                              f'retrieval:{expid}:hc')
                if conf.fcsets[expid].fcsystem in ['extended-range', 'medium-range']:
                    self.add_attr(['task:ecmwf_retrieve;mars',
                                   'variable:TYPE;cf'], f'retrieval:{expid}:hc:cf')
                    self.add_attr(['task:ecmwf_retrieve;mars',
                                   'variable:TYPE;pf'], f'retrieval:{expid}:hc:pf')


class EcmwfRetrieval:
    """Defines a single ECMWF retrieval request"""

    @staticmethod
    def factory(kwargs):
        """return appropriate MarsRetrieval subclass"""

        if kwargs['fcastobj'].fcsystem == 'extended-range':
            return _EcmwfExtendedRangeRetrieval(kwargs)

        raise NotImplementedError

    def __init__(self, kwargs):
        self.kwargs = dict()
        self.kwargs['class'] = 'od'
        self.kwargs['date'] = kwargs['date']
        self.kwargs['expver'] = kwargs['fcastobj'].expname
        self.kwargs['levtype'] = 'sfc'
        self.kwargs['param'] = params_ecmwf[kwargs['param']]['grib_code']
        self.kwargs['time'] = "00:00:00"
        self.kwargs['type'] = kwargs['type']
        self.kwargs['target'] = kwargs['tfile']



    def pprint(self):
        """print MARS request"""
        print('MARS retrieval request for target file {}:'.format(
            os.path.basename(self.kwargs['target'])))
        for mkey,mval in self.kwargs.items():
            print('  {} = {}'.format(mkey,mval))

    def execute(self,dryrun=False):
        """
        Execute mars retrieval
        :param dryrun: if True print mars request
        """
        tfile = self.kwargs['target']
        if os.path.exists(tfile):
            print('INFO: not performing MARS retrieval, already have', tfile)
        else:
            if dryrun:
                self.pprint()
            else:
                wdir = os.path.dirname(self.kwargs['target'])
                request = 'retrieve'
                for keyword, pyval in self.kwargs.items():
                    if isinstance(pyval, list):  # list separator in MARS requests is forward slash
                        marsval = '/'.join([str(item) for item in pyval])
                    elif '/' in str(pyval):  # forward slash can occur for path name and needs escaping
                        marsval = '"{}"'.format(pyval)
                    else:
                        marsval = pyval
                    request += ',\n{} = {}'.format(keyword, marsval)
                request += '\n'
                requestfilename = wdir + '/marsrequest'
                with open(requestfilename, 'w') as rfile:
                    rfile.write(request)
                with open(requestfilename, 'r') as rfile:
                    subprocess.check_call('mars', stdin=rfile)

class _EcmwfExtendedRangeRetrieval(EcmwfRetrieval):
    """Defines MARS retrieval of step data for ENS forecast"""
    # keywords needed: class, date, expver, [hdate], levtype, number, param, step,
    # stream, time, type, target
    def __init__(self, kwargs):
        super().__init__(kwargs)
        stepsize = 6
        self.kwargs['step'] = [0, 'to', int(kwargs['ndays'])*24, 'by', stepsize ]
        #'0/to/{}/by/{}'.format(int(kwargs['ndays'])*24, stepsize)
        if kwargs['mode'] == 'hc':
            self.kwargs['hdate'] = kwargs['fcastobj'].shcdates
            self.kwargs['stream'] = 'enfh'
        else:
            self.kwargs['stream'] = 'enfo'

        if self.kwargs['type'] == 'pf':
            self.kwargs['number'] = [ m+1 for m in range(int(kwargs['fcastobj'].enssize)-1) ]

        self.kwargs['grid'] = [1.0,1.0]






class EcmwfData:
    """ECMWF Data object calling a factory to
    retrieve appropriate class"""

    def __init__(self, conf, args):
        # provided by ecflow/env variable
        self.startdates = args.startdate
        self.type = args.exptype
        self.targetfile = '/home/nedb/transfer/tmp.grb'
        self.fcast = conf.fcsets[args.expid]
        if args.mode == 'hc':
            self.refdate =  self.fcast.hcrefdate
        else:
            self.refdate = self.fcast.dates

        self.cachedir = f'{conf.cachedir}/{self.fcast.fcsystem}/{self.fcast.expname}/{self.refdate}/{args.mode}/'
        setup_icecap.make_dir(self.cachedir)

        self.ndays = int(conf.ndays)
        self.mode = args.mode
        self.params = conf.params

        self.ldmean = False
        if self.fcast.fcsystem in ['extended-range']:
            setattr(self, 'ldmean', True)



        factory_args = dict(
            exptype=args.exptype,
            date=self.startdates,
            fcastobj=self.fcast,
            tfile = self.targetfile,
            type = self.type,
            ndays = conf.ndays,
            mode = args.mode,
            param = self.params
        )

        self.retrieval_request = EcmwfRetrieval.factory(factory_args)

    def get_from_tape(self, dryrun=False):
        """perform the MARS retrievals set up in init"""
        self.retrieval_request.execute(dryrun=dryrun)

    @staticmethod
    def _calc_dmean(da_tmp, group_dim):
        da_tmp_out = []
        for (label, group) in da_tmp.groupby(group_dim):
            da_in_tmp = group.copy()
            da_in_tmp['step'] = da_in_tmp.step + da_in_tmp[group_dim]
            da_in_tmp = da_in_tmp.rename({'step': 'time'})
            da_in_tmp = da_in_tmp.resample(time='1D').mean()
            da_tmp_out.append(da_in_tmp)
        return da_tmp_out

    def _check_files(self, check_level=2):

        files_to_check = self.make_filelist()
        for file in files_to_check:
            # quick check if exist
            if not os.path.exists(f'{self.cachedir}/{file}'):
                print(f'{self.cachedir}/{file}')
                raise 'Error: not all files are found in cache'
        if check_level > 1:
            global xr
            if xr is None:
                import xarray as xr

            for file in files_to_check:
                print(f'{self.cachedir}/{file}')
                ds_in = xr.open_dataset(f'{self.cachedir}/{file}')
                print(len(ds_in.time))
                if len(ds_in.time) < self.ndays:
                    raise f'Error: not all timesteps needed found in {self.cachedir}/{file}'



    def make_filelist(self):
        if self.fcast.fcsystem == 'extended-range':
            if self.mode == 'hc':
                files = [f'{date}_mem-{entry+1:03d}_{self.params}.nc'
                         for date in self.fcast.shcdates
                         for entry in range(int(self.fcast.enssize)-1)]

        return files


    def process(self):
        global xr
        if xr is None:
            import xarray as xr

        iname = params_ecmwf[self.params]["xr_code"]

        ds_in = xr.open_dataset(self.retrieval_request.kwargs['target'], engine='cfgrib')

        da_in = ds_in[iname].rename(self.params)

        is_number = 'number' in da_in.dims
        is_step = 'step' in da_in.dims
        is_time = 'time' in da_in.dims

        # make it a 5d array
        if not is_number:
            da_in.expand_dims({'number': 1})
        if not is_step:
            da_in.expand_dims({'step': 1})
        if not is_time:
            da_in.expand_dims({'time': 1})

        da_in = da_in.transpose('number', 'time', 'step', 'latitude', 'longitude')
        da_in = da_in.rename({'time': 'starttime'})

        if self.ldmean:
            da_out = self._calc_dmean(da_in, 'starttime')

        for da_out_save in da_out:
            for number in da_out_save['number']:
                da_out_save = da_out_save.isel(time=slice(self.ndays))
                da_out_save.sel(number=number).to_netcdf(self._get_cachename(da_out_save.sel(number=number)))


    def _get_cachename(self,da_tmp):
        return f'{self.cachedir}/' \
               f'{da_tmp.time[0].dt.strftime("%Y%m%d").values}' \
               f'_mem-{int(da_tmp["number"]):03d}_{da_tmp.name}.nc'
