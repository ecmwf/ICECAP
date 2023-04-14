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
    helpstr = 'experiment type (ensemble, analysis)'
    parser.add_argument('exptype', choices=['pf', 'cf'], help=helpstr)

def add_staging_mode(parser):
    """Add to parser a positional argument to specify type of experiment to stage."""
    helpstr = 'experiment mode (hindcast, forecast)'
    parser.add_argument('mode', choices=['fc', 'hc'], help=helpstr)

def add_config_option(parser):
    """Add to parser an option to specify config file."""
    parser.add_argument('-c', '--configfile',
                        default='icecap.conf',
                        help='configuration file to use')
