import typing as t
import construct as ct
from construct import this
import blk.binary as bin


def StringField(sz: t.Union[int, callable]) -> ct.Construct:
    return ct.FixedSized(sz, ct.CString('ascii'))


Header = ct.Struct(
    'magic' / ct.Const(bytes.fromhex('e5ac0010')),
    'version' / ct.Int32ul,  # 2.9.0.38 ~ 101111
    'level' / StringField(128),  # levels/avg_stalingrad_factory.bin
    'level_settings' / StringField(260),  # gamedata/missions/cta/tanks/stalingrad_factory/stalingrad_factory_dom.blk
    'battle_type' / StringField(128),  # stalingrad_factory_Dom
    'environment' / StringField(128),  # day
    'visibility' / StringField(32),  # good
    'rez_offset' / ct.Int32ul,
    'unk_40' / ct.Bytes(40),
    'ssid' / ct.Int64ul,
    'unk_8' / ct.Bytes(8),
    'm_set_size' / ct.Int32ul,
    'unk_28' / ct.Bytes(28),
    'loc_name' / StringField(128),  # missions/_Dom;stalingrad_factory/name
    'start_time' / ct.Int32ul,
    'time_limit' / ct.Int32ul,
    'score_limit' / ct.Int32ul,
    'unk_48' / ct.Bytes(48),
    'battle_type' / StringField(128),  # air_ground_Dom
    'battle_kill_streak' / StringField(128),  # killStreaksAircraftOrHelicopter_1
)


def FatBlockStream(sz: t.Union[int, callable, None] = None) -> ct.Construct:
    con = ct.GreedyBytes if sz is None else ct.Bytes(sz)
    return ct.RestreamData(con, bin.Fat)


def ZlibStream(sz: t.Union[int, callable, None] = None):
    con = ct.GreedyBytes if sz is None else ct.Bytes(sz)
    return ct.RestreamData(con, ct.Compressed(con, 'zlib'))


WRPLCliFile = ct.Struct(
    'header' / Header,
    'm_set' / FatBlockStream(this.header.m_set_size),
    'wrplu_offset' / ct.Tell,
    'wrplu' / ZlibStream(this.header.rez_offset - this.wrplu_offset),
    'rez' / bin.Fat,
)
