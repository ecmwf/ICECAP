"""Module containing functions to add arguments to existing parser"""

def add_staging_expid(parser):
    """Add to parser a positional argument to specify identifier of experiment to stage."""
    helpstr = 'Experiment ID of forecast to stage (or to determine verification dates)'
    parser.add_argument('expid', help=helpstr)

def add_staging_startdate(parser, allow_multiple=False):
    """Add to parser a positional argument to specify for which forecast start date to stage."""
    if allow_multiple:
        helpstr = 'start date of forecast in the format YYYYMMDD. Can be comma-separated list.'
    else:
        helpstr = 'start date of forecast (YYYYMMDD)'
    parser.add_argument('startdate', help=helpstr)

def add_staging_exptype(parser):
    """Add to parser a positional argument to specify type of experiment to stage."""
    helpstr = 'experiment type (pf, cf, fc)'
    parser.add_argument('exptype', choices=['pf', 'cf','fc','INIT','WIPE'], help=helpstr)

def add_staging_mode(parser):
    """Add to parser a positional argument to specify type of experiment to stage."""
    helpstr = 'experiment mode (hindcast, forecast)'
    parser.add_argument('mode', choices=['fc', 'hc'], help=helpstr)

def add_plotid(parser):
    """Add to parser a positional argument to specify plotid from config."""
    helpstr = 'plotid [name followed by plot_* in config]'
    parser.add_argument('plotid', help=helpstr)

def add_plot_config_option(parser):
    """Add to parser an option to specify config file."""
    parser.add_argument('-p', '--plotconfigfile',
                        default=False,
                        help='plot configuration file to use')

def add_config_option(parser):
    """Add to parser an option to specify config file."""
    parser.add_argument('-c', '--configfile',
                        default=['icecap.conf'],
                        help='configuration file to use')

def add_verbose_option(parser):
    """Add to parser an option for more debugging output"""
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='verbose for more debugging output')

def add_force_option(parser):
    """Add to parser an option to force rebuild"""
    parser.add_argument('-f', '--force', action='store_true', default=False,
                        help='force recreation of code and suite. '
                             + 'WARNING: Using force implies loss of old code '
                               'and suite definition.')

def add_wipe_option(parser):
    """Add to parser an option to wipe suite/environment"""
    parser.add_argument('-w', '--wipe', action='count', default=0,
                        help='delete data and runtime scripts, '
                             'and remove ecflow suite from server - '
                             'use -w for wiping only this suite; '
                             'use -ww to delete whole icecap from machine'
                        )
