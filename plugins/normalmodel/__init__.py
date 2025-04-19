from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="normalmodel",
    description="测试插件",
    usage='''
!test - 测试指令
'''.strip(),
    type="application",
    extra={
        "default_enabled": True
    }
)

svping = on_fullmatch("!test")

@svping.handle()
async def _():
    await svping.finish("pong!")