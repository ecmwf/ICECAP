""" Module containing some common functions"""

import os
import datetime as dt
import numpy as np
from dateutil.relativedelta import relativedelta

def set_xarray_attribute(data, da_ref,
                         params=None):
    """
    Set projection attributes for dataArrays in data list to the ones from da_ref.
    Needed as attributes are sometimes removed when applying xr funtions
    :param data: list of xr dataArrays
    :param da_ref: reference dataArray with parameters to copy
    :param params: attributes to copy
    :return: list of xr DataArrays with attributes from da_ref
    """

    if params is None:
        params = ['projection', 'central_longitude', 'central_latitude',
                  'true_scale_latitude']
    for proj_param in params:
        if proj_param in da_ref.attrs:
            data_out = []
            for _data in data:
                _data.attrs[proj_param] = getattr(da_ref, proj_param)
                data_out.append(_data)
    return data_out

def confdates_to_list(_dates):
    """ Convert dates for plotting in config to list
    :param _dates: dates from config
    :return: dates as list
    """
    if not _dates:
        return None

    if '/to/' not in _dates:
        return csv_to_list(_dates)

    if "/by/" in _dates:
        by_tmp = _dates.split('/by/')[1]
        by_unit = by_tmp[-1]
        by_value = by_tmp[:-1]
        _dates = _dates.split('/by/')[0]
    else:
        raise ValueError('by needs to be specified')


    _dates_split = _dates.split('/to/')

    _dates_split_len = list({len(d) for d in _dates.split('/to/')})
    if len(_dates_split_len) != 1:
        raise ValueError(f'LENGTH ERROR {_dates_split_len} Date config entry is not in right format '
                         f'(either MM/DD or YYYY/MM/DD')


    if _dates_split_len[0] == 4:
        _dates_split = ['2000' + _date for _date in _dates.split('/to/')]
        _dates_split = [dt.datetime.strptime(_datestring, '%Y%m%d') for _datestring in _dates_split]

        date_list = []
        start_date = _dates_split[0]
        while start_date <= _dates_split[1]:
            date_list.append(start_date.strftime("%Y%m%d").replace('2000', ''))
            if by_unit == 'd':
                start_date += dt.timedelta(days=int(by_value))
            elif by_unit == 'm':
                start_date += relativedelta(months=int(by_value))
            elif by_unit == 'y':
                start_date += relativedelta(years=int(by_value))

    elif _dates_split_len[0] == 8:
        date_list = []
        start_date = dt.datetime.strptime(str(_dates_split[0]), '%Y%m%d')
        while start_date <= dt.datetime.strptime(str(_dates_split[1]), '%Y%m%d'):
            date_list.append(start_date.strftime("%Y%m%d"))
            if by_unit == 'd':
                start_date += dt.timedelta(days=int(by_value))
            elif by_unit == 'm':
                start_date += relativedelta(months=int(by_value))
            elif by_unit == 'y':
                start_date += relativedelta(years=int(by_value))
    else:
        raise ValueError('Date config entry is not in right format '
                         '(either MM/DD or YYYY/MM/DD')

    return date_list


def to_datetime(date):
    """ https://gist.github.com/blaylockbk/1677b446bc741ee2db3e943ab7e4cabd?permalink_comment_id=3775327
    Converts a numpy datetime64 object to a python datetime object
    Input:
      date - a np.datetime64 object
    Output:
      DATE - a python datetime object
    """
    timestamp = ((date - np.datetime64('1970-01-01T00:00:00'))
                 / np.timedelta64(1, 's'))
    return dt.datetime.utcfromtimestamp(timestamp)



def convert_to_list(_obj):
    """
    Convert any object to a list
    :param _obj: an object
    :return: object as list
    """
    if isinstance(_obj, list):
        return _obj
    if np.iterable(_obj):
        return _obj

    return [_obj]

def string_to_datetime(_datestring):
    """ return string as datetime object"""
    return dt.datetime.strptime(_datestring, '%Y%m%d')

def datetime_to_string(_dtdate, formatting='%Y%m%d'):
    """return datetime as string object
    :param _dtdate: datetime object
    :param formatting: format of string
    :return: datetime as string
    """

    return _dtdate.strftime(formatting)

def csv_to_list(_args, sep=','):
    """
    Convert a comma separated string into a list object
    :param _args:
    :return: list object of dates
    """
    if _args is None:
        return [None]
    list_whitespace = _args.split(sep)
    list_nospace = [l.strip() for l in list_whitespace]

    return list_nospace

def make_days_datelist(_dates, _ndays):
    """
    Create list of all dates given start date and number of days
    :param _dates: startdate
    :param _ndays: number of days
    :return: list with all dates
    """
    alldates = []
    for _date in _dates:
        alldates += [_date + dt.timedelta(days=x) for x in range(_ndays)]
    return alldates

def create_list_target_verif(_target, _dates=None, as_list=False):
    """
    Using the target value in the config file; do either create a
    list of dates using _date as start point or
    create a python object (list or range)
    :param _target: target given in config file
    :param _dates: start date to be used
    :param as_list: False = return dates; True: return _target as python object
    :return: list of dates or python object of target
    """
    _target_des = csv_to_list(_target, sep=':')[0]
    _target_val = csv_to_list(_target, sep=':')[1]

    if _target_des == 's':
        raise f'Target description {_target_des} not implemented yet'

    if _target_des == 'i':
        _target_val = csv_to_list(_target_val, sep=',')
        _target_val = [int(_val)-1 for _val in _target_val]

    elif _target_des == 'r':
        _target_val = csv_to_list(_target_val, sep=',')
        if len(_target_val) == 1:
            _target_val = [0]+_target_val
        _target_val = range(int(_target_val[0]), int(_target_val[-1]))
    else:
        raise f'Target description {_target_des} not implemented yet'


    if as_list:
        return _target_val

    alldates = []
    for _date in _dates:
        alldates += [_date + dt.timedelta(days=x) for x in _target_val]

    return alldates




def make_hc_datelist(fromdates, todates):
    """
    Generate hindcast dates from start dand end year
    :param fromdates: start hindcast date
    :param todates:  end hindcast date
    :return: sorted hindcast list
    """
    hc_date_list = set()
    for (hc_from_date, hc_to_date) in zip(fromdates,todates):
        hc_date_list.update([dt.datetime(d,hc_from_date.month,hc_from_date.day) \
                             for d in range(hc_from_date.year, hc_to_date.year + 1)])

    return sorted(hc_date_list)

def make_hc_datelist_new(refdates, fromdates, todates):
    """
    Generate hindcast dates from start dand end year
    :param fromdates: start hindcast date
    :param todates:  end hindcast date
    :return: sorted hindcast list
    """
    hc_date_dict = {}
    shc_date_dict = {}
    alldates = []
    for (hc_refdate, hc_from_date, hc_to_date) in zip(refdates, fromdates,todates):
        dt_dates = [dt.datetime(d,hc_from_date.month,hc_from_date.day) \
                             for d in range(hc_from_date.year, hc_to_date.year + 1)]
        hc_date_dict.update({hc_refdate: dt_dates})
        shc_date_dict.update({hc_refdate: [d.strftime('%Y%m%d') for d in dt_dates]})
        alldates.append(dt_dates)


    return hc_date_dict, shc_date_dict, [num for sublist in alldates for num in sublist]

def make_dir(directory_name, verbose=False):
    """
    routine to create directory on operating system
    :param directory_name: name of directory to create
    :param verbose: if verbose is True provide additional output
    """
    if not os.path.isdir(directory_name):
        try:
            os.makedirs(directory_name)
        except OSError:
            raise RuntimeError('OS reported error when trying to create\n'
                               + directory_name
                               + '\nIs the path reachable, '
                                 'and do you have write permission?') from None
        if verbose:
            print(f'Created directory {directory_name}')


def print_banner(word):
    """
    Create printed output as banner
    (from https://code.activestate.com/recipes/577537-banner/)
    :param word: word to be printed
    """
    letterforms = '''\
       |       |       |       |       |       |       | |
  XXX  |  XXX  |  XXX  |   X   |       |  XXX  |  XXX  |!|
  X  X |  X  X |  X  X |       |       |       |       |"|
  X X  |  X X  |XXXXXXX|  X X  |XXXXXXX|  X X  |  X X  |#|
 XXXXX |X  X  X|X  X   | XXXXX |   X  X|X  X  X| XXXXX |$|
XXX   X|X X  X |XXX X  |   X   |  X XXX| X  X X|X   XXX|%|
  XX   | X  X  |  XX   | XXX   |X   X X|X    X | XXX  X|&|
  XXX  |  XXX  |   X   |  X    |       |       |       |'|
   XX  |  X    | X     | X     | X     |  X    |   XX  |(|
  XX   |    X  |     X |     X |     X |    X  |  XX   |)|
       | X   X |  X X  |XXXXXXX|  X X  | X   X |       |*|
       |   X   |   X   | XXXXX |   X   |   X   |       |+|
       |       |       |  XXX  |  XXX  |   X   |  X    |,|
       |       |       | XXXXX |       |       |       |-|
       |       |       |       |  XXX  |  XXX  |  XXX  |.|
      X|     X |    X  |   X   |  X    | X     |X      |/|
  XXX  | X   X |X     X|X     X|X     X| X   X |  XXX  |0|
   X   |  XX   | X X   |   X   |   X   |   X   | XXXXX |1|
 XXXXX |X     X|      X| XXXXX |X      |X      |XXXXXXX|2|
 XXXXX |X     X|      X| XXXXX |      X|X     X| XXXXX |3|
X      |X    X |X    X |X    X |XXXXXXX|     X |     X |4|
XXXXXXX|X      |X      |XXXXXX |      X|X     X| XXXXX |5|
 XXXXX |X     X|X      |XXXXXX |X     X|X     X| XXXXX |6|
XXXXXX |X    X |    X  |   X   |  X    |  X    |  X    |7|
 XXXXX |X     X|X     X| XXXXX |X     X|X     X| XXXXX |8|
 XXXXX |X     X|X     X| XXXXXX|      X|X     X| XXXXX |9|
   X   |  XXX  |   X   |       |   X   |  XXX  |   X   |:|
  XXX  |  XXX  |       |  XXX  |  XXX  |   X   |  X    |;|
    X  |   X   |  X    | X     |  X    |   X   |    X  |<|
       |       |XXXXXXX|       |XXXXXXX|       |       |=|
  X    |   X   |    X  |     X |    X  |   X   |  X    |>|
 XXXXX |X     X|      X|   XXX |   X   |       |   X   |?|
 XXXXX |X     X|X XXX X|X XXX X|X XXXX |X      | XXXXX |@|
   X   |  X X  | X   X |X     X|XXXXXXX|X     X|X     X|A|
XXXXXX |X     X|X     X|XXXXXX |X     X|X     X|XXXXXX |B|
 XXXXX |X     X|X      |X      |X      |X     X| XXXXX |C|
XXXXXX |X     X|X     X|X     X|X     X|X     X|XXXXXX |D|
XXXXXXX|X      |X      |XXXXX  |X      |X      |XXXXXXX|E|
XXXXXXX|X      |X      |XXXXX  |X      |X      |X      |F|
 XXXXX |X     X|X      |X  XXXX|X     X|X     X| XXXXX |G|
X     X|X     X|X     X|XXXXXXX|X     X|X     X|X     X|H|
  XXX  |   X   |   X   |   X   |   X   |   X   |  XXX  |I|
      X|      X|      X|      X|X     X|X     X| XXXXX |J|
X    X |X   X  |X  X   |XXX    |X  X   |X   X  |X    X |K|
X      |X      |X      |X      |X      |X      |XXXXXXX|L|
X     X|XX   XX|X X X X|X  X  X|X     X|X     X|X     X|M|
X     X|XX    X|X X   X|X  X  X|X   X X|X    XX|X     X|N|
XXXXXXX|X     X|X     X|X     X|X     X|X     X|XXXXXXX|O|
XXXXXX |X     X|X     X|XXXXXX |X      |X      |X      |P|
 XXXXX |X     X|X     X|X     X|X   X X|X    X | XXXX X|Q|
XXXXXX |X     X|X     X|XXXXXX |X   X  |X    X |X     X|R|
 XXXXX |X     X|X      | XXXXX |      X|X     X| XXXXX |S|
XXXXXXX|   X   |   X   |   X   |   X   |   X   |   X   |T|
X     X|X     X|X     X|X     X|X     X|X     X| XXXXX |U|
X     X|X     X|X     X|X     X| X   X |  X X  |   X   |V|
X     X|X  X  X|X  X  X|X  X  X|X  X  X|X  X  X| XX XX |W|
X     X| X   X |  X X  |   X   |  X X  | X   X |X     X|X|
X     X| X   X |  X X  |   X   |   X   |   X   |   X   |Y|
XXXXXXX|     X |    X  |   X   |  X    | X     |XXXXXXX|Z|
 XXXXX | X     | X     | X     | X     | X     | XXXXX |[|
X      | X     |  X    |   X   |    X  |     X |      X|\|
 XXXXX |     X |     X |     X |     X |     X | XXXXX |]|
   X   |  X X  | X   X |       |       |       |       |^|
       |       |       |       |       |       |XXXXXXX|_|
       |  XXX  |  XXX  |   X   |    X  |       |       |`|
       |   XX  |  X  X | X    X| XXXXXX| X    X| X    X|a|
       | XXXXX | X    X| XXXXX | X    X| X    X| XXXXX |b|
       |  XXXX | X    X| X     | X     | X    X|  XXXX |c|
       | XXXXX | X    X| X    X| X    X| X    X| XXXXX |d|
       | XXXXXX| X     | XXXXX | X     | X     | XXXXXX|e|
       | XXXXXX| X     | XXXXX | X     | X     | X     |f|
       |  XXXX | X    X| X     | X  XXX| X    X|  XXXX |g|
       | X    X| X    X| XXXXXX| X    X| X    X| X    X|h|
       |    X  |    X  |    X  |    X  |    X  |    X  |i|
       |      X|      X|      X|      X| X    X|  XXXX |j|
       | X    X| X   X | XXXX  | X  X  | X   X | X    X|k|
       | X     | X     | X     | X     | X     | XXXXXX|l|
       | X    X| XX  XX| X XX X| X    X| X    X| X    X|m|
       | X    X| XX   X| X X  X| X  X X| X   XX| X    X|n|
       |  XXXX | X    X| X    X| X    X| X    X|  XXXX |o|
       | XXXXX | X    X| X    X| XXXXX | X     | X     |p|
       |  XXXX | X    X| X    X| X  X X| X   X |  XXX X|q|
       | XXXXX | X    X| X    X| XXXXX | X   X | X    X|r|
       |  XXXX | X     |  XXXX |      X| X    X|  XXXX |s|
       |  XXXXX|    X  |    X  |    X  |    X  |    X  |t|
       | X    X| X    X| X    X| X    X| X    X|  XXXX |u|
       | X    X| X    X| X    X| X    X|  X  X |   XX  |v|
       | X    X| X    X| X    X| X XX X| XX  XX| X    X|w|
       | X    X|  X  X |   XX  |   XX  |  X  X | X    X|x|
       |  X   X|   X X |    X  |    X  |    X  |    X  |y|
       | XXXXXX|     X |    X  |   X   |  X    | XXXXXX|z|
  XXX  | X     | X     |XX     | X     | X     |  XXX  |{|
   X   |   X   |   X   |       |   X   |   X   |   X   |||
  XXX  |     X |     X |     XX|     X |     X |  XXX  |}|
 XX    |X  X  X|    XX |       |       |       |       |~|
    '''.splitlines()

    table = {}
    for form in letterforms:
        if '|' in form:
            table[form[-2]] = form[:-3].split('|')
    rows = len(list(table.values())[0])


    print("-" * 120)
    for row in range(rows):
        space = ' ' * 5
        text = '  '.join([table[c][row] for c in word])
        print(space, text.replace('X', '#'))

    print("-" * 120)

def print_info(text):
    """
    Print additional information preceded by INFO:
    :param text: text to be printed
    """
    print('*'*120)
    print(f'INFO: {text}')
    print('*' * 120)

plot_params ={
    'sic' : {
        'shortname':'sic',
        'longname':'sea ice fraction',
        'units':'fraction'
    }
}
