import aiosqlite
from contextlib import asynccontextmanager
from typing import List, AsyncIterator
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TableDefinition:
    name: str
    create_sql: str
    migrations: List[str] = None  # 版本迁移SQL（按版本顺序排列）


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class DatabaseManager(metaclass=Singleton):
    def __init__(self, db_path: str = Path(__file__).parent.parent.parent / "data" / "base_data.db"):
        self.db_path = db_path
        self._tables: List[TableDefinition] = []

    def register_table(self, table_def: TableDefinition):
        self._tables.append(table_def)
        return self  # 支持链式调用

    async def initialize(self):
        """初始化数据库（建表）"""
        async with self.connect() as conn:
            # 创建迁移记录表
            await conn.execute('''CREATE TABLE IF NOT EXISTS __migrations (
                table_name TEXT PRIMARY KEY,
                version INTEGER NOT NULL DEFAULT 0
            )''')

            # 初始化所有注册表
            for table_def in self._tables:
                await self._init_table(conn, table_def)

            await conn.commit()

    async def _init_table(self, conn: aiosqlite.Connection, table_def: TableDefinition):
        """初始化单个表结构"""
        # 检查表是否存在
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_def.name,)
        )
        exists = await cursor.fetchone()

        if not exists:  # 全新表
            await conn.execute(table_def.create_sql)
            await self._update_migration_version(conn, table_def.name, 0)
        else:
            current_version = await self._get_migration_version(conn, table_def.name)
            await self._apply_migrations(conn, table_def, current_version)

    async def _apply_migrations(self, conn: aiosqlite.Connection,
                                table_def: TableDefinition, current_version: int):
        """安全执行表迁移"""
        if not table_def.migrations:
            return

        target_version = len(table_def.migrations)

        # 添加重试机制和列存在检查
        for ver in range(current_version, target_version):
            migration_sql = table_def.migrations[ver]

            # 自动处理添加列的情况
            if "ADD COLUMN" in migration_sql.upper():
                column_name = migration_sql.split()[3]
                if await self._column_exists(conn, table_def.name, column_name):
                    continue  # 跳过已存在的列

            try:
                await conn.execute(migration_sql)
                await self._update_migration_version(conn, table_def.name, ver + 1)
            except aiosqlite.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    await self._update_migration_version(conn, table_def.name, ver + 1)
                    continue
                raise

    async def _column_exists(self, conn: aiosqlite.Connection, table: str, column: str) -> bool:
        """检查列是否存在"""
        cursor = await conn.execute(f"PRAGMA table_info({table})")
        columns = await cursor.fetchall()
        return any(col["name"] == column for col in columns)

    async def _get_migration_version(self, conn: aiosqlite.Connection, table_name: str) -> int:
        """获取当前迁移版本"""
        cursor = await conn.execute(
            "SELECT version FROM __migrations WHERE table_name = ?",
            (table_name,)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0

    async def _update_migration_version(self, conn: aiosqlite.Connection,
                                        table_name: str, version: int):
        """更新迁移版本"""
        await conn.execute(
            "INSERT OR REPLACE INTO __migrations (table_name, version) VALUES (?, ?)",
            (table_name, version)
        )

    # 连接管理
    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        """获取异步数据库连接"""
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row  # 添加这行
        try:
            yield conn
        finally:
            await conn.close()

    # 基础CRUD操作
    async def execute_query(self, sql: str, params: tuple = None) -> List[dict]:
        """通用查询方法"""
        async with self.connect() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(sql, params or ())
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def execute_write(self, sql: str, params: tuple = None):
        """通用写入方法"""
        async with self.connect() as conn:
            await conn.execute(sql, params or ())
            await conn.commit()
