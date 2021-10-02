"""
Распаковка клиентского реплея после смены формата.

Вход:
#2021.09.20 19.30.33.wrpl

Выход:
#2021.09.20 19.30.33.wrpl.d/
├── m_set.json
├── rez.json
└── wrplu.bin
"""

import argparse
from pathlib import Path
import typing as t
import io
import os
import zlib
import construct as ct
from construct import this
from blk.types import Section
import blk.binary as bin
import blk.text as txt
import blk.json as jsn

STRICT_BLK = 'strict_blk'
JSON = 'json'
JSON_2 = 'json_2'
JSON_3 = 'json_3'

out_type_map = {
    STRICT_BLK: txt.STRICT_BLK,
    JSON: jsn.JSON,
    JSON_2: jsn.JSON_2,
    JSON_3: jsn.JSON_3,
}


def suffix(out_format: str) -> str:
    return '.blkx' if out_format == STRICT_BLK else '.json'


def serialize_text(root: Section, ostream: t.TextIO, out_type: int, is_sorted: bool = False):
    if out_type == txt.STRICT_BLK:
        txt.serialize(root, ostream, dialect=txt.StrictDialect)
    elif out_type in (jsn.JSON, jsn.JSON_2, jsn.JSON_3):
        jsn.serialize(root, ostream, out_type, is_sorted)


def create_text(path: os.PathLike) -> t.TextIO:
    return open(path, 'w', newline='', encoding='utf8')


class StringFieldAdapter(ct.Adapter):
    def _decode(self, obj: bytes, context: ct.Container, path: str) -> str:
        bs = obj.rstrip(b'\x00')
        return bs.decode()


def StringField(sz: int) -> ct.Construct:
    return StringFieldAdapter(ct.Bytes(sz))


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


class FatBlock(ct.Adapter):
    def _decode(self, obj: bytes, context: ct.Container, path: str) -> Section:
        stream = io.BytesIO(obj)
        return bin.compose_fat(stream)


def FatBlockStream(sz: t.Union[int, callable, None] = None) -> ct.Construct:
    return FatBlock(ct.GreedyBytes if sz is None else ct.Bytes(sz))


class ZlibCompressed(ct.Adapter):
    def _decode(self, obj: bytes, context: ct.Container, path: str) -> bytes:
        return zlib.decompress(obj)


def ZlibStream(sz: t.Union[int, callable]) -> ct.Construct:
    return ZlibCompressed(ct.Bytes(sz))


WRPLCliFile = ct.Struct(
    'header' / Header,
    'm_set' / FatBlockStream(this.header.m_set_size),
    'wrplu_offset' / ct.Tell,
    'wrplu' / ZlibStream(this.header.rez_offset - this.wrplu_offset),
    'rez' / FatBlockStream(),
)


def main():
    parser = argparse.ArgumentParser(description='Распаковщик реплея.')
    parser.add_argument('replay', type=argparse.FileType('rb'), help='Файл реплея.')
    parser.add_argument('-o', dest='out_dir', type=Path, default=Path.cwd(),
                        help='Выходная директория. По умолчанию %(default)s.')
    parser.add_argument('--format', dest='out_format', choices=list(out_type_map), default=JSON,
                        help='Формат для blk. По умолчанию %(default)s.')
    ns = parser.parse_args()
    replay = ns.replay
    out_format = ns.out_format
    out_type = out_type_map[out_format]
    out_dir: Path = ns.out_dir / f'{replay.name}.d'
    out_dir.mkdir(parents=True, exist_ok=True)

    parsed = WRPLCliFile.parse_stream(replay)
    for name in ('m_set', 'rez'):
        section = parsed[name]
        out_path = (out_dir / name).with_suffix(suffix(out_format))
        with create_text(out_path) as ostream:
            serialize_text(section, ostream, out_type)

    out_path = out_dir / 'wrplu.bin'
    out_path.write_bytes(parsed['wrplu'])


if __name__ == '__main__':
    main()
