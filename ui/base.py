# base.py — MyOS 顶部标题栏 / 底部状态栏
#
# 从 main_window.py 分离出来的通用栏组件：
#   HeaderBar — 顶部标题栏（LOGO | 副标题 | ROS 连接状态 | 右侧双 logo）
#   FooterBar — 底部状态栏（版本号）
#
# 右侧双 logo（学校 / 车队）在启动过渡结束时由 show_logos() 淡入展示，
# 与 SplashPage 里的 logo 形成“从画面中心迁移到标题栏”的连续过渡。

import os

from PySide6 import QtCore, QtWidgets, QtGui

# logo 资源路径（style/icon 下的学校与车队 logo）
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHOOL_LOGO_PATH = os.path.join(_ROOT, "style", "icon", "SZPU.png")
TEAM_LOGO_PATH = os.path.join(_ROOT, "style", "icon", "魅影方程式.png")

LOGO_H = 32   # 标题栏内 logo 高度


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

        # 右侧：学校 / 车队 logo（启动过渡结束时由 show_logos() 淡入展示）
        self._logos = QtWidgets.QWidget(self)
        logos_layout = QtWidgets.QHBoxLayout(self._logos)
        logos_layout.setContentsMargins(0, 0, 0, 0)
        logos_layout.setSpacing(12)
        logos_layout.addWidget(self._make_logo_label(SCHOOL_LOGO_PATH))
        #logos_layout.addWidget(self._make_logo_label(TEAM_LOGO_PATH))
        layout.addWidget(self._logos)
        # 初始不可见（透明度 0），等待过渡动画结束时展示
        self._logos_effect = QtWidgets.QGraphicsOpacityEffect(self._logos)
        self._logos_effect.setOpacity(0.0)
        self._logos.setGraphicsEffect(self._logos_effect)
        self._fade_anim = QtCore.QPropertyAnimation(self._logos_effect, b"opacity", self)
        self._fade_anim.setDuration(500)
        self._fade_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._pos_anim = QtCore.QPropertyAnimation(self._logos, b"pos", self)
        self._pos_anim.setDuration(500)
        self._pos_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

    def _make_logo_label(self, path):
        """加载 logo 并按标题栏高度等比缩放"""
        img = QtGui.QImage(path)
        label = QtWidgets.QLabel()
        if not img.isNull():
            w = max(1, int(LOGO_H * img.width() / img.height()))
            pm = QtGui.QPixmap.fromImage(img).scaled(
                w, LOGO_H, QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation)
            label.setPixmap(pm)
        label.setFixedHeight(LOGO_H)
        return label

    def show_logos(self):
        """启动过渡结束时展示右侧 logo：淡入 + 轻微上浮"""
        if self._fade_anim.state() == QtCore.QAbstractAnimation.Running:
            return
        self._fade_anim.stop()
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()
        base = self._logos.pos()
        self._pos_anim.stop()
        self._pos_anim.setStartValue(base + QtCore.QPoint(0, 8))
        self._pos_anim.setEndValue(base)
        self._pos_anim.start()


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
