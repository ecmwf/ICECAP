"""
This module should contain all ecmwf specific relevant information, e.g.
mars retrieval, ecmwf retrieval flow
"""

import os
import subprocess
import xarray as xr


import flow
import utils
import dataobjects

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
        # _object.add_attr(['variable:EXEHOST;hpc-batch'], f'global')
        site = 'hpc'
        self.add_attr([f'variable:ECF_JOB_CMD;troika submit -o %ECF_JOBOUT% {site} %ECF_JOB%',
                       f'variable:ECF_KILL_CMD;troika kill {site} %ECF_JOB%',
                       f'variable:ECF_STATUS_CMD;troika monitor {site} %ECF_JOB%',
                       'variable:EXEHOST;hpc-batch'], 'global')

        for expid in conf.fcsets.keys():
            if conf.fcsets[expid].source == self.machine:
                if conf.fcsets[expid].mode in ['fc']:
                    loopdates = self.fcsets[expid].sdates
                elif conf.fcsets[expid].mode in ['hc']:
                    loopdates = self.fcsets[expid].shcrefdate

                self.add_attr([f'variable:EXPID;{expid}',
                               'trigger:verdata==complete'], f'retrieval:{expid}')

                self.add_attr([f'variable:EXPID;{expid}',
                               'variable:DATES;INIT',
                               'variable:TYPE;pf',
                               f'task:{conf.fcsets[expid].source}_retrieve'],
                              f'retrieval:{expid}:init')



                self.add_attr(['repeat:DATES;{}'.format(loopdates),
                               'trigger:init==complete'],
                              f'retrieval:{expid}:fc')

                if conf.fcsets[expid].fcsystem in ['extended-range', 'medium-range']:
                    self.add_attr(['task:ecmwf_retrieve;mars',
                                   'variable:TYPE;cf'], f'retrieval:{expid}:fc:cf')
                    self.add_attr(['task:ecmwf_retrieve;mars',
                                   'variable:TYPE;pf'], f'retrieval:{expid}:fc:pf')

                # add wipe family
                self.add_attr([f'variable:EXPID;{expid}',
                               'variable:DATES;WIPE',
                               'variable:TYPE;pf',
                               f'task:{conf.fcsets[expid].source}_retrieve'], f'clean:{expid}')




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
        self.kwargs['grid'] = kwargs['grid']



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

        self.kwargs['grid'] = kwargs['grid']



class EcmwfData(dataobjects.ForecastObject):
    """ECMWF Data object calling a factory to
    retrieve appropriate class"""

    def __init__(self, conf, args):

        super().__init__(conf, args)


        if args.startdate not in ['INIT','WIPE']:
            self.type = args.exptype

            self.ldmean = False
            if self.fcast.fcsystem in ['extended-range']:
                setattr(self, 'ldmean', True)

            self.linterp = True
            self.grid = self.verif_name
            self.periodic = True


            self.cycle = self.init_cycle(self.startdate)
            self.fccachedir = self.init_cachedir()


            if self.fcast.fcsystem in ['extended-range']:
                retrieval_grid = 'F320'
            else:
                raise ValueError(f'No grid for retrieval specified for {self.fcast.fcsystem}')

            self.tmptargetfile = f'{conf.tmpdir}/{self.source}/{args.expid}_{args.startdate}_{self.type}_{self.mode}/' \
                                 f'tmp_{args.expid}_{args.startdate}_{self.type}_{self.mode}.grb'
            utils.make_dir(os.path.dirname(self.tmptargetfile))

            factory_args = dict(
                exptype=args.exptype,
                date=self.startdate,
                fcastobj=self.fcast,
                tfile = self.tmptargetfile,
                type = self.type,
                ndays = self.ndays,
                mode = self.mode,
                param = self.params,
                grid = retrieval_grid
            )

            self.retrieval_request = EcmwfRetrieval.factory(factory_args)


    def get_from_tape(self, dryrun=False):
        """perform the MARS retrievals set up in init"""
        self.retrieval_request.execute(dryrun=dryrun)

    def make_filelist(self):
        """Generate a list of files which are expected to be staged"""
        filename = self._filenaming_convention('fc')
        files_list = []
        date = self.startdate

        if self.fcast.fcsystem == 'extended-range':
            if self.type == 'cf':
                members = range(1)
            elif self.type == 'pf':
                members = range(int(self.fcast.enssize) - 1)


            files = [filename.format(date, member, self.params, self.grid)
                     for member in members]


            _cachedir = self.fccachedir

            files_list += [_cachedir + '/' + file for file in files]

        return files_list




    @staticmethod
    def _calc_dmean(da_tmp):
        da_in_tmp = da_tmp.copy()
        da_in_tmp['step'] = da_in_tmp.step + da_in_tmp['starttime']
        da_in_tmp = da_in_tmp.rename({'step': 'time'})
        da_in_tmp = da_in_tmp.resample(time='1D').mean()

        return da_in_tmp

    def process(self):
        """Process retrieved ECMWF data and write to cache"""

        iname = params_ecmwf[self.params]["xr_code"]

        ds_in = xr.open_dataset(self.retrieval_request.kwargs['target'], engine='cfgrib')

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

        # split into list of files with one starttime
        files_pp = [da_in.sel(starttime=stime) for stime in da_in['starttime']]


        if self.ldmean:
            files_pp_dmean = [self._calc_dmean(file) for file in files_pp]
            files_pp = files_pp_dmean

        if self.keep_native == "yes":
            self.grid = 'native'
            for da_out_save in files_pp:
                for number in da_out_save['number'].values:
                    da_out_save = da_out_save.isel(time=slice(self.ndays))
                    ofile = self._save_filename(number=number)
                    da_out_save.sel(number=number).to_netcdf(ofile)

        self.grid = self.verif_name
        if self.linterp:
            files_pp_interp = [self.interpolate(file) for file in files_pp]
            files_pp = files_pp_interp

        for da_out_save in files_pp:
            for number in da_out_save['number'].values:
                da_out_save = da_out_save.isel(time=slice(self.ndays))
                ofile = self._save_filename(number=number)
                da_out_save.sel(number=number).to_netcdf(ofile)
