# main_window.py — MyOS 主窗口 & 仪表盘面板
#
# 包含三个类：
#   1. SplashPage       — 启动画面页（嵌入主窗口内部）
#   2. DashboardPanel   — 仪表盘模块（车速表 + 数据卡片）
#   3. MainWindow       — 主窗口（把各个模块拼在一起）
#
# 设计原则（Apple Fluid Interface）：
#   - 响应即时：状态切换零延迟反馈
#   - 可中断：所有动画基于当前呈现值，可被新动画平滑接管
#   - 弹簧物理：使用 QEasingCurve 弹簧曲线（OutCubic / OutBack）替代固定时长线性动画
#   - 材质深度：分层半透明背景 + 软阴影营造层次
#   - 光学字距：大字负字距收紧，小字微正字距
#   - 空间一致：进入与退出沿同一路径

import math
from PySide6 import QtCore, QtWidgets, QtGui

# splash 页显示时长（毫秒），到期后自动切换到仪表盘
SPLASH_DURATION_MS = 2200

# 动画时钟间隔（毫秒），约 60fps —— 与显示器刷新率对齐
ANIM_TICK_MS = 16


# ================================================================
#  SplashPage — 启动画面（嵌入在主窗口内部显示）
#  纯代码绘制：大标题 + 副标题 + loading 呼吸文字 + 柔光晕
#  动画基于经过时间（elapsed-time），保证任意刷新率下都平滑
# ================================================================

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


# ================================================================
#  DashboardPanel — 仪表盘模块（占位阶段）
#  仅显示一个红色虚线高亮的矩形占位区域，标识后续可视化模块的位置。
#  矩形尺寸：窗口宽度的一半 × 窗口高度的一半；水平居中、垂直置顶。
# ================================================================

class DashboardPanel(QtWidgets.QWidget):
    """仪表盘面板（占位阶段）：红色虚线矩形标识后续模块位置

    矩形宽 = 主窗口宽度 / 2，高 = 主窗口高度 / 2，
    水平居中、垂直置顶，内容暂留空，后续在此区域接入可视化模块。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboard-panel")
        # 占位阶段：无子控件，仅靠 paintEvent 绘制红色虚线矩形

    def resizeEvent(self, event):
        """主窗口尺寸变化时重绘，保持矩形居中置顶"""
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event):
        """绘制红色虚线高亮的占位矩形（窗口宽高的一半，居中置顶）"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # 以顶层主窗口尺寸为基准（用户要求相对窗口而非相对本面板）
        win = self.window()
        if win is not None:
            win_w = win.width()
            win_h = win.height()
        else:
            win_w = self.width()
            win_h = self.height()

        rect_w = win_w / 2
        rect_h = win_h / 2

        # 水平居中、垂直置顶（矩形顶部贴本面板顶部）
        x = (self.width() - rect_w) / 2
        y = 0
        rect = QtCore.QRectF(x, y, rect_w, rect_h)

        # 红色虚线边框高亮
        pen = QtGui.QPen(QtGui.QColor("#ff3b30"), 2, QtCore.Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(rect)

        painter.end()

    def play_entrance(self):
        """占位阶段无入场动画（保留方法以兼容 MainWindow 的调用）"""
        pass


# ================================================================
#  MainWindow — 主窗口
#  结构：顶部标题栏  |  中间面板区（QStackedWidget 可切换不同模块）
#       |  底部状态栏
#  切换 splash → dashboard 时使用交叉淡化 + 上浮，弹簧缓动
# ================================================================

class MainWindow(QtWidgets.QMainWindow):
    """MyOS 主窗口，所有功能模块的容器"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyOS A03")
        self.resize(1280, 800)
        self.setMinimumSize(960, 600)
        self._setup_ui()

    def _setup_ui(self):
        """搭建主窗口的整体布局：头部 + 面板区 + 底部"""
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        root_layout = QtWidgets.QVBoxLayout(central)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(16)

        # 顶部标题栏
        header = self._build_header()
        root_layout.addWidget(header)

        # QStackedWidget 卡片叠
        self.panel_stack = QtWidgets.QStackedWidget()
        root_layout.addWidget(self.panel_stack, stretch=1)

        # 第 0 页：启动画面
        self.splash_page = SplashPage()
        self.panel_stack.addWidget(self.splash_page)

        # 第 1 页：仪表盘面板
        self.dashboard_panel = DashboardPanel()
        self.panel_stack.addWidget(self.dashboard_panel)

        # 默认显示 splash 页
        self.panel_stack.setCurrentIndex(0)
        QtCore.QTimer.singleShot(SPLASH_DURATION_MS, self._on_splash_finished)

        # 底部状态栏
        footer = self._build_footer()
        root_layout.addWidget(footer)

    def _build_header(self):
        """构建顶部标题栏：LOGO | 副标题 | ROS 连接状态"""
        header = QtWidgets.QWidget()
        header.setFixedHeight(44)
        layout = QtWidgets.QHBoxLayout(header)
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

        # ROS 连接状态指示
        status_led = QtWidgets.QLabel("\u25cf  ROS 未连接")
        status_led.setObjectName("status-warn")
        layout.addWidget(status_led)

        return header

    def _on_splash_finished(self):
        """splash 定时器到期：流体过渡到仪表盘页面
           交叉淡化 + 上浮，OutCubic 弹簧缓动"""
        self.splash_page.stop_animation()

        # 给仪表盘加透明度效果，从 0 淡入到 1
        opacity_effect = QtWidgets.QGraphicsOpacityEffect(self.dashboard_panel)
        opacity_effect.setOpacity(0.0)
        self.dashboard_panel.setGraphicsEffect(opacity_effect)

        # 切换到仪表盘页（splash 即刻隐藏，但因背景同色，视觉上是淡入）
        self.panel_stack.setCurrentIndex(1)

        # 淡入动画：OutCubic，无过冲，优雅稳定
        fade = QtCore.QPropertyAnimation(opacity_effect, b"opacity", self)
        fade.setDuration(620)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        # 轻微上浮：模拟材质从下方"浮现"
        target = self.dashboard_panel.geometry()
        start = QtCore.QRect(target.x(), target.y() + 16,
                             target.width(), target.height())
        slide = QtCore.QPropertyAnimation(self.dashboard_panel, b"geometry", self)
        slide.setDuration(620)
        slide.setStartValue(start)
        slide.setEndValue(target)
        slide.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        fade.start()
        slide.start()

        # 淡入完成后触发卡片交错入场，并移除透明度效果让软阴影正常渲染
        fade.finished.connect(lambda: (
            self.dashboard_panel.setGraphicsEffect(None),
            self.dashboard_panel.play_entrance(),
        ))

    def _build_footer(self):
        """构建底部状态栏：显示版本号"""
        footer = QtWidgets.QWidget()
        footer.setFixedHeight(26)
        layout = QtWidgets.QHBoxLayout(footer)
        layout.setContentsMargins(0, 0, 0, 0)

        ver = QtWidgets.QLabel("MyOS v1.0(内测)")
        ver.setStyleSheet("color: #6c6c70; font-size: 10px; "
                          "letter-spacing: 0.04em;")
        layout.addWidget(ver)

        layout.addStretch()

        return footer
