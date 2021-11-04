import errno
from enum import IntEnum
import json
import os
import sys
from operator import attrgetter
from hashlib import md5
from typing import AnyStr, Optional, Sequence, Union
import click
import zstandard as zstd
try:
    from formats.vromfs_parser import vromfs_file
except ImportError:
    from wt_tools.formats.vromfs_parser import vromfs_file


class BlkType(IntEnum):
    FAT = 1
    FAT_ZSTD = 2
    SLIM = 3
    SLIM_ZSTD = 4
    SLIM_SZTD_DICT = 5


def mkdir_p(path):
    n_path = ''.join(os.path.split(path)[:-1])
    try:
        if n_path != '':
            os.makedirs(n_path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(n_path):
            pass
        else:
            raise


MAX_OUTPUT_SIZE = 5_000_000


def get_blk_content(node, dctx: Optional[zstd.ZstdDecompressor]) -> bytes:
    if node.file_data_size == 0:
        bs = b''
    else:
        pk_type = node.data[0]
        if (pk_type in (BlkType.FAT_ZSTD, BlkType.SLIM_ZSTD, BlkType.SLIM_SZTD_DICT)) and not dctx:
            raise RuntimeError("ZstdDecomressor instance expected, packed_type: {}".format(pk_type))

        if pk_type == BlkType.FAT:
            bs = node.data[1:]
        elif pk_type == BlkType.FAT_ZSTD:
            pk_size = int.from_bytes(node.data[1:4], byteorder='little')
            pk_offset = 4
            decoded = dctx.decompress(node.data[pk_offset:pk_offset+pk_size], max_output_size=MAX_OUTPUT_SIZE)
            bs = decoded[1:]
        elif pk_type == BlkType.SLIM:
            bs = node.data[1:]
        elif pk_type == BlkType.SLIM_ZSTD:
            bs = dctx.decompress(node.data[1:], max_output_size=MAX_OUTPUT_SIZE)
        elif pk_type == BlkType.SLIM_SZTD_DICT:
            bs = dctx.decompress(node.data[1:], max_output_size=MAX_OUTPUT_SIZE)
        else:
            bs = node.data

    return bs


def get_shared_names_content(node, dctx: zstd.ZstdDecompressor) -> bytes:
    pk_offset = 40
    return dctx.decompress(node.data[pk_offset:], max_output_size=MAX_OUTPUT_SIZE)


def get_dict_name(node) -> Optional[str]:
    offset = 8
    size = 32
    dict_id: bytes = node.data[offset:offset+size]
    if dict_id == b'\x00'*size:
        return None
    return f'{dict_id.hex()}.dict'


def normalize_name(name: str) -> str:
    return name.lstrip('/\\')


get_name = attrgetter("filename")
get_data = attrgetter("data")


Path = Union[AnyStr, os.PathLike]


def unpack(filename: Path, dest_dir: Path, file_list_path: Optional[Path] = None) -> Sequence[str]:
    """
    Unpack files from .vromfs.bin

    :param filename: path to .vromfs.bin file
    :param dest_dir: path to output dir
    :param file_list_path: path to file list, if you want to unpack only few files, in json list.
    :return internal names that have been written
    """

    if file_list_path:
        with open(file_list_path) as f:
            try:
                file_list = json.load(f)
            except json.JSONDecodeError as e:
                msg = "[FAIL] Load the file list from {}: {}".format(os.path.abspath(file_list_path), e)
                print(msg, file=sys.stderr)
                sys.exit(1)

        file_list = [os.path.normcase(p) for p in file_list]
    else:
        file_list = None

    if file_list == []:
        print("[WARN] Nothing to do: the file list is empty.")
        return ()

    with open(filename, 'rb') as f:
        data = f.read()
    parsed = vromfs_file.parse(data)

    names_ns = parsed.body.data.data.filename_table.filenames
    files_count = len(names_ns)
    data_ns = parsed.body.data.data.file_data_table.file_data_list
    nm_id = files_count - 1
    is_namemap_here = names_ns[nm_id].filename == 'nm'

    if is_namemap_here:
        dict_name = get_dict_name(data_ns[nm_id])
        if dict_name:
            dict_id = None
            for i, ns in enumerate(names_ns):
                if ns.filename == dict_name:
                    dict_id = i
                    break
            zstd_dict = zstd.ZstdCompressionDict(data_ns[dict_id].data, dict_type=zstd.DICT_TYPE_AUTO)
            dctx = zstd.ZstdDecompressor(dict_data=zstd_dict, format=zstd.FORMAT_ZSTD1)
        else:
            dctx = zstd.ZstdDecompressor(format=zstd.FORMAT_ZSTD1)
    else:
        dctx = None

    written_names = []

    with click.progressbar(range(files_count), label="Unpacking files") as bar:
        for i in bar:
            # clean leading slashes, there was a bug in 1.99.1.70 with "/version" file path
            internal_file_path = normalize_name(names_ns[i].filename)

            if (file_list is None) or (os.path.normcase(internal_file_path) in file_list):
                unpacked_filename = os.path.join(dest_dir, internal_file_path)
                mkdir_p(unpacked_filename)
                with open(unpacked_filename, 'wb') as f:
                    if os.path.basename(unpacked_filename) == 'nm':
                        bs = get_shared_names_content(data_ns[i], dctx)
                    elif unpacked_filename.endswith('.blk'):
                        bs = get_blk_content(data_ns[i], dctx)
                    else:
                        bs = data_ns[i].data

                    if bs:
                        f.write(bs)
                        written_names.append(internal_file_path)

    print("[OK] {} => {}".format(*map(os.path.abspath, (filename, dest_dir))))

    return tuple(written_names)


def files_list_info(filename: Path, dest_file: Optional[Path] = None) -> Optional[str]:
    with open(filename, 'rb') as f:
        data = f.read()
    parsed = vromfs_file.parse(data)
    names_ns = parsed.body.data.data.filename_table.filenames
    data_ns = parsed.body.data.data.file_data_table.file_data_list
    out_list = []

    for name, data in zip(map(get_name, names_ns), map(get_data, data_ns)):
        m = md5(data).hexdigest()
        out_list.append({"filename": os.path.normcase(name), "hash": m})

    out_json = json.dumps({'version': 1, 'filelist': out_list})
    if not dest_file:
        return out_json
    else:
        with open(dest_file, 'w') as f:
            f.write(out_json)
        print("[OK] {} => {}".format(*map(os.path.abspath, (filename, dest_file))))


@click.command()
@click.argument('filename', type=click.Path(exists=True, dir_okay=False))
@click.option('-O', '--output', 'output_path', type=click.Path(), default=None)
@click.option('--metadata', 'metadata', is_flag=True, default=False)
@click.option('--input_filelist', 'input_filelist', type=click.Path(), default=None)
def main(filename: os.PathLike, output_path: Optional[os.PathLike], metadata: bool, input_filelist: Optional[os.PathLike]):
    """
    vromfs_unpacker: unpacks vromfs file into folder

    FILENAME: vromfs file to unpack

    -O, --output: path where to unpack vromfs file, by default is FILENAME with appended _u, like some.vromfs.bin_u

    --metadata: if present, prints metadata of vromfs file: json with filename: md5_hash. If --output option used,
    prints to file instead.

    --input_filelist: pass the file with list of files you want to unpack and only this files will be unpacked.
    Files should be a json list format, like: `["buildtstamp", "gamedata/units/tankmodels/fr_b1_ter.blk"]`

    example: `vromfs_unpacker some.vromfs.bin` will unpack content to some.vromfs.bin_u folder. If you want to unpack to
    custom folder, use `vromfs_unpacker some.vromfs.bin --output my_folder`, that will unpack some.vromfs.bin folder to
    my_folder. If you want to get only file metadata, use `vromfs_unpacker some.vromfs.bin --metadata`. If you want to
    unpack only few selected manually files, place json list of files in file, and use
    `vromfs_unpacker some.vromfs.bin --input_filelist my_filelist.txt`
    """
    if metadata:
        if output_path:
            files_list_info(filename, dest_file=output_path)
        else:
            print(files_list_info(filename, dest_file=None))
    else:
        # unpack into output_folder/some.vromfs.bin folder
        if output_path:
            output_path = os.path.join(output_path, os.path.basename(filename))
        # unpack all into some.vromfs.bin_u folder
        else:
            head, tail = os.path.split(filename)
            output_path = os.path.join(head, tail + '_u')
        unpack(filename, output_path, input_filelist)


if __name__ == '__main__':
    main()
