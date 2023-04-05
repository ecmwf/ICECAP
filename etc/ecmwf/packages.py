"""
Print the versions of some important scientific packages we sue
"""

import importlib


def print_version(pname):
    p = importlib.import_module(pname)
    if pname in ['pandas', 'cartopy', 'matplotlib']:
        vdict = p._version.get_versions()
        version = vdict['version']
    elif pname == 'numpy':
        version = p.version.version
    elif pname == 'xarray':
        version = p.__version__
    else:
        raise RuntimeError
    print('{}: {}'.format(pname, version))
    
    
if __name__ == '__main__':
    print_version('cartopy')
    print_version('matplotlib')
    print_version('numpy')
    print_version('pandas')
    print_version('xarray')

