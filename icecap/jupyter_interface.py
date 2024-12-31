""" Module for Jupyter Notebook Interface """

import os
import glob
import argparse
import shutil
import datetime
import configparser
import numpy as np
from ipywidgets import widgets, VBox
from IPython.display import display
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

import utils
import namelist_entries
from icecap import icecap_api
import config
import dataobjects

jupyter_output = widgets.Output()

class Args(argparse.Namespace):
    """ Class to pass arguments to ICECAP functions """
    wipe = 0
    verbose = False
    force = True



class Icecap:
    """ ICECAP Jupyter class"""
    jupyter_output = widgets.Output()

    def __init__(self, configfile, wipe=0):
        jupyter_output.clear_output(wait=True)
        self.regions = namelist_entries.config_optnames['plot']['nsidc_region']['allowed_values']
        self.ofiles = None
        style = {'description_width': '100px'}

        self.verif_expname_fct = widgets.Dropdown(
            options=[(''), ('topaz5'),
                     ('35'), ('51')],
            value='topaz5',
            description='model name',
            style=style)

        self.verif_modelname_fct = widgets.Dropdown(
            options=[(''), ('cmcc'), ('ecmwf')],
            value='ecmwf',
            description='model name',
            style=style)

        self.verdata_fct = widgets.Dropdown(
            options=[('osi-cdr'), ('osi-401-b')],
            value='osi-cdr',
            description='observations',
            style=style)

        self.verif_dates_fct = widgets.DatePicker(
            description='date',
            value=datetime.datetime.strptime('20241010', '%Y%m%d'),
            style=style
        )

        self.points_fct = widgets.Text(
            value='',
            placeholder='coordinates in degrees',
            description='location',
            disabled=False,
            style=style,
            continuous_update=False
        )

        self.nsidc_region_fct = widgets.Dropdown(
            options=[r for r in self.regions if
                     len(r) > 4] + [''],
            value='',
            description='nsidc region', style=style)

        self.region_extent_fct = widgets.Text(
            value='',
            description='region extent:',
            disabled=False, style=style
        )

        self.finish_fct = widgets.ToggleButton(
            value=False,
            description='Run ICECAP',
            button_style='',  # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Description',
            icon='check'  # (FontAwesome names without the `fa-` prefix)
        )





        if not os.path.exists(configfile):
            raise ValueError(f'{configfile} does not exist')

        if wipe != 3: print(f'Loading config file {configfile}')
        self.conf = ConfigurationJupyter(configfile)


        # wipe all previous ICECAP files from that suite (except cache) and don't show dropdown
        if wipe == 3:
            dirlist = glob.glob(f'{self.conf.scratchdir}/*_tmp')
            dirlist += glob.glob(f'{self.conf.permdir}/*_tmp')
            dirlist = set(dirlist)
            for d in dirlist:
                shutil.rmtree(d)
            filelist = glob.glob("*tmp.conf")
            for file in filelist:
                os.remove(file)
        else:
            if wipe == 2:
                with jupyter_output:
                    print('Wiping previous ICECAP directories')
                    dirlist = glob.glob(f'{self.conf.scratchdir}/{self.conf.suitename}*_tmp')
                    dirlist += glob.glob(f'{self.conf.permdir}/{self.conf.suitename}*_tmp')
                    dirlist = set(dirlist)
                    for d in dirlist:
                        shutil.rmtree(d)
            if wipe >= 1:
                with jupyter_output:
                    print('Wiping previous configfiles')
                    filelist = glob.glob(f"{self.conf.suitename}_*tmp.conf")
                    for file in filelist:
                        os.remove(file)

            allowed_plottypes = ['ensmean', 'ice_distance','ice_extent', 'plume', 'break_up']
            if 'ensmean' == self.conf.plotsets['001'].plottype:
                needed_opts = ['verif_expname_fct', 'verif_dates_fct']
            elif 'ice_distance' == self.conf.plotsets['001'].plottype:
                needed_opts = ['verif_expname_fct', 'verif_dates_fct', 'points_fct']
            elif 'ice_extent' == self.conf.plotsets['001'].plottype:
                needed_opts = ['verif_expname_fct', 'verif_dates_fct','region_extent_fct','nsidc_region_fct']
            elif 'plume' == self.conf.plotsets['001'].plottype:
                needed_opts = ['verif_expname_fct', 'verif_dates_fct','region_extent_fct','nsidc_region_fct']
            elif 'break_up' == self.conf.plotsets['001'].plottype:
                needed_opts = ['verif_expname_fct', 'verif_dates_fct']
            else:
                raise NotImplementedError(f'ERROR: Plottype must be one of {allowed_plottypes}')

            # check if nsidc nc files are in sourcedir/etc...otherwise don't show nsidc box
            if 'nsidc_region_fct' in needed_opts:
                if not os.path.exists(f'{self.conf.sourcedir}/etc/nsidc_{self.conf.verdata}.nc'):
                    utils.print_info('No NSIDC region files found')
                    needed_opts = [n for n in needed_opts if n != 'nsidc_region_fct']


            for w in needed_opts:
                if hasattr(self.conf.plotsets['001'], w.replace('_fct','')):
                    val = getattr(self.conf.plotsets['001'], w.replace('_fct',''))
                elif hasattr(self.conf, w.replace('_fct','')):
                    val = getattr(self.conf, w.replace('_fct', ''))

                if val is None:
                    val = ''

                if 'dates' in w:
                    if 'yesterday' in val:
                        today = datetime.datetime.today()
                        yesterday = today - datetime.timedelta(days=1)
                        val = yesterday.strftime("%Y%m%d")
                    val = utils.string_to_datetime(val)
                setattr(getattr(self, w), 'value',val)

            if self.conf.plotsets['001'].verif_modelname is not None:
                needed_opts.remove('verif_expname_fct')
                needed_opts = ['verif_modelname_fct'] + needed_opts

            self.finish_fct.observe(self.button_pressed, 'value')
            self.nsidc_region_fct.observe(self.update_region_extent_fct, 'value')
            self.region_extent_fct.observe(self.update_nsidc_fct, 'value')


            self.verif_dates_fct.observe(self.update_dates_fct, 'value')
            self.verif_modelname_fct.observe(self.update_expname_cds_fct, 'value')
            self.update_expname_fct()
            self.needed_opts = needed_opts
            self.children_start = [getattr(self, n) for n in needed_opts] + [self.finish_fct] + [jupyter_output]
            self.box = VBox(children=self.children_start)
            display(self.box)

    def plot(self, maxcols=3, figsize=(16, 8)):
        """
        Plot png files in jupyter notebook
        :param maxcols: number of maximum columns
        :param figsize: figure size
        :return:
        """
        if self.ofiles is None:
            utils.print_info('No output created yet. Did you run ICECAP?')
            with jupyter_output:
                utils.print_info('No output created yet. Please run ICECAP first')
                return
        ncols = len(self.ofiles)
        nrows = 1
        if ncols > maxcols:
            ncols = maxcols
            nrows = int(np.ceil(len(self.ofiles) / maxcols))

        fig, axs = plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize, squeeze=False)
        axs = axs.flatten()
        for ii, img in enumerate(self.ofiles):
            axs[ii].imshow(mpimg.imread(img))
            axs[ii].set_axis_off()

        _ = [ax.set_visible(False) for ax in axs[(ii + 1):]]

    def button_pressed(self, *args):
        """ Execute ICECAP if button pressed
        1. Update config based on widget selection
        2. build complete config (fc block included)
        3. write complete config to new file
        4. read complete config into new config element using normal conf.py routine
        5. run ICECAP"""
        self.update_config()

        now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        newsuitename = self.conf.suitename.split('_date')[0]
        newsuitename = f'{newsuitename}_date-{now}_tmp'
        ofile = f'{newsuitename}.conf'
        self.conf.build_complete_config(newsuitename)
        self.conf.write_complete_config(ofile=ofile)
        self.updated_conf = config.Configuration(ofile)


        self.ofiles = self.exec_verbose("Running ICECAP ....",
                                         icecap_api, [self.updated_conf, Args()],
                                        jupyter_output, False)


        with jupyter_output:
            utils.print_info('Output files can be found here:')
            for file in self.ofiles:
                print(file)
            utils.print_info('Finished')


    def update_nsidc_fct(self, *args):
        """ Set NSIDC region to empty if region_extent is changed """
        if self.region_extent_fct.value != '':
            self.nsidc_region_fct.value =''

    def update_region_extent_fct(self, *args):
        """ Set region_extent to empty if NSIDC region is changed """
        if self.nsidc_region_fct.value != '':
            self.region_extent_fct.value =''

    def update_config(self):
        """ Update configuration based on widget selection """
        for w in self.needed_opts:
            val_widget = getattr(getattr(self, f'{w}'), 'value')
            if 'dates' in w:
                val_widget = utils.datetime_to_string(val_widget)
            if val_widget == '':
                val_widget = None

            if hasattr(self.conf.plotsets['001'], w.replace('_fct','')):
                setattr(self.conf.plotsets['001'],w.replace('_fct',''), val_widget)
            else:
                setattr(self.conf, w.replace('_fct', ''), val_widget)


    def update_expname_fct(self):
        """ Update expname options based on fcsystem.
        Also change date to 1st of month in case of seasonal forecasts """

        if self.conf.plotsets['001'].verif_fcsystem == 'medium-range':
            self.verif_expname_fct.options = ['topaz5']
        elif self.conf.plotsets['001'].verif_fcsystem == 'long-range':
            self.verif_expname_fct.options = ['51','35']
            self.verif_modelname_fct.options = ['ecmwf', 'cmcc']
            val = utils.datetime_to_string(self.verif_dates_fct.value)
            if val[-2:] != '01':
                with jupyter_output:
                    print('Setting start date to 1st of month for seasonal forecasts')
                val = f'{val[:-2]}01'
                self.verif_dates_fct.value = utils.string_to_datetime(val)

    def update_dates_fct(self, *args):
        """ Set day to first of month when seasonal forecasts are selected """
        if self.conf.plotsets['001'].verif_fcsystem == 'long-range':
            val = utils.datetime_to_string(self.verif_dates_fct.value)
            if val[-2:] != '01':
                with jupyter_output:
                    print('Setting start date to 1st of month for seasonal forecasts')
                val = f'{val[:-2]}01'
                self.verif_dates_fct.value = utils.string_to_datetime(val)
        if self.conf.plotsets['001'].calib_exists == 'yes':
            self.conf.plotsets['001'].calib_dates = val[4:]

    def update_expname_cds_fct(self, *args):
        """ Update expname and modelname for long-range fcsystem """
        if self.conf.plotsets['001'].verif_fcsystem == 'long-range':
            if self.verif_modelname_fct.value == 'ecmwf':
                self.verif_expname_fct.value = '51'
            elif self.verif_modelname_fct.value == 'cmcc':
                self.verif_expname_fct.value = '35'

    @staticmethod
    def exec_verbose(string, fct, args, output, debug=False):
        """
        Execute function fct either verbose or not
        :param string: string to print
        :param fct: function to execute
        :param args: arguments passed to fct
        :param output: display output variable
        :param debug: if True then print output from fct to display
        :return: function return value
        """
        if debug:
            with output:
                utils.print_info(string)
                return fct(*args)
        else:
            with output:
                utils.print_info(string)
            return fct(*args)



class ForecastConfigObjectJupyter:
    """A forecast config object corresponds to a single numerical experiment (used in config.py)."""

    def __init__(self, **kwargs):
        self.fcsystem = kwargs['fcsystem']
        self.expname = kwargs['expname']
        self.enssize = int(kwargs['enssize'])
        self.mode = kwargs['mode']  # hindcast mode (affects start dates)
        self.dates = kwargs['dates']
        self.ndays = kwargs['ndays']
        self.source = kwargs['source']
        self.modelname = kwargs['modelname']


class ConfigurationJupyter(config.Configuration):
    """ Jupyter notebook configuration class
    In contrast to config.Configuration it only reads environment, staging and plot_ from config file
    It uses _init_config from config.Configuration to read those sections
    fcset_001 is created later (after changes to dropdown menu are made)
    """
    def __init__(self, filename=None):
        conf_parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        conf_parser.read(filename)
        self.filename = filename
        self._init_config(conf_parser, 'environment')

        # change BASEDIR to path above
        for value in ['sourcedir','scratchdir','permdir','cachedir','calibrationdir']:
            if getattr(self, value) is not None:
                setattr(self, value,getattr(self, value).replace('BASEDIR', os.path.dirname(os.getcwd())))

        self._init_config(conf_parser, 'staging')

        plotsetlist = [section[5:] for section in conf_parser.sections()
                       if section.startswith('plot_')]
        if len(plotsetlist) != 1:
            raise ValueError('Only one plot can be used here')

        self.plotsets = {}
        for plotid in plotsetlist:
            section = 'plot_' + plotid
            self._init_config(conf_parser, section, 'plot', init=True)

        self.plotsets['001'] = dataobjects.PlotConfigObject(
            verif_ref=self.verif_ref,
            verif_expname=self.verif_expname,
            plottype=self.plottype,
            verif_mode=self.verif_mode,
            verif_fromyear=self.verif_fromyear,
            verif_toyear=self.verif_toyear,
            target=self.target,
            verif_enssize=self.verif_enssize,
            verif_fcsystem=self.verif_fcsystem,
            verif_refdate=self.verif_refdate,
            projection=self.projection,
            proj_options=self.proj_options,
            circle_border=self.circle_border,
            region_extent=self.region_extent,
            nsidc_region=self.nsidc_region,
            cmap=self.cmap,
            source=self.source,
            verif_dates=self.verif_dates,
            calib_mode=self.calib_mode,
            calib_dates=self.calib_dates,
            calib_enssize=self.calib_enssize,
            calib_refdate=self.calib_refdate,
            calib_fromyear=self.calib_fromyear,
            calib_toyear=self.calib_toyear,
            ofile=self.ofile,
            add_verdata=self.add_verdata,
            points=self.points,
            verif_modelname=self.verif_modelname,
            area_statistic=self.area_statistic,
            temporal_average=self.temporal_average,
            plot_shading=self.plot_shading,
            inset_position=self.inset_position,
            additional_mask=self.additional_mask,
            calib_method=self.calib_method,
            calib_exists=self.calib_exists,
            copy_id=self.copy_id
        )

    def build_complete_config(self, newsuitename):
        """ Create complete config by adding fcset dictionary to conf
        :param newsuitename: change suitename to newsuitename
        """

        self.suitename = newsuitename
        plotset = self.plotsets['001']

        if plotset.verif_fcsystem == 'medium-range':
            ndays = 10
        elif plotset.verif_fcsystem == 'long-range':
            ndays = 180
        else:
            raise ValueError('extended-range forecasts not implemented yet in this version of the notebook')

        self.fcsets = {}
        self.fcsets['001'] = ForecastConfigObjectJupyter(
            fcsystem=plotset.verif_fcsystem,
            expname=plotset.verif_expname,
            enssize=plotset.verif_enssize,
            dates=plotset.verif_dates,
            mode=plotset.verif_mode,
            ndays=int(ndays),
            source=plotset.verif_source,
            modelname=plotset.verif_modelname,
        )

    def write_complete_config(self,ofile):
        """ Write config file to ofile
        :param ofile: output file name
        """

        # save to a file
        with open(ofile, 'w') as configfile:
            section = 'environment'
            configfile.write(f'[{section}]\n')
            for name in config.config_optnames[section]:
                if hasattr(self, name):
                    val = getattr(self, name)
                    if val is not None:
                        if 'default_value' in config.config_optnames[section][name]:
                            default_val = config.config_optnames[section][name]['default_value'][0]
                            if val != default_val:
                                configfile.write(f'{name} = {val}')
                                configfile.write("\n")
                        else:
                            configfile.write(f'{name} = {val}')
                            configfile.write("\n")

            configfile.write("\n")
            section = 'staging'
            configfile.write(f'[{section}]\n')
            for name in config.config_optnames[section]:
                if hasattr(self, name):
                    val = getattr(self, name)
                    if val is not None:
                        if 'default_value' in config.config_optnames[section][name]:
                            default_val = config.config_optnames[section][name]['default_value'][0]
                            if val != default_val:
                                configfile.write(f'{name} = {val}')
                                configfile.write("\n")
                        else:
                            configfile.write(f'{name} = {val}')
                            configfile.write("\n")

            configfile.write("\n")
            section = 'fc_001'
            configfile.write(f'[{section}]\n')
            for name in config.config_optnames['fc']:
                if hasattr(self.fcsets['001'], name):
                    val = getattr(self.fcsets['001'], name)
                    if val is not None:
                        configfile.write(f'{name} = {val}')
                        configfile.write("\n")

            configfile.write("\n")
            section = 'plot_001'
            configfile.write(f'[{section}]\n')
            for name in config.config_optnames['plot']:
                if hasattr(self.plotsets['001'], name):
                    val = getattr(self.plotsets['001'], name)
                    if val is not None:
                        if 'default_value' in config.config_optnames['plot'][name]:
                            default_val = config.config_optnames['plot'][name]['default_value'][0]
                            if val != default_val:
                                configfile.write(f'{name} = {val}')
                                configfile.write("\n")
                        else:
                            configfile.write(f'{name} = {val}')
                            configfile.write("\n")
