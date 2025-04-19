from datetime import datetime, timedelta
from nonebot import on_command, on_message, logger, get_driver, Bot
from nonebot.adapters import Event, Message
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    PrivateMessageEvent
)
from nonebot.plugin.model import PluginMetadata
from nonebot.rule import to_me
from nonebot.exception import FinishedException

from utils.database.group_db import GroupDatabase
from utils.database.cdkey_db import CDKeyDatabase
from utils.qqdata import ApiGetGroupList

__plugin_meta__ = PluginMetadata(
    name="[kernel]群授权管理",
    description="机器人群授权管理",
    usage="""
（超级管理员，仅限私聊）!cdkey create [天数] [数量] - 创建指定天数的CDKey
（超级管理员，仅限私聊）!cdkey list - 列出所有CDKey
（超级管理员，仅限私聊）!cdkey delete [CDKey] - 删除指定CDKey
（超级管理员，仅限私聊）!cdkey assign [群号] [CDKey] - 为指定群分配CDKey
（普通用户，群聊）!cdkey use [CDKey] - 使用CDKey激活群授权""",
    type="application",
    config=None,
)

# 初始化数据库
auth_db = GroupDatabase()
cdkey_db = CDKeyDatabase()
driver = get_driver()


@driver.on_bot_connect
async def _(bot: Bot):
    await auth_db.initialize()
    groups = await ApiGetGroupList(bot)
    for group in groups:
        # 如果已经在数据库中，则略过
        if await auth_db.get_group_info(group.group_id):
            continue
        await auth_db.create_group_info(group_id=group.group_id)
    logger.info("群信息表初始化完毕")


sv_cdkey_admin = on_command("!cdkey", permission=SUPERUSER, priority=5, block=True, rule=to_me())
sv_cdkey_use = on_command("!cdkey use", priority=5, block=True)
sv_auth_status = on_command("!authstatus", priority=5, block=True)


def generate_cdkey(length: int = 16) -> str:
    import random
    import string
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


async def is_cdkey_valid(cdkey: str) -> bool:
    record = await cdkey_db.get_cdkey(cdkey)
    if not record:
        return False
    if record["expires"] and datetime.fromisoformat(record["expires"]) < datetime.now():
        return False
    return True


async def is_group_authed(group_id: str) -> bool:
    auth = await auth_db.get_group_info(group_id)
    if not auth or not auth["expires"]:
        return False
    return datetime.fromisoformat(auth["expires"]) > datetime.now()


async def group_authed_days(group_id: str) -> int:
    auth = await auth_db.get_group_info(group_id)
    if not auth or not auth["expires"]:
        return 0
    expires = datetime.fromisoformat(auth["expires"])
    days = (expires - datetime.now()).days
    return max(days, 0)


@sv_auth_status.handle()
async def handle_auth_status(matcher: Matcher, event: GroupMessageEvent):
    group_id = str(event.group_id)
    days = await group_authed_days(group_id)

    if days > 0:
        auth = await auth_db.get_group_info(group_id)
        expire_time = datetime.fromisoformat(auth["expires"]).strftime("%Y-%m-%d")
        await matcher.finish(f"群{group_id}授权生效，剩余{days}天\n到期时间：{expire_time}")
    else:
        await matcher.finish(f"群{group_id}未授权或授权已到期")


@sv_cdkey_admin.handle()
async def handle_cdkey_admin(matcher: Matcher, event: PrivateMessageEvent, args: Message = CommandArg()):
    cmd = args.extract_plain_text().strip().split()
    if not cmd:
        await matcher.finish(__plugin_meta__.usage)

    sub_cmd = cmd[0].lower()

    try:
        if sub_cmd == "create" and len(cmd) >= 3:
            days = int(cmd[1])
            count = int(cmd[2])

            if days <= 0:
                await matcher.finish("天数必须大于0")

            new_cdkeys = []
            expires = datetime.now() + timedelta(days=30)

            for _ in range(count):
                cdkey = generate_cdkey()
                await cdkey_db.create_cdkey(
                    cdkey=cdkey,
                    days=days,
                    created=datetime.now(),
                    expires=expires,
                    used=False
                )
                new_cdkeys.append(cdkey)

            await matcher.finish(
                f"成功创建{count}个CDKey（有效期至{expires.strftime('%Y-%m-%d')}）：\n" + "\n".join(new_cdkeys))

        elif sub_cmd == "list":
            cdkeys = await cdkey_db.get_all_cdkeys()
            if not cdkeys:
                await matcher.finish("没有可用的CDKey")

            msg = ["CDKey列表:"]
            for record in cdkeys:
                status = "✅ 未使用" if not record["used"] else "❌ 已使用"
                expires = datetime.fromisoformat(record["expires"]).strftime("%Y-%m-%d")
                msg.append(
                    f"{record['cdkey']} - {record['days']}天 | {status}\n"
                    f"有效期至: {expires} | 创建于: {record['created'][:10]}"
                )
            await matcher.finish("\n\n".join(msg))

        elif sub_cmd == "delete" and len(cmd) >= 2:
            cdkey = cmd[1]
            if await cdkey_db.get_cdkey(cdkey):
                await cdkey_db.delete_cdkey(cdkey)
                await matcher.finish(f"已删除CDKey: {cdkey}")
            else:
                await matcher.finish(f"未找到CDKey: {cdkey}")

        elif sub_cmd == "assign" and len(cmd) >= 3:
            group_id = cmd[1]
            cdkey = cmd[2]

            if not await is_cdkey_valid(cdkey):
                await matcher.finish("CDKey无效或已过期")

            cdkey_data = await cdkey_db.get_cdkey(cdkey)
            if cdkey_data["used"]:
                await matcher.finish("该CDKey已被使用")

            days = cdkey_data["days"]
            current_auth = await auth_db.get_group_info(group_id)
            now = datetime.now()

            # 计算新有效期
            if current_auth and current_auth["expires"]:
                current_expires = datetime.fromisoformat(current_auth["expires"])
                new_expires = max(current_expires, now) + timedelta(days=days)
            else:
                new_expires = now + timedelta(days=days)

            # 更新数据库
            async with auth_db.db.connect() as conn:
                await auth_db.create_group_info(
                    group_id=group_id,
                    cdkey=cdkey,
                    days=days,
                    expires=new_expires
                )
                await cdkey_db.mark_cdkey_used(cdkey, group_id)
                await conn.commit()

            expire_str = new_expires.strftime("%Y-%m-%d")
            await matcher.finish(f"成功为群 {group_id} 分配CDKey\n新到期时间: {expire_str}")

        else:
            await matcher.finish(__plugin_meta__.usage)

    except Exception as e:
        if isinstance(e, FinishedException):
            raise e
        logger.error(f"操作失败: {str(e)}")
        await matcher.finish("操作失败，请检查日志")


@sv_cdkey_use.handle()
async def handle_cdkey_use(matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()):
    cdkey = args.extract_plain_text().strip()
    if not cdkey:
        await matcher.finish("请提供要使用的CDKey")

    group_id = str(event.group_id)

    if not await is_cdkey_valid(cdkey):
        await matcher.finish("CDKey无效或已过期")

    cdkey_data = await cdkey_db.get_cdkey(cdkey)
    if cdkey_data["used"]:
        await matcher.finish("该CDKey已被使用")

    days = cdkey_data["days"]
    current_auth = await auth_db.get_group_info(group_id)
    now = datetime.now()

    # 计算新有效期
    if current_auth and current_auth["expires"]:
        current_expires = datetime.fromisoformat(current_auth["expires"])
        new_expires = max(current_expires, now) + timedelta(days=days)
    else:
        new_expires = now + timedelta(days=days)

    # 更新数据库
    async with auth_db.db.connect() as conn:
        await auth_db.create_group_info(
            group_id=group_id,
            cdkey=cdkey,
            days=days,
            expires=new_expires
        )
        await cdkey_db.mark_cdkey_used(cdkey, group_id)
        await conn.commit()

    expire_str = new_expires.strftime("%Y-%m-%d")
    await matcher.finish(f"CDKey使用成功！\n新到期时间: {expire_str}")


