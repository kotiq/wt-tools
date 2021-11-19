import json
import sys
from pathlib import Path
import typing as t
import cerberus as cb
import construct as ct
from construct import this
from typing_extensions import TypedDict
from blk.binary import Fat
from wt_tools.formats.wrpl_parser_ng import Header, Difficulty, SessionType

here = Path(__file__).parent

T = t.TypeVar('T')
TableT = t.MutableMapping
TablesT = t.MutableMapping[str, TableT]
UsersT = t.MutableMapping[int, str]
UnitsT = t.MutableMapping[str, t.Mapping]


class ReplayTablesT(TypedDict):
    info: t.Mapping[int, t.Any]
    users: UsersT
    units: UnitsT


class Error(Exception):
    def __init__(self, name: str):
        self.name = name


class SchemaError(Error):
    pass


class TableError(Error):
    def __init__(self, name: str, reason: t.Optional = None):
        super().__init__(name)
        self.reason = reason


class LoadSchemaError(SchemaError):
    def __str__(self):
        return 'Ошибка при загрузке схемы {}'.format(self.name)


class ValidateSchemaError(SchemaError):
    def __str__(self):
        return 'Ошибка при проверке схемы {}'.format(self.name)


class LoadTableError(TableError):
    def __str__(self):
        msg = 'Ошибка при загрузке таблицы {}'.format(self.name)
        if self.reason:
            msg += f': {self.reason}'
        return msg


class ValidateTableError(TableError):
    def __str__(self):
        return 'Ошибка при проверке таблицы {}: {}'.format(self.name, self.reason)


class SaveTableError(TableError):
    def __str__(self):
        msg = 'Ошибка при сохранении таблицы {}'.format(self.name)
        if self.reason:
            msg += f': {self.reason}'
        return msg


def br_from(er: int) -> float:
    """
    Вычисление боевого рейтинга по экономическому рангу.

    :param er: Экономический ранг
    :return: Боевой рейтинг
    """

    return round(er / 3.0 + 1, 1)


def er_from(br: float) -> int:
    """
    Вычисление экономического ранга по боевому рейтингу.

    :param br: Боевой рейтинг
    :return: Экономический ранг
    """
    return int(round((br - 1) * 3, 0))


schemas_root = here / 'schema'


class SectionTransformer(cb.Validator):
    def __init__(self, *args, **kwargs):
        kwargs['purge_unknown'] = True
        super().__init__(*args, **kwargs)

    def _normalize_coerce_int(self, value: str) -> int:
        return int(value)

    def _normalize_coerce_fst(self, values: t.Sequence[T]) -> T:
        return values[0]

    def _normalize_coerce_rm_hidden(self, mm: t.MutableMapping[str, t.Any]):
        to_remove = set(k for k in mm.keys() if k.startswith('__'))
        for k in to_remove:
            del mm[k]
        return mm


class TableTransformer(cb.Validator):
    def _normalize_coerce_int(self, value: str) -> int:
        return int(value)


def new_tables(names: t.Iterable[str]) -> TablesT:
    tables = {}
    for name in names:
        tables[name] = {}
    return tables


def clear_tables(tables: TablesT, names: t.Iterable[str]):
    for name in names:
        tables[name].clear()


WRPLCliFile = ct.Struct(
    'header' / Header,
    ct.Seek(this.header.rez_offset),
    'rez' / Fat,
)


class ReplaysDb:
    tables_names = ('replays', 'users', 'units')

    def __init__(self, *, replays_path: t.Optional[Path] = None, db_path: t.Optional[Path] = None):
        self.tables = new_tables(self.tables_names)
        self.replays_path = replays_path
        self.db_path = db_path

    def _load_table(self, db_path: Path, name: str) -> TableT:
        table_path = db_path / f'{name}.json'

        try:
            with open(table_path, encoding='utf8') as istream:
                table = json.load(istream)
        except (OSError, json.JSONDecodeError) as e:
            raise LoadTableError(name) from e

        return table

    @staticmethod
    def _validated(table: TableT, name: str) -> TableT:
        schema_path = schemas_root / f'{name}.json'

        try:
            with open(schema_path) as istream:
                schema = json.load(istream)
        except (OSError, json.JSONDecodeError) as e:
            raise LoadSchemaError(name) from e

        try:
            transformer = TableTransformer(schema)
        except cb.SchemaError as e:
            raise ValidateSchemaError(name) from e

        if not transformer({'_': table}):
            raise ValidateTableError(name, transformer.errors)

        return transformer.document['_']

    def load(self, db_path: t.Optional[Path] = None):
        """
        Загрузка и проверка таблиц из дампа.

        :param db_path: Директория с таблицами.
        :raise ValueError: нет db_path или self.db_path
        :raise LoadTableError from exc:
        :raise LoadSchemaError from exc: для разработчика
        :raise ValidateSchemaError from exc: для разработчика
        :raise ValidateTableError from exc:
        """

        if db_path is None:
            db_path = self.db_path

        if db_path is None:
            raise ValueError('не заданы db_path или self.db_path')

        for name in self.tables_names:
            table = self._load_table(db_path, name)
            self.tables[name] = self._validated(table, name)

    def _save_table(self, db_path: Path, name: str):
        table_path = db_path / f'{name}.json'
        table = self.tables[name]

        try:
            with open(table_path, 'w', encoding='utf8') as ostream:
                json.dump(table, ostream, indent=2)
        except OSError as e:
            raise SaveTableError(name) from e

    def save(self, db_path: t.Optional[Path] = None):
        """
        Сохранение таблиц.

        :param db_path: Директория с таблицами.
        :raise SaveTableError from exc:
        """

        if db_path is None:
            db_path = self.db_path

        if db_path is None:
            raise ValueError('не заданы db_path или self.db_path')

        try:
            db_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise SaveTableError('*') from e

        for name in self.tables_names:
            self._save_table(db_path, name)

    @staticmethod
    def _split_map(doc) -> ReplayTablesT:
        pi = doc['uiScriptsData']['playersInfo']
        info = {}
        users = {}
        units = {}
        for data in pi.values():
            pid = data['id']
            users[pid] = data['name']  # только последний ник при переименовании
            for m in data['crafts_info'].values():
                name = m['name']
                if name not in units:
                    units[name] = {
                        'rank': m['mrank'],  # экономический ранг
                        'tier': m['rank']  # ступень
                    }
            info[pid] = {
                'team': data['team'],
                'rank': data['rank'],
                'units': [m['name'] for m in data['crafts_info'].values()]
            }
        return {'info': info, 'users': users, 'units': units}

    def clear(self):
        """
        Очистка таблиц.
        """

        clear_tables(self.tables, self.tables_names)

    def _update(self, tables: TablesT):
        for name in self.tables_names:
            self.tables[name].update(tables[name])

    @staticmethod
    def _from_replays(replays_path: Path, sid_pred: t.Callable[[int], bool] = None) -> TablesT:
        section_schema_path = schemas_root / 'section.json'

        try:
            with open(section_schema_path) as istream:
                section_schema = json.load(istream)
        except (OSError, json.JSONDecodeError) as e:
            raise LoadSchemaError('section') from e

        try:
            section_transformer = SectionTransformer(section_schema)
        except cb.SchemaError as e:
            raise ValidateSchemaError('section') from e

        tables = new_tables(ReplaysDb.tables_names)
        users = tables['users']
        units = tables['units']
        replays = tables['replays']

        for replay_path in replays_path.glob('*.wrpl'):
            try:
                if sid_pred is None:
                    wrpl = WRPLCliFile.parse_file(replay_path)
                else:
                    header = Header.parse_file(replay_path)
                    if sid_pred(header.session_id):
                        wrpl = WRPLCliFile.parse_file(replay_path)
                    else:
                        continue
            except Exception as e:
                print('SKIP {}: {}'.format(replay_path, e), file=sys.stderr)
                continue

            if wrpl.header.session_type != SessionType.RANDOM_BATTLE:
                continue

            if not section_transformer(wrpl.rez):
                raise ValidateTableError('section', section_transformer.errors)

            m = ReplaysDb._split_map(section_transformer.document)
            session_id = wrpl.header.session_id

            replays[session_id] = {
                'difficulty': wrpl.header.difficulty.value,
                'start_time':  wrpl.header.start_time,
                'info': m['info'],
            }
            users.update(m['users'])
            units.update(m['units'])

        return tables

    def update_from_replays(self, *, replays_path: t.Optional[Path] = None, sid_pred: t.Callable[[int], bool] = None):
        """
        Создание таблиц по директории с повторами и их слияние с self.tables.

        :param replays_path: Директория с повторами.
        :param sid_pred: предикат от sid для загружаемых таблиц.
        :raise ValueError: нет replays_path или db.replays_path
        :raise LoadSchemaError from exc: для разработчика
        :raise ValidateSchemaError from exc: для разработчика
        :raise ValidateTableError: для разработчика
        """

        if replays_path is None:
            replays_path = self.replays_path

        if replays_path is None:
            raise ValueError('не заданы replays_path или db.replays_path')

        tables = ReplaysDb._from_replays(replays_path, sid_pred)
        self._update(tables)

    def summary(self) -> str:
        """
        Краткая сводка по таблицам.

        :return: строка {имя таблицы => число элементов 1-го уровня таблицы}.
        """

        return '\n'.join(f'len {name} = {len(self.tables[name])}' for name in self.tables_names)
