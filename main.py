import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OnebotAdapter

import config
import traceback
import sys

# 初始化 NoneBot
nonebot.init()

# 注册适配器
driver = nonebot.get_driver()
driver.register_adapter(OnebotAdapter)

# 加载内置插件
nonebot.load_builtin_plugins("echo")

# 无条件加载核心插件
nonebot.load_plugins("kernel")

# 按照插件列表加载可选插件
for model in config.plugins:
    nonebot.load_plugin("plugins." + model)

if __name__ == "__main__":
    try:
        nonebot.run()
    except KeyboardInterrupt as e:
        # 正常退出，打印退出消息，结束
        nonebot.logger.info("Manual exit.")
    except Exception as e:
        # 异常退出，打印局部变量
        exc_type, exc_value, exc_traceback = sys.exc_info()
        locals_dict = locals()

        error_msg = f"""
Error occurred!
Type: {exc_type.__name__}
Message: {exc_value}
Traceback:
{traceback.format_exc()}
Locals:
        """.strip()
        for i, j in dict(locals_dict).items():
            if i in ["exc_type", "exc_value", "exc_traceback", "locals_dict", "error_msg", "e"]:
                continue
            error_msg += f"{i} = {j}\n"
        nonebot.logger.info(error_msg)
        nonebot.logger.info("Program exit")