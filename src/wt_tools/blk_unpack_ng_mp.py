import os
import sys
from pathlib import Path
import logging
import multiprocessing as mp
import typing as t
from functools import partial
import click
from multiprocessing_logging import install_mp_handler
import blk_unpack as bbf3
import blk.binary as bin
import blk.text as txt
import blk.json as jsn


logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.DEBUG, stream=sys.stdout)
install_mp_handler()
INDENT = ' '*4


def serialize_text(root, ostream, out_type, is_sorted):
    if out_type == txt.STRICT_BLK:
        txt.serialize(root, ostream, dialect=txt.StrictDialect)
    elif out_type in (jsn.JSON, jsn.JSON_2, jsn.JSON_3):
        jsn.serialize(root, ostream, out_type, is_sorted)


def is_text(bs: bytes) -> bool:
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
    logging.info(file_path)

    try:
        with open(file_path, 'rb') as istream:
            bs = istream.read(4)
            # пустой файл
            if not bs:
                logging.info(f'{INDENT}Empty file')
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
                        logging.info(f'Loading NameMap from {nm_path!r}')
                        with open(nm_path, 'rb') as nm_istream:
                            names = bin.compose_names_data(nm_istream)
                if names:
                    istream.seek(0)
                    root = bin.compose_slim_data(names, istream)
                    with create_text(out_path) as ostream:
                        serialize_text(root, ostream, out_type, is_sorted)
                else:  # не найдена таблица имен
                    logging.error(f"{INDENT}NameMap not found")
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
                        logging.info(f'{INDENT}Copied as is')
                        out_path.write_bytes(bs)
                    else:
                        logging.info(f'{INDENT}Unknown file format')

    except (TypeError, EnvironmentError, bin.ComposeError) as e:
        logging.exception(f'{INDENT}{e}', exc_info=True)


def process_dir(dir_path: Path, out_type: int, is_sorted: bool, pool: mp.Pool):
    # Директории без общих имен обрабатываются пулом процессов из аргументов.
    # Для каждой корневой директории с общими именами создается новый пул процессов, которым обрабатываются все дочерние
    # директории.

    paths = tuple(dir_path.iterdir())

    for path in paths:
        if path.is_file() and path.name == 'nm':
            try:
                logging.info(f'Loading NameMap from {path!r}')
                with open(path, 'rb') as nm_istream:
                    names = bin.compose_names_data(nm_istream)

                with mp.Pool(None) as pool:
                    file_paths = file_paths_r(dir_path)
                    process_file_ = partial(process_file, names=names, out_type=out_type, is_sorted=is_sorted)
                    pool.map_async(process_file_, file_paths)
                    pool.close()
                    pool.join()
                return
            except bin.ComposeError as e:
                logging.error(f'{path}')
                logging.exception(f'{INDENT}{e}', exc_info=True)
                return

    dir_paths = []
    file_paths = []

    for path in paths:
        if path.is_dir():
            dir_paths.append(path)
        elif path.is_file():
            file_paths.append(path)

    for dir_path in dir_paths:
        process_dir(dir_path, out_type, is_sorted, pool)

    process_file_ = partial(process_file, names=None, out_type=out_type, is_sorted=is_sorted)
    pool.map_async(process_file_, file_paths)


def file_paths_r(dir_path: Path) -> t.Generator[Path, None, None]:
    for path in dir_path.iterdir():
        if path.is_dir():
            yield from file_paths_r(path)  # @r
        elif path.is_file():
            yield path


@click.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--format', 'out_format',
              type=click.Choice(['strict_blk', 'json', 'json_2', 'json_3'], case_sensitive=False),
              default='json', show_default=True)
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
        with mp.Pool(None) as pool:
            process_dir(path, out_type, is_sorted, pool)
            pool.close()
            pool.join()


if __name__ == '__main__':
    main()
