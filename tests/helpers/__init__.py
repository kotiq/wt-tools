import os
import pytest


def outdir_rpath(name):
    return os.path.join('tests', *name.split('.'))


def make_outpath(name):
    @pytest.fixture(scope='module')
    def outpath(buildpath):
        path = os.path.join(buildpath, outdir_rpath(name))
        os.makedirs(path, exist_ok=True)
        return path

    return outpath


def make_tmppath(name):
    @pytest.fixture(scope='module')
    def tmppath(tmpdir_factory):
        return str(tmpdir_factory.mktemp(name))

    return tmppath
