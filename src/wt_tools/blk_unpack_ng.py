import os
import sys
from pathlib import Path
from traceback import print_exc
import typing as t
import click
import blk_unpack as bbf3
import blk.binary as bin
from blk.binary.constructor import Name
import blk.text as txt
import blk.json as jsn


INDENT = ' '*4


def serialize_text(root, ostream, out_type, is_sorted):
    if out_type == txt.STRICT_BLK:
        txt.serialize(root, ostream, dialect=txt.StrictDialect)
    elif out_type in (jsn.JSON, jsn.JSON_2, jsn.JSON_3):
        jsn.serialize(root, ostream, out_type, is_sorted)


def is_text(bs: t.Iterable[bytes]) -> bool:
    restricted = bytes.fromhex('00 01 02 03 04 05 06 07 08 0b 0c 0e 0f 10 11 12 14 13 15 16 17 18 19')
    return not any(b in restricted for b in bs)


def create_text(path: os.PathLike) -> t.TextIO:
    return open(path, 'w', newline='', encoding='utf8')


def names_path(file_path: Path, nm: str) -> t.Optional[Path]:
    file_path = file_path.absolute()
    root_path = Path(file_path.drive + os.path.sep)

    dir_path = file_path.parent
    nm_path = dir_path / nm
    if nm_path.is_file():
        return nm_path

    while dir_path != root_path:
        dir_path = dir_path.parent
        nm_path = dir_path / nm
        if nm_path.is_file():
            return nm_path

    return None


def process_file(file_path: Path, names: t.Optional[t.Sequence], out_type: int, is_sorted: bool):
    if not file_path.suffix == '.blk':
        return

    out_path = file_path.with_suffix('.blkx')
    print(file_path)

    try:
        with open(file_path, 'rb') as istream:
            bs = istream.read(4)
            # пустой файл
            if not bs:
                print(f'{INDENT}Empty file')
                out_path.write_bytes(b'')
            # файл прежнего формата
            elif bs in (b'\x00BBF', b'\x00BBz'):
                istream.seek(0)
                bs = istream.read()
                bbf3_parser = bbf3.BLK(bs)
                ss = bbf3_parser.unpack(out_type, is_sorted=False)
                with create_text(out_path) as ostream:
                    ostream.write(ss)
            # файл с именами в nm
            elif not bs[0]:
                if names is None:
                    nm_path = names_path(file_path, 'nm')
                    if nm_path:
                        print(f'Loading NameMap from {nm_path!r}')
                        with open(nm_path, 'rb') as nm_istream:
                            names = bin.compose_names_data(nm_istream)
                if names:
                    istream.seek(0)
                    root = bin.compose_slim_data(names, istream)
                    with create_text(out_path) as ostream:
                        serialize_text(root, ostream, out_type, is_sorted)
                else:  # не найдена таблица имен
                    print(f"{INDENT}NameMap not found")
            # файл с именами внутри или текст
            else:
                istream.seek(0)
                try:
                    root = bin.compose_fat_data(istream)
                    with create_text(out_path) as ostream:
                        serialize_text(root, ostream, out_type, is_sorted)
                except bin.ComposeError:  # текст
                    # рабочей грамматики у меня пока нет
                    # есть парсер текста на parsy, но без строк в тройных кавычках и вложенных комментариев
                    # поэтому, считаю, что текст корректный
                    # выполняется только простая проверка на мелкие значения
                    istream.seek(0)
                    bs = istream.read()
                    if is_text(bs):
                        print(f'{INDENT}Copied as is')
                        out_path.write_bytes(bs)
                    else:
                        print(f'{INDENT}Unknown file format')

    except (TypeError, EnvironmentError, bin.ComposeError) as e:
        print(f'{INDENT}{e}')
        print_exc(file=sys.stdout)


def process_dir(dir_path: Path, out_type: int, is_sorted: bool):
    paths = tuple(dir_path.iterdir())

    for path in paths:
        if path.is_file() and path.name == 'nm':
            try:
                print(f'Loading NameMap from {path!r}')
                with open(path, 'rb') as nm_istream:
                    names = bin.compose_names_data(nm_istream)

                process_slim_dir(dir_path, names, out_type, is_sorted)
                return
            except bin.ComposeError as e:
                print(f'{path}')
                print(f'{INDENT}{e}')
                return

    for path in paths:
        if path.is_dir():
            process_dir(path, out_type, is_sorted)
        elif path.is_file():
            process_file(path, None, out_type, is_sorted)


def process_slim_dir(dir_path: Path, names: t.Sequence[Name], out_type: int, is_sorted: bool):
    for path in dir_path.iterdir():
        if path.is_dir():
            process_slim_dir(path, names, out_type, is_sorted)  # @r
        elif path.is_file():
            process_file(path, names, out_type, is_sorted)


@click.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--format', 'out_format',
              type=click.Choice(['strict_blk', 'json', 'json_2', 'json_3'], case_sensitive=False), default='json',
              show_default=True)
@click.option('--sort', 'is_sorted', is_flag=True, default=False)
def main(path: str, out_format: str, is_sorted: bool):
    out_type = {
        'strict_blk': txt.STRICT_BLK,
        'json': jsn.JSON,
        'json_2': jsn.JSON_2,
        'json_3': jsn.JSON_3,
    }[out_format]

    path = Path(path)
    if path.is_file():
        process_file(path, None, out_type, is_sorted)
    else:
        process_dir(path, out_type, is_sorted)


if __name__ == '__main__':
    main()
