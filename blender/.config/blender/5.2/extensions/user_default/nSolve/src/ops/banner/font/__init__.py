import blf

from os import path

def load(font):
    _path = path.join(path.dirname(__file__), font)
    return blf.load(_path) if path.isfile(_path) else 0
