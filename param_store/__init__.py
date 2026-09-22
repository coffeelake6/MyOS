# param_store — MyOS 参数配置文件读写层（通用数据层）
#
# 职责：读取 / 修改 / 写回 yaml 参数文件，监控外部修改（QFileSystemWatcher）。
# 行级写回保留注释/格式/顺序。
#
# 每个功能模块（感知/建图/规划/...）各自创建 ParamStore，注入自己的
# 目录与映射表，变量名带模块前缀互不混淆。
# 目录路径统一写在 config/config.yaml 的 param_dirs 段，通过
# myos_config.CONFIG.param_dir() 读取，代码里不再硬编码路径：
#
#   感知模块：
#     from myos_config import CONFIG
#     from param_store import (ParamStore, perception_display_name_for,
#                               PERCEPTION_KEY_NAMES, PERCEPTION_GROUP_NAMES)
#     store = ParamStore(config_dir=CONFIG.param_dir("perception"),
#                        display_name_fn=perception_display_name_for,
#                        key_names=PERCEPTION_KEY_NAMES,
#                        group_names=PERCEPTION_GROUP_NAMES)

from .store import (
    ParamStore,
    YamlFileStore,
    ParamValue,
    # ---- 感知模块专属常量 / 函数 ----
    PERCEPTION_FILE_DISPLAY_NAMES,
    PERCEPTION_KEY_NAMES,
    PERCEPTION_GROUP_NAMES,
    perception_display_name_for,
    # ---- 建图模块专属常量 / 函数 ----
    MAPPING_FILE_DISPLAY_NAMES,
    MAPPING_KEY_NAMES,
    MAPPING_GROUP_NAMES,
    mapping_display_name_for,
    # ---- 规划模块专属常量 / 函数 ----
    PLANNING_FILE_DISPLAY_NAMES,
    PLANNING_KEY_NAMES,
    PLANNING_GROUP_NAMES,
    planning_display_name_for,
)

__all__ = [
    "ParamStore",
    "YamlFileStore",
    "ParamValue",
    "PERCEPTION_FILE_DISPLAY_NAMES",
    "PERCEPTION_KEY_NAMES",
    "PERCEPTION_GROUP_NAMES",
    "perception_display_name_for",
    "MAPPING_FILE_DISPLAY_NAMES",
    "MAPPING_KEY_NAMES",
    "MAPPING_GROUP_NAMES",
    "mapping_display_name_for",
    "PLANNING_FILE_DISPLAY_NAMES",
    "PLANNING_KEY_NAMES",
    "PLANNING_GROUP_NAMES",
    "planning_display_name_for",
]
