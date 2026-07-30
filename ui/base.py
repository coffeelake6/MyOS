# base.py — MyOS 顶部标题栏 / 底部状态栏
#
# 从 main_window.py 分离出来的通用栏组件：
#   HeaderBar — 顶部标题栏（LOGO | 副标题 | ROS 连接状态）
#   FooterBar — 底部状态栏（版本号）

from PySide6 import QtCore, QtWidgets


class HeaderBar(QtWidgets.QWidget):
    """顶部标题栏：LOGO | 副标题 | ROS 连接状态"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # LOGO
        logo = QtWidgets.QLabel("MyOS")
        logo.setStyleSheet("color: #00d4aa; font-size: 22px; font-weight: 700; "
                           "letter-spacing: -0.02em;")
        layout.addWidget(logo)

        separator = QtWidgets.QLabel("|")
        separator.setStyleSheet("color: #2a2b36; font-size: 22px;")
        layout.addWidget(separator)

        subtitle = QtWidgets.QLabel("A03 无人系统操作面板")
        subtitle.setStyleSheet("color: #8e8e93; font-size: 13px; "
                               "letter-spacing: 0.02em;")
        layout.addWidget(subtitle)

        layout.addStretch()

        # ROS 连接状态指示（暂未启用，保留以备后续接入）
        status_led = QtWidgets.QLabel("\u25cf  ROS 未连接")
        status_led.setObjectName("status-warn")
        # layout.addWidget(status_led)


class FooterBar(QtWidgets.QWidget):
    """底部状态栏：版本号"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        ver = QtWidgets.QLabel("MyOS v1.0(内测)")
        ver.setStyleSheet("color: #6c6c70; font-size: 10px; "
                          "letter-spacing: 0.04em;")
        layout.addWidget(ver)

        layout.addStretch()
