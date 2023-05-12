""" Script for metric calculation and plotting """
import argparse

import clargs
import config
import metrics
import utils
import map_plot

if __name__ == '__main__':
    des = 'Plot a metric from staged data files'
    parser = argparse.ArgumentParser(description=des,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    clargs.add_config_option(parser)
    clargs.add_verbose_option(parser)
    clargs.add_plotid(parser)

    args = parser.parse_args()
    conf = config.Configuration(file=args.configfile)
    utils.print_banner(conf.plotsets[args.plotid].plottype)

    m = metrics.factory.create(args.plotid, conf)
    m.compute()
    m.save()
    p = map_plot.MapPlot(conf, args.plotid,m)
    p.plot(m, args.verbose)
