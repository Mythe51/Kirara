'''
插件名：bilibili
插件功能：
1. 实现短链接/小程序解析（视频、专栏、直播间）
2. 实现UP主的视频、动态、开播/下播订阅
3. 相关信息存储在数据库当中
'''

import bilibili_api

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="bilibili",
    description="哔哩哔哩插件，实现群内对bilibili UP主的订阅以及小程序解析",
    usage="指令："
          "!b订阅 添加 [uid] [vdl] - 订阅指定UP主，v代表video，d代表dynamic，l代表live，等价的英文指令为!bsub add"
          "!b订阅 删除 [uid] - 取消订阅指定的UP主，该UP主全部的订阅类型都将被取消，等价的英文指令为!bsub remove"
          "（被动）小程序/链接/短链接自动解析，支持视频、专栏、直播间"
          "注：感叹号为英文感叹号",
    type="application",
    extra={
        "default_enabled": False # 可以不填，默认False
    }
)

from nonebot import on_command, Bot
from nonebot.message import Event

sv_bsub = on_command(("!b订阅", "!bsub"), block=True)

@sv_bsub.handle
async def _(bot: Bot, ev: Event):
    args = ev.get_plaintext().strip().split()
    if not args or len(args) < 2:
        await sv_bsub.send("缺少必要参数")
        await sv_bsub.finish(__plugin_meta__.usage)

    if args[0] == "添加" or args[0] == "add":
        pass
    elif args[0] == "删除" or args[0] == "remove":
        pass
    else:
        await sv_bsub.send("未知参数：" + args[0])
        await sv_bsub.finish(__plugin_meta__.usage)


