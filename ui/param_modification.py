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
    """感知模块 —— 待配置：YOLO / Pointpillars / 时间同步 等参数组"""

    module_name = "感知"

    def groups(self):
        return []


class MappingModule(ModuleInterface):
    """建图模块 —— 待配置参数组"""

    module_name = "建图"

    def groups(self):
        return []


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

        # 标题
        title = QtWidgets.QLabel("参数修改")
        title.setStyleSheet("color: #e5e5ea; font-size: 15px; font-weight: 600; "
                            "letter-spacing: 0.01em;")
        root.addWidget(title)

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
        """构建单个模块的内容页：目前为空态占位，参数组接入后在此渲染"""
        page = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(page)
        v.setContentsMargins(8, 12, 8, 12)
        v.addStretch(1)
        if module.groups():
            # 有参数组时逐组渲染（待实现）
            for g in module.groups():
                pass
        else:
            label = QtWidgets.QLabel("「%s」参数组待配置" % module.module_name)
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setStyleSheet("color: #565a64; font-size: 12px;")
            label.setWordWrap(True)
            v.addWidget(label)
        v.addStretch(1)
        return page

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
