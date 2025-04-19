from nonebot import on_command, get_driver, Bot
from nonebot.adapters import Message
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.params import CommandArg
from nonebot import logger

from typing import List
from asyncio import sleep
from random import randint, random

from utils.qqdata import ApiGetGroupList

__plugin_meta__ = PluginMetadata(
    name="[kernel]群组广播",
    description="向所有群组发送广播消息",
    usage="（超级管理员、仅限私聊）!broadcast <消息内容>",
    type="application",
    config=None,
)

# 不在这里加权限控制的原因是如果权限不足需要提示用户
sv_broadcast = on_command(("!广播", "!broadcast"))

@sv_broadcast.handle()
async def _(bot: Bot, ev: PrivateMessageEvent, args: Message=CommandArg()):
    # 条件检查
    if ev.get_user_id() not in get_driver().config.superusers:
        await sv_broadcast.finish("权限不足")
    argline = args.extract_plain_text()
    if not argline:
        await sv_broadcast.finish("广播内容为空")

    group_list = await ApiGetGroupList(bot)
    group_num_list : List[int] = []
    for group in group_list:
        group_num_list.append(group.group_id)

    await sv_broadcast.send(f'开始推送')

    succeed = 0
    failed = 0
    for group in group_num_list:
        message = f"{argline}\n随机数防暴毙：{randint(100000, 999999)}"

        message_id = await bot.call_api('send_msg', group_id=group, message=message)
        if message_id:
            succeed += 1
            logger.info(f'向{group}推送消息成功')
        else:
            failed += 1
            logger.warning(f'向{group}推送消息失败')
            await sv_broadcast.send(f'向{group}推送消息失败')
        await sleep(random() * 5)

    await sv_broadcast.send(f'推送完成，共计向{len(group_num_list)}个群推送了消息\n成功{succeed}个\n失败{failed}个')
