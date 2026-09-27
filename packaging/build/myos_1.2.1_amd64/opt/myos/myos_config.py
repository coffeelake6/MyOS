# myos_config.py — MyOS 集中配置（config/config.yaml 的唯一入口）
#
# 所有可调数据统一写在 config/config.yaml：
#   - 相机画面话题（初始订阅 + 下拉候选）
#   - 快捷启动的 sh 脚本目录与脚本列表
#   - bag 包录制可选话题
#   - 实时数据面板的映射（键 / 话题 / 单位 / 小数位）
#   - 参数修改面板各模块的 yaml 目录（感知 / 建图 / 规划）
#   - 界面主题（浅色 / 深色，也可在界面上用胶囊按钮切换，会自动写回这里）
#
# 「主配置」：参数修改面板上可以选另一个 config.yaml 作为主配置，它同样是
# 一份完整的程序配置。本文件 param_panel.main_config 指向它时，下面这些业务段
# 以主配置为准，主配置没写的段沿用本文件（再兜底 DEFAULTS）：
#   camera / launch / bag / data_items / param_dirs
# 主配置里的相对路径（param_dirs、launch.script_dir）按主配置所在目录解析，
# 便于「配置 + 参数目录一起搬走」。界面主题 ui.theme 与 param_panel 本身是
# 引导段，固定从本项目 config.yaml 读（否则无法退出 / 改回）。
#
# yaml 里没写全的键自动用下方 DEFAULTS 兜底：缺字段、写错类型都不影响启动；
# 在 yaml 里增删条目（如多一个候选话题、少一个数据项），界面自动适配。
# 改动 yaml 后重启程序即生效；调用 load() / reload() 可重新加载。

import os
import re

import yaml

# 项目根目录与配置文件路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")

# 「主配置」可以覆盖的业务段（其余段 —— ui.theme / param_panel —— 是引导段，
# 固定从本项目 config.yaml 读。param_dirs 也在列表里，但它不参与按段合并：
# 相对路径的解析基准不同，由 _Config.param_dir 逐模块处理）
_MAIN_CONFIG_SECTIONS = ("camera", "launch", "bag", "data_items", "param_dirs")

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
    "param_dirs": {
        # 参数修改面板各模块扫描的 yaml 目录（部署到新机器时改这里即可）
        "perception": "/home/a03/A03/perception/src/param/config",
        "mapping": "/home/a03/A03/MYSLAM/src/FAST_LIO/config",
        "planning": "/home/a03/A03/Planning/src/Param/config",
    },
    "param_panel": {
        # 参数修改面板使用的「主配置 yaml」路径（该文件里要有 param_dirs 段）
        "main_config": "",
    },
    "ui": {
        # 界面主题：light=灰底黑字（默认），dark=原来的黑底白字
        "theme": "light",
    },
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

    def __init__(self, raw, path=CONFIG_PATH, main_path="", main_raw=None):
        self._raw = raw
        self.path = path              # 本项目 config.yaml（主题 / 主配置写回时用）
        self._main_path = main_path   # 主配置 yaml 路径；未设置 = 空串
        self._main_raw = main_raw or {}                                   # 主配置原样内容
        self._main_base = (os.path.dirname(os.path.abspath(main_path))
                           if main_path else BASE_DIR)                    # 相对路径解析基准
        # 主配置 param_dirs 段（已解析成绝对路径）；没提到的模块回退本项目
        self._main_dirs = param_dirs_of(main_path) if main_path else {}

    def reload(self):
        """就地重新加载（self 引用不变，所有持有者自动看到新值）"""
        self.__dict__.update(load(self.path).__dict__)
        return self

    def _resolve(self, rel, base):
        """把可能是相对路径的字符串解析成绝对路径（空串原样返回）"""
        rel = os.path.expanduser(str(rel or "").strip())
        if not rel:
            return ""
        return rel if os.path.isabs(rel) else os.path.join(base, rel)

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
        """sh 脚本目录

        主配置写了该键 → 相对路径按主配置所在目录解析；否则按项目根目录。
        """
        main_launch = self._main_raw.get("launch")
        if isinstance(main_launch, dict) and str(main_launch.get("script_dir") or "").strip():
            return self._resolve(main_launch["script_dir"], self._main_base)
        rel = self._raw["launch"]["script_dir"] or "sh"
        return self._resolve(rel, BASE_DIR)

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

    # ---- 参数修改面板：模块 yaml 目录 ----
    def param_dir(self, module_key):
        """某模块的 yaml 参数目录（感知 / 建图 / 规划）

        主配置 param_dirs 段写了的模块以它为准（相对路径按主配置所在目录解析）；
        没写的模块用本项目 config.yaml（相对路径按项目根目录解析）；再兜底内置
        默认路径。该模块无内置默认 → 返回空串（此时该模块显示空态）。
        """
        if module_key in self._main_dirs:
            return self._main_dirs[module_key]
        default = DEFAULTS["param_dirs"].get(module_key, "")
        rel = (self._raw["param_dirs"] or {}).get(module_key) or default
        return self._resolve(rel, BASE_DIR)

    # ---- 参数修改面板：主配置 yaml ----
    def param_main_config(self):
        """参数修改面板使用的「主配置 yaml」路径；未设置返回空串

        它是一份完整的程序配置：camera / launch / bag / data_items / param_dirs
        这些业务段以它为准，主配置没写的段沿用本项目 config.yaml。
        一般不用手改：在面板上点「浏览」选一个 config.yaml 会自动写回这里。
        相对路径按本项目根目录解析为绝对路径。
        """
        return self._main_path

    # ---- 界面主题 ----
    def ui_theme(self):
        """界面主题名：light=灰底黑字（默认），dark=原来的黑底白字

        写错 / 留空 → 用内置默认（light）。
        """
        ui = self._raw.get("ui")
        if not isinstance(ui, dict):
            ui = {}
        name = str(ui.get("theme") or "").strip().lower()
        return name if name in ("light", "dark") else DEFAULTS["ui"]["theme"]


def load(path=CONFIG_PATH):
    """读取 yaml 并与默认值合并，返回 _Config

    合并顺序：DEFAULTS ← 本项目 config.yaml ← 主配置的业务段。
    主配置指本项目 param_panel.main_config 指向的那份 yaml（它本身也是一份
    完整配置）：写了 camera / launch / bag / data_items 段就以它为准，没写的
    沿用本项目；param_dirs 段由 _Config.param_dir 按模块逐个决定。
    主配置读不到 → 全部按本项目，不影响启动。
    """
    raw = _read_yaml(path)
    merged = _deep_merge(DEFAULTS, raw)

    main_path = ""
    pp = raw.get("param_panel")
    if isinstance(pp, dict):
        rel = os.path.expanduser(str(pp.get("main_config") or "").strip())
        if rel:
            main_path = rel if os.path.isabs(rel) else os.path.join(BASE_DIR, rel)

    main_raw = _read_yaml(main_path) if main_path else {}
    overrides = {}
    for sec in _MAIN_CONFIG_SECTIONS:
        if sec == "param_dirs":
            continue        # 相对路径基准不同，由 _Config.param_dir 逐模块处理
        val = main_raw.get(sec)
        if val is not None:
            overrides[sec] = val
    if overrides:
        merged = _deep_merge(merged, overrides)

    return _Config(merged, path, main_path=main_path, main_raw=main_raw)


def main_config_sections_of(path):
    """某个「主配置 yaml」里实际包含的业务段名集合

    界面用来校验（一个段都没有说明选错了文件）与提示（哪些变化需要重启）。
    """
    raw = _read_yaml(path)
    return {sec for sec in _MAIN_CONFIG_SECTIONS if raw.get(sec) is not None}


def reload():
    """就地重新加载全局配置（CONFIG 引用不变，所有持有者自动看到新值）

    界面上切换主配置后调用：相机候选话题 / 脚本目录与列表 / bag 录制话题 /
    参数目录立即生效；相机默认订阅与实时数据项涉及 ROS 订阅，需重启程序。
    """
    return CONFIG.reload()


# 参数修改面板支持的模块键（与 config.yaml 的 param_dirs 段一一对应）
PARAM_MODULE_KEYS = ("perception", "mapping", "planning")


def param_dirs_of(path):
    """读取任意「主配置 yaml」里的 param_dirs 段

    返回 {模块键: 绝对目录}；相对路径按该主配置所在目录解析（配置和参数目录
    一起搬走也能用）。文件读不到 / 没有 param_dirs 段 → 返回 {}。
    """
    raw = _read_yaml(path)
    dirs = raw.get("param_dirs")
    if not isinstance(dirs, dict):
        return {}
    base = os.path.dirname(os.path.abspath(path))
    out = {}
    for key, val in dirs.items():
        rel = os.path.expanduser(str(val or "").strip())
        if not rel:
            continue
        full = rel if os.path.isabs(rel) else os.path.join(base, rel)
        out[str(key)] = os.path.realpath(full)      # 归一化，去掉 .. 等冗余段
    return out


def active_param_dirs():
    """参数修改面板当前生效的各模块 yaml 目录 {模块键: 绝对目录}

    主配置 param_dirs 段写了的模块用它（相对路径按主配置所在目录解析），
    没提到的模块回退本项目 config.yaml（见 _Config.param_dir）。
    """
    return {k: CONFIG.param_dir(k) for k in PARAM_MODULE_KEYS}


def _yaml_scalar(s):
    """写回 yaml 时的最小引号处理（含 : # 等会歧义的字符才加引号）"""
    if not s:
        return '""'
    if re.search(r"[:#]|^\s|\s$", s):
        return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')
    return s


def save_param_main_config(path, config_path=None):
    """把「主配置 yaml」路径写回本项目 config.yaml（只动 param_panel.main_config）

    参数面板上选定主配置后调用；path 传空串 = 恢复为本项目 config.yaml 的 param_dirs。
    行级改写，保留文件里其余内容与注释；找不到 param_panel 段就补一段；
    文件不可写只打印警告，不影响程序继续跑。
    """
    path = str(path or "").strip()
    if config_path is None:
        config_path = getattr(CONFIG, "path", CONFIG_PATH)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        print(f"[myos_config] 读取 {config_path} 失败，主配置未写回: {e}")
        return False

    value = _yaml_scalar(path)
    out = []
    header_idx = None      # param_panel: 段头在 out 中的位置
    in_section = False
    replaced = False
    for raw in lines:
        line = raw.rstrip("\n")
        if re.match(r"^param_panel\s*:\s*$", line):
            header_idx = len(out)
            in_section = True
            out.append(raw)
            continue
        if in_section:
            if line.strip() and not line.startswith((" ", "\t")):
                in_section = False                     # 回到下一个顶层键
            elif not replaced and re.match(r"^\s+main_config\s*:", line):
                indent = line[:len(line) - len(line.lstrip())]
                out.append(f"{indent}main_config: {value}\n")
                replaced = True
                continue
        out.append(raw)

    if not replaced:
        if header_idx is not None:
            # 已有 param_panel: 段但没写 main_config：紧跟段头插一行，
            # 不能再补一个顶层 param_panel:（会变成重复键）
            out.insert(header_idx + 1, f"  main_config: {value}\n")
        else:
            out.append(
                "\n# ---------- 参数修改面板：主配置 ----------\n"
                "# 面板按这个主配置 yaml 里的 param_dirs 段加载各模块参数；留空则用本文件的。\n"
                "# 一般不用手改：在参数修改面板上点「浏览」选一个 config.yaml 会自动写回这里。\n"
                f"param_panel:\n  main_config: {value}\n")

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.writelines(out)
    except OSError as e:
        print(f"[myos_config] 写入 {config_path} 失败，主配置未写回: {e}")
        return False
    return True


def save_ui_theme(name, path=None):
    """把界面主题写回 config.yaml（行级改写，只动 ui.theme 的值）

    界面上切换主题时调用：保留文件里其余内容与注释不变。
    找不到 ui 段就补一段；文件不可写只打印警告，不影响程序继续跑。
    path 不给就用当前 CONFIG 对应的文件。
    """
    if name not in ("light", "dark"):
        return False
    if path is None:
        path = getattr(CONFIG, "path", CONFIG_PATH)
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        print(f"[myos_config] 读取 {path} 失败，主题未写回: {e}")
        return False

    out = []
    in_ui = False          # 是否正处于顶层 ui: 段内
    replaced = False
    for raw in lines:
        line = raw.rstrip("\n")
        if re.match(r"^ui\s*:\s*$", line):
            in_ui = True
            out.append(raw)
            continue
        if in_ui:
            if line.strip() and not line.startswith((" ", "\t")):
                in_ui = False                      # 回到下一个顶层键
            elif not replaced and re.match(r"^\s+theme\s*:", line):
                indent = line[:len(line) - len(line.lstrip())]
                out.append(f"{indent}theme: {name}\n")
                replaced = True
                continue
        out.append(raw)

    if not replaced:
        if in_ui:                                  # 有 ui: 段但没写 theme
            out.append(f"  theme: {name}\n")
        else:                                      # 完全没有 ui: 段 → 补一段
            out.append(
                "\n# ---------- 界面主题 ----------\n"
                "# light = 灰底黑字（默认）   dark = 原来的黑底白字\n"
                "# 也可以在界面顶部用胶囊按钮切换，会自动写回这里，下次启动生效。\n"
                f"ui:\n  theme: {name}\n")

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(out)
    except OSError as e:
        print(f"[myos_config] 写入 {path} 失败，主题未写回: {e}")
        return False
    return True


# 启动时加载一次（改动 yaml 后重启程序生效）
CONFIG = load()
