from nonebot import on_fullmatch
from config import *

sv_about = on_fullmatch(("!关于", "!about"))

@sv_about.handle()
async def _():
    await sv_about.finish(f"""欢迎使用Kirara bot。
Code by mythe based on nonebot2。
内核版本：{ver_kernel}
插件包版本：{ver_plugin}""")
