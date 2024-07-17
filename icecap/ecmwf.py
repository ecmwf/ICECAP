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
                    loopdates = self.fcsets[expid].shcrefdate_loop

                self.add_attr([f'variable:EXPID;{expid}',
                               'trigger:verdata==complete'], f'retrieval:{expid}')

                self.add_attr([f'variable:EXPID;{expid}',
                               f'variable:DATES;{loopdates[0]}',
                               'variable:TYPE;INIT',
                               f'task:{conf.fcsets[expid].source}_retrieve'],
                              f'retrieval:{expid}:init')



                self.add_attr([f'repeat:DATES;{loopdates}',
                               'trigger:init==complete'],
                              f'retrieval:{expid}:fc')

                if conf.fcsets[expid].fcsystem in ['extended-range', 'medium-range', 's2s']:
                    self.add_attr(['task:ecmwf_retrieve;mars',
                                   'variable:TYPE;cf'], f'retrieval:{expid}:fc:cf')
                    if conf.fcsets[expid].enssize > 1:
                        self.add_attr(['task:ecmwf_retrieve;mars',
                                       'variable:TYPE;pf'], f'retrieval:{expid}:fc:pf')

                if conf.fcsets[expid].fcsystem in ['long-range']:
                    self.add_attr(['task:ecmwf_retrieve;mars',
                                   'variable:TYPE;fc'], f'retrieval:{expid}:fc')


                # add wipe family
                if conf.keep_native == 'yes':
                    self.add_attr([f'variable:EXPID;{expid}',
                                   'variable:DATES;WIPE',
                                   'variable:TYPE;WIPE',
                                   f'task:{conf.fcsets[expid].source}_retrieve'], f'clean:{expid}')




class EcmwfRetrieval:
    """Defines a single ECMWF retrieval request"""

    @staticmethod
    def factory(kwargs):
        """return appropriate MarsRetrieval subclass"""

        if kwargs['fcsystem'] == 'long-range':
            return _EcmwfLongRangeRetrieval(kwargs)
        if kwargs['fcsystem'] == 'extended-range':
            return _EcmwfExtendedRangeRetrieval(kwargs)
        if kwargs['fcsystem'] == 'medium-range':
            return _EcmwfMediumRangeRetrieval(kwargs)
        if kwargs['fcsystem'] == 's2s':
            return _EcmwfS2sRetrieval(kwargs)


        raise NotImplementedError

    def __init__(self, kwargs):
        self.kwargs = {}
        self.kwargs['date'] = kwargs['date']
        self.kwargs['expver'] = kwargs['expname']
        self.kwargs['levtype'] = 'sfc'
        if kwargs['exptype'] == 'INIT':
            self.kwargs['param'] = '172.128'
        else:
            self.kwargs['param'] = '31.128'
        self.kwargs['time'] = "00:00:00"
        self.kwargs['target'] = kwargs['tfile']
        if kwargs['grid'] is not None:
            self.kwargs['grid'] = kwargs['grid']

        if kwargs['mode'] == 'hc':
            self.kwargs['hdate'] = kwargs['shcdates'][kwargs['loopvalue']]




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
        self.kwargs['type'] = kwargs['exptype']
        self.kwargs['origin'] = kwargs['origin']


        stepsize = 24
        step_offset = 0
        if self.kwargs['origin'] in ['rjtd'] and kwargs['mode'] == 'fc':
            step_offset = 12
            self.kwargs['time'] = "12:00:00"
        self.kwargs['step'] = [f'{n * stepsize + step_offset}-{(n + 1) * stepsize + step_offset}'
                               for n in range(int(kwargs['ndays']))]

        if kwargs['mode'] == 'hc':
            self.kwargs['stream'] = 'enfh'
        else:
            self.kwargs['stream'] = 'enfo'

        if self.kwargs['type'] == 'pf':
            self.kwargs['number'] = [ m+1 for m in range(int(kwargs['enssize'])-1)]

        self.kwargs['origin'] = kwargs['origin']
        self.kwargs['class'] = 's2'


class _EcmwfMediumRangeRetrieval(EcmwfRetrieval):
    """Defines MARS retrieval of step data for medium-range forecast"""
    # keywords needed: class, date, expver, [hdate], levtype, number, param, step,
    # stream, time, type, target
    def __init__(self, kwargs):
        super().__init__(kwargs)
        self.kwargs['class'] = 'od'
        stepsize = 6
        self.kwargs['step'] = [0, 'to', int(kwargs['ndays'])*24-stepsize, 'by', stepsize ]


        if kwargs['mode'] == 'hc':
            self.kwargs['stream'] = 'enfh'
        else:
            self.kwargs['stream'] = 'enfo'

        if kwargs['exptype'] =='INIT':
            self.kwargs['type'] = 'cf'
            self.kwargs['step'] = self.kwargs['step'][0]
            if kwargs['mode'] == 'hc':
                self.kwargs['hdate'] = self.kwargs['hdate'][0]
        else:
            self.kwargs['type'] = kwargs['exptype']

        if self.kwargs['type'] == 'pf':
            self.kwargs['number'] = [ m+1 for m in range(int(kwargs['enssize'])-1) ]



class _EcmwfExtendedRangeRetrieval(EcmwfRetrieval):
    """Defines MARS retrieval of step data for ENS forecast"""
    # keywords needed: class, date, expver, [hdate], levtype, number, param, step,
    # stream, time, type, target
    def __init__(self, kwargs):
        super().__init__(kwargs)
        self.kwargs['class'] = 'od'
        stepsize = 6
        self.kwargs['step'] = [0, 'to', int(kwargs['ndays'])*24-stepsize, 'by', stepsize ]

        if int(kwargs['cycle'][:2]) >= 48:
            if kwargs['mode'] == 'hc':
                self.kwargs['stream'] = 'eefh'
            else:
                self.kwargs['stream'] = 'eefo'
        else:
            if kwargs['mode'] == 'hc':
                self.kwargs['stream'] = 'enfh'
            else:
                self.kwargs['stream'] = 'enfo'

        if kwargs['exptype'] =='INIT':
            self.kwargs['type'] = 'cf'
            self.kwargs['step'] = self.kwargs['step'][0]
            if kwargs['mode'] == 'hc':
                self.kwargs['hdate'] = self.kwargs['hdate'][0]
        else:
            self.kwargs['type'] = kwargs['exptype']

        if self.kwargs['type'] == 'pf':
            self.kwargs['number'] = [ m+1 for m in range(int(kwargs['enssize'])-1) ]


class _EcmwfLongRangeRetrieval(EcmwfRetrieval):
    """Defines MARS retrieval of step data for ENS forecast"""
    # keywords needed: class, date, expver, [hdate], levtype, number, param, step,
    # stream, time, type, target
    def __init__(self, kwargs):
        super().__init__(kwargs)
        self.kwargs['class'] = 'rd'
        stepsize = 24
        self.kwargs['step'] = [0, 'to', int(kwargs['ndays'])*24, 'by', stepsize ]



        self.kwargs['number'] = list(range(int(kwargs['enssize'])))
        self.kwargs['origin'] = 'ecmf'

        self.kwargs['method'] = '1'
        self.kwargs['stream'] = 'mmsf'
        self.kwargs['type'] = kwargs['exptype']

        # for SEAS5 we need to set system variable
        if self.kwargs['expver'] == 'SEAS5':
            self.kwargs['expver'] = '0001'
            self.kwargs['system'] = '5'
            self.kwargs['class'] = 'od'

        if kwargs['exptype'] =='INIT':
            self.kwargs['type'] = 'fc'
            self.kwargs['step'] = self.kwargs['step'][0]


class EcmwfData(dataobjects.ForecastObject):
    """ECMWF Data object calling a factory to
    retrieve appropriate class"""

    def __init__(self, conf, args):
        super().__init__(conf, args)


        if args.exptype not in ['WIPE']:
            self.type = args.exptype
            self.ldmean = False
            if self.fcsystem in ['extended-range', 'medium-range']:
                self.ldmean = True

            self.lsm = False
            if self.fcsystem not in ['s2s']:
                self.lsm = True

            self.offset = 0
            if self.fcsystem in ['s2s','long-range']:
                self.offset = 12

            self.linterp = True
            self.periodic = True


            self.cycle = self.init_cycle(self.startdate)
            self.fccachedir = self.init_cachedir()



            if self.fcsystem in ['medium-range']:
                retrieval_grid = 'F640'
            elif self.fcsystem in ['extended-range', 'long-range']:
                retrieval_grid = 'F320'
            elif self.fcsystem in ['s2s']:
                retrieval_grid = None
            else:
                raise ValueError(f'No grid for retrieval specified for {self.fcsystem}')



            self.tmptargetfile = f'{conf.tmpdir}/{self.source}/{self.modelname}/' \
                                 f'{args.expid}_{args.startdate}_{self.type}_{self.mode}/' \
                                 f'tmp_{args.expid}_{args.startdate}_{self.type}_{self.mode}'


            if self.type == 'INIT':
                self.enssize = 1
                self.tmptargetfile += '.grb'
                cycles_alldates = [self.init_cycle(d) for d in self.refdate]
                cycles = list(dict.fromkeys(cycles_alldates))
                cycle_firstdate = [self.sdates[cycles_alldates.index(_cycle)] for _cycle in cycles]
                cycle_info = [f'{cycles[i]}:{cycle_firstdate[i]}' for i in range(len(cycles))]
                if len(cycles) > 1:
                    raise ValueError(f'Retrieval of forceast data from different model cycles in one config'
                                     f'section not possible --> please create one [fc_expID] entry for '
                                     f' forecast data from each cycle. First dates of cycles in your selection are '
                                     f'{"/ ".join(cycle_info)}')

            else:
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
                loopvalue=args.startdate,
                exptype=args.exptype,
                date=self.startdate,
                expname=self.expname,
                fcsystem=self.fcsystem,
                tfile = self.tmptargetfile,
                ndays = self.ndays,
                mode = self.mode,
                param = self.params,
                grid = retrieval_grid,
                cycle = self.cycle,
                origin = self.modelname,
                shcdates = self.shcdates,
                enssize = self.enssize
            )

            self.retrieval_request = EcmwfRetrieval.factory(factory_args)


    def _make_download_filelist(self):
        """
        MARS will retrieve data in separate files using HDATE for hindcasts and
        NUMBER for ensembles. Here a list containing all expected files is created which later used
        for processing
        :return: list of filenames of downloaded files
        """

        if self.fcsystem == 'long-range':
            number = list(range(int(self.enssize)))
            _files = [self.tmptargetfile.replace('[NUMBER]', str(n)) for n in number]
        else:
            if self.mode == 'hc':
                if self.type == 'pf':
                    number = [ m+1 for m in range(int(self.enssize)-1) ]
                    _files = []
                    for num in number:
                        for _date in self.shcdates[self.loopvalue]:
                            _files.append(self.tmptargetfile.replace('[HDATE]', _date).replace('[NUMBER]', str(num)))
                else:
                    _files = [self.tmptargetfile.replace('[HDATE]', str(_date))
                              for _date in self.shcdates[self.loopvalue]]
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
            dates = self.shcdates[self.loopvalue]


        if self.fcsystem in ['extended-range', 'medium-range','s2s']:
            if self.type == 'cf':
                members = range(1)
            elif self.type == 'pf':
                members = range(int(self.enssize) - 1)

        if self.fcsystem in ['long-range']:
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
        """Process retrieved ECMWF data and write to cache"""

        xr.set_options(keep_attrs=True)

        for file in self._make_download_filelist():
            print(file)

            ds_in = xr.open_dataset(file, engine='cfgrib')
            if len(list(ds_in.data_vars))>1:
                raise ValueError(f'More than one variable detected in file {file}')
            iname = list(ds_in.data_vars)[0]

            da_in = ds_in[iname].rename(self.params)




            # mask using the land-sea mask (if necessary for the respective dataset)
            if self.lsm:
                da_lsm = xr.open_dataarray(f'{self.fccachedir}/lsm.nc')
                if 'number' in da_lsm.dims:
                    da_lsm = da_lsm.isel(number=0)
                # drop coords not in dims as otherwise time is deleted from da_in after where command
                da_lsm = da_lsm.drop([i for i in da_lsm.coords if i not in da_lsm.dims])
                da_in = da_in.where(da_lsm==0)
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
            da_out = convert_step2time(da_out, offset_hour=self.offset)
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
                    da_out_save = self.interpolate(da_out.sel(number=[number]))
                else:
                    da_out_save = da_out.sel(number=number)
                ofile = self._save_filename(date=startdate, number=number, grid=self.grid)
                da_out_save.sel(number=number).to_netcdf(ofile)
