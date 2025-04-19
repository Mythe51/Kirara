from nonebot import Bot
from dataclasses import dataclass


@dataclass
class GroupInfo:
    group_id: int
    group_name: str
    member_count: int
    max_member_count: int

async def ApiGetGroupInfo(bot: Bot, group) -> GroupInfo:
    if not bot:
        raise Exception("bot为空，请检查传入参数")
    if isinstance(group, str):
        group = str(group)
    data = await bot.call_api("get_group_info", group_id=group)
    retdata = GroupInfo(
        data["group_id"],
        data["group_name"],
        data["member_count"],
        data["max_member_count"]
    )
    return retdata

async def ApiGetGroupList(bot: Bot) -> list[GroupInfo]:
    if not bot:
        raise Exception("bot为空，请检查传入参数")
    retdata = []
    groups = await bot.call_api("get_group_list")
    for group in groups:
        data = GroupInfo(
            group["group_id"],
            group["group_name"],
            group["member_count"],
            group["max_member_count"]
        )
        retdata.append(data)
    return retdata


@dataclass
class GroupMemberInfo:
    group_id: int           # 群号
    user_id: int            # QQ号
    nickname: str           # 昵称
    card: str               # 群名片、备注
    sex: str                # 性别，male/female/unknown
    age: int                # 年龄
    area: str               # 地区
    join_time: int          # 加群的时间戳
    last_sent_time: int     # 最后发言的时间戳
    level: str              # 成员等级
    role: str               # 成员角色，owner/admin/member
    title: str              # 专属头衔

async def ApiGetGroupMemberInfo(bot: Bot, group, user) -> GroupMemberInfo:
    if not bot:
        raise Exception("bot为空，请检查传入参数")
    if isinstance(group, str):
        group = str(group)
    if isinstance(user, str):
        user = str(user)
    data = await bot.call_api("get_group_member_info", group_id=group, user_id=user)
    retdata = GroupMemberInfo(
        data["group_id"],
        data["user_id"],
        data["nickname"],
        data["card"],
        data["sex"],
        data["age"],
        data["area"],
        data["join_time"],
        data["last_sent_time"],
        data["level"],
        data["role"],
        data["title"],
    )
    return retdata

async def ApiGetGroupMemberList(bot: Bot, group) -> list:
    if not bot:
        raise Exception("bot为空，请检查传入参数")
    if isinstance(group, str):
        group = str(group)
    members = await bot.call_api("get_group_member_list", group_id=group)
    retdata = []
    for member in members:
        info = await ApiGetGroupMemberInfo(bot, member["group_id"], member["user_id"])
        retdata.append(info)
    return retdata


@dataclass
class StrangerInfo:
    user_id: int
    nickname: str
    sex: str
    age: int

async def ApiGetStrangerInfo(bot: Bot, user) -> StrangerInfo:
    if not bot:
        raise Exception("bot为空，请检查传入参数")
    if isinstance(user, str):
        user = str(user)
    info = await bot.call_api("get_stranger_info", user_id=user)
    retdata = StrangerInfo(
        info["user_id"],
        info["nickname"],
        info["sex"],
        info["age"]
    )
    return retdata