from pathlib import Path
import pytest


def pytest_addoption(parser):
    buildpath = {
        'name': 'buildpath',
        'help': 'Директория для промежуточных построений тестами.'
    }

    blkdatapath = {
        'name': 'blkdatapath',
        'help': 'Директория с блоками данных blk или bbf3 файлами.'
    }

    wtpath = {
        'name': 'wtpath',
        'help': 'Директория War Thunder.',
    }

    enpath = {
        'name': 'enpath',
        'help': 'Директория Enlisted.'
    }

    cdkpath = {
        'name': 'cdkpath',
        'help': 'Директория WarThunderCDK.'
    }

    for m in buildpath, blkdatapath, wtpath, enpath, cdkpath:
        parser.addini(**m)


def maybepath(name, scope):
    def f(pytestconfig):
        value = pytestconfig.getini(name)
        return Path(value) if value else None

    f.__name__ = name
    return pytest.fixture(scope=scope)(f)


buildpath = maybepath('buildpath', 'session')
blkdatapath = maybepath('blkdatapath', 'session')
wtpath = maybepath('wtpath', 'session')
enpath = maybepath('enpath', 'session')
cdkpath = maybepath('cdkpath', 'session')
