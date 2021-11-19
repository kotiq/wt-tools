import pytest


def test_load_without_db_path_raises_ValueError(db_without_db_path):
    with pytest.raises(ValueError, match='db_path'):
        db_without_db_path.load(db_path=None)
