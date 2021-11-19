import json
from pathlib import Path
import pytest
from _pytest.monkeypatch import MonkeyPatch
from blk import Section, Int, Str
from wt_tools import replays_db
from wt_tools.replays_db.replays_db import SectionTransformer


@pytest.fixture(scope='module')
def monkeymodule():
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture()
def users_json():
    return {
        "0": "Player0",
        "1": "Player1",
    }


@pytest.fixture()
def users():
    return {
        0: "Player0",
        1: "Player1",
    }


@pytest.fixture()
def users_with_non_int_id_json():
    return {
        "a0": "Player0"
    }


@pytest.fixture()
def users_with_non_nat_id_json():
    return {
        "-1": "Player0"
    }


@pytest.fixture()
def units_json():
    return {
        "unit0": {
            "rank": 0,
            "tier": 1
        },
        "unit1": {
            "rank": 7,
            "tier": 2
        }
    }


@pytest.fixture()
def units():
    return {
        "unit0": {
            "rank": 0,
            "tier": 1
        },
        "unit1": {
            "rank": 7,
            "tier": 2
        }
    }


@pytest.fixture()
def replays_json():
    return {
        "0": {
            "difficulty": 0,
            "start_time": 0,
            "info": {
                "0": {
                    "team": 1,
                    "rank": 0,
                    "units": ["unit0"]
                },
                "1": {
                    "team": 2,
                    "rank": 7,
                    "units": ["unit1"]
                }
            }
        }
    }


@pytest.fixture()
def replays():
    return {
        0: {
            "difficulty": 0,
            "start_time": 0,
            "info": {
                0: {
                    "team": 1,
                    "rank": 0,
                    "units": ["unit0"]
                },
                1: {
                    "team": 2,
                    "rank": 7,
                    "units": ["unit1"]
                }
            }
        }
    }


@pytest.fixture()
def section_transformer():
    schemas_root = Path(replays_db.__path__[0])
    with open(schemas_root / 'schema' / 'section.json') as istream:
        schema = json.load(istream)
    return SectionTransformer(schema)


@pytest.fixture()
def partial_wrpl_rez():
    root = Section()
    ui_scripts_data = Section()
    players_info = Section()

    player_info_key = '__int_0'
    player_info_value = Section()

    player_info_value.add('name', Str('root'))
    player_info_value.add('id', Int(0))
    player_info_value.add('team', Int(0))
    player_info_value.add('rank', Int(0))

    crafts_info = Section()
    unit0 = Section()
    unit0.add('name', Str('unit0'))
    unit0.add('mrank', Int(0))
    unit0.add('rank', Int(1))

    crafts_info.add('array0', unit0)
    player_info_value.add('crafts_info', crafts_info)

    players_info.add(player_info_key, player_info_value)

    ui_scripts_data.add('playersInfo', players_info)
    root.add('uiScriptsData', ui_scripts_data)

    return root


@pytest.fixture()
def section_map():
    return {
        'uiScriptsData': {
            'playersInfo': {
                '__int_0': {
                    'name': 'root',
                    'id': 0,
                    'team': 0,
                    'rank': 0,  # economic rank
                    'crafts_info': {
                        'array0': {
                            'name': 'unit0',
                            'mrank': 0,  # economic rank
                            'rank': 1  # tier
                        }
                    }
                }
            }
        }
    }


@pytest.fixture()
def section_tables():
    return {
        'info': {
            0: {
                'team': 0,
                'rank': 0,
                'units': ['unit0']
            }
        },
        'users': {
            0: 'root'
        },
        'units': {
            'unit0': {
                'rank': 0,
                'tier': 1
            }
        }
    }