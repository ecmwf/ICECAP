"""
This module contains the central configuration of the suite the user
wants to run. Virtually all other modules import this. The configuration
is parsed from a user-editable configuration file.
"""
import argparse
import configparser
import os

import numpy as np
import dataobjects





DEFAULT_CONF_NAME = 'icecap.conf'

# this dictionary defines all option names which can be provided through the config file
# it defines if the option is optional or what values are can be used
config_optnames = {
    'environment': {
        'user': {
            'printname' : "user name",
            'optional' : False
        },
        'machine': {
            'printname' : 'machine',
            'optional' : False,
            'allowed_values' : ['ecmwf','test']
        },
        'ecflow': {
            'printname' : 'use ecflow',
            'optional' : True,
            'allowed_values' : ["yes", "no"]
        },
        'suitename': {
            'printname' : 'name of suite',
            'optional' : False
        },
        'sourcedir': {
            'printname': 'Directory of source code',
            'optional' : False
        },
        'rundir': {
            'printname': 'Directory for runtime copy of ecFlow and Python scripts',
            'optional' : False
        },
        'datadir': {
            'printname': 'Directory for data/metrics/plots',
            'optional' : False
        },
        'tmpdir': {
            'printname': 'temporary working directory',
            'optional' : False,
        },
        'cachedir':{
            'printname': 'cache directory',
            'optional' : False
        }
    }, # end environment
    'ecflow': {
        'ecfhomeroot': {
            'printname': 'Root directory for ecFlow-generated files (ECF_HOME)',
            'optional' : False,
        },
        'ecflow_host': {
            'printname': 'ecflow hostname',
            'optional' : False
        },
        'ecflow_port': {
            'printname': 'ecflow host port',
            'optional' : ['ecflow:yes']
        }
    }, # end ecflow
    'staging': {
        'verdata' : {
            'printname' : 'verifying dataset',
            'optional' : False
        },
        'params':{
            'printname':'variable name',
            'optional' : False
        },
        # might be useful for debugging but will not re-calc native if interpolated fields exist
        'keep_native' : {
            'printname' : 'store daily mean data in native grid (additionally)',
            'optional' : True,
            'default_value' : ["no"],
            'allowed_values' : ["yes", "no"]
        }
    }, # end staging
    'fc' : {
        'fcsystem' : {
            'printname':'forecasting system name',
            'optional' : False,
            'allowed_values' : ["medium-range", "extended-range","long-range"]
        },
        'expname' : {
            'printname':'experiment name',
            'optional' : False,
        },

        'enssize':{
            'printname' : 'ensemble size',
            'optional' : True,
        },
        'dates':{
            'printname' : 'forecast dates',
            'optional' : ['mode:fc'],
        },
        'mode':{
            'printname': 'forcast or hindcast mode',
            'optional' : False,
            'allowed_values' : ["hc", "fc"]
        },
        'hcrefdate':{
            'printname' : 'hindcast reference date',
            'optional' : True
        },
        'hcfromdate':{
            'printname' : 'first hindcast year',
            'optional' : ['mode:hc']
        },
        'hctodate':{
            'printname' : 'first hindcast year',
            'optional' : ['mode:hc'],
        },
        'ndays': {
            'printname' : 'number of days to be staged',
            'optional' : False
        },
        'ref' : {
            'printname' : 'use this forecast as reference',
            'optional' : True,
            'default_value' : ["no"],
            'allowed_values' : ["yes", "no"]
        }
    }, # end fc
    'plot' : {
        'verif_expname' : {
            'printname':'experiment name for plotting',
            'optional' : False,
        },
        'plottype' : {
            'printname':'plot type',
            'optional' : False,
            'allowed_values' : ["interp_check"]
        },
        'verif_mode':{
            'printname': 'forcast or hindcast mode for plotting',
            'optional' : False,
        },
        'verif_fromdate':{
            'printname' : 'first year',
            'optional' : False,
        },
        'verif_todate':{
            'printname' : 'last year',
            'optional' : False,
        },
        'target':{
            'printname' : 'target time for plotting',
            'optional' : False,
        },
        'verif_enssize':{
            'printname' : 'ensemble size used for metrics',
            'optional' : False
        },
        'verif_fcsystem':{
            'printname' : 'forecast system specification',
            'optional' : False,
            'allowed_values' : ["medium-range", "extended-range","long-range"]
        },
        'verif_refdate':{
            'printname' : 'experiment reference date',
            'optional':False
        }
    }
}




class ConfigurationError(Exception):
    """user-defined exceptions to raise for bad configurations"""
    @staticmethod
    def add_hint(message, hint):
        """Add hint to message"""
        if hint is None:
            return message

        return message + '\nHINT: ' + hint

class MissingEntry(ConfigurationError):
    """exception to raise if an section is expected but not present"""
    def __init__(self, section, hint=None):
        message = 'Optname [{}] is not defined in config.py'.format(section)
        hmessage = self.add_hint(message, hint)
        super().__init__(hmessage)

class MissingSection(ConfigurationError):
    """exception to raise if an section is expected but not present"""
    def __init__(self, section, hint=None):
        message = 'Section [{}] is required for configuration.'.format(section)
        hmessage = self.add_hint(message, hint)
        super().__init__(hmessage)


class InvalidSection(ConfigurationError):
    """exception to raise when encountering a section with an invalid name"""
    def __init__(self, section, hint=None):
        message = f'Section [{section}]: name not valid.'
        hmessage = self.add_hint(message, hint)
        super().__init__(hmessage)


class MissingOption(ConfigurationError):
    """exception to raise if an option is expected but not present"""
    def __init__(self, section, option, hint=None):
        message = 'Missing option [{}] -> {}'.format(section, option)
        hmessage = self.add_hint(message, hint)
        super().__init__(hmessage)


class InvalidOption(ConfigurationError):
    """exception to raise if the value of an option is not recognized"""
    def __init__(self, section, option, hint=None):
        message = '[{}] -> {}: value not valid.'.format(section, option)
        hmessage = self.add_hint(message, hint)
        super().__init__(hmessage)


class ConflictingOptions(ConfigurationError):
    """exception to raise if there is a conflict within a set of options"""
    def __init__(self, optionlist, hint=None):
        # optionlist is a list of pairs (section, option)
        opstr = ', '.join(['([{}] -> {})'.format(s,o) for (s,o) in optionlist])
        message = 'conflicting options: ' + opstr
        hmessage = self.add_hint(message, hint)
        super().__init__(hmessage)

class Configuration():
    """The ICECAP configuration used by every callable script."""

    def __init__(self, file=None):
        """Initialise Configuration instance from text file"""

        self.user = None
        self.machine = None
        self.ecflow = None
        self.suitename = None
        self.sourcedir = None
        self.rundir = None
        self.datadir = None
        self.ecfhomeroot = None
        self.ecflow_host = None
        self.ecflow_port = None
        self.lonlatres = None
        self.verdata = None
        self.params = None
        self.fcsystem = None
        self.expname = None
        self.enssize = None
        self.dates = None
        self.mode = None
        self.hcrefdate = None
        self.hcfromdate = None
        self.hctodate = None
        self.ref = None
        self.ndays = None

        # the following attributes are only temporally allocated
        # but later saved for each plotID in the config file
        self.verif_expname = None
        self.plottype = None
        self.verif_mode = None
        self.verif_fromdate = None
        self.verif_todate = None
        self.target = None
        self.verif_enssize = None
        self.verif_fcsystem = None
        self.verif_refdate = None


        conf_parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        self.filename = file
        if not os.path.isfile(self.filename):
            raise RuntimeError('Configuration file {} not found.'.format(self.filename))
        conf_parser.read(self.filename)

        # attributes to beways initialized irrespective of environment or ecflow setting
        self.default_config_filename = DEFAULT_CONF_NAME


        # now initialize the environment as this determines batch/ecflow mode and machine
        self._init_config(conf_parser, 'environment')

        # some default values in icecap which can't be changed via config file
        self.stagedir = self.datadir + '/stage'  # staged data files
        self.metricdir = self.datadir + '/metrics'  # metrics computed from data
        self.plotdir = self.datadir + '/plots'  # plots of metrics
        self.pydir = self.rundir + '/py'  # Python scripts
        self.ecffilesdir = self.rundir + '/ecf_files'  # ECF_FILES
        self.ecfincdir = self.ecffilesdir + '/include'  # ECF_INC


        # set up ecflow variables if needed
        if self.ecflow:
            # some default values in icecap which can't be changed via config file
            self.toplevel_suite = 'icecap'
            self.begin_suite_suspended = True
            self.stop_at_first_problem = False
            self.stage_sources_together = True
            self.split_get = True

            self._init_config(conf_parser, 'ecflow')


        # get forecast attributes from config
        self._init_config(conf_parser, 'staging')

        # get fc config entries
        fcsetlist = [section[3:] for section in conf_parser.sections() if section.startswith('fc_')]
        if len(fcsetlist) == 0:
            raise MissingSection('fc_*', 'At least one forecast section needed.')
        self.fcsets = dict()
        for expid in fcsetlist:
            section = 'fc_' + expid
            self._init_config(conf_parser, section, 'fc', init=True)

            # check if hcrefdate given for mode='hc' and machine='ecmwf'
            if self.hcrefdate is None and self.machine in ['ecmwf'] and self.mode in ['hc']:
                raise 'hcrefdate needs to be defined for hindcast mode on ecmwf'


            self.fcsets[expid] = dataobjects.ForecastConfigObject(
                fcsystem = self.fcsystem,
                expname = self.expname,
                enssize = self.enssize,
                dates = self.dates,
                mode = self.mode,
                hcrefdate = self.hcrefdate,
                hcfromdate = self.hcfromdate,
                hctodate=self.hctodate,
                ref = self.ref,
                ndays = int(self.ndays)
            )

        # check for 'ref' keyword
        self.refexp = None
        if len(fcsetlist) > 1:
            _ref_list = [i for i in self.fcsets if self.fcsets[i].ref == "yes"]
            if len(_ref_list) > 1:
                raise 'More than one experiment labelled with ref = yes in config'

        # all daily dates as one list (used later for obs retrieval)
        sdates_verif = []
        for fcset in self.fcsets:
            sdates_verif += getattr(self.fcsets[fcset], 'salldates')
        self.salldates = list(dict.fromkeys(sdates_verif))

        # get fc config entries
        plotsetlist = [section[5:] for section in conf_parser.sections()
                       if section.startswith('plot_')]

        self.plotsets = dict()
        for plotid in plotsetlist:
            section = 'plot_' + plotid
            self._init_config(conf_parser, section, 'plot', init=True)

            self.plotsets[plotid] = dataobjects.PlotConfigObject(
                verif_expname=self.verif_expname,
                plottype =self.plottype,
                verif_mode = self.verif_mode,
                verif_fromdate = self.verif_fromdate,
                verif_todate = self.verif_todate,
                target = self.target,
                verif_enssize = self.verif_enssize,
                verif_fcsystem = self.verif_fcsystem,
                verif_refdate = self.verif_refdate
                )






    def __str__(self):
        """Return string representation of configuration for printing"""
        lines = list()
        lines.append(f'\nInfo about configuration in {self.filename}:')

        secname = 'environment'
        lines.append('\n* Section [%s]' % (secname))
        for optname in  config_optnames[secname]:
            lines.append(f'%s: {getattr(self, optname)}'
                         % (config_optnames[secname][optname]['printname']))

        if self.ecflow:
            secname = 'ecflow'
            lines.append('\n* Section [%s]' % (secname))
            for optname in config_optnames[secname]:
                lines.append(f'%s: {getattr(self, optname)}'
                             % (config_optnames[secname][optname]['printname']))

        secname = 'staging'
        lines.append('\n* Section [%s]' % (secname))
        for optname in config_optnames[secname]:
            lines.append(f'%s: {getattr(self, optname)}'
                         % (config_optnames[secname][optname]['printname']))

        lines.append('\n* Forecast experiments')
        secname = 'fc'
        for expid in list(self.fcsets):
            lines.append(f'{expid}')
            for optname in config_optnames['fc']:
                if hasattr(self.fcsets[expid], optname):
                    lines.append(f'%s: {getattr(self.fcsets[expid], optname)}'
                                 % (config_optnames[secname][optname]['printname']))

        lines.append('\n* Plotting')
        secname = 'plot'
        for plotid in list(self.plotsets):
            lines.append(f'{plotid}')
            for optname in config_optnames['plot']:
                if hasattr(self.plotsets[plotid], optname):
                    lines.append(f'%s: {getattr(self.plotsets[plotid], optname)}'
                                 % (config_optnames[secname][optname]['printname']))





        return '\n  '.join(lines)

    def _init_config(self, _conf_parser, secname, section_config_name=None, init=False):
        """
        function to initialise config entries for specific config section
        :param _conf_parser: coniguration parser object
        :param secname: section name in config
        :param section_config_name: section name in config_optnames dictionary
        :param init: set to True if all values in config shoudl be re-initialized with None
        """
        if section_config_name is None:
            section_config_name = secname
        for optname in config_optnames[section_config_name]:
            self._set_config_entry(_conf_parser, secname, optname,
                                   section_config_name, init)











    def _set_config_entry(self, _conf_parser, section, name,
                          section_config_name, init):
        """
        Set object attribute for each config entry
        :param _conf_parser: configuration parser object
        :param section: section name in config
        :param name: name of the specific config entry
        :param section_config_name: section name in config_optnames dictionary
        :param init: set to True if all values in config shoudl be re-initialized with None
        """

        if not hasattr(self, name) or init is True:
            # initialize to None if not set before or if desired using init=True
            setattr(self, name, None)

        if name not in config_optnames[section_config_name].keys():
            raise MissingEntry(section, name)

        if _conf_parser.has_option(section, name):
            if 'allowed_values' not in config_optnames[section_config_name][name].keys():
                setattr(self, name, _conf_parser.get(section, name))
            elif 'allowed_values' in config_optnames[section_config_name][name].keys() and \
                    _conf_parser.get(section, name) in \
                    config_optnames[section_config_name][name]['allowed_values']:
                setattr(self, name, _conf_parser.get(section, name))
            else:
                raise InvalidOption(section, name)
        # else if config entry not specified --> check if optional
        else:
            # optional can be True/False but also depend on other config entries
            _optional =  np.atleast_1d(config_optnames[section_config_name][name]['optional']).tolist()

            if False in _optional:
                raise MissingOption(section, name)
            if True not in _optional:
                self._lookup_config_dict(section_config_name, name, 'optional')
            # if entry is optional --> check for default_values
            else:
                if 'default_value' in config_optnames[section_config_name][name].keys():
                    _default = np.atleast_1d(config_optnames[section_config_name][name]['default_value']).tolist()

                    if "yes" in _default or "no" in _default:
                        setattr(self, name, _default[0])
                    else:
                        self._lookup_config_dict(section_config_name, name, 'default_value')


    def _lookup_config_dict(self, section, name, opt_name):
        """
        function to set object attribute to default value or optional value
        (migth depend on other config entries)
        :param section: section name in config_optnames dictionary
        :param name: name of config entry
        :param opt_name: optional or default_value
        :return:
        """

        if opt_name not in ['default', 'optional']:
            raise 'Only default/optional allowed in _lookup_config_dict'

        _args = np.atleast_1d(config_optnames[section][name][opt_name]).tolist()
        for _arg in _args:
            _args = _arg.split(':')
            if opt_name in ['default_value']:
                if _args[1] == getattr(self, _args[0]):
                    setattr(self, name, _args[2])
                    return
            elif opt_name in ['optional']:
                if _args[1] == str(getattr(self, _args[0])):
                    raise MissingOption(section, name)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Print the ICEPAC configuration')
    helpstr = 'configuration file to use'
    parser.add_argument('-c', '--configfile', help=helpstr,
                        default=DEFAULT_CONF_NAME, nargs="+")

    args = parser.parse_args()
    conf = Configuration(file=args.configfile)
    print(conf)
