import pytest
from wt_tools.replays_db.replays_db import ReplaysDb, ValidateTableError


def test_validated_users(users_json, users):
    assert ReplaysDb._validated(users_json, 'users') == users


def test_validated_users_with_non_int_id_raises_ValidateTableError(users_with_non_int_id_json):
    with pytest.raises(ValidateTableError):
        ReplaysDb._validated(users_with_non_int_id_json, 'users')


def test_validated_users_with_non_nat_id_raisesValidateTableError(users_with_non_nat_id_json):
    with pytest.raises(ValidateTableError):
        ReplaysDb._validated(users_with_non_nat_id_json, 'users')


def test_validated_units(units_json, units):
    assert ReplaysDb._validated(units_json, 'units') == units


def test_validated_replays(replays_json, replays):
    assert ReplaysDb._validated(replays_json, 'replays') == replays


def test_section_transformer_call(section_transformer, partial_wrpl_rez, section_map):
    section_transformer(partial_wrpl_rez)
    assert section_transformer.document == section_map


def test_split_map(section_map, section_tables):
    assert ReplaysDb._split_map(section_map) == section_tables
