import argparse
from wt_tools.formats.wrpl_parser_ng import WRPLCliFile


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('replay', type=argparse.FileType('rb'))
    return parser.parse_args()


def main():
    args_ns = parse_args()
    parsed = WRPLCliFile.parse_stream(args_ns.replay)

    print(f'difficilty: {parsed.header.difficulty.name}')
    print(f'session type: {parsed.header.session_type.name}')
    print(f'battle_class: {parsed.header.battle_class}')

    print(f'm_set_size: {parsed.header.m_set_size:_}')
    print(f'wrplu_offset: {parsed.wrplu_offset:_}')
    print(f'wrplu_size: {parsed.header.rez_offset - parsed.wrplu_offset:_}')
    print(f'rez_offset: {parsed.header.rez_offset:_}')


if __name__ == '__main__':
    main()
