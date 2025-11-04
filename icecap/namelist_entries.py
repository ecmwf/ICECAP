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
            'optional' : True,
            'allowed_values' : ['ecmwf','jupyter']
        },
        'ecflow': {
            'printname' : 'use ecflow',
            'optional' : True,
            'default_value' : ["yes"],
            'allowed_values' : ["yes",'no']
        },
        'suitename': {
            'printname' : 'name of suite',
            'optional' : False
        },
        'sourcedir': {
            'printname': 'Directory of source code',
            'optional' : False
        },
        'scratchdir': {
            'printname': 'Base directory for data/metrics/plots',
            'optional' : False
        },
        'permdir': {
            'printname': 'Base directory for runtime scripts',
            'optional' : False
        },
        'cachedir':{
            'printname': 'cache directory',
            'optional' : False
        },
        'python_exe':{
            'printname': 'python binary',
            'optional' : True
        },
        'job_memory':{
            'printname': 'maximum memory per job',
            'optional' : True,
            'allowed_values' : ["", "16GB","128GB"],
            'default_value' : [""],
        },
        'calibrationdir':{
            'printname': 'directory of preexisting calibration files',
            'optional' : True,
        },
    }, # end environment
    'ecflow': {
        'ecfhomeroot': {
            'printname': 'Root directory for ecFlow-generated files (ECF_HOME)',
            'optional' : ['ecflow:yes'],
        },
        'ecflow_host': {
            'printname': 'ecflow hostname',
            'optional' : ['ecflow:yes']
        },
        'ecflow_port': {
            'printname': 'ecflow host port',
            'optional' : ['ecflow:yes']
        },
        'maximum_processes_plot': {
            'printname': 'maximum number of parallel plot processes',
            'optional' : True,
            'default_value' : ["8"],

        },
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
            'optional' : ['fcsystem:s2s'],
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
            'optional' : True
            #'optional' : ['mode:hc']
        },
        'hctodate':{
            'printname' : 'first hindcast year',
            'optional' : True
            #'optional' : ['mode:hc'],
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
        },
        'fromyear' : {
            'printname' : 'start year of data to retrieve',
            'optional' : True
        },
        'toyear' : {
            'printname' : 'end year of data to retrieve',
            'optional' : True
        },
    }, # end fc
    'plot' : {
        'verif_ref' : {
            'printname':'observation name for plotting',
            'optional' : True,
            'allowed_values': ["osi-cdr", 'osi-401-b']
        },
        'verif_expname' : {
            'printname':'experiment name for plotting',
            'optional' : True,
        },
        'plottype' : {
            'printname':'plot type',
            'optional' : False,
            'allowed_values' : ["interp_check","ensmean","forecast_error",
                                "ice_distance", "plume", "freeze_up", "break_up", 'brier',
                                'crps', 'rmse', 'ser','iiee','sps','mae',
                                'brier_edge','linear_trend',
                                'rmse_edge',
                                'ice_extent', 'cycle', 'mae','calc_calib']
        },
        'verif_mode':{
            'printname': 'forcast or hindcast mode for plotting',
            'optional' : True,
        },
        'verif_fromyear':{
            'printname' : 'first year',
            'optional' : True
        },
        'verif_toyear':{
            'printname' : 'last year',
            'optional' : True
        },
        'target':{
            'printname' : 'target time for plotting',
            'optional' : True,
        },
        'verif_enssize':{
            'printname' : 'ensemble size used for metrics',
            'optional' : True
        },
        'verif_fcsystem':{
            'printname' : 'forecast system specification',
            'optional' : True,
            'allowed_values' : ["medium-range", "extended-range","long-range", 's2s']
        },
        'verif_dates' : {
            'printname' : 'experiment forecast dates only for mode=fc',
            'optional':['verif_mode:fc']
        },
        'verif_refdate':{
            'printname' : 'experiment reference date',
            'optional': True
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
        'region_extent':{
            'printname' : 'boundaries of the map/area averaging',
            'optional' : True
        },
        'nsidc_region':{
            'printname' : 'NSIDC region identifier',
            'optional' : True,
            'allowed_values' : ['None', 'CARC','BEAS','CHUS','ESS','LS',
                                'KS','BARS','EGS','BBLS','GOSL','HB','CAA',
                                'BERS','SOO','SOJ','BYS','BALS','GOA',
                                'carc', 'beas', 'chus', 'ess', 'ls', 'ks', 'bars', 'egs', 'bbls',
                                'gosl', 'hb', 'caa', 'bers', 'soo', 'soj', 'bys', 'bals', 'goa',
                                'central_arctic', 'beaufort_sea', 'chukchi_sea',
                                'east_siberian_sea', 'laptev_sea', 'kara_sea', 'barents_sea',
                                'east_greenland_sea', 'baffin_bay_and_labrador_seas',
                                'gulf_of_st_lawrence', 'hudson_bay', 'canadian_archipelago',
                                'bering_sea', 'sea_of_okhotsk', 'sea_of_japan',
                                'bohai_and_yellow_seas', 'baltic_sea', 'gulf_of_alaska'
                                ]
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
            'optional': True
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
            'printname' : 'add observations to plot',
            'optional' : True
        },
        'points' : {
            'printname' : 'points to be used for ice distance calculation',
            'optional' : ['plottype:ice_distance']
        },
        'verif_modelname' : {
            'printname':'model name (for S2S)',
            'optional' : ['verif_fcsystem:s2s'],
        },
        'area_statistic' : {
            'printname':'area statistics',
            'optional' : True,
        },
        'temporal_average' : {
            'printname':'temporal averaging',
            'optional' : True,
        },
        'plot_shading': {
            'printname':'plot ensemble shaded',
            'optional' : True
        },
        'inset_position': {
            'printname':'inset position of map plot',
            'optional' : True
        },
        'additional_mask': {
            'printname':'use additional land-sea-mask',
            'optional' : True
        },
        'calib_method' : {
            'printname':'Method used for calibration',
            'optional' : True,
            'allowed_values' : ["mean", "mean+trend", "anom","score",
                                'persistence', 'None']
        },
        'calib_exists': {
            'printname':'Specify whether calibration file has been precomputed',
            'optional' : True,
            'allowed_values' : ["yes", "no"],
        },
        'copy_id' : {
            'printname':'Copy config from different plotset',
            'optional' : True
        },
    }
}
