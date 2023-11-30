"""Script to be executed to clean all temporary files from suite"""

import argparse
import shutil
import os
import config
import clargs
import utils

os.environ['HDF5_USE_FILE_LOCKING']='FALSE'


if __name__ == '__main__':
    description = 'Stage forecast from Met Norway Thredds server (experimental)'
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    clargs.add_config_option(parser)
    args = parser.parse_args()
    conf = config.Configuration(file=args.configfile)

    shutil.rmtree(conf.tmpdir)


    utils.print_banner('ALL DONE')
