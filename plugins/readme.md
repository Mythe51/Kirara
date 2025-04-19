**这个文件存放用户插件**

出于设计模式的考虑，只可以使用这个文件夹下的代码调用框架代码
应当避免框架代码调用这个文件下的代码
应当避免本应属于这个文件夹下的代码跑到框架文件夹下

为了使用户插件能被正确识别，用户插件应当包含如下的头：
```python
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="插件名称，与文件夹名或文件名（单独文件的话）一致",
    description="插件描述",
    usage="插件使用方法，鼓励在插件内使用这个属性输出使用方法",
    type="application",
    extra={
        "default_enabled": True # 可以不填，默认False
    }
)
```

这个文件夹下插件的加载依赖于主文件夹的config.py
如果你希望你的插件被加载，请修改config.py中的plugins数组，使其包含你要加载的插件的文件夹名或文件名
