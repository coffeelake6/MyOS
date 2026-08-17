# store.py — MyOS 参数文件数据层
#
# YamlFileStore  单文件：yaml 解析、行级写回（保留注释/格式/顺序）、修改追踪
# ParamStore     聚合：管理全部参数文件 + 外部修改监控（QFileSystemWatcher）
#
# 行级写回原理：
#   用 yaml.compose() 拿到节点树，每个标量值节点带有 start_mark/end_mark
#   （行号 + 列号）。修改时只重写值所在行的值区间，行内注释、其它行
#   原样保留。写回前重新解析磁盘文本做行号校验，防止外部修改后写错位置。

import copy
import json
import os
import re
from dataclasses import dataclass

import yaml
from PySide6 import QtCore

# ============================================================
#  感知模块导入的 yaml 文件夹（固定绝对路径）
#  部署/更换机器时，修改这一行为目标机器的实际路径即可；
#  也可用环境变量 MYOS_PARAMS_DIR 覆盖（优先级更高，无需改代码）。
#
#  后续接入其他模块（建图/规划/控制/驱动）时，仿照此结构新增
#  MAPPING_CONFIG_DIR / PLANNING_CONFIG_DIR ... 各模块独立命名，
#  由各模块的 ModuleInterface 实现传入自己的 ParamStore。
# ============================================================
_APP_ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PERCEPTION_CONFIG_DIR = os.environ.get("MYOS_PARAMS_DIR") or (
    "/home/coffeelake/MyOS/MyOS/config/perception"
)


def resolve_config_dir(config_dir):
    """把传入的目录统一解析为绝对路径

    None → None（由各模块自行传入默认目录常量，如 PERCEPTION_CONFIG_DIR）；
    绝对路径 → realpath 规范化；
    相对路径 → 先按当前工作目录解析（找不到再回退到项目根解析），最终为绝对路径。
    """
    if config_dir is None:
        return None
    if os.path.isabs(config_dir):
        return os.path.realpath(config_dir)
    # 相对路径：先按 cwd 解析，找不到再按项目根解析
    for base in (os.getcwd(), _APP_ROOT):
        candidate = os.path.realpath(os.path.join(base, config_dir))
        if os.path.isdir(candidate):
            return candidate
    return os.path.realpath(os.path.join(os.getcwd(), config_dir))

# ---- 感知模块专属：文件名 → 中文显示名（可选映射） ----
# 目录下新增的 yaml 自动出现在 UI 中，删减也自动消失，数量不固定
PERCEPTION_FILE_DISPLAY_NAMES = {
    "sys_time.yaml":      "时间同步",
    "yolo.yaml":          "YOLO 检测",
    "yolovis.yaml":       "YOLO 可视化",
    "dbscan.yaml":        "DBSCAN 聚类",
    "pointpillars.yaml":  "PointPillars 检测",
    "iou.yaml":           "IOU 融合",
    "reprojection.yaml":  "重投影",
}


def perception_display_name_for(filename):
    """感知模块：yaml 文件名 → 显示名（未映射时用去掉扩展名的文件名）"""
    return PERCEPTION_FILE_DISPLAY_NAMES.get(
        filename, filename[:-5] if filename.endswith(".yaml") else filename)


# ============================================================
#  建图模块导入的 yaml 文件夹（固定绝对路径）
#  部署/更换机器时修改此路径，或设环境变量 MYOS_SLAM_DIR 覆盖。
# ============================================================
MAPPING_CONFIG_DIR = os.environ.get("MYOS_SLAM_DIR") or (
    "/home/coffeelake/MyOS/MyOS/config/slam"
)

# ---- 建图模块专属：文件名 → 中文显示名 ----
MAPPING_FILE_DISPLAY_NAMES = {
    "velodyne.yaml": "Velodyne 建图",
}


def mapping_display_name_for(filename):
    """建图模块：yaml 文件名 → 显示名"""
    return MAPPING_FILE_DISPLAY_NAMES.get(
        filename, filename[:-5] if filename.endswith(".yaml") else filename)

# ---- 感知模块专属：键名 → 中文显示名（未命中的直接显示原键名） ----
PERCEPTION_KEY_NAMES = {
    # 通用
    "sub_topic": "订阅话题", "pub": "发布话题", "frameID": "坐标系",
    "lidar_sub": "雷达输入话题", "imageVis": "可视化名称",
    # yolo.yaml
    "yolo_weight": "模型权重", "conf": "置信度",
    # dbscan.yaml
    "distance_threshold": "聚类距离阈值", "ztop": "最大高度",
    "zbottom": "最小高度", "y_left": "左侧边界", "y_right": "右侧边界",
    # iou.yaml
    "left_calib_file": "左目标定文件", "right_calib_file": "右目标定文件",
    "yolo_sub1": "YOLO 左目话题", "yolo_sub2": "YOLO 右目话题",
    "pointpillars_sub": "PP 检测话题", "pub_colored_cloud": "彩色点云话题",
    "left_iou_threshold": "左目 IoU 阈值", "right_iou_threshold": "右目 IoU 阈值",
    # pointpillars.yaml
    "pointpillars_ros_path": "PP 包路径", "config_path": "模型配置路径",
    "pth_path": "权重文件路径", "z": "高度阈值",
    # reprojection.yaml
    "calib_file1": "左目标定文件", "calib_file2": "右目标定文件",
    "lidar_topic": "雷达话题", "image1_topic": "左目图像话题",
    "image2_topic": "右目图像话题", "output1_topic": "左目输出话题",
    "output2_topic": "右目输出话题",
    # sys_time.yaml
    "lidar_sub_topic": "雷达订阅话题", "camera1_sub_topic": "左目订阅话题",
    "camera2_sub_topic": "右目订阅话题", "camera1_pub_topic": "左目发布话题",
    "camera2_pub_topic": "右目发布话题", "lidar_pub_topic": "雷达发布话题",
    "max_interval_duration": "最大时间间隔",
}

# ---- 感知模块专属：嵌套分组名 → 中文（如 left/right、highway/line） ----
PERCEPTION_GROUP_NAMES = {
    "left": "左目", "right": "右目",
    "highway": "高速场景", "line": "直线场景",
}

# ---- 建图模块专属：键名 → 中文显示名（velodyne.yaml，lidar-IMU 建图） ----
MAPPING_KEY_NAMES = {
    # common
    "lid_topic": "雷达话题", "imu_topic": "IMU 话题",
    "time_sync_en": "时间同步", "time_offset_lidar_to_imu": "雷达-IMU 时间偏移",
    "use_imu_time": "使用 IMU 时间",
    # preprocess
    "lidar_type": "雷达类型", "scan_line": "扫描线数", "scan_rate": "扫描频率",
    "timestamp_unit": "时间戳单位", "blind": "盲区",
    # mapping
    "acc_cov": "加速度噪声协方差", "gyr_cov": "陀螺仪噪声协方差",
    "b_acc_cov": "加速度零偏游走", "b_gyr_cov": "陀螺仪零偏游走",
    "extrinsic_est_en": "在线外参估计",
    "extrinsic_T": "外参平移", "extrinsic_R": "外参旋转",
    "fov_degree": "FOV 角度", "det_range": "检测距离",
    # publish
    "path_en": "发布路径", "scan_publish_en": "发布点云",
    "dense_publish_en": "发布稠密点云", "scan_bodyframe_pub_en": "发布车体系点云",
    "odometry_en": "计算里程计", "odometry_publish_en": "发布里程计",
    # pcd_save
    "pcd_save_en": "保存点云", "interval": "保存间隔",
}

# ---- 建图模块专属：嵌套分组名 → 中文 ----
MAPPING_GROUP_NAMES = {
    "common": "通用", "preprocess": "预处理",
    "mapping": "建图", "publish": "发布", "pcd_save": "点云保存",
}


def group_display(path_prefix, group_names):
    """把嵌套分组路径（如 ('left',)）按映射表转为中文显示名，如 '左目'"""
    return " / ".join(group_names.get(p, p) for p in path_prefix)


# ---------------------------------------------------------------------------
#  数据模型
# ---------------------------------------------------------------------------


@dataclass
class ParamValue:
    """一个叶子参数（扁平化后）"""

    path: tuple            # yaml 内路径，如 ("left", "conf")
    key: str               # 叶子键名，如 "conf"
    value: object          # 当前值
    vtype: str             # number / bool / text
    is_int: bool           # number 时是否为整数
    group_name: str        # 嵌套分组显示名（无分组为 ""）
    display_name: str      # 中文显示名


def _parse_locations(text):
    """compose 解析：返回 {路径: (行号, 起始列, 结束列, 是否多行)}"""
    out = {}
    doc = yaml.compose(text)
    if doc is None:
        return out

    def walk(node, prefix):
        if isinstance(node, yaml.MappingNode):
            for k_node, v_node in node.value:
                path = prefix + (k_node.value,)
                if isinstance(v_node, yaml.ScalarNode):
                    sm, em = v_node.start_mark, v_node.end_mark
                    out[path] = (sm.line, sm.column, em.column, sm.line != em.line)
                else:
                    walk(v_node, path)
        # SequenceNode / 其它：当前结构不支持，跳过（保存时对应路径会报错）

    walk(doc, ())
    return out


def _get_path(data, path):
    """按路径取 dict 中的值；不存在返回 None"""
    cur = data
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _set_path(data, path, value):
    cur = data
    for p in path[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    cur[path[-1]] = value


def _classify(value):
    """值 → (vtype, is_int)"""
    if isinstance(value, bool):
        return "bool", False
    if isinstance(value, int):
        return "number", True
    if isinstance(value, float):
        return "number", False
    return "text", False


def _needs_quotes(s):
    """判断字符串写回 yaml 时是否需要引号（plain 会改变类型/歧义）"""
    if s == "":
        return True
    if s.strip() != s:
        return True
    if s[0] in '!&*-?|>%@`"\'#,[]{}':
        return True
    if re.search(r":\s|#|\n", s):
        return True
    try:
        if not isinstance(yaml.safe_load(s), str):
            return True
    except Exception:
        return True
    return False


def _repr_scalar(value, quoted, orig):
    """把值序列化为 yaml 行内文本（保留原引号风格 / 原格式）"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    s = str(value)
    if quoted:
        if orig[:1] == '"':
            return json.dumps(s, ensure_ascii=False)
        return "'" + s.replace("'", "''") + "'"
    if _needs_quotes(s):
        return json.dumps(s, ensure_ascii=False)
    return s


def _coerce(value, old):
    """把 UI 给的值转换为原值类型（int 参数保持 int、float 保持 float）"""
    if isinstance(old, bool):
        return bool(value)
    if isinstance(old, int):
        return int(value)
    if isinstance(old, float):
        return float(value)
    return value


# ---------------------------------------------------------------------------
#  单文件存储
# ---------------------------------------------------------------------------


class YamlFileStore:
    """一个 yaml 参数文件的读 / 改 / 写

    Args:
        filename:      文件名（如 "yolo.yaml"）
        display_name:  展示名（由所属模块提供，如感知模块的中文映射）
        path:          文件绝对路径
        key_names:     该模块的 键名→中文 映射表（可选，未命中显示原键名）
        group_names:   该模块的 嵌套分组名→中文 映射表（可选）
    """

    def __init__(self, filename, display_name, path,
                 key_names=None, group_names=None):
        self.filename = filename
        self.display_name = display_name
        self.path = path
        self._key_names = key_names or {}
        self._group_names = group_names or {}
        self._data = {}
        self._baseline = {}       # 最近一次加载的原始数据快照（判定“改回原值”）
        self._locations = {}      # 路径 → (line, col, end_col, multi_line)
        self._loaded_text = ""
        self._dirty = set()       # 已修改的路径集合

    # ----- 读取 -----

    def load(self):
        """从磁盘加载；文件不存在或解析失败返回 False"""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print(f"[param_store] {self.filename} 读取失败: {e}")
            return False
        return self._apply_text(text)

    def _apply_text(self, text):
        """应用一段文本作为新内容；返回是否有实质变化"""
        if text == self._loaded_text:
            return False
        try:
            data = yaml.safe_load(text)
            locs = _parse_locations(text)
        except yaml.YAMLError as e:
            print(f"[param_store] {self.filename} 解析失败: {e}")
            return False
        self._data = data if isinstance(data, dict) else {}
        self._baseline = copy.deepcopy(self._data)
        self._locations = locs
        self._loaded_text = text
        self._dirty = set()
        return True

    def reload(self):
        """重新读盘（丢弃本地修改）；返回是否发生变化"""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError:
            return False
        return self._apply_text(text)

    # ----- 查询 -----

    def params(self):
        """扁平化参数列表（按文件内顺序）"""
        out = []
        for path, loc in self._locations.items():
            line, col, end_col, multi_line = loc
            if multi_line:
                continue  # 多行值不渲染（避免误编辑）
            value = _get_path(self._data, path)
            if value is None:
                # 空值：当作可编辑文本（值为空字符串）
                vtype, is_int = "text", False
                value = ""
            else:
                vtype, is_int = _classify(value)
            key = path[-1]
            out.append(ParamValue(
                path=path, key=key, value=value, vtype=vtype, is_int=is_int,
                group_name=group_display(path[:-1], self._group_names),
                display_name=self._key_names.get(key, key),
            ))
        return out

    def dirty(self):
        return bool(self._dirty)

    def dirty_paths(self):
        return list(self._dirty)

    def get_value(self, path):
        return _get_path(self._data, path)

    # ----- 修改 -----

    def set_value(self, path, value):
        """修改参数值（内存中）；值回到原始加载值时自动清除修改标记"""
        old = _get_path(self._data, path)
        if old is None:
            return False
        new = _coerce(value, old)
        if _get_path(self._baseline, path) == new:
            # 改回了原始值：数据复位，清除修改标记
            _set_path(self._data, path, _get_path(self._baseline, path))
            self._dirty.discard(path)
            return True
        if old == new:
            return True  # 值未变化
        _set_path(self._data, path, new)
        self._dirty.add(path)
        return True

    # ----- 写回 -----

    def save(self):
        """行级写回磁盘；返回 (ok, 消息)。失败时不做任何写入"""
        if not self._dirty:
            return True, f"{self.filename}: 无修改"
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            return False, f"{self.filename}: 读取失败 ({e})"

        # 重新解析磁盘文本，校验每个修改路径的行号没有漂移
        fresh = _parse_locations(text)
        for p in self._dirty:
            old_loc = self._locations.get(p)
            new_loc = fresh.get(p)
            if old_loc is None or new_loc is None or old_loc != new_loc:
                return False, (f"{self.filename}: 参数「{'.'.join(p)}」所在行已变化"
                               "（文件可能被外部修改），已取消保存，请先重新加载")
            if old_loc[3]:
                return False, (f"{self.filename}: 参数「{'.'.join(p)}」为多行值，"
                               "不支持自动写回，请手动修改文件")

        # 逐行替换
        lines = text.splitlines(keepends=True)
        for p in self._dirty:
            line_no, col, end_col, _ = self._locations[p]
            line = lines[line_no]
            orig = line[col:end_col]
            quoted = orig[:1] in ("'", '"')
            new_repr = _repr_scalar(_get_path(self._data, p), quoted, orig)
            lines[line_no] = line[:col] + new_repr + line[end_col:]
        new_text = "".join(lines)

        # 安全网：新文本必须能解析，且所有修改值一致，才允许落盘
        try:
            new_data = yaml.safe_load(new_text) or {}
            for p in self._dirty:
                if _get_path(new_data, p) != _get_path(self._data, p):
                    return False, f"{self.filename}: 写回校验不一致，已取消保存"
        except yaml.YAMLError as e:
            return False, f"{self.filename}: 写回结果解析失败 ({e})，已取消保存"

        # 原子写：先写临时文件再替换
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(new_text)
            os.replace(tmp, self.path)
        except OSError as e:
            return False, f"{self.filename}: 写入失败 ({e})"

        # 保存成功后同步重建行号表 / 基线：
        # 值长度变化会导致后续保存的行号校验误判「文件被外部修改」
        self._loaded_text = new_text
        self._locations = _parse_locations(new_text)
        n = len(self._dirty)
        self._dirty = set()
        self._baseline = copy.deepcopy(self._data)
        return True, f"{self.filename}: 已保存 {n} 项修改"


# ---------------------------------------------------------------------------
#  聚合存储 + 外部修改监控
# ---------------------------------------------------------------------------


def _plain_display_name(filename):
    """默认显示名：去掉 .yaml 扩展名（未提供映射时的兜底）"""
    return filename[:-5] if filename.endswith(".yaml") else filename


class ParamStore(QtCore.QObject):
    """管理一个模块的 yaml 参数目录（通用数据层，每个模块各自创建实例）

    各模块通过构造参数注入自己的目录与映射表，互不混淆：
      ParamStore(config_dir=PERCEPTION_CONFIG_DIR,
                 display_name_fn=perception_display_name_for,
                 key_names=PERCEPTION_KEY_NAMES,
                 group_names=PERCEPTION_GROUP_NAMES)

    信号：
      file_changed(文件名)  — 文件内容被外部修改且已自动重新加载（无本地冲突）
      file_conflict(文件名) — 文件被外部修改但本地有未保存修改，未应用外部内容，
                               由 UI 提示用户选择「重新加载」或「忽略」
      files_scanned()       — 目录扫描发现文件集合变化（新增/删除），UI 应重建卡片
    """

    file_changed = QtCore.Signal(str)
    file_conflict = QtCore.Signal(str)
    files_scanned = QtCore.Signal()

    def __init__(self, config_dir, display_name_fn=None,
                 key_names=None, group_names=None, parent=None):
        super().__init__(parent)
        # config_dir 必填：由各模块传入自己的目录常量（如 PERCEPTION_CONFIG_DIR）
        self._config_dir = resolve_config_dir(config_dir)
        if not self._config_dir:
            raise ValueError("ParamStore 需要指定 config_dir"
                             "（各模块传入自己的目录常量，如 PERCEPTION_CONFIG_DIR）")
        self._display_name_fn = display_name_fn or _plain_display_name
        self._key_names = key_names or {}
        self._group_names = group_names or {}
        self._files = []
        self._by_name = {}
        self._by_path = {}
        self._loaded = False

        self._watcher = QtCore.QFileSystemWatcher(self)
        # 文件内容变化 / 目录增删变化都要处理
        self._watcher.fileChanged.connect(self._on_fs_changed)
        self._watcher.directoryChanged.connect(self._on_fs_changed)
        self._pending = set()
        self._debounce = QtCore.QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(400)
        self._debounce.timeout.connect(self._flush)

    # ----- 扫描 / 加载 -----

    def load_all(self):
        if self._loaded:
            return
        self._loaded = True
        self.scan()
        # 监听目录本身：新增/删除/重命名 yaml 时触发重新扫描
        if os.path.isdir(self._config_dir):
            self._watcher.addPath(self._config_dir)

    def scan(self):
        """扫描配置目录下的所有 *.yaml，与当前文件集合做差异同步

        新增文件 → 建 YamlFileStore 并加载；删除文件 → 移除（未保存修改丢弃）。
        集合变化时发 files_scanned 信号。返回是否发生变化。
        """
        if not os.path.isdir(self._config_dir):
            if self._files:
                self._files.clear()
                self._by_name.clear()
                self._by_path.clear()
                self.files_scanned.emit()
            return False
        try:
            names = sorted(
                f for f in os.listdir(self._config_dir)
                if f.endswith(".yaml")
                and os.path.isfile(os.path.join(self._config_dir, f)))
        except OSError as e:
            print(f"[param_store] 目录扫描失败: {e}")
            return False

        changed = False
        # 新增
        for name in names:
            if name in self._by_name:
                continue
            path = os.path.join(self._config_dir, name)
            fs = YamlFileStore(name, self._display_name_fn(name), path,
                               key_names=self._key_names,
                               group_names=self._group_names)
            fs.load()
            self._files.append(fs)
            self._by_name[name] = fs
            self._by_path[path] = fs
            self._watcher.addPath(path)
            changed = True
        # 删除
        for fs in list(self._files):
            if fs.filename not in names:
                if fs.dirty():
                    print(f"[param_store] {fs.filename} 已被移除，其未保存修改被丢弃")
                self._files.remove(fs)
                self._by_name.pop(fs.filename, None)
                self._by_path.pop(fs.path, None)
                self._watcher.removePath(fs.path)
                changed = True

        # 文件名排序，保证 UI 顺序稳定
        self._files.sort(key=lambda fs: fs.filename)
        if changed:
            self.files_scanned.emit()
        return changed

    def files(self):
        return list(self._files)

    def file(self, filename):
        return self._by_name.get(filename)

    # ----- 保存 / 重载 -----

    def save_all(self):
        """一键保存所有有修改的文件；返回 (ok, 汇总消息)"""
        msgs, ok_all = [], True
        for fs in self._files:
            if fs.dirty():
                ok, msg = fs.save()
                msgs.append(msg)
                if not ok:
                    ok_all = False
        if not msgs:
            return True, "无未保存的修改"
        return ok_all, "；".join(msgs)

    def reload_all(self):
        """全部重新读盘（丢弃本地修改）；返回发生变化的文件名列表"""
        changed = []
        for fs in self._files:
            if fs.reload():
                changed.append(fs.filename)
        return changed

    def any_dirty(self):
        return any(f.dirty() for f in self._files)

    def dirty_count(self):
        return sum(len(f.dirty_paths()) for f in self._files)

    # ----- 外部修改监控 -----

    def _on_fs_changed(self, path):
        self._pending.add(path)
        self._debounce.start()

    def _flush(self):
        # Linux 下编辑器可能用 rename 替换文件导致 watcher 失效，每次重新挂载
        for fs in self._files:
            self._watcher.addPath(fs.path)
        if os.path.isdir(self._config_dir):
            self._watcher.addPath(self._config_dir)
        pending, self._pending = self._pending, set()
        for path in pending:
            if path == self._config_dir:
                # 目录事件：文件增删 → 重新扫描（scan 内部发 files_scanned）
                self.scan()
                continue
            fs = self._by_path.get(path)
            if fs is None:
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                continue  # 文件暂时不可读（可能正在保存中），等待下次事件
            if text == fs._loaded_text:
                continue  # 内容未变化（如权限/时间戳事件）
            if fs.dirty():
                # 本地有未保存修改：不应用外部内容，交由 UI 决定
                self.file_conflict.emit(fs.filename)
                continue
            if fs._apply_text(text):
                self.file_changed.emit(fs.filename)
