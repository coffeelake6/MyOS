# param_modification.py — 参数修改面板（MyOS）
#
# 功能：按「模块 → 参数组 → 参数」三级结构，在右侧面板中查看与修改系统参数。
# 五个模块（感知/建图/规划/控制/仿真）均以接口风格定义（ModuleInterface），
# 每个模块由若干参数组（ParamGroupInterface）组成，参数组由若干参数（ParamSpec）组成。
#
# 当前为 UI 骨架阶段：界面已绘制完毕，参数内容留空，待接入数据源后填充；
# 新增/删减模块只需修改 MODULES 列表或实现 ModuleInterface 即可。
#
# 设计（Apple Fluid Interface）：
#   - 模块选择区：横向分段，悬停/选中背景平滑过渡（120ms OutCubic），选中项底部强调条
#   - 页面切换：内容区淡入（160ms OutCubic），结束后移除特效避免压平子级阴影
#
# 颜色统一取自 theme.T 的 token（见 ui/theme.py），本文件不写死色值；
# 自绘控件在 paintEvent 里实时取色，切换主题后自动跟着变。

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

from PySide6 import QtCore, QtWidgets, QtGui

from theme import T

from myos_config import (
    CONFIG,
    active_param_dirs,
    main_config_sections_of,
    reload as reload_config,
    save_param_main_config,
)
from param_store import (
    ParamStore,
    perception_display_name_for,
    PERCEPTION_KEY_NAMES,
    PERCEPTION_GROUP_NAMES,
    mapping_display_name_for,
    MAPPING_KEY_NAMES,
    MAPPING_GROUP_NAMES,
    planning_display_name_for,
    PLANNING_KEY_NAMES,
    PLANNING_GROUP_NAMES,
)
from param_widgets import GroupCard, SaveButton, NotifyBar, INPUT_QSS

# ---------------------------------------------------------------------------
#  参数数据层（接口风格，便于后期维护与增删）
# ---------------------------------------------------------------------------


@dataclass
class ParamSpec:
    """单个参数的描述（参数组返回的参数列表元素）

    Args:
        name:  显示名，如 "置信度"
        key:   内部键，如 "confidence"
        value: 当前值（内容阶段留空）
        ptype: 编辑控件类型：text / number / bool / select / path
    """

    name: str = ""
    key: str = ""
    value: object = None
    ptype: str = "text"


class ParamGroupInterface(ABC):
    """参数组接口：一组相关参数的集合（如 YOLO 参数组）"""

    group_name = ""     # 参数组名，如 "YOLO"

    @abstractmethod
    def params(self) -> List[ParamSpec]:
        """返回本组参数列表（内容阶段留空）"""
        return []

    def load(self):
        """从配置源加载（待实现）"""
        pass

    def save(self):
        """写回配置源（待实现）"""
        pass


class ModuleInterface(ABC):
    """模块接口：感知 / 建图 / 规划 / 控制 / 驱动"""

    module_name = ""    # 模块名，如 "感知"

    @abstractmethod
    def groups(self) -> List[ParamGroupInterface]:
        """返回该模块的参数组列表（内容阶段留空）"""
        return []

    def load(self):
        """加载该模块所有参数组（待实现）"""
        pass

    def save(self):
        """保存该模块所有参数组（待实现）"""
        pass


# ---------------------------------------------------------------------------
#  五个模块的接口实现（内容留空，待接入参数组后填充）
# ---------------------------------------------------------------------------


class PerceptionModule(ModuleInterface):
    """感知模块 —— 读取配置目录下的所有 yaml 参数文件

    通过 config_dir 指定一个文件夹路径，扫描其中全部 *.yaml，
    每个文件对应一个独立 ROS 功能包（节点），自动生成一个参数组。
    文件数量不固定：往目录里增删 yaml，UI 自动适配（新增卡片/移除卡片）。

    Args:
        config_dir: yaml 目录路径；默认取 config.yaml 的
                    param_dirs.perception（留空则目录为空、显示空态）
    """

    module_name = "感知"
    config_key = "perception"      # 对应主配置 param_dirs 段里的键名

    def __init__(self, store=None, config_dir=None):
        # 感知模块的 ParamStore：注入感知专属目录与映射表
        # （后续建图/规划等模块各自创建自己的 ParamStore，互不混淆）
        if store is None:
            store = ParamStore(
                config_dir if config_dir is not None else CONFIG.param_dir("perception"),
                display_name_fn=perception_display_name_for,
                key_names=PERCEPTION_KEY_NAMES,
                group_names=PERCEPTION_GROUP_NAMES,
            )
        self.store = store
        self.store.load_all()

    def groups(self):
        return [YamlGroupAdapter(fs) for fs in self.store.files()]

    def save(self):
        """一键保存所有 yaml 文件；返回 (ok, 汇总消息)"""
        return self.store.save_all()

    def reload(self):
        """全部重新读盘（丢弃未保存修改）；返回变化的文件名列表"""
        return self.store.reload_all()


class YamlGroupAdapter(ParamGroupInterface):
    """一个 yaml 文件 → 一个参数组（包装 YamlFileStore）"""

    def __init__(self, file_store):
        self._fs = file_store

    @property
    def group_name(self):
        return self._fs.display_name

    @property
    def filename(self):
        return self._fs.filename

    @property
    def file_store(self):
        return self._fs

    def params(self):
        """返回扁平化的参数描述（ParamValue 列表，来自数据层）"""
        return self._fs.params()


class MappingModule(ModuleInterface):
    """建图模块 —— 读取 config.yaml 中 param_dirs.mapping 目录的 yaml 参数文件
    （lidar-IMU 建图）

    与感知模块同构：注入建图专属目录与映射表，创建独立的 ParamStore，
    与感知模块互不干扰。目录下增删 yaml 自动适配。
    """

    module_name = "建图"
    config_key = "mapping"

    def __init__(self, store=None, config_dir=None):
        if store is None:
            store = ParamStore(
                config_dir if config_dir is not None else CONFIG.param_dir("mapping"),
                display_name_fn=mapping_display_name_for,
                key_names=MAPPING_KEY_NAMES,
                group_names=MAPPING_GROUP_NAMES,
            )
        self.store = store
        self.store.load_all()

    def groups(self):
        return [YamlGroupAdapter(fs) for fs in self.store.files()]

    def save(self):
        """一键保存该模块所有 yaml 文件；返回 (ok, 汇总消息)"""
        return self.store.save_all()

    def reload(self):
        """全部重新读盘（丢弃未保存修改）；返回变化的文件名列表"""
        return self.store.reload_all()


class PlanningModule(ModuleInterface):
    """规划模块 —— 读取 config.yaml 中 param_dirs.planning 目录的 yaml 参数文件

    与感知/建图模块同构：注入规划专属目录与映射表，创建独立的 ParamStore。
    目前包含：路径生成(skidpad)、速度规划(velocity_planner)、
    QP 优化(qp)、样条插值(path_planner_interp)。
    """

    module_name = "规划"
    config_key = "planning"

    def __init__(self, store=None, config_dir=None):
        if store is None:
            store = ParamStore(
                config_dir if config_dir is not None else CONFIG.param_dir("planning"),
                display_name_fn=planning_display_name_for,
                key_names=PLANNING_KEY_NAMES,
                group_names=PLANNING_GROUP_NAMES,
            )
        self.store = store
        self.store.load_all()

    def groups(self):
        return [YamlGroupAdapter(fs) for fs in self.store.files()]

    def save(self):
        """一键保存该模块所有 yaml 文件；返回 (ok, 汇总消息)"""
        return self.store.save_all()

    def reload(self):
        """全部重新读盘（丢弃未保存修改）；返回变化的文件名列表"""
        return self.store.reload_all()


class ControlModule(ModuleInterface):
    """控制模块 —— 待配置参数组"""

    module_name = "控制"

    def groups(self):
        return []


class SDKModule(ModuleInterface):
    """SDK模块 —— 待配置参数组"""

    module_name = "驱动"

    def groups(self):
        return []


# 各模块的 yaml 目录：优先取「主配置 yaml」（config.yaml 的 param_panel.main_config）
# 里 param_dirs 段的配置，没设主配置就用本项目 config.yaml 的 param_dirs。
# 在面板上换主配置会立即生效并写回 config.yaml，下次启动即按这里加载。
_PARAM_DIRS = active_param_dirs()

# 五个模块的注册列表（增删模块改这里即可）
# 感知 / 建图 / 规划已接入 yaml 参数；其余模块待配置
MODULES = [
    PerceptionModule(config_dir=_PARAM_DIRS.get("perception", "")),
    MappingModule(config_dir=_PARAM_DIRS.get("mapping", "")),
    PlanningModule(config_dir=_PARAM_DIRS.get("planning", "")),
    ControlModule(),
    SDKModule(),
]


# ---------------------------------------------------------------------------
#  UI
# ---------------------------------------------------------------------------


def _lerp_color(c1, c2, t):
    """按 t(0~1) 在两种颜色间线性插值（含 alpha）

    注意必须带上 alpha：起始色若是 QColor(0, 0, 0, 0)（透明），
    丢掉 alpha 会变成"不透明黑"，静息态就会被涂成黑块。
    """
    return QtGui.QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
        int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
    )


class _ModuleRow(QtWidgets.QPushButton):
    """横向模块选择单元：悬停/按压/选中背景平滑过渡，选中项底部强调条"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._hover = 0.0
        self._press = 0.0
        self._active = 0.0
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedHeight(36)
        self._hover_anim = QtCore.QPropertyAnimation(self, b"hover", self)
        self._hover_anim.setDuration(120)
        self._hover_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._press_anim = QtCore.QPropertyAnimation(self, b"press", self)
        self._press_anim.setDuration(90)
        self._press_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._active_anim = QtCore.QPropertyAnimation(self, b"active", self)
        self._active_anim.setDuration(160)
        self._active_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

    # ----- 动画属性 -----

    def _get_hover(self):
        return self._hover

    def _set_hover(self, v):
        self._hover = v
        self.update()

    hover = QtCore.Property(float, _get_hover, _set_hover)

    def _get_press(self):
        return self._press

    def _set_press(self, v):
        self._press = v
        self.update()

    press = QtCore.Property(float, _get_press, _set_press)

    def _get_active(self):
        return self._active

    def _set_active(self, v):
        self._active = v
        self.update()

    active = QtCore.Property(float, _get_active, _set_active)

    def set_active(self, on):
        """选中状态（平滑切换）"""
        self._active_anim.stop()
        self._active_anim.setStartValue(self._active)
        self._active_anim.setEndValue(1.0 if on else 0.0)
        self._active_anim.start()

    # ----- 事件 -----

    def enterEvent(self, e):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._press_anim.stop()
        self._press_anim.setStartValue(self._press)
        self._press_anim.setEndValue(1.0)
        self._press_anim.start()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._press_anim.stop()
        self._press_anim.setStartValue(self._press)
        self._press_anim.setEndValue(0.0)
        self._press_anim.start()
        super().mouseReleaseEvent(e)

    # ----- 绘制 -----

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = self.rect()
        # 底色：本控件带 QSS 背景规则，Qt 会按“不透明”处理、不再绘制父控件内容，
        # 因此必须自行铺满整块，否则未绘制区域会露出黑色残影
        base = T.qcolor("card_bg")
        p.fillRect(r, base)
        # 背景：悬停提亮 → 按压加深 → 选中淡绿底
        bg = _lerp_color(base, T.qcolor("hover"), self._hover)
        bg = _lerp_color(bg, T.qcolor("press"), self._press)
        bg = _lerp_color(bg, T.qcolor("active_soft"), self._active)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(QtCore.QRectF(0, 0, r.width() - 1, r.height() - 1), 8, 8)
        # 底部强调条（选中时淡入）
        if self._active > 0:
            p.setBrush(T.qcolor("accent", alpha=int(255 * self._active)))
            p.drawRoundedRect(QtCore.QRectF(10, r.height() - 4,
                                            r.width() - 20, 2), 1, 1)
        # 模块名（居中）
        f = self.font()
        f.setPixelSize(12)
        p.setFont(f)
        p.setPen(_lerp_color(T.qcolor("fg"), T.qcolor("accent"), self._active))
        p.drawText(QtCore.QRect(2, 0, r.width() - 4, r.height()),
                   QtCore.Qt.AlignCenter, self.text())
        p.end()


class _EditablePage(QtWidgets.QWidget):
    """一个可编辑模块的参数页：提示条 + yaml 目录 + 滚动卡片区 + 底部保存条

    每个模块（感知/建图/...）各持有一个页面实例，拥有独立的 store、
    卡片列表、保存状态与外部修改处理，互不干扰。
    """

    def __init__(self, module, store, parent=None):
        super().__init__(parent)
        self._module = module
        self.store = store
        self._cards = []
        self._cards_by_name = {}
        self._pending_conflict = None
        T.styled(self, INPUT_QSS)  # 输入控件样式（仅本页生效）

        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(8, 12, 8, 8)
        v.setSpacing(8)

        # 外部修改提示条（默认隐藏）
        self._notify_bar = NotifyBar()
        self._notify_bar.reload_requested.connect(self._on_conflict_reload)
        self._notify_bar.ignore_requested.connect(self._notify_bar.hide_bar)
        v.addWidget(self._notify_bar)

        # 当前 yaml 文件夹（绝对路径，便于确认导入的目录）
        self._dir_label = QtWidgets.QLabel()
        T.styled(self._dir_label, "color: @fg_faint; font-size: 10px;")
        self._dir_label.setWordWrap(True)
        v.addWidget(self._dir_label)

        # 目录里没有 yaml 时的提示（有卡片时隐藏）
        self._empty_hint = QtWidgets.QLabel("该目录下没有 .yaml 参数文件")
        self._empty_hint.setAlignment(QtCore.Qt.AlignCenter)
        self._empty_hint.setWordWrap(True)
        T.styled(self._empty_hint, "color: @fg_faint; font-size: 12px;")
        v.addWidget(self._empty_hint)

        # 滚动卡片区（每 yaml 一张卡片）
        cards_w = QtWidgets.QWidget()
        self._cards_lay = QtWidgets.QVBoxLayout(cards_w)
        self._cards_lay.setContentsMargins(0, 0, 0, 0)
        self._cards_lay.setSpacing(10)
        for g in module.groups():
            card = GroupCard(g)
            card.changed.connect(self._refresh_save_state)
            card.rebuild()
            self._cards_lay.addWidget(card)
            self._cards.append(card)
            self._cards_by_name[g.filename] = card
        self._cards_lay.addStretch(1)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        T.styled(scroll, "QScrollArea { background: transparent; border: none; }")
        T.styled(scroll.viewport(), "background: transparent;")
        scroll.setWidget(cards_w)
        v.addWidget(scroll, stretch=1)

        # 底部保存条
        bar = QtWidgets.QWidget()
        bl = QtWidgets.QHBoxLayout(bar)
        bl.setContentsMargins(0, 2, 0, 0)
        bl.setSpacing(8)
        self._save_summary = QtWidgets.QLabel()
        T.styled(self._save_summary, "color: @fg_dim; font-size: 11px;")
        self._save_btn = SaveButton("保存全部修改")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_all)
        bl.addWidget(self._save_summary, stretch=1)
        bl.addWidget(self._save_btn)
        v.addWidget(bar)

        # 外部修改监控：无冲突自动重载；有冲突提示用户；文件增删重建卡片
        store.file_changed.connect(self._on_file_changed)
        store.file_conflict.connect(self._on_file_conflict)
        store.files_scanned.connect(self._rebuild_cards)

        self._update_dir_label()
        self._refresh_save_state()
        self._update_empty_hint()

    # ------------------------------------------------------------------
    #  切换参数目录（主配置切换时由面板调用）
    # ------------------------------------------------------------------

    def set_config_dir(self, config_dir):
        """换本页扫描的 yaml 目录；目录没变返回 False

        数据层重扫新目录（files_scanned → _rebuild_cards 重建卡片）。
        """
        if not self.store.set_config_dir(config_dir):
            return False
        self._update_dir_label()
        return True

    def _update_dir_label(self):
        """刷新顶部「yaml 目录」标签（完整路径过长，另存 tooltip）"""
        d = self.store._config_dir
        self._dir_label.setText("yaml 目录：%s" % (d if d else "未配置"))
        self._dir_label.setToolTip(d)

    def _update_empty_hint(self):
        """没有卡片时显示「目录下没有 yaml」提示，避免只剩一个路径标签"""
        self._empty_hint.setVisible(not self._cards)

    # ------------------------------------------------------------------
    #  保存 / 刷新 / 外部修改（页面级，状态独立）
    # ------------------------------------------------------------------

    def _refresh_save_state(self):
        """刷新保存条状态（修改计数 / 按钮可用性）"""
        n = self.store.dirty_count()
        self._save_btn.setEnabled(n > 0)
        if n > 0:
            self._save_summary.setText("%d 项修改待保存" % n)
            T.styled(self._save_summary, "color: @accent; font-size: 11px;")
        else:
            self._save_summary.setText("所有修改已保存")
            T.styled(self._save_summary, "color: @fg_faint; font-size: 11px;")

    def _save_all(self):
        """一键保存本模块全部 yaml 文件"""
        ok, msg = self._module.save()
        self._save_btn.set_result(ok, msg)
        for card in self._cards:
            card.refresh_dirty()
        self._refresh_save_state()

    def reload_all(self):
        """目录扫描 + 全部重新读盘（丢弃未保存修改）"""
        self.store.scan()  # 捕捉文件增删（内部发 files_scanned → 重建卡片）
        changed = self.store.reload_all()
        for name in changed:
            card = self._cards_by_name.get(name)
            if card is not None:
                card.rebuild()
        self._refresh_save_state()

    def _rebuild_cards(self):
        """目录扫描发现文件增删：按最新文件列表重建全部卡片"""
        for card in self._cards:
            self._cards_lay.removeWidget(card)
            card.deleteLater()
        self._cards = []
        self._cards_by_name = {}
        for g in self._module.groups():
            card = GroupCard(g)
            card.changed.connect(self._refresh_save_state)
            card.rebuild()
            self._cards_lay.insertWidget(self._cards_lay.count() - 1, card)
            self._cards.append(card)
            self._cards_by_name[g.filename] = card
        self._refresh_save_state()
        self._update_empty_hint()

    def _on_file_changed(self, filename):
        """外部修改文件且无本地冲突：数据层已重载，重建对应卡片"""
        card = self._cards_by_name.get(filename)
        if card is not None:
            card.rebuild()
        self._refresh_save_state()

    def _on_file_conflict(self, filename):
        """外部修改文件但本地有未保存修改：提示用户选择"""
        self._pending_conflict = filename
        self._notify_bar.show_message(filename)

    def _on_conflict_reload(self):
        """用户选择「重新加载」：丢弃本地修改，按磁盘内容重建"""
        name = self._pending_conflict
        card = self._cards_by_name.get(name) if name else None
        if card is not None:
            card._adapter.file_store.reload()
            card.rebuild()
        self._notify_bar.hide_bar()
        self._pending_conflict = None
        self._refresh_save_state()


class ParamModificationPanel(QtWidgets.QWidget):
    """参数修改主面板：上方横向模块选择区 + 下方参数组内容区（固定宽 320）"""

    # 主配置切换并全局重载后发出：主窗口据此刷新其他面板
    config_applied = QtCore.Signal()

    def __init__(self, modules=None, parent=None):
        super().__init__(parent)
        self.setObjectName("param-panel")
        self.setFixedWidth(320)
        self._modules = list(modules) if modules is not None else list(MODULES)
        self._rows = []
        self._fade_anims = []

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 16)
        root.setSpacing(12)

        # 标题行：标题 + 右侧重新读取按钮
        title_row = QtWidgets.QHBoxLayout()
        title_row.setSpacing(6)
        title = QtWidgets.QLabel("参数修改")
        T.styled(title, "color: @fg; font-size: 15px; font-weight: 600; "
                        "letter-spacing: 0.01em;")
        title_row.addWidget(title)
        title_row.addStretch(1)
        self._refresh_btn = QtWidgets.QPushButton("\u21bb")
        self._refresh_btn.setFixedSize(24, 24)
        self._refresh_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._refresh_btn.setToolTip("重新读取所有 yaml 文件（丢弃未保存的修改）")
        T.styled(
            self._refresh_btn,
            "QPushButton { background: transparent; color: @fg_dim; border: none;"
            " border-radius: 12px; font-size: 14px; }"
            "QPushButton:hover { background: @hover; color: @fg; }"
            "QPushButton:pressed { background: @press; }"
            "QPushButton:disabled { color: @fg_disabled; }")
        self._refresh_btn.clicked.connect(self._reload_all)
        title_row.addWidget(self._refresh_btn)
        root.addLayout(title_row)

        # 主配置行：显示当前生效的「主配置 yaml」——整个程序的配置来源
        # （相机话题 / 快捷启动 / bag 录制 / 实时数据 / 各模块参数目录）；
        # 点「浏览」选一个 yaml 即整套参数导入并立即生效（涉及 ROS 订阅的需重启）
        self._main_config_path = CONFIG.param_main_config()
        main_row = QtWidgets.QHBoxLayout()
        main_row.setSpacing(6)
        main_label = QtWidgets.QLabel("主配置")
        T.styled(main_label, "color: @fg_dim; font-size: 11px;")
        main_row.addWidget(main_label)
        self._main_config_edit = QtWidgets.QLineEdit()
        self._main_config_edit.setReadOnly(True)
        self._main_config_edit.setPlaceholderText("未指定（用本目录 config.yaml）")
        self._main_config_edit.setText(self._main_config_path)
        self._main_config_edit.setToolTip(self._main_config_path)
        T.styled(
            self._main_config_edit,
            "QLineEdit { background: @input_bg; color: @fg_dim; border: 1px solid"
            " @input_border; border-radius: 6px; padding: 2px 6px; font-size: 11px; }"
            "QLineEdit:focus { border-color: @accent; }")
        main_row.addWidget(self._main_config_edit, stretch=1)
        self._browse_main_btn = QtWidgets.QPushButton("浏览")
        self._browse_main_btn.setFixedHeight(24)
        self._browse_main_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._browse_main_btn.setToolTip(
            "选择一个 config.yaml 作为整个程序的配置来源：\n"
            "相机话题 / 快捷启动脚本 / bag 录制话题 / 实时数据项 / 各模块参数目录。\n"
            "未写到的段沿用本项目 config；路径会记住（下次启动仍生效）。")
        T.styled(
            self._browse_main_btn,
            # min-height: 0 才能让 setFixedHeight(24) 生效（与左侧输入框同高）
            "QPushButton { background: @input_bg; color: @fg; border: 1px solid"
            " @input_border; border-radius: 6px; padding: 2px 10px; font-size: 11px;"
            " min-height: 0px; }"
            "QPushButton:hover { background: @hover; }"
            "QPushButton:pressed { background: @press; }"
            "QPushButton:disabled { color: @fg_disabled; }")
        self._browse_main_btn.clicked.connect(self._browse_main_config)
        main_row.addWidget(self._browse_main_btn)
        root.addLayout(main_row)

        # 可编辑页面列表（感知/建图等已接入 yaml 的模块各占一页）
        self._editable_pages = []
        self._refresh_btn.setEnabled(False)

        # 模块选择区（横向分段）
        selector = QtWidgets.QWidget()
        sel_layout = QtWidgets.QHBoxLayout(selector)
        sel_layout.setContentsMargins(0, 0, 0, 0)
        sel_layout.setSpacing(6)
        for i, m in enumerate(self._modules):
            row = _ModuleRow(m.module_name)
            row.clicked.connect(lambda _=False, idx=i: self._select_module(idx))
            sel_layout.addWidget(row, stretch=1)
            self._rows.append(row)
        root.addWidget(selector)

        # 分隔线
        divider = QtWidgets.QFrame()
        divider.setFixedHeight(1)
        T.styled(divider, "background-color: @divider; border: none;")
        root.addWidget(divider)

        # 内容区：每个模块一页（当前为空态占位，参数组接入后自动渲染）
        self._stack = QtWidgets.QStackedWidget()
        self._pages = []
        for m in self._modules:
            page = self._build_module_page(m)
            self._stack.addWidget(page)
            self._pages.append(page)
        root.addWidget(self._stack, stretch=1)

        self._select_module(0)

    # ----- 模块页构建 -----

    def _build_module_page(self, module):
        """构建单个模块的内容页

        模块带 store（感知/建图等已接入 yaml）→ 可编辑参数页（独立实例），
        目录为空时页内给出提示；否则显示空态占位。
        """
        store = getattr(module, "store", None)
        if store is not None:
            page = _EditablePage(module, store)
            self._editable_pages.append(page)
            self._refresh_btn.setEnabled(True)
            return page
        page = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(page)
        v.setContentsMargins(8, 12, 8, 12)
        v.addStretch(1)
        label = QtWidgets.QLabel("「%s」参数组待配置" % module.module_name)
        label.setAlignment(QtCore.Qt.AlignCenter)
        T.styled(label, "color: @fg_faint; font-size: 12px;")
        label.setWordWrap(True)
        v.addWidget(label)
        v.addStretch(1)
        return page



    # ------------------------------------------------------------------
    #  保存 / 刷新 / 外部修改
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    #  刷新（对所有可编辑页面生效）
    # ------------------------------------------------------------------

    def _reload_all(self):
        """重新读取全部 yaml 文件（有未保存修改时需确认）"""
        if not self._confirm_discard_dirty("重新加载"):
            return
        for p in list(self._editable_pages):
            p.reload_all()

    def _confirm_discard_dirty(self, action):
        """有未保存修改时先确认；返回 True = 继续（这些修改会被丢弃）"""
        n = sum(p.store.dirty_count() for p in self._editable_pages)
        if n <= 0:
            return True
        ret = QtWidgets.QMessageBox.question(
            self, action,
            "有 %d 项未保存的修改，%s将丢弃它们。\n继续？" % (n, action),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)
        return ret == QtWidgets.QMessageBox.Yes

    # ------------------------------------------------------------------
    #  主配置 yaml：整个程序的配置来源（各业务段 + 各模块参数目录）
    # ------------------------------------------------------------------

    def _browse_main_config(self):
        """选一个「主配置 yaml」，把它的业务段整体作为程序配置来源"""
        start = self._main_config_path or QtCore.QDir.homePath()
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择主配置 yaml（整个程序的配置来源）", start,
            "YAML 文件 (*.yaml *.yml);;所有文件 (*)")
        if not path:
            return
        sections = main_config_sections_of(path)
        if not sections:
            QtWidgets.QMessageBox.warning(
                self, "无法导入",
                "这个文件里没有可用的配置段，读不到任何参数。\n\n"
                "请选择形如 config/config.yaml 的主配置文件：\n"
                "它用 camera / launch / bag / data_items / param_dirs\n"
                "等段描述整个程序的配置。")
            return
        if not self._confirm_discard_dirty("切换主配置"):
            return
        self._apply_main_config(path, sections)

    def _apply_main_config(self, path, sections):
        """应用主配置：写回本项目 config.yaml → 全局重载 → 刷新各界面

        主配置写了的业务段以它为准，没写的沿用本项目 config.yaml。
        可原地刷新的（相机候选话题 / 脚本目录与列表 / bag 录制话题 / 参数目录）
        立即生效；相机默认订阅话题与实时数据项由 ROS 节点在启动时建立，
        运行中不重建订阅，需重启程序。
        """
        self._main_config_path = path
        self._main_config_edit.setText(path)
        self._main_config_edit.setToolTip(path)
        # 记住路径（下次启动按它加载）；写不进去只打印警告，本次运行仍然生效
        save_param_main_config(path)

        # 重载前记下运行中无法重建的订阅参数，用来精确提示「哪些需要重启」
        old_initial = CONFIG.camera_initial_topics()
        old_items = [(i["key"], i["topic"]) for i in CONFIG.data_items()]

        # 原地重载全局配置：所有 from myos_config import CONFIG 的持有者立即看到新值
        reload_config()

        # 参数模块目录按新配置逐个刷新（含主配置没写到的模块回退本项目）
        dirs = active_param_dirs()
        for page in list(self._editable_pages):
            key = getattr(page._module, "config_key", None)
            if not key:
                continue                    # 控制 / 驱动等尚未接入 yaml 的模块
            page.set_config_dir(dirs.get(key, ""))

        # 主题等其余界面按新配置刷新（主题是引导段，固定取本项目，不受影响）
        self.config_applied.emit()

        need_restart = []
        if CONFIG.camera_initial_topics() != old_initial:
            need_restart.append("相机默认订阅话题")
        if [(i["key"], i["topic"]) for i in CONFIG.data_items()] != old_items:
            need_restart.append("实时数据项")
        msg = "已应用主配置：\n%s\n\n" % path
        if need_restart:
            msg += "「%s」需重启程序后生效。\n" % "、".join(need_restart)
        msg += "相机候选话题、快捷启动脚本、bag 录制话题、参数目录已立即刷新。"
        QtWidgets.QMessageBox.information(self, "主配置已应用", msg)



    # ----- 切换逻辑 -----

    def _select_module(self, idx):
        """选中第 idx 个模块：高亮行 + 内容页淡入"""
        for i, row in enumerate(self._rows):
            row.set_active(i == idx)
        self._stack.setCurrentIndex(idx)
        self._fade_in(self._pages[idx])

    def _fade_in(self, page):
        """内容页淡入（OutCubic），结束后移除特效避免压平子级阴影"""
        eff = QtWidgets.QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(eff)
        eff.setOpacity(0.0)
        fade = QtCore.QPropertyAnimation(eff, b"opacity", page)
        fade.setDuration(160)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        fade.finished.connect(lambda e=eff: self._clear_effect(page, e))
        fade.start()
        self._fade_anims.append(fade)

    @staticmethod
    def _clear_effect(page, eff):
        """仅当页面仍挂着同一特效时才移除（防止旧动画误清新特效）"""
        if page.graphicsEffect() is eff:
            page.setGraphicsEffect(None)

    # ----- 面板外观 -----

    def paintEvent(self, e):
        """绘制面板圆角底 + 描边"""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtGui.QPen(T.qcolor("card_border"), 1))
        p.setBrush(T.qcolor("card_bg"))
        p.drawRoundedRect(QtCore.QRectF(0.5, 0.5,
                                        self.width() - 1, self.height() - 1), 12, 12)
        p.end()
