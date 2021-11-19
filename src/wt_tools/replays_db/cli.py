import argparse
from collections import Counter
from operator import itemgetter
from pathlib import Path
import sys
from wt_tools.replays_db.replays_db import ReplaysDb, Error, br_from, er_from, Difficulty

get_info = itemgetter('info')
get_rank = itemgetter('rank')
get_units = itemgetter('units')
get_difficulty = itemgetter('difficulty')


def part_by(replays, update, uid, unit, rank, difficulty):
    counter = Counter()
    for info in map(get_info, filter(lambda v: get_difficulty(v) == difficulty, replays.values())):
        data = info.get(uid)
        if data and unit in get_units(data) and rank == get_rank(data):
            update(counter, info)
    return counter


def update_max_rank(counter, info):
    max_rank = max(map(get_rank, info.values()))
    counter.update([max_rank])


def update_min_max_rank(counter, info):
    max_rank = max(map(get_rank, info.values()))
    min_rank = min(map(get_rank, info.values()))
    counter.update([(min_rank, max_rank)])


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true', help='Дополнительная информация.')
    subparsers = parser.add_subparsers(dest='subparser_name', help='Помощь по командам')
    parser_update = subparsers.add_parser('update')
    parser_update.add_argument('db', type=Path, help='Директория с таблицами.')
    parser_update.add_argument('replays', type=Path, help='Директория с повторами.')
    parser_update.add_argument('--from', dest='from_', type=int, default=None, help='Номер повтора <от>.')
    parser_update.add_argument('--to', type=int, default=None, help='Номер повтора <до, включительно>.')

    parser_query = subparsers.add_parser('query')
    parser_query.add_argument('db', type=Path, help='Директория с таблицами.')
    parser_query.add_argument('what', choices=('max', 'minmax'),
                              help='Режим: max - разница от наибольшего ранга, '
                                   'minmax - представленные диапазоны рагнов.')
    parser_query.add_argument('user_id', type=int)
    parser_query.add_argument('unit_id')
    parser_query.add_argument('br', type=float)
    parser_query.add_argument('difficulty', choices=('arcade', 'realistic', 'hardcore'), help='Уровень сложности.')

    return parser.parse_args()


def main():
    args_ns = get_args()
    verbose = args_ns.verbose
    if verbose:
        print('args_ns:')
        for name, value in vars(args_ns).items():
            print(f'  {name} => {value!r}')

    subparser_name = args_ns.subparser_name
    if subparser_name == 'update':
        replays_: Path = args_ns.replays
        if not replays_.exists():
            print('Ожидалась существующая директория для replays')
            return 1

        if not replays_.is_dir():
            print('Ожидалась директория для replays: mode={:#o}'.format(replays_.stat().st_mode), file=sys.stderr)
            return 1

        db: Path = args_ns.db
        if db.exists() and not db.is_dir():
            print('Ожидалась директория для db: mode={:#o}'.format(db.stat().st_mode), file=sys.stderr)
            return 1

        try:
            db.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print('Не удалось создать директорию db: {}'.format(e), file=sys.stderr)
            return 1

        from_, to = args_ns.from_, args_ns.to
        if from_ is not None and from_ < 0:
            print('Ожидалось натуральное для from: {}'.format(from_), file=sys.stderr)
            return 1
        if to is not None and to < 0:
            print('Ожидалось натуральное для to: {}'.format(to), file=sys.stderr)
            return 1
        if from_ is not None and to is not None and from_ > to:
            print('Ожидалось from <= to: {} > {}'.format(from_, to))
            return 1

        if from_ is None and to is None:
            sid_pred = None
        elif from_ is None and to is not None:
            def sid_pred(sid):
                return sid <= to
        elif from_ is not None and to is None:
            def sid_pred(sid):
                return sid >= from_
        else:
            def sid_pred(sid):
                return from_ <= sid <= to

        rdb = ReplaysDb(replays_path=replays_, db_path=db)
        try:
            rdb.update_from_replays(sid_pred=sid_pred)
            rdb.save()
        except Error as e:
            msg = str(e)
            cause = e.__cause__
            if cause:
                msg = f'{msg}: {e}'
            print(msg, file=sys.stderr)
            return 1
    elif subparser_name == 'query':
        db: Path = args_ns.db

        if not db.exists():
            print('Ожидалась существующая директория для db'.format(), file=sys.stderr)
            return 1

        if not db.is_dir():
            print('Ожидалась директория для db: mode={:#o}'.format(db.stat().st_mode), file=sys.stderr)
            return 1

        difficulty = args_ns.difficulty
        difficulty = Difficulty[difficulty.upper()]

        user_id = args_ns.user_id
        if user_id < 0:
            print('Ожидалось натуральное для user_id: {}'.format(user_id), file=sys.stderr)
            return 1

        unit_id = args_ns.unit_id
        br = args_ns.br

        if br < 1.0:
            print('Ожидалось превышающее 1.0 для br: {}'.format(br), file=sys.stderr)
            return 1

        br_text = format(br, '.1f')
        if br_text.split('.')[-1] not in ('0', '3', '7'):
            print('Ожидалось x.0, x.3 или x.7 для br: {}'.format(br_text), file=sys.stderr)

        rank = er_from(br)

        rdb = ReplaysDb(db_path=db)
        try:
            rdb.load()
            users = rdb.tables['users']
            units = rdb.tables['units']
            replays = rdb.tables['replays']

            if user_id not in users:
                print('Не найден пользователь для user_id: {}'.format(user_id), file=sys.stderr)
                return 1
            if unit_id not in units:
                print('Не найдена техника с unit_id: {}'.format(unit_id), file=sys.stderr)
                return 1

            what = args_ns.what
            if what == 'max':
                counter = part_by(replays, update_max_rank, user_id, unit_id, rank, difficulty)
                if not counter:
                    print('Не найдены повторы, удовлетворяющие запросу.')
                    return 3
                total = sum(counter.values())
                print('Сессий: {}'.format(total))
                for r in sorted(counter):
                    count = counter[r]
                    print(f'{r - rank} => {100*count/total:>4.1f}%')
            elif what == 'minmax':
                counter = part_by(replays, update_min_max_rank, user_id, unit_id, rank, difficulty)
                if not counter:
                    print('Не найдены повторы, удовлетворяющие запросу.')
                    return 3
                total = sum(counter.values())
                print('Сессий: {}'.format(total))
                print('Эффективный ранг набора: {}'.format(rank))
                for p in sorted(counter):
                    count = counter[p]
                    rs = tuple(map(rank.__rsub__, p))
                    print(f'{rs!s:<7} => {100*count/total:>4.1f}%')
            else:
                raise RuntimeError('what')

        except Error as e:
            msg = str(e)
            cause = e.__cause__
            if cause:
                msg = f'{msg}: {e}'
            print(msg, file=sys.stderr)
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
