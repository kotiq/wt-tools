import pytest


def test_update_from_replays_without_replays_path_raises_ValueError(db_without_replays_path):
    with pytest.raises(ValueError, match='replays_path'):
        db_without_replays_path.update_from_replays(replays_path=None)
