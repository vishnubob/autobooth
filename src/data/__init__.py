import os

datadir = os.path.abspath(os.path.split(__file__)[0])

def get_data_path(datatype=None, filename=None):
    return os.path.join(datadir, datatype, filename)


