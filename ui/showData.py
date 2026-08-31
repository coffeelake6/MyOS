# showData.py — MyOS 关键数据监控模块
#
# 竖向键值对列表展示关键话题数据；数据来自 ros_bridge.getData 的 DATA_ITEMS
# 配置（键由用户定义，值由订阅的 ROS 话题解析）。增删数据项只需改 DATA_ITEMS，
# 面板行会自动同步（无 ROS 时显示占位 "—"，UI 仍可独立运行）。
#
# 设计（Apple Fluid Interface）：
#   - 值更新时强调色短暂闪烁（400ms）后恢复，反馈即时且不打扰
#   - 面板外观与参数修改面板一致：圆角卡片 + 描边

from PySide6 import QtCore, QtWidgets, QtGui

PANEL_WIDTH = 230   # 面板固定宽度

# 无 ROS 环境下的兜底键列表（保证骨架行可见；有 ROS 时以 DATA_ITEMS 为准）
_FALLBACK_KEYS = ["YOLO推理时间", "Pointpillars推理时间", "融合速度", "当前发布转角"]


class _DataRow(QtWidgets.QWidget):
    """一行键值对：键（左，次级色，过长省略）+ 值（右，加粗，更新时闪烁）"""

    def __init__(self, key, parent=None):
        super().__init__(parent)
        self._full_key = key
        self.setFixedHeight(30)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(8)

        self.key_label = QtWidgets.QLabel(key)
        self.key_label.setStyleSheet("color: #8e8e93; font-size: 12px;")
        self.key_label.setMaximumWidth(130)
        lay.addWidget(self.key_label)

        lay.addStretch(1)

        self.value_label = QtWidgets.QLabel("—")
        self.value_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.value_label.setStyleSheet(self._style("#e5e5ea"))
        lay.addWidget(self.value_label)

        self._last = None
        self._flash_timer = QtCore.QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._restore_color)

    @staticmethod
    def _style(color):
        return f"color: {color}; font-size: 12px; font-weight: 600;"

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # 键过长时省略号（避免挤压右侧值）；初始布局宽度为 0 时不做省略
        w = self.key_label.width()
        if w <= 0:
            return
        fm = self.key_label.fontMetrics()
        self.key_label.setText(fm.elidedText(self._full_key, QtCore.Qt.ElideRight, w))

    def set_value(self, text):
        """收到新值：值变化时更新文本；无论值是否变化都重启闪烁。

        形成“实时心跳”——数据持续流入时保持强调色（每帧重启 400ms 定时器），
        数据停止后约 400ms 内回到默认色。这样暂停 bag / 重新播放后，
        只要新数据到达就会可见地刷新；数据停了也有明确的状态反馈。
        """
        if text != self._last:
            self._last = text
            self.value_label.setText(text)
        self.value_label.setStyleSheet(self._style("#00d4aa"))
        self._flash_timer.start(400)

    def _restore_color(self):
        self.value_label.setStyleSheet(self._style("#e5e5ea"))


class showData(QtWidgets.QWidget):
    """关键数据监控面板：竖向键值对列表（固定宽 PANEL_WIDTH）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("show-data")
        self.setFixedWidth(PANEL_WIDTH)
        self._rows = {}

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 16)
        root.setSpacing(10)

        # 标题
        title = QtWidgets.QLabel("实时数据")
        title.setStyleSheet("color: #e5e5ea; font-size: 15px; font-weight: 600; "
                            "letter-spacing: 0.01em;")
        root.addWidget(title)

        # 数据行列表（滚动）
        self._list = QtWidgets.QWidget()
        self._list_layout = QtWidgets.QVBoxLayout(self._list)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch(1)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setStyleSheet("background: transparent;")
        scroll.setWidget(self._list)
        root.addWidget(scroll, stretch=1)

        # ROS 数据桥（无 ROS 时静默跳过，仅保留骨架行显示占位 "—"）
        keys = list(_FALLBACK_KEYS)
        try:
            from ros_bridge.getData import setup_data_bridge, DATA_ITEMS
            self._bridge = setup_data_bridge(self, self._on_data)
            if self._bridge is not None:
                keys = [i.key for i in self._bridge.items()]
            else:
                keys = [i.key for i in DATA_ITEMS]
        except Exception as e:
            print(f"[showData] 未启用 ROS 数据桥: {e}")
            self._bridge = None
        for k in keys:
            self._add_row(k)

    # ----- 对外接口：DataSubscriber 信号槽 -----

    def _add_row(self, key):
        row = _DataRow(key)
        self._list_layout.insertWidget(self._list_layout.count() - 1, row)
        self._rows[key] = row

    @QtCore.Slot(str, str)
    def _on_data(self, key, text):
        """收到某键的新值并刷新对应行"""
        row = self._rows.get(key)
        if row is not None:
            row.set_value(text)

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
