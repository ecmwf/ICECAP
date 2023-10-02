""" General information about forecast
needed at different stages of ICECAP

One example is get_cycle, which depends on the model but is needed for staging
and plotting (as data is stored in sub-folders based on cycle name)
"""

import datetime as dt
import utils


def get_cycle(**kwargs):
    """
    Get information on model version
    :param kwargs: dictionary with keys needed here
    :return: cycle inforamtion (str)
    """

    thisdate = kwargs['thisdate']
    cycle = None

    # ECMWF internal block
    if kwargs['source'] == 'ecmwf':
        loper = (kwargs['fcsystem'] in ['extended-range', 'medium-range'] and kwargs['expname'] == '0001')
        ls2secmwf = (kwargs['fcsystem'] == 's2s' and kwargs['modelname'] == 'ecmf')

        #if operational or s2s/ecmwf model
        if loper or ls2secmwf:

            cycle_dates = [
                ('pre41r1', dt.datetime(1975, 1, 1, 0)),
                ('41r1', dt.datetime(2015, 5, 12, 0)),
                ('41r2', dt.datetime(2016, 3, 8, 0)),
                ('43r1', dt.datetime(2016, 11, 22, 0)),
                ('43r3', dt.datetime(2017, 7, 11, 0)),
                ('45r1', dt.datetime(2018, 6, 5, 0)),
                ('46r1', dt.datetime(2019, 6, 11, 0)),
                ('47r1', dt.datetime(2020, 6, 30, 0)),
                ('47r2', dt.datetime(2021, 5, 11, 0)),
                ('47r3', dt.datetime(2021, 10, 12, 0)),
                ('48r1', dt.datetime(2023, 6, 27, 0)),
            ]
            cycles = [cd[0] for cd in cycle_dates]
            dates = [cd[1] for cd in cycle_dates]
            for i in range(len(dates) - 1):
                if dates[i] <= utils.string_to_datetime(thisdate) < dates[i + 1]:
                    cycle = cycles[i]
            if utils.string_to_datetime(thisdate) >= dates[-1]:
                cycle = cycles[-1]

            return cycle

        ### S2S BLOCK
        ### ECMF defined as OPER above
        if kwargs['fcsystem'] in ['s2s']:
            if kwargs['modelname'] in ['amm', 'anso', 'kwbc']:
                cycle = 'latest'
            elif kwargs['modelname'] == 'babj':  # CMA
                # forecast start 2015 but hcrefdate is 2014-05-01 for v1
                cycle_dates = [
                    ('v1', dt.datetime(2014, 1, 1, 0)),
                    ('v2', dt.datetime(2019, 11, 11, 0)),
                ]
            elif kwargs['modelname'] == 'isac':  # CNR-ISAC
                # forecast start Nov 2015 but hcrefdate is 2015-03-26 for v1
                cycle_dates = [
                    ('v1', dt.datetime(2015, 3, 26, 0)),
                    ('v2', dt.datetime(2017, 6, 8, 0)),
                ]
            elif kwargs['modelname'] == 'lfpw':  # CNRM
                if kwargs['mode'] == 'hc':
                    cycle_dates = [
                        ('v1', dt.datetime(2014, 12, 1, 0)),
                        ('v2', dt.datetime(2019, 7, 1, 0)),
                    ]
                else:
                    cycle_dates = [
                        ('v1', dt.datetime(2016, 3, 1, 0)),
                        ('v2', dt.datetime(2020, 10, 22, 0)),
                    ]
            elif kwargs['modelname'] == 'cwao':  # ECCC
                cycle_dates = [
                    ('v1', dt.datetime(2016, 1, 7, 0)),
                    ('v2', dt.datetime(2018, 9, 20, 0)),
                    ('v3', dt.datetime(2019, 7, 4, 0)),
                    ('v4', dt.datetime(2021, 12, 2, 0)),
                ]
            elif kwargs['modelname'] == 'rums':  # HMRC
                cycle_dates = [
                    ('v1', dt.datetime(2015, 1, 7, 0)),
                    ('v2', dt.datetime(2017, 6, 8, 0)),
                    ('v3', dt.datetime(2021, 1, 7, 0)),
                    ('v4', dt.datetime(2022, 9, 15, 0)),
                ]
            elif kwargs['modelname'] == 'rjtd':  # JMA
                if kwargs['mode'] == 'hc':
                    cycle_dates = [
                        ('v1', dt.datetime(2014, 3, 4, 0)),
                        ('v2', dt.datetime(2017, 1, 31, 0)),
                        ('v3', dt.datetime(2020, 3, 31, 0)),
                        ('v4', dt.datetime(2021, 3, 31, 0)),
                        ('v5', dt.datetime(2022, 3, 31, 0)),
                        ('v6', dt.datetime(2022, 9, 30, 0)),
                    ]
                else:
                    cycle_dates = [
                        ('v1', dt.datetime(2015, 1, 6, 0)),
                        ('v2', dt.datetime(2017, 3, 22, 0)),
                        ('v3', dt.datetime(2020, 3, 24, 0)),
                        ('v4', dt.datetime(2021, 3, 30, 0)),
                        ('v5', dt.datetime(2022, 3, 15, 0)),
                        ('v6', dt.datetime(2023, 2, 19, 0)),
                    ]
            elif kwargs['modelname'] == 'rksl':  # KMA
                cycle_dates = [
                    ('v1', dt.datetime(2016, 11, 1, 0)),
                    ('v2', dt.datetime(2020, 9, 1, 0)),
                    ('v3', dt.datetime(2022, 2, 22, 0)),
                    ('v4', dt.datetime(2023, 6, 1, 0)),
                ]
            elif kwargs['modelname'] == 'egrr':  # UKMO
                cycle_dates = [
                    ('v1', dt.datetime(2015, 12, 1, 0)),
                    ('v2', dt.datetime(2016, 1, 1, 0)),
                    ('v3', dt.datetime(2016, 4, 17, 0)),
                    ('v4', dt.datetime(2017, 3, 25, 0)),
                    ('v5', dt.datetime(2018, 9, 1, 0)),
                    ('v6', dt.datetime(2019, 4, 3, 0)),
                    ('v7', dt.datetime(2021, 2, 2, 0)),
                ]

            cycles = [cd[0] for cd in cycle_dates]
            dates = [cd[1] for cd in cycle_dates]
            for i in range(len(dates) - 1):
                if dates[i] <= utils.string_to_datetime(thisdate) < dates[i + 1]:
                    cycle = cycles[i]
            if utils.string_to_datetime(thisdate) >= dates[-1]:
                cycle = cycles[-1]

            return cycle
        ### END S2S BLOCK

    # set to 'latest' if not defined
    if cycle is None:
        cycle = 'latest'

    return cycle
