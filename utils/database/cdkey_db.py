from datetime import datetime
from typing import Optional
from .database_manager import DatabaseManager, TableDefinition

class CDKeyDatabase:
    def __init__(self):
        self.db = DatabaseManager()
        self._register_tables()

    def _register_tables(self):
        self.db.register_table(
            TableDefinition(
                name="cdkey",
                create_sql="""CREATE TABLE cdkey (
                    cdkey TEXT PRIMARY KEY,
                    days INTEGER,
                    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires TIMESTAMP,
                    used BOOLEAN DEFAULT FALSE,
                    used_by TEXT,
                    used_at TIMESTAMP
                ) WITHOUT ROWID;""",
                migrations=[]
            )
        )

    async def initialize(self):
        await self.db.initialize()

    async def create_cdkey(self, cdkey: str, days: int,
                         created: datetime, expires: Optional[datetime],
                         used: bool = False, used_by: Optional[str] = None,
                         used_at: Optional[datetime] = None):
        await self.db.execute_write(
            """INSERT INTO cdkey VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cdkey) DO UPDATE SET
                days = excluded.days,
                expires = excluded.expires,
                used = excluded.used,
                used_by = excluded.used_by,
                used_at = excluded.used_at""",
            (cdkey, days, created, expires, used, used_by, used_at)
        )

    async def get_cdkey(self, cdkey: str) -> Optional[dict]:
        result = await self.db.execute_query(
            "SELECT * FROM cdkey WHERE cdkey = ?",
            (cdkey,)
        )
        return result[0] if result else None

    async def get_all_cdkeys(self) -> list:
        return await self.db.execute_query("SELECT * FROM cdkey ORDER BY created DESC")

    async def mark_cdkey_used(self, cdkey: str, group_id: str):
        await self.db.execute_write(
            """UPDATE cdkey SET 
                used = TRUE,
                used_by = ?,
                used_at = CURRENT_TIMESTAMP
                WHERE cdkey = ?""",
            (group_id, cdkey)
        )

    async def delete_cdkey(self, cdkey: str):
        await self.db.execute_write("DELETE FROM cdkey WHERE cdkey = ?", (cdkey,))
