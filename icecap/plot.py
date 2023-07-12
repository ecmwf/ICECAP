""" Script for metric calculation and plotting """
import argparse
import tracemalloc

import clargs
import config
import metrics
import utils
import map_plot


if __name__ == '__main__':
    tracemalloc.start()
    des = 'Plot a metric from staged data files'
    parser = argparse.ArgumentParser(description=des,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    clargs.add_config_option(parser)
    clargs.add_verbose_option(parser)
    clargs.add_plot_config_option(parser)
    clargs.add_plotid(parser)

    args = parser.parse_args()
    if args.plotconfigfile:
        args.configfile.append(args.plotconfigfile)

    conf = config.Configuration(file=args.configfile)
    utils.print_banner(conf.plotsets[args.plotid].plottype)

    m = metrics.factory.create(args.plotid, conf)

    m.compute()
    m.save()
    if m.gettype() == 'map':
        p = map_plot.MapPlot(conf, args.plotid,m)
    elif m.gettype() == 'ts':
        print('ts')
        p = map_plot.TsPlot(m)



    print('plotting')
    p.plot(m, args.verbose)
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current memory usage is {current / 10 ** 6}MB; Peak was {peak / 10 ** 6}MB")
    tracemalloc.stop()
