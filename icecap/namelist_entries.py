"""
This module consists of a dictionary with all allowed namelist entries,
which can be defined in icecap.conf
Thus introducing a new parameter demands for an entry here
"""

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
        'source' : {
            'printname' : "source of the forecasts",
            'optional' : True,
        },
        'fcsystem' : {
            'printname':'forecasting system name',
            'optional' : False,
            'allowed_values' : ["medium-range", "extended-range",
                                "long-range", "s2s"]
        },
        'modelname' : {
            'printname':'model name (for S2S)',
            'optional' : ['fcsystem:s2s', 'fcsystem:long-range'],
        },
        'expname' : {
            'printname':'experiment name',
            'optional' : False,
        },

        'enssize':{
            'printname' : 'ensemble size',
            'optional' : True,
        },
        'mode':{
            'printname': 'forcast or hindcast mode',
            'optional' : False,
            'allowed_values' : ["hc", "fc"]
        },
        'dates':{
            'printname' : 'forecast dates',
            'optional' : ['mode:fc'],
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
            'allowed_values' : ["interp_check","ensmean","bias","bias_corrected_map",
                                "ice_distance", "area_mean_ts"]
        },
        'verif_mode':{
            'printname': 'forcast or hindcast mode for plotting',
            'optional' : False,
        },
        'verif_fromyear':{
            'printname' : 'first year',
            'optional' : ['mode:hc']
        },
        'verif_toyear':{
            'printname' : 'last year',
            'optional' : ['mode:hc']
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
            'allowed_values' : ["medium-range", "extended-range","long-range", 's2s']
        },
        'verif_dates' : {
            'printname' : 'experiment forecast dates only for mode=fc',
            'optional':['verif_mode:fc']
        },
        'verif_refdate':{
            'printname' : 'experiment reference date',
            'optional': ['verif_mode:hc']
        },
        'projection' :{
            'printname' : 'map projection',
            'optional' : True,
        },
        'proj_options' :{
            'printname': 'projection options',
            'optional': True
        },
        'circle_border' : {
            'printname':'plot circular plot',
            'optional' : True,
            'default_value' : ["yes"],
            'allowed_values' : ["yes", "no"]
        },
        'plot_extent':{
            'printname' : 'boundaries of the map',
            'optional' : True
        },
        'cmap':{
            'printname' : 'colormap to be used',
            'optional' :True
        },
        'source': {
            'printname' : 'source of forecast system',
            'optional' : True
        },
        'calib_mode' : {
            'printname' : 'mode (hc/fc) of calibration system',
            'optional' : True
        },
        'calib_dates' : {
            'printname' : 'dates used for calibration',
            'optional' : True
        },
        'calib_refdate' : {
            'printname' : 'reference date used for calibration',
            'optional': ['calib_mode:hc']
        },
        'calib_fromyear' : {
            'printname' : 'start year used for calibration',
            'optional' : True
        },
        'calib_toyear' : {
            'printname' : 'start year used for calibration',
            'optional' : True
        },
        'calib_enssize' : {
            'printname' : 'ensemble size used for calibration',
            'optional' : True
        },
        'ofile' : {
            'printname' : 'output file name',
            'optional' : True
        },
        'add_verdata' : {
            'printname' : 'add observations to plot (only ice distance currently)',
            'optional' : True,
            'default_value' : ["no"],
            'allowed_values' : ["yes", "no"]
        },
        'points' : {
            'printname' : 'points to be used for ice distance calculation',
            'optional' : ['plottype:ice_distance']
        },
        'modelname' : {
            'printname':'model name (for S2S)',
            'optional' : ['verif_fcsystem:s2s', 'verif_fcsystem:long-range'],
        },
        'area_mean' : {
            'printname':'area average',
            'optional' : True,
            'allowed_values' : ["data", "score"]
        }
    }
}