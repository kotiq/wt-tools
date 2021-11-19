import pytest


def test_save_without_db_path_raises_ValueError(db_without_db_path):
    with pytest.raises(ValueError, match='db_path'):
        db_without_db_path.save(db_path=None)
