import os
import shutil
import logging
import pytest
from vromfs_unpacker import unpack
from helpers import make_outpath, make_tmppath
from . import stem

outpath = make_outpath(__name__)
tmppath = make_tmppath(__name__)


def blk_file_size(dirname):
    for dir_, subs, files in os.walk(dirname):
        for file_ in files:
            if file_.endswith('.blk'):
                path = os.path.join(dir_, file_)
                stat_ = os.stat(path)
                size = stat_.st_size
                yield path, size


@pytest.fixture(scope='module')
def log_largest_blk(tmppath, outpath):
    log_file = os.path.join(outpath, 'largest_blk.log')
    if os.path.isfile(log_file):
        os.unlink(log_file)

    yield

    logger = logging.getLogger('test_unpack')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(log_file)
    logger.addHandler(fh)

    try:
        name, size = max(blk_file_size(tmppath), key=lambda kv: kv[1])
        rname = name[len(tmppath):].lstrip(os.path.sep)
        logger.info(f'{rname!r}: {size:_}')
    except ValueError:
        logger.info('Нет blk файлов.')


@pytest.mark.parametrize('rpath', [
    'aces.vromfs.bin',
    'char.vromfs.bin',
    'game.vromfs.bin',
    'gui.vromfs.bin',
    'lang.vromfs.bin',
    'launcher.vromfs.bin',
    'mis.vromfs.bin',
    'webUi.vromfs.bin',
    'wwdata.vromfs.bin',
], ids=stem)
def test_unpack(binrespath, rpath, tmppath, log_largest_blk):
    filename = os.path.join(binrespath, rpath)
    dist_dir = os.path.join(tmppath, f'{rpath}_u')
    if os.path.isdir(dist_dir):
        shutil.rmtree(dist_dir)

    unpack(filename, dist_dir)
