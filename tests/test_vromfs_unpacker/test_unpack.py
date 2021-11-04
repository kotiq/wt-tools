import json
import logging
from pathlib import Path
import pytest
from pytest_lazyfixture import lazy_fixture
from wt_tools.vromfs_unpacker import unpack
from helpers import check_path, make_tmppath

tmppath = make_tmppath(__name__)


@pytest.fixture(scope='module')
def nm_version_file_list_path(tmppath):
    path = tmppath / 'nm_version.json'
    data = ['version', 'nm']
    with open(path, 'w') as ostream:
        json.dump(data, ostream)
    return path


nm_version_file_list_path_ = lazy_fixture('nm_version_file_list_path')


@pytest.mark.parametrize('file_list_path', [
    pytest.param(None, id='all'),
    pytest.param(nm_version_file_list_path_, id='nm_version')
])
def test_unpack_wt(wtpath, file_list_path: Path, tmp_path):
    logging.info(f'dst path: {tmp_path}')
    check_path(wtpath, 'wtpath')
    image_paths = tuple(wtpath.rglob('*.vromfs.bin'))
    if not image_paths:
        pytest.skip('Не содержит .vromfs.bin: wtpath: {}'.format(wtpath))

    for src_path in image_paths:
        rel_src_path = src_path.relative_to(wtpath)
        logging.info(f'image: {rel_src_path}')
        dst_path = tmp_path / rel_src_path.with_suffix('').with_suffix('')
        written_names = unpack(src_path, dst_path, file_list_path)

        if file_list_path:
            file_list = json.load(file_list_path.open())
            assert len(written_names) <= len(file_list)
        else:
            assert written_names

        size = 0
        for name in written_names:
            path = dst_path / name
            stat = path.stat()
            assert stat.st_size
            size += stat.st_size

        logging.info(f'total: {len(written_names):_} files, {size:_} bytes')
