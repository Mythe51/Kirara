from nonebot import on_command, get_driver, on_fullmatch, logger
from nonebot.adapters import Message, Event
from nonebot.exception import FinishedException
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

import psutil
import os
import re
import platform

import asyncio


# 不在这里加权限控制的原因是如果权限不足需要提示用户
sv_cmd = on_command("!cmd")
sv_ping = on_fullmatch("!ping")
sv_srvstat = on_fullmatch("!srvstat")
sv_netstat = on_fullmatch("!netstat")
sv_restart = on_fullmatch("!restart")

__plugin_meta__ = PluginMetadata(
    name="[kernel]系统命令",
    description="提供系统命令执行、服务器状态查询等功能",
    usage="命令列表：\n"
          "（超级管理员）!cmd <命令> - 执行系统命令\n"
          "（超级管理员）!restart - 重启nonebot\n"
          "!ping - 测试服务器响应\n"
          "!srvstat - 查询服务器状态\n"
          "!netstat - 查询网络信息",
    type="application",
    config=None,
)

@sv_cmd.handle()
async def _(ev: Event, args: Message=CommandArg()):
    if ev.get_user_id() not in get_driver().config.superusers:
        await sv_cmd.finish("权限不足")
    cmd = args.extract_plain_text()
    if not cmd:
        await sv_cmd.finish("命令行为空")

    try:
        # 异步执行命令
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)

        logger.info(f"管理员 {ev.get_user_id()} 执行命令: {cmd}")
        if proc.returncode != 0:
            logger.warning(f"命令执行失败（返回码 {proc.returncode}）：\n{stderr.decode().strip()}")
            await sv_cmd.finish(f"命令执行失败（返回码 {proc.returncode}）：\n{stderr.decode().strip()}")
        else:
            logger.info("执行成功")
            await sv_cmd.finish("执行结果（返回前500个字符）：\n" + stdout.decode("gbk").strip()[:500])
    except asyncio.TimeoutError:
        proc.kill()
        logger.warning("执行超时")
        await sv_cmd.finish("命令执行超时")
    except Exception as e:
        if isinstance(e, FinishedException):
            raise e
        logger.warning(f"发生错误：{str(e)}")
        await sv_cmd.finish(f"发生错误：\n{str(e)}")

@sv_ping.handle()
async def _():
    await sv_ping.finish("pong!")


@sv_srvstat.handle()
async def _():
    try:
        await sv_srvstat.finish(f"{CpuInfo()}\n{MemInfo()}\n{DiskInfo()}")
    except Exception as e:
        if isinstance(e, FinishedException):
            raise e
        await sv_srvstat.finish(f"获取服务器状态失败: {str(e)}")


@sv_netstat.handle()
async def _():
    if platform.system() != "Windows":
        await sv_netstat.finish("此功能仅在Windows系统上可用")

    try:
        output = os.popen("ipconfig /all").read()
        ipv6_matches = re.findall(r"(([a-f0-9]{1,4}:){7}[a-f0-9]{1,4})", output, re.I)
        ipv4_matches = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", output)

        ipv6addr = ipv6_matches[0][0] if ipv6_matches else "未找到"
        ipv4addr = ipv4_matches[0] if ipv4_matches else "未找到"

        await sv_netstat.finish(
            f"本机的IPv4地址为：{ipv4addr}\n"
            f"IPv6地址为：{ipv6addr}\n\n"
            f"注：结果只反映当前服务器情况"
        )
    except Exception as e:
        if isinstance(e, FinishedException):
            raise e
        await sv_netstat.finish(f"获取网络信息失败: {str(e)}")

@sv_restart.handle()
async def _(ev: Event):
    if ev.get_user_id() not in get_driver().config.superusers:
        await sv_restart.finish("拒绝访问：您不是管理员")
    logger.info("执行操作：指令重启")
    await sv_restart.send("正在重启，请稍等")
    path = os.path.dirname(__file__)
    os.system(path + "\\restart.exe " + str(os.getpid()) + " main.py")

def MemInfo() -> str:
    try:
        memory = psutil.virtual_memory()
        total = round(memory.total / 1024.0 / 1024.0, 2)
        used = round(memory.used / 1024.0 / 1024.0, 2)
        free = round(memory.free / 1024.0 / 1024.0, 2)
        percent = memory.percent

        info = f'''
=== MemoryInfo ===
total memory: {total} MB;
used: {used} MB; free: {free} MB
usage: {percent}%
        '''.strip()
        return info
    except Exception as e:
        return f"获取内存信息失败: {str(e)}"


def CpuInfo() -> str:
    try:
        count = psutil.cpu_count(logical=False)
        usage = psutil.cpu_percent(interval=0.5, percpu=True)
        times = psutil.cpu_times_percent(percpu=False)

        info = f'''
=== CpuInfo ===
total core: {count};
usage(avg): {round(sum(usage) / len(usage), 2)}%
usage(per): {", ".join([str(i) + "%" for i in usage])}
[user: {times.user}%; system: {times.system}%; idle: {times.idle}%]
        '''.strip()
        return info
    except Exception as e:
        return f"获取CPU信息失败: {str(e)}"


def DiskInfo() -> str:
    try:
        disk = psutil.disk_usage("C:\\")
        info = f'''
=== DiskInfo ===
total: {round(disk.total / 1024 / 1024 / 1024, 2)} GB
used: {round(disk.used / 1024 / 1024 / 1024, 2)} GB
usage: {disk.percent}%
        '''.strip()
        return info
    except Exception as e:
        return f"获取磁盘信息失败: {str(e)}"