# myos_config.py — MyOS 集中配置（config/config.yaml 的唯一入口）
#
# 所有可调数据统一写在 config/config.yaml：
#   - 相机画面话题（初始订阅 + 下拉候选）
#   - 快捷启动的 sh 脚本列表
#   - bag 包录制可选话题
#   - 实时数据面板的映射（键 / 话题 / 单位 / 小数位）
#
# yaml 里没写全的键自动用下方 DEFAULTS 兜底：缺字段、写错类型都不影响启动；
# 在 yaml 里增删条目（如多一个候选话题、少一个数据项），界面自动适配。
# 改动 yaml 后重启程序即生效；调用 load() 可重新加载。

import os

import yaml

# 项目根目录与配置文件路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")

# 内置默认值：yaml 缺失 / 写错 / 漏项时的兜底（与改动前的硬编码一致）
DEFAULTS = {
    "camera": {
        # 启动时两路相机默认订阅的话题（cam1 / cam2 为固定槽位，只改值）
        "initial_topics": {
            "cam1": "/01/image_rect_color",
            "cam2": "/02/image_rect_color",
        },
        # 画面下方下拉框的可选话题（增删即自动同步）
        "candidate_topics": [
            "/01/image_rect_color",
            "/02/image_rect_color",
            "/reprojection_image1",
            "/reprojection_image2",
        ],
    },
    "launch": {
        # sh 脚本目录（相对项目根目录，或写绝对路径）
        "script_dir": "sh",
        # 下拉框列出的脚本文件名（显式列表，增删脚本 = 改这里）
        "scripts": [
            "test_highway.sh",
            "test_line.sh",
            "test_skidpad.sh",
        ],
    },
    "bag": {
        # bag 录制面板可勾选的话题（增删即自动同步）
        "record_topics": [
            "/01/image_rect_color",
            "/02/image_rect_color",
            "/fusion/velocity",
            "/control/steering_angle",
        ],
    },
    "data_items": [
        # 实时数据面板：key=显示名，topic=订阅话题（消息类型固定
        # std_msgs/Float32，取值字段固定 data），unit=单位，decimals=小数位
        {"key": "YOLO推理时间", "topic": "/yolov11_time", "unit": "ms", "decimals": 2},
        {"key": "Pointpillars推理时间", "topic": "/pointpillars_trt_time", "unit": "ms", "decimals": 2},
        {"key": "融合速度", "topic": "/iou_fusion_time", "unit": "ms", "decimals": 2},
        {"key": "运动补偿", "topic": "/motion_compensation_time", "unit": "ms", "decimals": 2},
        {"key": "点云坐标转换", "topic": "/cluster_tf_time", "unit": "ms", "decimals": 2},
    ],
}


def _deep_merge(base, override):
    """递归合并配置：dict 按键合并；list / 标量整体替换（override 优先）"""
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override if override is not None else base
    out = dict(base)
    for k, v in override.items():
        if v is None:
            continue                      # yaml 显式留空 → 保留默认
        if isinstance(out.get(k), dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _read_yaml(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"[myos_config] 读取 {path} 失败，使用默认配置: {e}")
        return {}


class _Config:
    """读取合并后的配置，统一做类型清洗 + 路径解析"""

    def __init__(self, raw):
        self._raw = raw

    # ---- 相机画面 ----
    def camera_initial_topics(self):
        """启动时两路相机的默认订阅话题（cam1/cam2 槽位始终存在）"""
        topics = dict(DEFAULTS["camera"]["initial_topics"])
        user = self._raw["camera"]["initial_topics"] or {}
        for k, v in user.items():
            if isinstance(v, str) and v.strip():
                topics[k] = v.strip()
        return topics

    def camera_candidate_topics(self):
        """下拉框可选话题（去空）"""
        return [str(t).strip() for t in (self._raw["camera"]["candidate_topics"] or [])
                if t and str(t).strip()]

    # ---- 快捷启动 ----
    def launch_script_dir(self):
        """sh 脚本目录（相对项目根目录的相对路径会解析成绝对路径）"""
        rel = self._raw["launch"]["script_dir"] or "sh"
        rel = os.path.expanduser(str(rel))
        return rel if os.path.isabs(rel) else os.path.join(BASE_DIR, rel)

    def launch_scripts(self):
        """下拉框列出的脚本文件名（去空）"""
        return [str(s).strip() for s in (self._raw["launch"]["scripts"] or [])
                if s and str(s).strip()]

    # ---- bag 录制 ----
    def bag_record_topics(self):
        """录制面板可勾选话题（去空）"""
        return [str(t).strip() for t in (self._raw["bag"]["record_topics"] or [])
                if t and str(t).strip()]

    # ---- 实时数据 ----
    def data_items(self):
        """实时数据面板配置项（key/topic 必填，缺字段自动兜底）"""
        items = []
        for it in self._raw["data_items"] or []:
            if not isinstance(it, dict):
                continue
            key = str(it.get("key") or "").strip()
            topic = str(it.get("topic") or "").strip()
            if not key or not topic:
                continue
            items.append({
                "key": key,
                "topic": topic,
                "unit": str(it.get("unit") or ""),
                "decimals": int(it.get("decimals") or 2),
            })
        return items


def load(path=CONFIG_PATH):
    """读取 yaml 并与默认值合并，返回 _Config"""
    return _Config(_deep_merge(DEFAULTS, _read_yaml(path)))


# 启动时加载一次（改动 yaml 后重启程序生效）
CONFIG = load()
