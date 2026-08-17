# param_widgets.py — 参数修改面板的控件库
#
# 包含：参数行（数值/文本/布尔）、自绘开关、可折叠分组卡片、保存按钮、外部修改提示条。
# 动画遵循 Apple Fluid Interface 原则：
#   - 反馈在 pointer-down（按下即反馈）
#   - 所有动画基于当前呈现值，可被新动画平滑接管（可中断）
#   - 临界阻尼缓动（OutCubic）默认无回弹，仅展开/收起沿同一路径
#   - 状态切换零延迟

from PySide6 import QtCore, QtWidgets, QtGui


def _lerp_color(c1, c2, t):
    """按 t(0~1) 在两种颜色间线性插值"""
    return QtGui.QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
    )


# ---------------------------------------------------------------------------
#  输入框样式（QSS）—— 深底 + 荧光绿焦点，步进按钮自绘箭头
# ---------------------------------------------------------------------------

INPUT_QSS = """
QSpinBox, QDoubleSpinBox, QLineEdit {
    background-color: #1b1f29;
    border: 1px solid #262a35;
    border-radius: 6px;
    padding: 2px 6px;
    color: #e6e6ea;
    font-size: 12px;
    selection-background-color: #00d4aa;
    selection-color: #0c0d12;
}
QSpinBox:hover, QDoubleSpinBox:hover, QLineEdit:hover { border-color: #363c4d; }
QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus { border-color: #00d4aa; }
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border; subcontrol-position: top right;
    width: 15px; border-left: 1px solid #262a35;
    background: transparent; border-top-right-radius: 5px;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 15px; border-left: 1px solid #262a35;
    background: transparent; border-bottom-right-radius: 5px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background: #242938; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    width: 0; height: 0;
    border-left: 3px solid transparent; border-right: 3px solid transparent;
    border-bottom: 4px solid #8e8e93;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    width: 0; height: 0;
    border-left: 3px solid transparent; border-right: 3px solid transparent;
    border-top: 4px solid #8e8e93;
}
QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover { border-bottom-color: #e6e6ea; }
QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover { border-top-color: #e6e6ea; }
"""


def infer_step(value):
    """按数值数量级推断步长：1/2/5×10^k"""
    a = abs(float(value))
    if a >= 100:
        return 1.0
    if a >= 10:
        return 0.5
    if a >= 1:
        return 0.1
    if a >= 0.1:
        return 0.01
    if a >= 0.01:
        return 0.001
    if a >= 0.001:
        return 0.0001
    return 0.00001


def step_decimals(step):
    """步长 → 输入框保留小数位（至少 1 位，保证浮点可回写）"""
    s = repr(float(step))
    if "e" in s:
        return 6
    return max(1, len(s.split(".")[1]))


# ---------------------------------------------------------------------------
#  ToggleSwitch — 自绘开关（布尔参数）
# ---------------------------------------------------------------------------


class ToggleSwitch(QtWidgets.QAbstractButton):
    """胶囊轨道 + 滑块，切换 120ms OutCubic，按下时滑块轻微放大"""

    toggled = QtCore.Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(40, 22)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._t = 1.0 if checked else 0.0
        self._press = 0.0
        self._t_anim = QtCore.QPropertyAnimation(self, b"t", self)
        self._t_anim.setDuration(120)
        self._t_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._press_anim = QtCore.QPropertyAnimation(self, b"press", self)
        self._press_anim.setDuration(90)
        self._press_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

    def _get_t(self):
        return self._t

    def _set_t(self, v):
        self._t = v
        self.update()

    t = QtCore.Property(float, _get_t, _set_t)

    def _get_press(self):
        return self._press

    def _set_press(self, v):
        self._press = v
        self.update()

    press = QtCore.Property(float, _get_press, _set_press)

    def nextCheckState(self):
        super().nextCheckState()
        self._t_anim.stop()
        self._t_anim.setStartValue(self._t)
        self._t_anim.setEndValue(1.0 if self.isChecked() else 0.0)
        self._t_anim.start()
        self.toggled.emit(self.isChecked())

    def set_checked_external(self, value):
        """外部同步状态（保存/重载），不发信号、无动画、直接到最终位置"""
        self._t_anim.stop()
        self._t = 1.0 if value else 0.0
        self.setChecked(bool(value))
        self.update()

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

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()
        # 轨道：灰 → 荧光绿插值
        col = _lerp_color(QtGui.QColor("#2a2d38"), QtGui.QColor("#00d4aa"), self._t)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(col)
        p.drawRoundedRect(QtCore.QRectF(0.5, 0.5, w - 1, h - 1), h / 2, h / 2)
        # 滑块：按压时放大 3px（pointer-down 反馈）
        pad = 2
        slide = h - 2 * pad + 3 * self._press
        x = pad + self._t * (w - 2 * pad - slide)
        p.setBrush(QtGui.QColor("#ffffff"))
        p.drawEllipse(QtCore.QPointF(x + slide / 2, h / 2), slide / 2, slide / 2)
        p.end()


# ---------------------------------------------------------------------------
#  ParamRow — 单个参数行（名称 + 编辑控件 + 未保存圆点）
# ---------------------------------------------------------------------------


class ParamRow(QtWidgets.QWidget):
    """一行参数：左名称、右编辑控件；值变化发 changed(路径, 值) 信号

    控件按类型：int → QSpinBox；float → QDoubleSpinBox（步长按数量级）；
    str → QLineEdit（失焦/回车提交）；bool → ToggleSwitch。
    行背景悬停微亮（OutCubic），未保存时名称右侧圆点淡入。
    """

    changed = QtCore.Signal(tuple, object)

    NAME_W = 92   # 名称列宽
    ROW_H = 40    # 行高

    def __init__(self, pv, parent=None):
        super().__init__(parent)
        self._pv = pv
        self._hover = 0.0
        self._hover_anim = QtCore.QPropertyAnimation(self, b"hover", self)
        self._hover_anim.setDuration(120)
        self._hover_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.setFixedHeight(self.ROW_H)

        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.setSpacing(8)

        # 名称（过长省略）
        self.name_label = QtWidgets.QLabel(pv.display_name)
        self.name_label.setFixedWidth(self.NAME_W)
        self.name_label.setStyleSheet(
            "color: #8e8e93; font-size: 12px; background: transparent;")
        lay.addWidget(self.name_label)

        lay.addStretch(1)

        # 编辑控件
        self._editor = self._build_editor(pv)
        lay.addWidget(self._editor)

        # 未保存圆点
        self.dot = QtWidgets.QLabel()
        self.dot.setFixedSize(8, 8)
        self.dot.setStyleSheet(
            "background-color: #00d4aa; border-radius: 4px; background-clip: content;")
        self.dot.setVisible(False)
        lay.addWidget(self.dot)

    # ----- 控件构建 -----

    def _build_editor(self, pv):
        if pv.vtype == "number":
            if pv.is_int:
                box = QtWidgets.QSpinBox(self)
                box.setRange(-1000000000, 1000000000)
                box.setSingleStep(1)
                box.setValue(int(pv.value))
                box.valueChanged.connect(lambda v: self.changed.emit(pv.path, v))
            else:
                box = QtWidgets.QDoubleSpinBox(self)
                step = infer_step(pv.value)
                box.setRange(-1000000000.0, 1000000000.0)
                box.setSingleStep(step)
                box.setDecimals(step_decimals(step))
                box.setValue(float(pv.value))
                box.valueChanged.connect(lambda v: self.changed.emit(pv.path, v))
            return box
        if pv.vtype == "bool":
            sw = ToggleSwitch(bool(pv.value), self)
            sw.toggled.connect(lambda v: self.changed.emit(pv.path, v))
            return sw
        # text
        edit = QtWidgets.QLineEdit(str(pv.value), self)
        edit.setMinimumWidth(120)
        # 失焦 / 回车才提交，避免每敲一个字符就写内存
        edit.editingFinished.connect(lambda: self.changed.emit(pv.path, edit.text()))
        return edit

    @property
    def path(self):
        return self._pv.path

    # ----- 外部刷新 -----

    def set_value(self, value):
        """外部（保存/重载）同步控件值，不触发 changed"""
        ed = self._editor
        ed.blockSignals(True)
        if isinstance(ed, QtWidgets.QSpinBox):
            ed.setValue(int(value))
        elif isinstance(ed, QtWidgets.QDoubleSpinBox):
            ed.setValue(float(value))
        elif isinstance(ed, ToggleSwitch):
            if ed.isChecked() != bool(value):
                ed.set_checked_external(value)
        else:
            ed.setText(str(value))
        ed.blockSignals(False)

    def set_dirty(self, on):
        """未保存圆点淡入/淡出"""
        if on == self.dot.isVisible():
            return
        eff = QtWidgets.QGraphicsOpacityEffect(self.dot)
        self.dot.setGraphicsEffect(eff)
        eff.setOpacity(0.0 if not on else 1.0)
        self.dot.setVisible(True)
        fade = QtCore.QPropertyAnimation(eff, b"opacity", self)
        fade.setDuration(160)
        fade.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        if on:
            fade.setStartValue(0.0)
            fade.setEndValue(1.0)
        else:
            fade.setStartValue(1.0)
            fade.setEndValue(0.0)
            fade.finished.connect(lambda: self.dot.setVisible(False))
        fade.start()

    # ----- 悬停 / 绘制 -----

    def _get_hover(self):
        return self._hover

    def _set_hover(self, v):
        self._hover = v
        self.update()

    hover = QtCore.Property(float, _get_hover, _set_hover)

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

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        # 悬停微亮（很轻微，不抢内容）
        bg = _lerp_color(QtGui.QColor(0, 0, 0, 0), QtGui.QColor("#181b24"), self._hover)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(QtCore.QRectF(0.5, 1.0, self.width() - 1, self.height() - 2), 7, 7)
        p.end()


# ---------------------------------------------------------------------------
#  GroupCard — 可折叠分组卡片（一个 yaml 文件一张）
# ---------------------------------------------------------------------------


class _CardTitle(QtWidgets.QWidget):
    """卡片标题：箭头（旋转动画）+ 中文组名 + 文件名 + 未保存计数胶囊"""

    clicked = QtCore.Signal()

    def __init__(self, name, filename, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._name = name
        self._filename = filename
        self._angle = 90.0          # 箭头展开角（90° 表示展开）
        self._hover = 0.0
        self._count = 0
        self._angle_anim = QtCore.QPropertyAnimation(self, b"angle", self)
        self._angle_anim.setDuration(180)
        self._angle_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._hover_anim = QtCore.QPropertyAnimation(self, b"hover", self)
        self._hover_anim.setDuration(120)
        self._hover_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

    def _get_angle(self):
        return self._angle

    def _set_angle(self, v):
        self._angle = v
        self.update()

    angle = QtCore.Property(float, _get_angle, _set_angle)

    def _get_hover(self):
        return self._hover

    def _set_hover(self, v):
        self._hover = v
        self.update()

    hover = QtCore.Property(float, _get_hover, _set_hover)

    def set_angle(self, angle):
        """目标角度（0 折叠 / 90 展开）"""
        self._angle_anim.stop()
        self._angle_anim.setStartValue(self._angle)
        self._angle_anim.setEndValue(angle)
        self._angle_anim.start()

    def set_dirty_count(self, n):
        self._count = n
        self.update()

    def mousePressEvent(self, e):
        self.clicked.emit()
        super().mousePressEvent(e)

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

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()
        # 悬停背景
        bg = _lerp_color(QtGui.QColor(0, 0, 0, 0), QtGui.QColor("#171a23"), self._hover)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(QtCore.QRectF(0.5, 0.5, w - 1, h - 1), 7, 7)
        # 箭头（旋转）
        p.save()
        p.translate(16, h / 2)
        p.rotate(self._angle)
        tri = QtGui.QPolygonF([QtCore.QPointF(0, -3.5), QtCore.QPointF(0, 3.5),
                               QtCore.QPointF(4.5, 0)])
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor("#8e8e93"))
        p.drawPolygon(tri)
        p.restore()
        # 组名（第一行）
        f = self.font()
        f.setPixelSize(13)
        f.setWeight(QtGui.QFont.DemiBold)
        p.setFont(f)
        p.setPen(QtGui.QColor("#e5e5ea"))
        p.drawText(QtCore.QRect(30, 2, w - 150, 18), QtCore.Qt.AlignVCenter, self._name)
        # 文件名（第二行）
        f2 = self.font()
        f2.setPixelSize(10)
        p.setFont(f2)
        p.setPen(QtGui.QColor("#565a64"))
        p.drawText(QtCore.QRect(30, 20, w - 150, 15), QtCore.Qt.AlignVCenter, self._filename)
        # 未保存计数胶囊
        if self._count > 0:
            text = "%d 项未保存" % self._count
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(text)
            cw = tw + 18
            cx = w - cw - 12
            cy = (h - 18) / 2
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor(0, 212, 170, 26))
            p.drawRoundedRect(QtCore.QRectF(cx, cy, cw, 18), 9, 9)
            f3 = self.font()
            f3.setPixelSize(10)
            p.setFont(f3)
            p.setPen(QtGui.QColor("#00d4aa"))
            p.drawText(QtCore.QRect(int(cx), int(cy), int(cw), 18),
                       QtCore.Qt.AlignCenter, text)
        p.end()


class GroupCard(QtWidgets.QWidget):
    """一个 yaml 文件的可折叠卡片：标题 + 嵌套分组小标题 + 参数行

    信号：changed() — 任一参数被修改（供面板刷新保存条）
    """

    changed = QtCore.Signal()

    def __init__(self, adapter, parent=None):
        super().__init__(parent)
        self._adapter = adapter
        self._rows = []          # [(ParamRow, ParamValue)]
        self._collapsed = False

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._title = _CardTitle(adapter.group_name, adapter.filename, self)
        self._title.clicked.connect(self._toggle)
        root.addWidget(self._title)

        self._body = QtWidgets.QWidget(self)
        self._body_layout = QtWidgets.QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(10, 4, 10, 10)
        self._body_layout.setSpacing(4)
        root.addWidget(self._body)

        self._body_anim = QtCore.QPropertyAnimation(self._body, b"maximumHeight", self)
        self._body_anim.setDuration(200)
        self._body_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

    # ----- 渲染 -----

    def rebuild(self):
        """从数据层重建全部参数行（保存/外部重载后调用）"""
        while self._body_layout.count():
            item = self._body_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._rows = []
        prev_group = None
        for pv in self._adapter.params():
            if pv.group_name != prev_group and pv.group_name:
                g = QtWidgets.QLabel(pv.group_name)
                g.setContentsMargins(2, 6, 0, 0)
                g.setStyleSheet(
                    "color: #565a64; font-size: 11px; font-weight: 600;"
                    "background: transparent;")
                self._body_layout.addWidget(g)
                prev_group = pv.group_name
            row = ParamRow(pv)
            row.changed.connect(self._on_row_changed)
            self._body_layout.addWidget(row)
            self._rows.append((row, pv))
        self._body_layout.addStretch(1)
        self.refresh_dirty()
        # 高度同步：折叠态保持 0，展开态立即适应新内容
        if not self._collapsed:
            self._body_anim.stop()
            self._body.setMaximumHeight(self._body.sizeHint().height())

    def refresh_dirty(self):
        """按数据层 dirty 状态刷新行圆点与标题计数"""
        dirty_paths = self._adapter.file_store.dirty_paths()
        n = 0
        for row, pv in self._rows:
            on = pv.path in dirty_paths
            row.set_dirty(on)
            n += 1 if on else 0
        self._title.set_dirty_count(n)

    # ----- 折叠 / 展开 -----

    def _toggle(self):
        if self._collapsed:
            self._expand()
        else:
            self._collapse()

    def _expand(self):
        self._collapsed = False
        self._title.set_angle(90.0)
        target = self._body.sizeHint().height()
        self._body_anim.stop()
        self._body_anim.setStartValue(self._body.maximumHeight())
        self._body_anim.setEndValue(target)
        self._body_anim.start()

    def _collapse(self):
        self._collapsed = True
        self._title.set_angle(0.0)
        self._body_anim.stop()
        self._body_anim.setStartValue(self._body.maximumHeight())
        self._body_anim.setEndValue(0)
        self._body_anim.start()

    # ----- 信号 -----

    def _on_row_changed(self, path, value):
        self._adapter.file_store.set_value(path, value)
        self.refresh_dirty()
        self.changed.emit()

    # ----- 外观 -----

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtGui.QPen(QtGui.QColor("#1f232d"), 1))
        p.setBrush(QtGui.QColor("#12141a"))
        p.drawRoundedRect(QtCore.QRectF(0.5, 0.5,
                                        self.width() - 1, self.height() - 1), 12, 12)
        p.end()


# ---------------------------------------------------------------------------
#  SaveButton — 保存按钮（自绘，带成功/失败状态）
# ---------------------------------------------------------------------------


class SaveButton(QtWidgets.QPushButton):
    """主按钮：荧光绿底，hover 提亮、按下微缩（pointer-down 反馈）

    set_result(ok, msg)：ok → "已保存 ✓" 600ms 恢复；失败 → "保存失败" 红色 2s，
    失败原因放 tooltip。
    """

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._hover = 0.0
        self._press = 0.0
        self._tint = 0.0            # 0 正常 / 1 保存成功 / 2 保存失败
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedHeight(32)
        self.setMinimumWidth(120)
        self._hover_anim = QtCore.QPropertyAnimation(self, b"hover", self)
        self._hover_anim.setDuration(120)
        self._hover_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._press_anim = QtCore.QPropertyAnimation(self, b"press", self)
        self._press_anim.setDuration(90)
        self._press_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._tint_anim = QtCore.QPropertyAnimation(self, b"tint", self)
        self._tint_anim.setDuration(160)
        self._tint_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._reset_timer = QtCore.QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self._reset_state)

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

    def _get_tint(self):
        return self._tint

    def _set_tint(self, v):
        self._tint = v
        self.update()

    tint = QtCore.Property(float, _get_tint, _set_tint)

    def set_result(self, ok, msg):
        self.setToolTip(msg)
        self._reset_timer.stop()
        self._tint_anim.stop()
        self._tint_anim.setStartValue(self._tint)
        self._tint_anim.setEndValue(1.0 if ok else 2.0)
        self._tint_anim.start()
        self.setText("已保存 ✓" if ok else "保存失败")
        self._reset_timer.start(1200 if ok else 2600)

    def _reset_state(self):
        self._tint_anim.stop()
        self._tint_anim.setStartValue(self._tint)
        self._tint_anim.setEndValue(0.0)
        self._tint_anim.start()
        self.setText("保存全部修改")

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

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()
        enabled = self.isEnabled()
        # 底色：荧光绿 → hover 提亮 → press 加深；失败时橙色
        base = QtGui.QColor("#00d4aa")
        if self._tint >= 1.5:
            base = QtGui.QColor("#ff6b35")
        elif self._tint >= 0.5:
            base = QtGui.QColor("#2ee0bd")
        if not enabled:
            base = QtGui.QColor("#22303c")
        bg = _lerp_color(base, base.lighter(112), self._hover)
        bg = _lerp_color(bg, bg.darker(112), self._press)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(bg)
        r = QtCore.QRectF(0.5 + self._press * 0.6, 0.5 + self._press * 0.6,
                          w - 1 - self._press * 1.2, h - 1 - self._press * 1.2)
        p.drawRoundedRect(r, 9, 9)
        # 文字
        f = self.font()
        f.setPixelSize(12)
        f.setWeight(QtGui.QFont.DemiBold)
        p.setFont(f)
        col = QtGui.QColor("#0c0d12") if enabled else QtGui.QColor("#5b6a75")
        p.setPen(col)
        p.drawText(QtCore.QRect(0, 0, w, h), QtCore.Qt.AlignCenter, self.text())
        p.end()


# ---------------------------------------------------------------------------
#  NotifyBar — 外部修改提示条（橙色）
# ---------------------------------------------------------------------------


class NotifyBar(QtWidgets.QWidget):
    """「文件已被外部修改」提示条：文本 + [重新加载] [忽略]

    显示/隐藏带 200ms 淡入淡出 + 轻微位移（进入与退出沿同一路径）。
    """

    reload_requested = QtCore.Signal()
    ignore_requested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setVisible(False)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 6, 0)
        lay.setSpacing(8)

        icon = QtWidgets.QLabel("⚠")
        icon.setStyleSheet("color: #ff6b35; font-size: 13px; background: transparent;")
        lay.addWidget(icon)

        self.label = QtWidgets.QLabel()
        self.label.setStyleSheet("color: #ffb28a; font-size: 11px; background: transparent;")
        lay.addWidget(self.label, stretch=1)

        self.reload_btn = self._make_btn("重新加载", lambda: self.reload_requested.emit())
        self.ignore_btn = self._make_btn("忽略", lambda: self.ignore_requested.emit())
        lay.addWidget(self.reload_btn)
        lay.addWidget(self.ignore_btn)

    @staticmethod
    def _make_btn(text, slot):
        b = QtWidgets.QPushButton(text)
        b.setCursor(QtCore.Qt.PointingHandCursor)
        b.setFixedHeight(22)
        b.setStyleSheet(
            "QPushButton { background: #2a1d14; color: #ffb28a; border: 1px solid #4a2e1c;"
            " border-radius: 6px; font-size: 11px; padding: 0 10px; }"
            "QPushButton:hover { background: #35251a; border-color: #ff6b35; }"
            "QPushButton:pressed { background: #1f150e; }")
        b.clicked.connect(slot)
        return b

    def show_message(self, filename):
        self.label.setText("「%s」已被外部修改" % filename)
        if self.isVisible():
            return
        self._anim = QtCore.QPropertyAnimation(self, b"pos", self)
        self.setVisible(True)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._anim.setStartValue(self.pos() + QtCore.QPoint(0, -8))
        self._anim.setEndValue(self.pos())
        self._anim.start()

    def hide_bar(self):
        if not self.isVisible():
            return
        self.setVisible(False)
