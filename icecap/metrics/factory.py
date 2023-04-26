""" Factory importing the relevant metric"""
import importlib

def create(name, conf):
    """ return an instance of appropriate Metric Subclass
    :param name: name of metric
    :param conf: configuration object
    :return: metric object
    """

    metric_name = conf.plotsets[name].plottype
    metric_module = importlib.import_module('metrics.' + metric_name)
    return metric_module.Metric(name, conf)
