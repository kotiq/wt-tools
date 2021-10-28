"""
Распаковка клиентского реплея.

Вход:
#2021.09.20 19.30.33.wrpl

Выход:
#2021.09.20 19.30.33.wrpl.d/
├── m_set.blkx
├── rez.blkx
├── ssid.txt
└── wrplu.bin
"""

import argparse
from pathlib import Path
import typing as t
import os
import sys
import construct as ct
from blk.types import Section
import blk.text as txt
import blk.json as jsn
from formats.wrpl import WRPLCliFile

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
    replay_path = Path(replay.name)
    out_dir: Path = ns.out_dir / f'{replay_path.name}.d'

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print('Ошибка при создании выходной директории {}: {}'.format(out_dir, e), file=sys.stderr)
        return 1

    try:
        parsed = WRPLCliFile.parse_stream(replay)
    except ct.ConstructError as e:
        print('Ошибка при разборе входного файла {}: {}'.format(replay.name, e), file=sys.stderr)
        return 1

    for name in ('m_set', 'rez'):
        section = parsed[name]
        out_path = (out_dir / name).with_suffix(suffix(out_format))
        with create_text(out_path) as ostream:
            serialize_text(section, ostream, out_type)

    out_path = out_dir / 'wrplu.bin'
    out_path.write_bytes(parsed.wrplu)

    out_path = out_dir / 'ssid.txt'
    ssid = parsed.header.ssid
    out_path.write_text(str(ssid))

    print(f'{replay.name} => {out_dir}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
