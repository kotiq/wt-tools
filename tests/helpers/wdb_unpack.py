from pathlib import Path
import sys
import blk.binary as bin
import blk.text as txt

replays_path = Path('/media/games/kotiq/WarThunder/Replays/')


def main():
    in_path = replays_path / 'replays.wdb'
    out_path = in_path.with_suffix('.txt')
    with open(in_path, 'rb') as istream:
        root = bin.Fat.parse_stream(istream)
    with open(out_path, 'w', encoding='utf8') as ostream:
        txt.serialize(root, ostream)
    print(f'[OK] {in_path} => {out_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
