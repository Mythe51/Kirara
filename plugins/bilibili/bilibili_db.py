import aiosqlite
import pathlib
import asyncio
import datetime

from dataclasses import dataclass
from typing import List

'''
gid: 群id，即群号
uid：订阅的UP主的id，即B站uid
last_update_video：上一次更新的视频BV号
last_update_time：上一次更新的时间
'''
db_subvideo_inital = """
CREATE TABLE IF NOT EXISTS bilibili_subvideo (
    gid TEXT,
    uid TEXT,
    last_update_video TEXT,
    last_update_time TIMESTAMP
);
"""

'''
gid: 群id，即群号
uid：订阅的UP主的id，即B站uid
last_update_dynamic：上一次更新的动态id
last_update_time：上一次更新的时间
'''
db_subdynamic_inital = """
CREATE TABLE IF NOT EXISTS bilibili_subdynamic (
    gid TEXT,
    uid TEXT,
    last_update_dynamic TEXT,
    last_update_time TIMESTAMP
);
"""

db_sublive_inital = """
CREATE TABLE IF NOT EXISTS bilibili_sublive (
    gid TEXT,
    uid TEXT,
    rid TEXT,
    status BOOLEAN,
    last_update_time TIMESTAMP
);
"""

@dataclass
class SubVideoInfo:
    gid: str
    uid: str
    last_update_video: str
    last_update_time: str

    def __str__(self):
        return f"gid: {self.gid}, uid: {self.uid}, last_update_video: {self.last_update_video}, last_update_time: {self.last_update_time}"

    def __init__(self, gid, uid, last_update_video, last_update_time):
        self.gid = gid
        self.uid = uid
        self.last_update_video = last_update_video
        self.last_update_time = last_update_time

@dataclass
class SubDynamicInfo:
    gid: str
    uid: str
    last_update_dynamic: str
    last_update_time: str

    def __str__(self):
        return f"gid: {self.gid}, uid: {self.uid}, last_update_dynamic: {self.last_update_dynamic}, last_update_time: {self.last_update_time}"

    def __init__(self, gid, uid, last_update_dynamic, last_update_time):
        self.gid = gid
        self.uid = uid
        self.last_update_dynamic = last_update_dynamic
        self.last_update_time = last_update_time

@dataclass
class SubLiveInfo:
    gid: str
    uid: str
    rid: str
    status: bool
    last_update_time: str

    def __str__(self):
        return f"gid: {self.gid}, uid: {self.uid}, rid: {self.rid}, status: {self.status}, last_update_time: {self.last_update_time}"

    def __init__(self, gid, uid, rid, status, last_update_time):
        self.gid = gid
        self.uid = uid
        self.rid = rid
        self.status = status
        self.last_update_time = last_update_time

class bDatabase:

    def __init__(self, db_path = ""):
        if db_path != "":
            self.db_path = db_path
        else:
            self.db_path = pathlib.Path(__file__).parent / "bilibili_db.db"

    async def init_database(self):
        await self._init_db()

    async def _init_db(self):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.executescript(db_subvideo_inital)
            await conn.executescript(db_subdynamic_inital)
            await conn.executescript(db_sublive_inital)

    async def sub_add_video(self, gid, uid):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("INSERT INTO bilibili_subvideo (gid, uid) VALUES (?, ?)",
                               (gid, uid))
            await conn.commit()

    async def sub_remove_video(self, gid, uid):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("DELETE FROM bilibili_subvideo WHERE gid = ? AND uid = ?",
                               (gid, uid))
            await conn.commit()

    async def sub_add_dynamic(self, gid, uid):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("INSERT INTO bilibili_subdynamic (gid, uid) VALUES (?, ?)",
                               (gid, uid))
            await conn.commit()

    async def sub_remove_dynamic(self, gid, uid):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("DELETE FROM bilibili_subdynamic WHERE gid = ? AND uid = ?",
                               (gid, uid))
            await conn.commit()

    async def sub_add_live(self, gid, uid, rid):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("INSERT INTO bilibili_sublive (gid, uid, rid) VALUES (?, ?, ?)",
                               (gid, uid, rid))
            await conn.commit()

    async def sub_remove_live(self, gid, uid, rid):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("DELETE FROM bilibili_sublive WHERE gid = ? AND uid = ? AND rid = ?",
                               (gid, uid, rid))
            await conn.commit()

    async def sub_get_video_group(self, gid) -> list[SubVideoInfo]:
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("SELECT * FROM bilibili_subvideo WHERE gid = ?", (gid,))
            rows = await cursor.fetchall()
            return [SubVideoInfo(*row) for row in rows]

    async def sub_get_video_all(self) -> list[SubVideoInfo]:
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("SELECT * FROM bilibili_subvideo")
            rows = await cursor.fetchall()
            return [SubVideoInfo(*row) for row in rows]

    async def sub_get_dynamic_group(self, gid) -> list[SubDynamicInfo]:
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("SELECT * FROM bilibili_subdynamic WHERE gid = ?", (gid,))
            rows = await cursor.fetchall()
            return [SubDynamicInfo(*row) for row in rows]

    async def sub_get_dynamic_all(self) -> list[SubDynamicInfo]:
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("SELECT * FROM bilibili_subdynamic")
            rows = await cursor.fetchall()
            return [SubDynamicInfo(*row) for row in rows]

    async def sub_get_live_group(self, gid) -> list[SubLiveInfo]:
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("SELECT * FROM bilibili_sublive WHERE gid = ?", (gid,))
            rows = await cursor.fetchall()
            return [SubLiveInfo(*row) for row in rows]

    async def sub_get_live_all(self) -> list[SubLiveInfo]:
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("SELECT * FROM bilibili_sublive")
            rows = await cursor.fetchall()
            return [SubLiveInfo(*row) for row in rows]

    async def sub_set_video_last(self, gid, uid, video_id):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("UPDATE bilibili_subvideo SET last_update_time = CURRENT_TIMESTAMP, last_update_video = ? WHERE gid = ? AND uid = ?",
                               (video_id, gid, uid))
            await conn.commit()

    async def sub_set_dynamic_last(self, gid, uid, dynamic_id):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("UPDATE bilibili_subdynamic SET last_update_time = CURRENT_TIMESTAMP, last_update_dynamic = ? WHERE gid = ? AND uid = ?",
                               (dynamic_id, gid, uid))
            await conn.commit()

    async def sub_set_live_last(self, gid, uid, room_id, status):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("UPDATE bilibili_sublive SET last_update_time = CURRENT_TIMESTAMP, status = ? WHERE gid = ? AND uid = ? AND rid = ?",
                               (status, gid, uid, room_id))
            await conn.commit()



if __name__ == '__main__':
    db = bDatabase()
    asyncio.run(db.init_database())
    asyncio.run(db.sub_set_live_last("123", "456", "789", True))
    data = asyncio.run(db.sub_get_live_all())
    print(data)
