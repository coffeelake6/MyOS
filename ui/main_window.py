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
#  DashboardPanel — 仪表盘模块（图像显示区）
#  在红色虚线高亮的矩形区域内，左右并排显示两路相机图像。
#  矩形尺寸：窗口宽度的一半 × 窗口高度的一半；水平居中、垂直置顶。
# ================================================================

class DashboardPanel(QtWidgets.QWidget):
    """仪表盘面板：红色虚线矩形内左右并排显示两路相机图像

    矩形宽 = 主窗口宽度 / 2，高 = 主窗口高度 / 2，
    水平居中、垂直置顶；内部左右两半分别显示 camera1 / camera2。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboard-panel")

        # 两路图像显示标签（透明背景，让红色虚线边框透出）
        self.img1_label = QtWidgets.QLabel(self)
        self.img2_label = QtWidgets.QLabel(self)
        for lbl in (self.img1_label, self.img2_label):
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setStyleSheet("background: transparent;")
            lbl.setMinimumSize(2, 2)

        # 缓存最新 QImage，供窗口缩放时按比例刷新
        self._img1 = None
        self._img2 = None

    # ----- 几何 -----

    def _frame_rect(self):
        """计算占位矩形（窗口宽高的一半，居中置顶）"""
        win = self.window()
        win_w = win.width() if win is not None else self.width()
        win_h = win.height() if win is not None else self.height()
        rw = win_w / 2
        rh = win_h / 2
        x = (self.width() - rw) / 2
        y = 0
        return QtCore.QRectF(x, y, rw, rh)

    def _layout_images(self):
        """根据矩形区域定位两路图像标签（左右各半，留边距给虚线边框）"""
        r = self._frame_rect()
        inset = 6   # 留出红色虚线边框 + 间距
        gap = 8     # 两路图像之间的间隔
        x = int(r.x() + inset)
        y = int(r.y() + inset)
        w = int(r.width() - 2 * inset)
        h = int(r.height() - 2 * inset)
        half = (w - gap) // 2
        self.img1_label.setGeometry(x, y, half, h)
        self.img2_label.setGeometry(x + half + gap, y, half, h)
        self._refresh_pixmaps()

    def resizeEvent(self, event):
        """窗口尺寸变化时重新定位图像标签并重绘"""
        super().resizeEvent(event)
        self._layout_images()
        self.update()

    def paintEvent(self, event):
        """绘制红色虚线高亮的矩形边框"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        r = self._frame_rect()
        pen = QtGui.QPen(QtGui.QColor("#ff3b30"), 2, QtCore.Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(r)
        painter.end()

    # ----- 对外接口：ImageSubscriber 信号槽 -----

    @QtCore.Slot(QtGui.QImage)
    def set_image1(self, qimg):
        """接收 camera1 图像并显示"""
        self._img1 = qimg
        self._refresh_label(self.img1_label, qimg)

    @QtCore.Slot(QtGui.QImage)
    def set_image2(self, qimg):
        """接收 camera2 图像并显示"""
        self._img2 = qimg
        self._refresh_label(self.img2_label, qimg)

    def _refresh_label(self, label, qimg):
        """把 QImage 缩放到标签尺寸后贴到 QLabel（保持长宽比）"""
        if qimg is None or qimg.isNull():
            return
        if label.width() < 2 or label.height() < 2:
            return  # 尚未布局，等 resize 后由 _refresh_pixmaps 贴图
        pm = QtGui.QPixmap.fromImage(qimg)
        label.setPixmap(pm.scaled(label.size(), QtCore.Qt.KeepAspectRatio,
                                  QtCore.Qt.SmoothTransformation))

    def _refresh_pixmaps(self):
        """窗口缩放后按新尺寸重贴两路图像"""
        if self._img1 is not None:
            self._refresh_label(self.img1_label, self._img1)
        if self._img2 is not None:
            self._refresh_label(self.img2_label, self._img2)

    def play_entrance(self):
        """无入场动画（保留方法以兼容 MainWindow 的调用）"""
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

        # ROS 图像桥：订阅两路相机话题，图像送至仪表盘矩形区域
        self._setup_ros_image_bridge()

        # 默认显示 splash 页
        self.panel_stack.setCurrentIndex(0)
        QtCore.QTimer.singleShot(SPLASH_DURATION_MS, self._on_splash_finished)

        # 底部状态栏
        footer = self._build_footer()
        root_layout.addWidget(footer)

    def _setup_ros_image_bridge(self):
        """创建 ROS 图像订阅桥并连接到仪表盘；无 ROS 时静默跳过"""
        try:
            from ros_bridge.getImg import ImageSubscriber
        except Exception as e:
            print(f"[MyOS] 未加载 ROS 图像桥（getImg）: {e}")
            self.ros_bridge = None
            return
        try:
            self.ros_bridge = ImageSubscriber(parent=self)
            self.ros_bridge.image1_received.connect(self.dashboard_panel.set_image1)
            self.ros_bridge.image2_received.connect(self.dashboard_panel.set_image2)
            self.ros_bridge.start()
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.aboutToQuit.connect(self.ros_bridge.shutdown)
            print(f"[MyOS] ROS 图像桥已启动: {self.ros_bridge.topics()}")
        except Exception as e:
            print(f"[MyOS] ROS 图像桥启动失败: {e}")
            self.ros_bridge = None

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
