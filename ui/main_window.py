# main_window.py — MyOS 主窗口
#
# 仅包含 MainWindow 类，负责把各个分离的模块拼在一起：
#   - SplashPage   （ui/SplashPage.py）   启动画面页
#   - showImg      （ui/showImg.py）      图像显示模块（自带 ROS 图像桥）
#   - HeaderBar    （ui/base.py）         顶部标题栏
#   - FooterBar    （ui/base.py）         底部状态栏
#
# 设计原则（Apple Fluid Interface）：
#   - 响应即时：状态切换零延迟反馈
#   - 可中断：所有动画基于当前呈现值，可被新动画平滑接管
#   - 弹簧物理：使用 QEasingCurve 弹簧曲线（OutCubic / OutBack）替代固定时长线性动画
#   - 空间一致：进入与退出沿同一路径

from PySide6 import QtCore, QtWidgets, QtGui

from SplashPage import SplashPage
from showImg import showImg
from showData import showData
from base import HeaderBar, FooterBar
from param_modification import ParamModificationPanel
from launch_panel import LaunchPanel

# splash 页显示时长（毫秒），到期后自动切换到仪表盘
SPLASH_DURATION_MS = 2200


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
        self.resize(1280, 900)
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
        self.header_bar = HeaderBar()
        root_layout.addWidget(self.header_bar)



        # QStackedWidget 卡片叠（第 0 页启动画面 / 第 1 页图像+参数）
        self.panel_stack = QtWidgets.QStackedWidget()
        root_layout.addWidget(self.panel_stack, stretch=1)

        # 第 0 页：启动画面
        self.splash_page = SplashPage()
        self.panel_stack.addWidget(self.splash_page)


        # 第 1 页：左列（图像 + 快捷启动） + 实时数据 + 参数修改（合并为一页）
        page1 = QtWidgets.QWidget()
        page1_layout = QtWidgets.QHBoxLayout(page1)
        page1_layout.setContentsMargins(0, 0, 0, 0)
        page1_layout.setSpacing(16)

        # 左列：上图像卡片（自适应）+ 下快捷启动面板（固定高度）
        left_col = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        self.show_img = showImg()
        left_layout.addWidget(self.show_img, stretch=1)

        self.launch_panel = LaunchPanel()
        left_layout.addWidget(self.launch_panel)

        page1_layout.addWidget(left_col, stretch=1)

        self.show_data = showData()
        page1_layout.addWidget(self.show_data)

        self.param_panel = ParamModificationPanel()
        page1_layout.addWidget(self.param_panel)
        self.panel_stack.addWidget(page1)

        # 默认显示 splash 页
        self.panel_stack.setCurrentIndex(0)
        QtCore.QTimer.singleShot(SPLASH_DURATION_MS, self._on_splash_finished)

        # 底部状态栏
        footer = FooterBar()
        root_layout.addWidget(footer)

    def _on_splash_finished(self):
        """splash 定时器到期：流体过渡到图像显示页面
           交叉淡化 + 上浮，OutCubic 弹簧缓动"""
        self.splash_page.stop_animation()

        # 过渡开始：标题栏右侧同步淡入双 logo，与 splash 中心 logo 形成“迁移”连续感
        self.header_bar.show_logos()

        # 给图像面板加透明度效果，从 0 淡入到 1
        opacity_effect = QtWidgets.QGraphicsOpacityEffect(self.show_img)
        opacity_effect.setOpacity(0.0)
        self.show_img.setGraphicsEffect(opacity_effect)

        # 切换到图像显示页（splash 即刻隐藏，但因背景同色，视觉上是淡入）
        self.panel_stack.setCurrentIndex(1)

        # 淡入动画：OutCubic，无过冲，优雅稳定
        fade = QtCore.QPropertyAnimation(opacity_effect, b"opacity", self)
        fade.setDuration(620)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        # 轻微上浮：模拟材质从下方"浮现"
        target = self.show_img.geometry()
        start = QtCore.QRect(target.x(), target.y() + 16,
                             target.width(), target.height())
        slide = QtCore.QPropertyAnimation(self.show_img, b"geometry", self)
        slide.setDuration(620)
        slide.setStartValue(start)
        slide.setEndValue(target)
        slide.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        fade.start()
        slide.start()

        # 淡入完成后触发卡片交错入场，并移除透明度效果让软阴影正常渲染
        fade.finished.connect(lambda: (
            self.show_img.setGraphicsEffect(None),
            self.show_img.play_entrance(),
        ))
