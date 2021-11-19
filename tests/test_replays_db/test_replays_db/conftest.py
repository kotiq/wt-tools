import pytest
from wt_tools.replays_db.replays_db import ReplaysDb


@pytest.fixture()
def db_without_db_path():
    return ReplaysDb(db_path=None)


@pytest.fixture()
def db_without_replays_path():
    return ReplaysDb(replays_path=None)
