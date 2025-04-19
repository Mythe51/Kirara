import json
from pathlib import Path

from nonebot import on_command, on_notice, on_request, on_message, logger, get_driver, Bot
from nonebot.adapters import Event
from nonebot.rule import to_me
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent

CONFIG_PATH = Path(__file__).parent / "debug_config.json"

DEFAULT_CONFIG = {
    "enabled": False,
    "monitored_events": [],
    "monitored_groups": [],
}


def load_config() -> dict:
    """加载配置文件"""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return DEFAULT_CONFIG.copy()
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """保存配置文件"""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存配置文件失败: {e}")


config = load_config()

__plugin_meta__ = PluginMetadata(
    name="[kernel]调试监视器",
    description="提供事件监视和调试功能，可配置监控特定事件类型和群组",
    usage='''
指令列表:
（超级管理员，仅限私聊）!debug on - 开启事件监视
（超级管理员，仅限私聊）!debug off - 关闭事件监视
（超级管理员，仅限私聊）!debug add [事件类型] - 添加监视事件类型
（超级管理员，仅限私聊）!debug remove [事件类型] - 移除监视事件类型
（超级管理员，仅限私聊）!debug group add [群号] - 添加监视群聊
（超级管理员，仅限私聊）!debug group remove [群号] - 移除监视群聊
（超级管理员，仅限私聊）!debug list - 显示当前配置状态
    '''.strip(),
    type="application",
    config=None
)

ev_debug = on_command(("!debug", ), priority=5, block=True, rule=to_me(), permission=SUPERUSER)

@ev_debug.handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    global config

    args = args.extract_plain_text().strip().split()
    if not args:
        await matcher.finish(__plugin_meta__.usage)

    cmd = args[0].lower()

    if cmd == "on":
        config["enabled"] = True
        save_config(config)
        await matcher.finish("事件监视已开启")
    elif cmd == "off":
        config["enabled"] = False
        save_config(config)
        await matcher.finish("事件监视已关闭")
    elif cmd == "add" and len(args) > 1:
        event_type = args[1]
        if event_type not in config["monitored_events"]:
            config["monitored_events"].append(event_type)
            save_config(config)
            await matcher.finish(f"已添加监视事件类型: {event_type}")
        else:
            await matcher.finish(f"事件类型已存在: {event_type}")
    elif cmd == "remove" and len(args) > 1:
        event_type = args[1]
        if event_type in config["monitored_events"]:
            config["monitored_events"].remove(event_type)
            save_config(config)
            await matcher.finish(f"已移除监视事件类型: {event_type}")
        else:
            await matcher.finish(f"未找到事件类型: {event_type}")
    elif cmd == "group":
        if len(args) < 3:
            await matcher.finish("参数不足，请指定 add/remove 和群号")
        sub_cmd = args[1]
        group_id = args[2]
        if sub_cmd == "add":
            if group_id not in config["monitored_groups"]:
                config["monitored_groups"].append(group_id)
                save_config(config)
                await matcher.finish(f"已添加监视群聊: {group_id}")
            else:
                await matcher.finish(f"群聊已存在: {group_id}")
        elif sub_cmd == "remove":
            if group_id in config["monitored_groups"]:
                config["monitored_groups"].remove(group_id)
                save_config(config)
                await matcher.finish(f"已移除监视群聊: {group_id}")
            else:
                await matcher.finish(f"未找到群聊: {group_id}")
    elif cmd == "list":
        enabled = "开启" if config["enabled"] else "关闭"
        events = "\n".join(config["monitored_events"]) or "无"
        groups = "\n".join(config["monitored_groups"]) or "无"
        await matcher.finish(
            f"当前监视配置:\n"
            f"状态: {enabled}\n"
            f"监视的事件类型:\n{events}\n"
            f"监视的群聊:\n{groups}"
        )
    else:
        await matcher.finish(__plugin_meta__.usage)


async def log_event(event: Event):
    if not config["enabled"]:
        return

    # 检查事件类型
    event_type = event.get_type()
    logger.info(event_type)
    if config["monitored_events"] and event_type not in config["monitored_events"]:
        return

    # 如果是群消息事件，检查群号
    if isinstance(event, GroupMessageEvent):
        group_id = str(event.group_id)
        if config["monitored_groups"] and group_id not in config["monitored_groups"]:
            return

    # 输出事件信息到控制台
    logger.info("=" * 20)
    logger.info(f"事件类型: {event_type}")
    logger.info(f"事件内容: {event.model_dump_json()}")
    logger.info("=" * 20)


driver = get_driver()
@driver.on_bot_connect
async def start_notify(bot: Bot):
    superuser = driver.config.superusers
    superuser = list(superuser)[0]
    await bot.call_api('send_msg', user_id=superuser, message="提示：bot上线")


# 这里执行不到
@driver.on_bot_disconnect
async def start_notify(bot: Bot):
    superuser = driver.config.superusers
    superuser = list(superuser)[0]
    try:
        await bot.call_api('send_msg', user_id=superuser, message="提示：bot下线")
    except Exception as e:
        logger.warning(str(e))


on_message(priority=1, block=False).append_handler(log_event)
on_notice(priority=1, block=False).append_handler(log_event)
on_request(priority=1, block=False).append_handler(log_event)
