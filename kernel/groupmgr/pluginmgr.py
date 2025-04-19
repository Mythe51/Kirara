'''
这个模块负责控制用户插件的使用，具体功能如下
1. 在群聊中，超级管理员可以使用命令控制某个用户插件在这个群的开启和关闭，所有人都可以使用命令查看本群开启了哪些用户插件
2. 在私聊中，超级管理员可以使用命令控制某个用户插件在某个群的开启和关闭，并且可以使用命令查看所有用户插件在所有群的开启情况
3. 除非用户插件中设置了某个特定值，否则这个插件默认在所有群都是关闭状态
4. 这个模块依据两个指标判断用户插件是否被执行，一是群是否授权，二是用户插件在这个群是否开启
'''
from nonebot import on_command, get_driver, logger
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata, get_loaded_plugins, Plugin
from nonebot.message import run_preprocessor
from nonebot.exception import MatcherException, IgnoredException

from typing import List

import config
from utils.qqdata import ApiGetGroupList
from utils.database.group_db import GroupDatabase

# 初始化数据库
group_db = GroupDatabase()
driver = get_driver()


@driver.on_startup
async def _():
    await group_db.initialize()


__plugin_meta__ = PluginMetadata(
    name="[kernel]插件管理器",
    description="管理插件在群组的启用状态",
    usage='''
!plugin enable <插件名> - 启用本群插件
!plugin disable <插件名> - 禁用本群插件
!plugin list - 查看本群插件状态
'''.strip(),
    type="application",
    extra={}
)

plugin_matcher = on_command("!plugin", priority=5, block=True)


# 获取插件元数据，元数据不存在则使用默认元数据
def get_plugin_metadata(plugin: Plugin) -> PluginMetadata:
    try:
        if hasattr(plugin, "metadata") and plugin.metadata:
            return plugin.metadata
        else:
            return PluginMetadata(plugin.name, "", "", extra={"default_enabled": False})
    except:
        return PluginMetadata(plugin.name, "", "", extra={"default_enabled": False})


@plugin_matcher.handle()
async def handle_plugin(
        matcher: Matcher,
        event: GroupMessageEvent,
        args: Message = CommandArg()
):
    # 权限验证
    is_superuser = str(event.user_id) in get_driver().config.superusers

    cmd_args = args.extract_plain_text().strip().split()
    if not cmd_args:
        await matcher.finish(__plugin_meta__.usage)

    operation = cmd_args[0].lower()
    plugin_name = cmd_args[1] if len(cmd_args) > 1 else None

    try:
        group_id = str(event.group_id)

        if operation == "enable" and plugin_name:       # 启用
            if not is_superuser:
                await matcher.finish("权限不足")
            await toggle_plugin(matcher, plugin_name, group_id, True)
        elif operation == "disable" and plugin_name:    # 禁用
            if not is_superuser:
                await matcher.finish("权限不足")
            await toggle_plugin(matcher, plugin_name, group_id, False)
        elif operation == "list":                       # 列出
            plugins = await group_db.get_group_plugins(group_id)
            data: List[str] = []
            for name, state in plugins.items():
                data.append(f"|O| {name}" if state else f"|X| {name}")
            msg = [
                f"群 {group_id} 插件状态:",
                ("\n  ".join(data) if data else "无"),
            ]
            await matcher.finish("\n".join(msg))
        else:
            await matcher.finish(__plugin_meta__.usage)

    except MatcherException:
        raise
    except Exception as e:
        logger.error(f"插件管理失败: {str(e)}")
        await matcher.finish("操作失败，请检查日志")


# 切换插件状态
async def toggle_plugin(
        matcher: Matcher,
        plugin_name: str,
        group_id: str,
        enable: bool
):
    # 验证插件存在
    plugin = next((p for p in get_loaded_plugins() if p.name == plugin_name), None)
    if not plugin:
        await matcher.finish(f"未找到插件: {plugin_name}")

    # 验证群存在
    if not await group_db.is_group_authed(group_id):
        await matcher.finish(f"群 {group_id} 未授权或授权已过期")

    # 更新数据库
    await group_db.set_plugin_enabled(group_id, plugin_name, enable)
    action = "启用" if enable else "禁用"
    await matcher.finish(f"已{action}插件 [{plugin_name}] 在群 {group_id}")



# 插件可用性检查
@driver.on_bot_connect
async def init_pluginmgr(bot: Bot):


    # 检查所有插件是否都存在于数据库，不存在的补上
    user_plugins_config = config.plugins
    user_plugins_loaded: List[Plugin] = []
    for plugin in get_loaded_plugins():
        if plugin.name in user_plugins_config:
            user_plugins_loaded.append(plugin)

    groups = await ApiGetGroupList(bot)
    for group in groups:
        user_plugins_database = await group_db.get_group_plugins(str(group.group_id))
        for plugin in user_plugins_loaded:
            if plugin.name not in user_plugins_database.keys():
                meta = get_plugin_metadata(plugin)
                enabled = meta.extra.get("default_enabled", False)
                await group_db.set_plugin_enabled(str(group.group_id), plugin.name, enabled)

@run_preprocessor
async def check_plugin_availability(event: Event, matcher: Matcher):
    if not isinstance(event, GroupMessageEvent):
        return

    try:
        current_plugin = matcher.plugin
        group_id = str(event.group_id)

        # 核心功能无条件启用
        if current_plugin.name not in config.plugins:
            logger.info(f"核心插件启用: {current_plugin.name} @ {group_id}")
            return

        # 先检查数据库中是否启用
        db_enabled = await group_db.is_plugin_enabled(group_id, current_plugin.name)
        if not db_enabled:
            logger.info(f"插件未启用，跳过: {current_plugin.name} @ {group_id}")
            raise IgnoredException("插件未启用")

        # 再检查是否授权使用
        is_authed = await group_db.is_group_authed(group_id)
        if not is_authed:
            logger.info(f"群未授权，跳过: {current_plugin.name} @ {group_id}")
            raise IgnoredException("群未授权")

        logger.info(f"消息处理: {current_plugin.name} @ {group_id}")
    except MatcherException:
        raise
    except IgnoredException:
        raise
    except Exception as e:
        logger.error(f"插件检查错误: {str(e)}")


