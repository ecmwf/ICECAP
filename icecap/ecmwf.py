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
from cds import convert_step2time

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



                self.add_attr([f'repeat:DATES;{loopdates}',
                               'trigger:init==complete'],
                              f'retrieval:{expid}:fc')

                if conf.fcsets[expid].fcsystem in ['extended-range', 'medium-range', 's2s']:
                    self.add_attr(['task:ecmwf_retrieve;mars',
                                   'variable:TYPE;cf'], f'retrieval:{expid}:fc:cf')
                    self.add_attr(['task:ecmwf_retrieve;mars',
                                   'variable:TYPE;pf'], f'retrieval:{expid}:fc:pf')

                if conf.fcsets[expid].fcsystem in ['long-range']:
                    self.add_attr(['task:ecmwf_retrieve;mars',
                                   'variable:TYPE;fc'], f'retrieval:{expid}:fc')


                # add wipe family
                if conf.keep_native == 'yes':
                    self.add_attr([f'variable:EXPID;{expid}',
                                   'variable:DATES;WIPE',
                                   'variable:TYPE;pf',
                                   f'task:{conf.fcsets[expid].source}_retrieve'], f'clean:{expid}')




class EcmwfRetrieval:
    """Defines a single ECMWF retrieval request"""

    @staticmethod
    def factory(kwargs):
        """return appropriate MarsRetrieval subclass"""

        if kwargs['fcastobj'].fcsystem == 'long-range':
            return _EcmwfLongRangeRetrieval(kwargs)
        if kwargs['fcastobj'].fcsystem == 'extended-range':
            return _EcmwfExtendedRangeRetrieval(kwargs)
        if kwargs['fcastobj'].fcsystem == 'medium-range':
            return _EcmwfMediumRangeRetrieval(kwargs)
        if kwargs['fcastobj'].fcsystem == 's2s':
            return _EcmwfS2sRetrieval(kwargs)


        raise NotImplementedError

    def __init__(self, kwargs):
        self.kwargs = {}
        self.kwargs['date'] = kwargs['date']
        self.kwargs['expver'] = kwargs['fcastobj'].expname
        self.kwargs['levtype'] = 'sfc'
        self.kwargs['param'] = params_ecmwf[kwargs['param']]['grib_code']
        self.kwargs['time'] = "00:00:00"
        self.kwargs['target'] = kwargs['tfile']
        if kwargs['grid'] is not None:
            self.kwargs['grid'] = kwargs['grid']




    def pprint(self):
        """print MARS request"""
        print(f'MARS retrieval request for target file {os.path.basename(self.kwargs["target"])}:')
        for mkey,mval in self.kwargs.items():
            print(f'  {mkey} = {mval}')

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
                        marsval = f'"{pyval}"'
                    else:
                        marsval = pyval
                    request += f',\n{keyword} = {marsval}'
                request += '\n'
                requestfilename = wdir + '/marsrequest'
                with open(requestfilename, 'w', encoding="utf-8") as rfile:
                    rfile.write(request)

                with open(requestfilename, 'r', encoding="utf-8") as rfile:
                    subprocess.check_call('mars', stdin=rfile)


class _EcmwfS2sRetrieval(EcmwfRetrieval):
    """Defines MARS retrieval of step data for S2S forecast"""
    def __init__(self, kwargs):
        super().__init__(kwargs)
        self.kwargs['type'] = kwargs['type']
        self.kwargs['origin'] = kwargs['origin']


        stepsize = 24
        step_offset = 0
        if self.kwargs['origin'] in ['rjtd'] and kwargs['mode'] == 'fc':
            step_offset = 12
        self.kwargs['step'] = [f'{n * stepsize + step_offset}-{(n + 1) * stepsize + step_offset}'
                               for n in range(int(kwargs['ndays']))]

        if kwargs['mode'] == 'hc':
            self.kwargs['hdate'] = kwargs['fcastobj'].shcdates
            self.kwargs['stream'] = 'enfh'
        else:
            self.kwargs['stream'] = 'enfo'

        if self.kwargs['type'] == 'pf':
            self.kwargs['number'] = [ m+1 for m in range(int(kwargs['fcastobj'].enssize)-1)]

        self.kwargs['origin'] = kwargs['origin']
        self.kwargs['class'] = 's2'


class _EcmwfMediumRangeRetrieval(EcmwfRetrieval):
    """Defines MARS retrieval of step data for medium-range forecast"""
    # keywords needed: class, date, expver, [hdate], levtype, number, param, step,
    # stream, time, type, target
    def __init__(self, kwargs):
        super().__init__(kwargs)
        self.kwargs['type'] = kwargs['type']
        self.kwargs['class'] = 'od'
        stepsize = 6
        self.kwargs['step'] = [0, 'to', int(kwargs['ndays'])*24, 'by', stepsize ]


        if kwargs['mode'] == 'hc':
            self.kwargs['hdate'] = kwargs['fcastobj'].shcdates
            self.kwargs['stream'] = 'enfh'
        else:
            self.kwargs['stream'] = 'enfo'

        if self.kwargs['type'] == 'pf':
            self.kwargs['number'] = [ m+1 for m in range(int(kwargs['fcastobj'].enssize)-1) ]



class _EcmwfExtendedRangeRetrieval(EcmwfRetrieval):
    """Defines MARS retrieval of step data for ENS forecast"""
    # keywords needed: class, date, expver, [hdate], levtype, number, param, step,
    # stream, time, type, target
    def __init__(self, kwargs):
        super().__init__(kwargs)
        self.kwargs['type'] = kwargs['type']
        self.kwargs['class'] = 'od'
        stepsize = 6
        self.kwargs['step'] = [0, 'to', int(kwargs['ndays'])*24, 'by', stepsize ]

        if int(kwargs['cycle'][:2]) >= 48:
            if kwargs['mode'] == 'hc':
                self.kwargs['hdate'] = kwargs['fcastobj'].shcdates
                self.kwargs['stream'] = 'eefh'
            else:
                self.kwargs['stream'] = 'eefo'
        else:
            if kwargs['mode'] == 'hc':
                self.kwargs['hdate'] = kwargs['fcastobj'].shcdates
                self.kwargs['stream'] = 'enfh'
            else:
                self.kwargs['stream'] = 'enfo'

        if self.kwargs['type'] == 'pf':
            self.kwargs['number'] = [ m+1 for m in range(int(kwargs['fcastobj'].enssize)-1) ]


class _EcmwfLongRangeRetrieval(EcmwfRetrieval):
    """Defines MARS retrieval of step data for ENS forecast"""
    # keywords needed: class, date, expver, [hdate], levtype, number, param, step,
    # stream, time, type, target
    def __init__(self, kwargs):
        super().__init__(kwargs)
        self.kwargs['class'] = 'rd'
        stepsize = 24
        self.kwargs['step'] = [0, 'to', int(kwargs['ndays'])*24, 'by', stepsize ]



        self.kwargs['number'] = [ m for m in range(int(kwargs['fcastobj'].enssize)) ]

        if kwargs['origin'] != 'ecmwf':
            raise ValueError('Only ecmwf is allowed for source=ecmwf and fcsystem=long-range')
        self.kwargs['origin'] = 'ecmf'

        self.kwargs['method'] = '1'
        self.kwargs['stream'] = 'mmsf'
        self.kwargs['type'] = kwargs['type']

        # for SEAS5 we need to set system variable
        if self.kwargs['expver'] == 'SEAS5':
            self.kwargs['expver'] = '0001'
            self.kwargs['system'] = '5'
            self.kwargs['class'] = 'od'


class EcmwfData(dataobjects.ForecastObject):
    """ECMWF Data object calling a factory to
    retrieve appropriate class"""

    def __init__(self, conf, args):
        super().__init__(conf, args)

        if args.startdate not in ['INIT','WIPE']:
            self.type = args.exptype

            self.ldmean = False
            if self.fcast.fcsystem in ['extended-range', 'medium-range']:
                setattr(self, 'ldmean', True)

            self.linterp = True
            self.periodic = True


            self.cycle = self.init_cycle(self.startdate)
            self.fccachedir = self.init_cachedir()

            if self.fcast.fcsystem in ['medium-range']:
                retrieval_grid = 'F640'
            elif self.fcast.fcsystem in ['extended-range', 'long-range']:
                retrieval_grid = 'F320'
            elif self.fcast.fcsystem in ['s2s']:
                retrieval_grid = None
            else:
                raise ValueError(f'No grid for retrieval specified for {self.fcast.fcsystem}')

            self.tmptargetfile = f'{conf.tmpdir}/{self.source}/{self.modelname}/{args.expid}_{args.startdate}_{self.type}_{self.mode}/' \
                                 f'tmp_{args.expid}_{args.startdate}_{self.type}_{self.mode}'

            if self.mode == 'hc':
                if self.type == 'pf':
                    self.tmptargetfile += '_[NUMBER]_[HDATE].grb'
                else:
                    self.tmptargetfile += '_[HDATE].grb'
            else:
                if self.type in ['pf','fc']:
                    self.tmptargetfile += '_[NUMBER].grb'
                else:
                    self.tmptargetfile += '.grb'

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
                grid = retrieval_grid,
                cycle = self.cycle,
                origin = self.modelname
            )

            self.retrieval_request = EcmwfRetrieval.factory(factory_args)


    def _make_download_filelist(self):
        """
        MARS will retrieve data in separate files using HDATE for hindcasts and
        NUMBER for ensembles. Here a list containing all expected files is created which later used
        for processing
        :return: list of filenames of downloaded files
        """

        if self.fcast.fcsystem == 'long-range':
            number = list(range(int(self.enssize)))
            _files = [self.tmptargetfile.replace('[NUMBER]', str(n)) for n in number]
        else:
            if self.mode == 'hc':
                if self.type == 'pf':
                    number = [ m+1 for m in range(int(self.enssize)-1) ]
                    _files = []
                    for num in number:
                        for _date in self.fcast.shcdates:
                            _files.append(self.tmptargetfile.replace('[HDATE]', _date).replace('[NUMBER]', str(num)))
                else:
                    _files = [self.tmptargetfile.replace('[HDATE]', str(_date)) for _date in self.fcast.shcdates]
            else:
                if self.type == 'pf':
                    number = [m + 1 for m in range(int(self.enssize) - 1)]
                    _files = [self.tmptargetfile.replace('[NUMBER]', str(n)) for n in number]
                else:
                    _files = [self.tmptargetfile]

        return _files



    def get_from_tape(self, dryrun=False):
        """perform the MARS retrievals set up in init"""
        self.retrieval_request.execute(dryrun=dryrun)



    def make_filelist(self):
        """Generate a list of files which are expected to be staged"""
        filename = self._filenaming_convention('fc')
        files_list = []

        dates = [self.startdate]
        if self.mode == 'hc':
            dates = self.fcast.shcdates


        if self.fcast.fcsystem in ['extended-range', 'medium-range','s2s']:
            if self.type == 'cf':
                members = range(1)
            elif self.type == 'pf':
                members = range(int(self.fcast.enssize) - 1)

        if self.fcast.fcsystem in ['long-range']:
            members = range(int(self.fcast.enssize))

        files = [filename.format(date, member, self.params, self.grid)
                 for date in dates
                 for member in members]


        _cachedir = self.fccachedir

        files_list += [_cachedir + '/' + file for file in files]

        return files_list


    def process(self):
        """Process retrieved ECMWF data and write to cache"""



        iname = 'siconc'
        for file in self._make_download_filelist():

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
