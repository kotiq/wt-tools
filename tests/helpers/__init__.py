from pathlib import Path
import pytest


def _outdir_rpath(name):
    return Path('tests', *name.split('.'))


def make_outpath(name: str):
    @pytest.fixture(scope='module')
    def outpath(buildpath: Path):
        path = buildpath / _outdir_rpath(name)
        path.mkdir(parents=True, exist_ok=True)
        return path

    return outpath


def make_tmppath(name: str):
    @pytest.fixture(scope='module')
    def tmppath(tmp_path_factory):
        return tmp_path_factory.mktemp(name)

    return tmppath


def check_path(path: Path, name: str):
    if path is None:
        pytest.skip('Не настроен путь: {}'.format(name))
    elif not path.is_dir():
        pytest.skip('Не директория: {}: {}'.format(name, path))
