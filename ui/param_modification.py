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

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

from PySide6 import QtCore, QtWidgets, QtGui

from param_store import (
    ParamStore,
    PERCEPTION_CONFIG_DIR,
    perception_display_name_for,
    PERCEPTION_KEY_NAMES,
    PERCEPTION_GROUP_NAMES,
    MAPPING_CONFIG_DIR,
    mapping_display_name_for,
    MAPPING_KEY_NAMES,
    MAPPING_GROUP_NAMES,
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
        config_dir: yaml 目录路径；默认 config/param/config
    """

    module_name = "感知"

    def __init__(self, store=None, config_dir=None):
        # 感知模块的 ParamStore：注入感知专属目录与映射表
        # （后续建图/规划等模块各自创建自己的 ParamStore，互不混淆）
        if store is None:
            store = ParamStore(
                config_dir if config_dir is not None else PERCEPTION_CONFIG_DIR,
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
    """建图模块 —— 读取 config/slam 下的 yaml 参数文件（lidar-IMU 建图）

    与感知模块同构：注入建图专属目录与映射表，创建独立的 ParamStore，
    与感知模块互不干扰。目录下增删 yaml 自动适配。
    """

    module_name = "建图"

    def __init__(self, store=None, config_dir=None):
        if store is None:
            store = ParamStore(
                config_dir if config_dir is not None else MAPPING_CONFIG_DIR,
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
    """规划模块 —— 待配置参数组"""

    module_name = "规划"

    def groups(self):
        return []


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


# 五个模块的注册列表（增删模块改这里即可）
# 感知 / 建图已接入 yaml 参数；其余模块待配置
MODULES = [
    PerceptionModule(),
    MappingModule(),
    PlanningModule(),
    ControlModule(),
    SDKModule(),
]


# ---------------------------------------------------------------------------
#  UI
# ---------------------------------------------------------------------------


def _lerp_color(c1, c2, t):
    """按 t(0~1) 在两种颜色间线性插值"""
    return QtGui.QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
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
        # 背景：悬停提亮 → 按压加深 → 选中深绿底
        bg = _lerp_color(QtGui.QColor(0, 0, 0, 0), QtGui.QColor("#1b1f29"), self._hover)
        bg = _lerp_color(bg, QtGui.QColor("#14161d"), self._press)
        bg = _lerp_color(bg, QtGui.QColor("#182a26"), self._active)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(QtCore.QRectF(0, 0, r.width() - 1, r.height() - 1), 8, 8)
        # 底部强调条（选中时淡入）
        if self._active > 0:
            p.setBrush(QtGui.QColor(0, 212, 170, int(255 * self._active)))
            p.drawRoundedRect(QtCore.QRectF(10, r.height() - 4,
                                            r.width() - 20, 2), 1, 1)
        # 模块名（居中）
        f = self.font()
        f.setPixelSize(12)
        p.setFont(f)
        p.setPen(_lerp_color(QtGui.QColor("#e5e5ea"), QtGui.QColor("#00d4aa"), self._active))
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
        self.setStyleSheet(INPUT_QSS)  # 输入控件深色样式（仅本页生效）

        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(8, 12, 8, 8)
        v.setSpacing(8)

        # 外部修改提示条（默认隐藏）
        self._notify_bar = NotifyBar()
        self._notify_bar.reload_requested.connect(self._on_conflict_reload)
        self._notify_bar.ignore_requested.connect(self._notify_bar.hide_bar)
        v.addWidget(self._notify_bar)

        # 当前 yaml 文件夹（绝对路径，便于确认导入的目录）
        dir_label = QtWidgets.QLabel("yaml 目录：%s" % store._config_dir)
        dir_label.setStyleSheet("color: #565a64; font-size: 10px;")
        dir_label.setWordWrap(True)
        v.addWidget(dir_label)

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
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setStyleSheet("background: transparent;")
        scroll.setWidget(cards_w)
        v.addWidget(scroll, stretch=1)

        # 底部保存条
        bar = QtWidgets.QWidget()
        bl = QtWidgets.QHBoxLayout(bar)
        bl.setContentsMargins(0, 2, 0, 0)
        bl.setSpacing(8)
        self._save_summary = QtWidgets.QLabel()
        self._save_summary.setStyleSheet("color: #8e8e93; font-size: 11px;")
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

        self._refresh_save_state()

    # ------------------------------------------------------------------
    #  保存 / 刷新 / 外部修改（页面级，状态独立）
    # ------------------------------------------------------------------

    def _refresh_save_state(self):
        """刷新保存条状态（修改计数 / 按钮可用性）"""
        n = self.store.dirty_count()
        self._save_btn.setEnabled(n > 0)
        if n > 0:
            self._save_summary.setText("%d 项修改待保存" % n)
            self._save_summary.setStyleSheet("color: #00d4aa; font-size: 11px;")
        else:
            self._save_summary.setText("所有修改已保存")
            self._save_summary.setStyleSheet("color: #565a64; font-size: 11px;")

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
        title.setStyleSheet("color: #e5e5ea; font-size: 15px; font-weight: 600; "
                            "letter-spacing: 0.01em;")
        title_row.addWidget(title)
        title_row.addStretch(1)
        self._refresh_btn = QtWidgets.QPushButton("\u21bb")
        self._refresh_btn.setFixedSize(24, 24)
        self._refresh_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._refresh_btn.setToolTip("重新读取所有 yaml 文件（丢弃未保存的修改）")
        self._refresh_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #8e8e93; border: none;"
            " border-radius: 12px; font-size: 14px; }"
            "QPushButton:hover { background: #1b1f29; color: #e5e5ea; }"
            "QPushButton:pressed { background: #14161d; }"
            "QPushButton:disabled { color: #3a3e49; }")
        self._refresh_btn.clicked.connect(self._reload_all)
        title_row.addWidget(self._refresh_btn)
        root.addLayout(title_row)

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
        divider.setStyleSheet("background-color: #1f232d; border: none;")
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

        模块带 store（感知/建图等已接入 yaml）→ 可编辑参数页（独立实例）；
        否则显示空态占位。
        """
        store = getattr(module, "store", None)
        if store is not None and module.groups():
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
        label.setStyleSheet("color: #565a64; font-size: 12px;")
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
        pages = list(self._editable_pages)
        n = sum(p.store.dirty_count() for p in pages)
        if n > 0:
            ret = QtWidgets.QMessageBox.question(
                self, "重新加载",
                "有 %d 项未保存的修改，重新加载将丢弃它们。\n继续？" % n,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No)
            if ret != QtWidgets.QMessageBox.Yes:
                return
        for p in pages:
            p.reload_all()



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
        p.setPen(QtGui.QPen(QtGui.QColor("#1f232d"), 1))
        p.setBrush(QtGui.QColor("#12141a"))
        p.drawRoundedRect(QtCore.QRectF(0.5, 0.5,
                                        self.width() - 1, self.height() - 1), 12, 12)
        p.end()
