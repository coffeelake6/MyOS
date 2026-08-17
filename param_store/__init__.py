# param_store — MyOS 参数配置文件读写层（通用数据层）
#
# 职责：读取 / 修改 / 写回 yaml 参数文件，监控外部修改（QFileSystemWatcher）。
# 行级写回保留注释/格式/顺序。
#
# 每个功能模块（感知/建图/规划/...）各自创建 ParamStore，注入自己的
# 目录与映射表，变量名带模块前缀互不混淆：
#
#   感知模块：
#     from param_store import (ParamStore, PERCEPTION_CONFIG_DIR,
#                               perception_display_name_for,
#                               PERCEPTION_KEY_NAMES, PERCEPTION_GROUP_NAMES)
#     store = ParamStore(config_dir=PERCEPTION_CONFIG_DIR,
#                        display_name_fn=perception_display_name_for,
#                        key_names=PERCEPTION_KEY_NAMES,
#                        group_names=PERCEPTION_GROUP_NAMES)
#
#   后续接入建图模块时，仿照感知新增 MAPPING_CONFIG_DIR / MAPPING_KEY_NAMES...
#   并创建自己的 ParamStore 实例即可，与感知完全隔离。

from .store import (
    ParamStore,
    YamlFileStore,
    ParamValue,
    # ---- 感知模块专属常量 / 函数 ----
    PERCEPTION_CONFIG_DIR,
    PERCEPTION_FILE_DISPLAY_NAMES,
    PERCEPTION_KEY_NAMES,
    PERCEPTION_GROUP_NAMES,
    perception_display_name_for,
    # ---- 建图模块专属常量 / 函数 ----
    MAPPING_CONFIG_DIR,
    MAPPING_FILE_DISPLAY_NAMES,
    MAPPING_KEY_NAMES,
    MAPPING_GROUP_NAMES,
    mapping_display_name_for,
)

__all__ = [
    "ParamStore",
    "YamlFileStore",
    "ParamValue",
    "PERCEPTION_CONFIG_DIR",
    "PERCEPTION_FILE_DISPLAY_NAMES",
    "PERCEPTION_KEY_NAMES",
    "PERCEPTION_GROUP_NAMES",
    "perception_display_name_for",
    "MAPPING_CONFIG_DIR",
    "MAPPING_FILE_DISPLAY_NAMES",
    "MAPPING_KEY_NAMES",
    "MAPPING_GROUP_NAMES",
    "mapping_display_name_for",
]
