#!/usr/bin/env python3
"""
Setup script to be executed to start ICECAP
"""

import argparse
import config
import setup_icecap
import clargs




parser = argparse.ArgumentParser(description='Set up ICECAP suite '
                                             + '(create directories, copy code to runtime '
                                               'directory, build & play ecflow suite '
                                               'if needed)',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
clargs.add_config_option(parser)
clargs.add_verbose_option(parser)
clargs.add_force_option(parser)
clargs.add_wipe_option(parser)

def icecap_api(conf, args):
    """
    API running ICECAP
    :param conf: configuration object
    :param args: command line arguments
    :return: N/A
    """
    execution_host = setup_icecap.ExecutionHost(conf)
    flow = setup_icecap.create_flow(conf)

    if args.wipe > 0:
        execution_host.wipe(args)
        if conf.ecflow == 'yes':
            flow.wipe_ecflow_host(args.wipe)

    else:
        execution_host.setup(args)
        if conf.ecflow == 'yes':
            if args.verbose:
                flow.to_json()
            flow.build_ecflow()
            flow.save_defs(force=args.force)
            flow.load_ecflow(force=args.force)

if __name__ == '__main__':
    args = parser.parse_args()
    conf = config.Configuration(file=args.configfile)
    icecap_api(conf, args)
