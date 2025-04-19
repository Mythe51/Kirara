from datetime import datetime
from typing import Optional, Dict, List
import json
from .database_manager import DatabaseManager, TableDefinition

class GroupDatabase:
    def __init__(self):
        self.db = DatabaseManager()
        self._register_tables()

    def _register_tables(self):
        self.db.register_table(
            TableDefinition(
                name="group_info",
                create_sql="""CREATE TABLE group_info (
                    group_id TEXT PRIMARY KEY,
                    cdkey TEXT,
                    days INTEGER,
                    expires TIMESTAMP,
                    authed_at TIMESTAMP,
                    plugins TEXT
                )""",
                migrations=[]
            )
        )

    async def initialize(self):
        await self.db.initialize()

    # 插件状态管理
    async def update_group_plugins(self, group_id: str, plugins: Dict[str, bool]):
        plugins_json = json.dumps(plugins)
        await self.db.execute_write(
            """INSERT INTO group_info (group_id, plugins)
            VALUES (?, ?)
            ON CONFLICT(group_id) DO UPDATE SET
                plugins = excluded.plugins""",
            (group_id, plugins_json)
        )

    async def get_group_plugins(self, group_id: str) -> Dict[str, bool]:
        result = await self.db.execute_query(
            "SELECT plugins FROM group_info WHERE group_id = ?",
            (group_id,)
        )
        return json.loads(result[0]["plugins"]) if result and result[0]["plugins"] else {}

    async def get_groups_by_plugin(self, plugin_name: str) -> List[str]:
        results = await self.db.execute_query(
            "SELECT group_id FROM group_info WHERE json_extract(plugins, ?) = 1",
            (f"$.{plugin_name}",)
        )
        return [row["group_id"] for row in results]

    async def get_all_plugin_states(self) -> Dict[str, Dict[str, bool]]:
        results = await self.db.execute_query(
            "SELECT group_id, plugins FROM group_info"
        )
        return {
            row["group_id"]: json.loads(row["plugins"])
            for row in results if row["plugins"]
        }

    # 群信息管理
    async def create_group_info(self, group_id: str,
                              cdkey: Optional[str] = None,
                              days: Optional[int] = None,
                              expires: Optional[datetime] = None,
                              plugins: Optional[Dict[str, bool]] = None):
        plugins_json = json.dumps(plugins) if plugins else None
        await self.db.execute_write(
            """INSERT INTO group_info VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(group_id) DO UPDATE SET
                cdkey = excluded.cdkey,
                days = excluded.days,
                expires = excluded.expires,
                authed_at = excluded.authed_at,
                plugins = excluded.plugins""",
            (group_id, cdkey, days, expires, None, plugins_json)
        )

    async def get_group_info(self, group_id: str) -> Optional[dict]:
        result = await self.db.execute_query(
            """SELECT g.*, c.expires as cdkey_expires 
            FROM group_info g
            LEFT JOIN cdkey c ON g.cdkey = c.cdkey
            WHERE g.group_id = ?""",
            (group_id,)
        )
        if result:
            data = dict(result[0])
            if data.get("plugins"):
                data["plugins"] = json.loads(data["plugins"])
            return data
        return None

    async def set_group_auth(self, group_id: str, cdkey: str, days: int, expires: Optional[datetime] = None):
        await self.db.execute_write(
            """INSERT INTO group_info (group_id, cdkey, days, expires, authed_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(group_id) DO UPDATE SET
                cdkey = excluded.cdkey,
                days = excluded.days,
                expires = excluded.expires""",
            (group_id, cdkey, days, expires, datetime.now())
        )

    async def update_group_expiry(self, group_id: str, new_expires: datetime):
        await self.db.execute_write(
            "UPDATE group_info SET expires = ? WHERE group_id = ?",
            (new_expires, group_id)
        )

    async def get_expiring_groups(self, days: int = 3) -> list:
        return await self.db.execute_query(
            """SELECT * FROM group_info 
            WHERE expires BETWEEN datetime('now') AND datetime('now', ? || ' days')
            ORDER BY expires ASC""",
            (f"+{days}",)
        )

    async def is_group_authed(self, group_id: str) -> bool:
        group_info = await self.get_group_info(group_id)
        if not group_info or not group_info.get("expires"):
            return False
        return datetime.fromisoformat(group_info["expires"]) > datetime.now()

    # 新增方法：检查插件是否在群中启用
    async def is_plugin_enabled(self, group_id: str, plugin_name: str) -> bool:
        plugins = await self.get_group_plugins(group_id)
        return plugins.get(plugin_name, False)

    # 新增方法：设置插件在群中的启用状态
    async def set_plugin_enabled(self, group_id: str, plugin_name: str, enabled: bool):
        plugins = await self.get_group_plugins(group_id)
        plugins[plugin_name] = enabled
        await self.update_group_plugins(group_id, plugins)
