import os
import shutil
import pytest
import construct as ct
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


def is_text(bs: bytes) -> bool:
    restricted = bytes.fromhex('00 01 02 03 04 05 06 07 08 0b 0c 0e 0f 10 11 12 14 13 15 16 17 18 19')
    return not any(b in restricted for b in bs)


def is_bbf3(bs):
    return bs[:4] in (b'\x00BBF', b'\x00BBz')


def is_slim(bs):
    return not bs[0]


def test_unpack_type_2(binrespath, tmppath):
    rpath = 'regional.vromfs.bin'
    filename = os.path.join(binrespath, rpath)
    dist_dir = os.path.join(tmppath, f'{rpath}_u')
    if os.path.isdir(dist_dir):
        shutil.rmtree(dist_dir)

    unpack(filename, dist_dir)

    filepath = os.path.join(dist_dir, 'dldata', 'downloadable_decals.blk')
    with open(filepath, 'rb') as istream:
        bs = istream.read(4)
        assert bs
        if not (is_bbf3(bs) or is_slim(bs)):
            istream.seek(0)
            RawCString = ct.NullTerminated(ct.GreedyBytes)
            Names = ct.FocusedSeq(
                'names',
                'names_count' / ct.VarInt,
                'names' / ct.Prefixed(ct.VarInt, RawCString[ct.this.names_count])
            )
            names = Names.parse_stream(istream)
            assert all(map(is_text, names))
