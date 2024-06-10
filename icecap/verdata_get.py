"""Script to be executed to retrieve and process verification data"""

import os
import argparse
import config
import clargs
import verdata
import utils

os.environ['HDF5_USE_FILE_LOCKING']='FALSE'

def verdata_api(conf, verbose=False):
    """
    API running all steps to retrieve verifying data
    (can e.g also called from jupyter notebook)
    :param conf: configuration object
    :param verbose: True or False
    :return: N/A
    """
    data = verdata.VerifData(conf)
    if not data.check_cache(check_level=1, verbose=verbose):
        data.process(verbose=verbose)

    utils.print_banner('ALL DONE')

if __name__ == '__main__':
    description = 'Stage forecast or analysis from MARS tape archive'
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    clargs.add_config_option(parser)
    clargs.add_verbose_option(parser)
    args = parser.parse_args()
    conf = config.Configuration(file=args.configfile)
    verdata_api(conf, verbose=args.verbose)
