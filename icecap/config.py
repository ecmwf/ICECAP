"""
This module contains the central configuration of the suite the user
wants to run. Virtually all other modules import this. The configuration
is parsed from a user-editable configuration file.
"""
import argparse
import configparser
import os
import numpy as np

import namelist_entries
import dataobjects

DEFAULT_CONF_NAME = ['icecap.conf']

config_optnames = namelist_entries.config_optnames


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
        message = f'Optname [{section}] is not defined in config.py'
        hmessage = self.add_hint(message, hint)
        super().__init__(hmessage)

class MissingSection(ConfigurationError):
    """exception to raise if an section is expected but not present"""
    def __init__(self, section, hint=None):
        message = f'Section [{section}] is required for configuration.'
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
        message = f'Missing option [{section}] -> {option}'
        hmessage = self.add_hint(message, hint)
        super().__init__(hmessage)


class InvalidOption(ConfigurationError):
    """exception to raise if the value of an option is not recognized"""
    def __init__(self, section, option, hint=None):
        message = f'[{section}] -> {option}: value not valid.'
        hmessage = self.add_hint(message, hint)
        super().__init__(hmessage)


class ConflictingOptions(ConfigurationError):
    """exception to raise if there is a conflict within a set of options"""
    def __init__(self, optionlist, hint=None):
        # optionlist is a list of pairs (section, option)
        opstr = ', '.join([f'([{s}] -> {o})' for (s,o) in optionlist])
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
        self.source = None

        # the following attributes are only temporally allocated
        # but later saved for each plotID in the config file
        self.verif_expname = None
        self.plottype = None
        self.verif_mode = None
        self.target = None
        self.verif_dates = None
        self.verif_enssize = None
        self.verif_fcsystem = None
        self.verif_refdate = None
        self.verif_fromyear = None
        self.verif_toyear = None
        self.cmap = None
        self.plot_extent = None
        self.projection = None
        self.proj_options = None
        self.circle_border = None
        self.calib_dates = None
        self.calib_mode = None
        self.calib_enssize = None
        self.calib_fcsystem = None
        self.calib_refdate = None
        self.calib_fromyear = None
        self.calib_toyear = None
        self.points = None
        self.add_verdata = None
        self.ofile = None




        conf_parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        self.filename = file

        for filename in self.filename:
            if not os.path.isfile(filename):
                raise RuntimeError(f'Configuration file {self.filename} not found.')
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
        self.fcsets = {}
        for expid in fcsetlist:
            section = 'fc_' + expid
            self._init_config(conf_parser, section, 'fc', init=True)

            # check if hcrefdate given for mode='hc' and machine='ecmwf'
            if self.hcrefdate is None and self.machine in ['ecmwf'] and self.mode in ['hc']:
                raise ValueError('hcrefdate needs to be defined for hindcast mode on ecmwf')

            if self.source is None:
                self.source = self.machine

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
                ndays = int(self.ndays),
                source = self.source
            )

        # check for 'ref' keyword
        self.refexp = None
        if len(fcsetlist) > 1:
            _ref_list = [i for i in self.fcsets if self.fcsets[i].ref == "yes"]
            if len(_ref_list) > 1:
                raise ValueError('More than one experiment labelled with ref = yes in config')

        # all daily dates as one list (used later for obs retrieval)
        sdates_verif = []
        for fcset in self.fcsets:
            sdates_verif += getattr(self.fcsets[fcset], 'salldates')
        self.salldates = list(dict.fromkeys(sdates_verif))

        # get fc config entries
        plotsetlist = [section[5:] for section in conf_parser.sections()
                       if section.startswith('plot_')]

        self.plotsets = {}
        for plotid in plotsetlist:
            section = 'plot_' + plotid
            self._init_config(conf_parser, section, 'plot', init=True)

            if self.source is None:
                self.source = self.machine

            self.plotsets[plotid] = dataobjects.PlotConfigObject(
                verif_expname=self.verif_expname,
                plottype =self.plottype,
                verif_mode = self.verif_mode,
                verif_fromyear = self.verif_fromyear,
                verif_toyear = self.verif_toyear,
                target = self.target,
                verif_enssize = self.verif_enssize,
                verif_fcsystem = self.verif_fcsystem,
                verif_refdate = self.verif_refdate,
                projection = self.projection,
                proj_options = self.proj_options,
                circle_border=self.circle_border,
                plot_extent = self.plot_extent,
                cmap = self.cmap,
                source = self.source,
                verif_dates = self.verif_dates,
                calib_mode = self.calib_mode,
                calib_dates = self.calib_dates,
                calib_enssize=self.calib_enssize,
                calib_refdate=self.calib_refdate,
                calib_fromyear=self.calib_fromyear,
                calib_toyear=self.calib_toyear,
                ofile=self.ofile,
                add_verdata=self.add_verdata,
                points=self.points
                )


    def __str__(self):
        """Return string representation of configuration for printing"""
        lines = []
        lines.append(f'\nInfo about configuration in {self.filename}:')

        secname = 'environment'
        lines.append(f'\n* Section [{secname}]')
        for optname in  config_optnames[secname]:
            lines.append(f'%s: {getattr(self, optname)}'
                         % (config_optnames[secname][optname]['printname']))

        if self.ecflow:
            secname = 'ecflow'
            lines.append(f'\n* Section [{secname}]')
            for optname in config_optnames[secname]:
                lines.append(f'%s: {getattr(self, optname)}'
                             % (config_optnames[secname][optname]['printname']))

        secname = 'staging'
        lines.append(f'\n* Section [{secname}]')
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
            lines.append('')

        lines.append('\n* Plotting')
        secname = 'plot'
        for plotid in list(self.plotsets):
            lines.append(f'{plotid}')
            for optname in config_optnames['plot']:
                if hasattr(self.plotsets[plotid], optname):
                    lines.append(f'%s: {getattr(self.plotsets[plotid], optname)}'
                                 % (config_optnames[secname][optname]['printname']))
            lines.append('')





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
        (might depend on other config entries)
        :param section: section name in config_optnames dictionary
        :param name: name of config entry
        :param opt_name: optional or default_value
        :return:
        """

        if opt_name not in ['default', 'optional']:
            raise ValueError('Only default/optional allowed in _lookup_config_dict')

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
