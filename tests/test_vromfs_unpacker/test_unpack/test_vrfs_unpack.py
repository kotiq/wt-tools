import os
import shutil
import pytest
from vromfs_unpacker import unpack
from helpers import make_tmppath
from . import stem

tmppath = make_tmppath(__name__)

ZSTD_MAGIC = bytes.fromhex('28B52FFD')


@pytest.mark.parametrize('rpath', [
    'regional.vromfs.bin',
    'gui.vromfs.bin',
    'launcher.vromfs.bin',
], ids=stem)
def test_unpack(binrespath, rpath, tmppath):
    filename = os.path.join(binrespath, rpath)
    dist_dir = os.path.join(tmppath, f'{rpath}_u')
    if os.path.isdir(dist_dir):
        shutil.rmtree(dist_dir)

    unpack(filename, dist_dir)

    nm = os.path.join(dist_dir, 'nm')
    if os.path.isfile(nm):
        with open(nm, 'rb') as istream:
            istream.seek(0x28)
            bs = istream.read(4)
            assert bs != ZSTD_MAGIC, nm
    else:
        for dir_, subs, files in os.walk(dist_dir):
            for file_ in files:
                if file_.endswith('.blk'):
                    path = os.path.join(dir_, file_)
                    with open(path, 'rb') as istream:
                        bs = istream.read(8)
                        assert ZSTD_MAGIC not in bs, path
