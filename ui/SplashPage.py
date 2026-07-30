# SplashPage.py — MyOS 启动画面页
#
# 嵌入主窗口内部显示：纯代码绘制大标题 + 副标题 + loading 呼吸文字 + 柔光晕。
# 动画基于经过时间（elapsed-time），保证任意刷新率下都平滑。

import math
from PySide6 import QtCore, QtWidgets, QtGui

# 动画时钟间隔（毫秒），约 60fps —— 与显示器刷新率对齐
ANIM_TICK_MS = 16


class SplashPage(QtWidgets.QWidget):
    """嵌入主窗口内部的启动画面，logo 带柔光晕与微缩放呼吸"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("splash-page")
        self.setStyleSheet("background-color: #0c0d12;")

        # 经过时间驱动动画，避免依赖固定 tick 的累积误差
        self._elapsed = QtCore.QElapsedTimer()
        self._elapsed.start()

        self._breath_timer = QtCore.QTimer(self)
        self._breath_timer.timeout.connect(self._on_anim_tick)
        self._breath_timer.start(ANIM_TICK_MS)

    def _on_anim_tick(self):
        """每帧根据经过时间计算呼吸值，触发重绘"""
        self.update()

    def stop_animation(self):
        """停止动画定时器"""
        self._breath_timer.stop()

    def paintEvent(self, event):
        """绘制 splash 页面：柔光晕 + 居中大标题 + 副标题 + loading 呼吸文字"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # 经过毫秒数，呼吸周期 2.4s（约 0.42Hz，低于易引发前庭不适的阈值）
        t = self._elapsed.elapsed()
        phase = (t / 2400.0) * 2 * math.pi
        # 用 (sin+1)/2 映射到 0..1，再做 ease-in-out 平滑
        raw = (math.sin(phase) + 1.0) / 2.0
        breath = raw * raw * (3 - 2 * raw)  # smoothstep，比纯 sin 更自然

        cx, cy = w // 2, h // 2 - 150

        # --- 柔光晕：径向渐变模拟材质发光 ---
        glow_radius = 180 + 30 * breath
        glow_grad = QtGui.QRadialGradient(cx, cy, glow_radius)
        glow_color = QtGui.QColor("#00d4aa")
        glow_color.setAlphaF(0.18 * breath + 0.05)
        glow_grad.setColorAt(0, glow_color)
        transparent = QtGui.QColor("#00d4aa")
        transparent.setAlpha(0)
        glow_grad.setColorAt(1, transparent)
        painter.setBrush(QtGui.QBrush(glow_grad))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(QtCore.QPointF(cx, cy), glow_radius, glow_radius)

        # --- 大标题 MyOS：微缩放呼吸 + 负字距收紧 ---
        scale = 1.0 + 0.04 * breath
        painter.save()
        painter.translate(cx, cy)
        painter.scale(scale, scale)
        painter.setFont(QtGui.QFont("SF Pro Display", 80, QtGui.QFont.Bold))
        # 大字负字距：字越大字距越开，需收紧
        title_font = QtGui.QFont("SF Pro Display", 80, QtGui.QFont.Bold)
        title_font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, -2)
        painter.setFont(title_font)
        title_color = QtGui.QColor("#00d4aa")
        title_color.setAlphaF(0.85 + 0.15 * breath)
        painter.setPen(title_color)
        painter.drawText(QtCore.QRect(-w // 2, -65, w, 130),
                         QtCore.Qt.AlignCenter, "MyOS")
        painter.restore()

        # --- 副标题 ---
        sub_font = QtGui.QFont("SF Pro Text", 15)
        sub_font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 1)
        painter.setFont(sub_font)
        sub_color = QtGui.QColor("#8e8e93")
        sub_color.setAlphaF(0.6 + 0.3 * breath)
        painter.setPen(sub_color)
        painter.drawText(QtCore.QRect(0, h // 2, w, 30),
                         QtCore.Qt.AlignCenter, "A03 无人系统操作面板")

        # --- loading 文字 ---
        load_font = QtGui.QFont("SF Pro Text", 11)
        load_font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 2)
        painter.setFont(load_font)
        load_color = QtGui.QColor("#6c6c70")
        load_color.setAlphaF(0.4 + 0.5 * breath)
        painter.setPen(load_color)
        painter.drawText(QtCore.QRect(0, h // 2 + 40, w, 25),
                         QtCore.Qt.AlignCenter, "v1.0  —  loading")

        painter.end()
