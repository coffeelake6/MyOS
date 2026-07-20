# main_window.py — MyOS 主窗口 & 仪表盘面板
#
# 包含三个类：
#   1. SplashPage       — 启动画面页（嵌入主窗口内部）
#   2. DashboardPanel   — 仪表盘模块（车速表 + 数据卡片）
#   3. MainWindow       — 主窗口（把各个模块拼在一起）
#
# 后续新增模块（如调参面板、启动面板）也在这个文件或同目录下新建 .py 文件

import math
from PySide6 import QtCore, QtWidgets, QtGui

# splash 页显示时长（毫秒），到期后自动切换到仪表盘
SPLASH_DURATION_MS = 2500

# 呼吸动画定时器间隔（毫秒），约 60fps
BREATH_TICK_MS = 50

# 呼吸动画速度：每 tick 增加的角度（弧度），值越大呼吸越快
BREATH_SPEED = 0.1


# ================================================================
#  SplashPage — 启动画面（嵌入在主窗口内部显示）
#  纯代码绘制：大标题 + 副标题 + loading 呼吸文字
# ================================================================

class SplashPage(QtWidgets.QWidget):
    """嵌入主窗口内部的启动画面，loading 文字带呼吸动画"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("splash-page")
        self.setStyleSheet("background-color: #0a0a0f;")

        self._breath_angle = 0.0
        self._breath_alpha = 1.0

        self._breath_timer = QtCore.QTimer(self)
        self._breath_timer.timeout.connect(self._on_anim_tick)
        self._breath_timer.start(BREATH_TICK_MS)

    def _on_anim_tick(self):
        """每帧更新呼吸角度，触发重绘"""
        self._breath_angle += BREATH_SPEED
        self._breath_alpha = 0.4 + 0.6 * (math.sin(self._breath_angle))
        self.update()

    def stop_animation(self):
        """停止动画定时器"""
        self._breath_timer.stop()

    def paintEvent(self, event):
        """绘制 splash 页面：居中大标题 + 副标题 + loading 呼吸文字"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        painter.setFont(QtGui.QFont("Consolas", 80, QtGui.QFont.Bold))
        breath_color = QtGui.QColor("#00d4aa")
        breath_color.setAlphaF(self._breath_alpha)
        painter.setPen(breath_color)
        painter.drawText(QtCore.QRect(0, h // 2 - 150, w, 130),
                         QtCore.Qt.AlignCenter, "MyOS")

        painter.setFont(QtGui.QFont("Consolas", 15))
        sub_color = QtGui.QColor("#888888")
        sub_color.setAlphaF(self._breath_alpha)
        painter.setPen(sub_color)
        painter.drawText(QtCore.QRect(0, h // 2, w, 30),
                         QtCore.Qt.AlignCenter, "A03 无人系统操作面板")

        load_color = QtGui.QColor("#555555")
        load_color.setAlphaF(self._breath_alpha)
        painter.setFont(QtGui.QFont("Consolas", 11))
        painter.setPen(load_color)
        painter.drawText(QtCore.QRect(0, h // 2 + 40, w, 25),
                         QtCore.Qt.AlignCenter, "v1.0  —  loading ...")

        painter.end()


# ================================================================
#  DashboardPanel — 仪表盘模块
#  左侧：圆形车速表（QPainter 手绘）
#  右侧：4 列数据卡片（车辆状态 / 检测结果 / 路径信息 / 模块状态）
# ================================================================

class DashboardPanel(QtWidgets.QWidget):
    """仪表盘面板：实时显示车辆关键数据"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboard-panel")
        self._setup_ui()  # 初始化界面

    def _setup_ui(self):
        """搭建仪表盘的界面布局"""
        # 外层使用垂直布局：标题在上，内容在下
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 面板标题 "DASHBOARD"（荧光绿色 + 下划线，样式由 QSS 的 #panel-title 控制）
        title = QtWidgets.QLabel("DASHBOARD")
        title.setObjectName("panel-title")
        layout.addWidget(title)

        # 内容区域：水平布局，左边放车速表，右边放数据网格
        content = QtWidgets.QHBoxLayout()
        content.setSpacing(16)
        layout.addLayout(content)

        # stretch 参数控制宽度比例：车速表占 2 份，数据网格占 3 份
        content.addWidget(self._build_speed_gauge(), stretch=2)
        content.addWidget(self._build_data_grid(), stretch=3)

    # ----- 车速表 -----

    def _build_speed_gauge(self):
        """构建左侧的车速仪表盘（圆形表盘 + 数字读数）"""
        # 用一个 QFrame 容器包裹，应用 #panel 样式（圆角、深色背景）
        container = QtWidgets.QFrame()
        container.setObjectName("panel")
        gauge_layout = QtWidgets.QVBoxLayout(container)
        gauge_layout.setAlignment(QtCore.Qt.AlignCenter)

        # 圆形表盘画布（QLabel 充当画布，用 QPainter 在上面绘图）
        self.gauge_canvas = QtWidgets.QLabel()
        self.gauge_canvas.setFixedSize(220, 220)
        self.gauge_canvas.setAlignment(QtCore.Qt.AlignCenter)
        self._draw_gauge_placeholder()  # 画一个静态的占位表盘
        gauge_layout.addWidget(self.gauge_canvas, alignment=QtCore.Qt.AlignCenter)

        # 车速数字显示（大字，荧光绿，样式由 #dashboard-value 控制）
        self.speed_label = QtWidgets.QLabel("0.0")
        self.speed_label.setObjectName("dashboard-value")
        self.speed_label.setAlignment(QtCore.Qt.AlignCenter)
        gauge_layout.addWidget(self.speed_label)

        # 单位 "km/h"（小字，灰色，样式由 #dashboard-unit 控制）
        unit_label = QtWidgets.QLabel("km/h")
        unit_label.setObjectName("dashboard-unit")
        unit_label.setAlignment(QtCore.Qt.AlignCenter)
        gauge_layout.addWidget(unit_label)

        return container

    def _draw_gauge_placeholder(self):
        """用 QPainter 手绘一个圆形车速表的静态占位图
           后续接入 ROS 数据后，可以根据实际车速动态重绘指针角度"""
        # 创建一张 220x220 的透明画布
        pixmap = QtGui.QPixmap(220, 220)
        pixmap.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)  # 抗锯齿

        center = QtCore.QPoint(110, 110)  # 表盘圆心
        radius = 90                        # 表盘半径

        # 画弧线刻度（深灰色粗弧线，从 30° 到 330°，即 300° 的范围）
        pen = QtGui.QPen(QtGui.QColor("#1e1e2e"), 10)
        painter.setPen(pen)
        # drawArc 参数：矩形区域、起始角度（1/16 度为单位）、弧长（1/16 度为单位）
        painter.drawArc(QtCore.QRect(center.x() - radius, center.y() - radius,
                                       radius * 2, radius * 2),
                        30 * 16,     # 起始角度 30°，乘以 16 是因为 Qt 用 1/16 度做单位
                        300 * 16)    # 弧长 300°

        # 画指针（从圆心向右的一条线，代表 0 刻度）
        pen = QtGui.QPen(QtGui.QColor("#00d4aa"), 4)
        painter.setPen(pen)
        painter.drawLine(center, center)

        # 画底部的 "KM/H" 文字
        painter.setPen(QtGui.QPen(QtGui.QColor("#00d4aa"), 3))
        painter.drawText(QtCore.QRect(0, 0, 220, 30), QtCore.Qt.AlignCenter, "KM/H")

        painter.end()  # 释放画笔
        self.gauge_canvas.setPixmap(pixmap)  # 把画好的图贴到 QLabel 上

    # ----- 数据卡片网格 -----

    def _build_data_grid(self):
        """构建右侧的 4 列数据卡片（车辆状态 / 检测结果 / 路径信息 / 模块状态）"""
        container = QtWidgets.QFrame()
        container.setObjectName("panel")
        grid = QtWidgets.QGridLayout(container)
        grid.setSpacing(8)

        # cards 数据结构：
        #   [ (组名, [ (标签, 默认值, 单位), ... ]), ... ]
        #   组名会作为 QGroupBox 的标题
        #   默认值会在面板初始化时显示
        cards = [
            ("VEHICLE STATE", [       # 车辆状态
                ("SPEED", "0.0", "km/h"),
                ("STEERING", "0.0", "deg"),
                ("GEAR", "N", ""),
            ]),
            ("DETECTION", [           # 检测结果
                ("YOLO", "0", "cones"),
                ("LIDAR", "0", "objs"),
                ("I O U", "0", "fused"),
            ]),
            ("PATH INFO", [           # 路径信息
                ("POINTS", "0", "pts"),
                ("DISTANCE", "0.0", "m"),
                ("CURVATURE", "0.000", "1/m"),
            ]),
            ("MODULE STATUS", [       # 模块状态（在线/离线）
                ("YOLO", "OFFLINE", ""),
                ("LIDAR", "OFFLINE", ""),
                ("PLANNER", "OFFLINE", ""),
                ("CONTROL", "OFFLINE", ""),
            ]),
        ]

        # 用字典保存每个数据标签的引用，方便后续 update_xxx 方法直接修改文字
        self.data_widgets = {}

        # 遍历 cards，为每一列创建一个 QGroupBox
        for col, (group_name, fields) in enumerate(cards):
            group = QtWidgets.QGroupBox(group_name)  # 分组框，标题是组名
            group_layout = QtWidgets.QVBoxLayout(group)
            group_layout.setSpacing(6)

            # 遍历组内的每个字段，创建一行：标签名 —— 数值 —— 单位
            for label, value, unit in fields:
                row = QtWidgets.QHBoxLayout()

                # 左侧：字段名（小号灰色字）
                lbl = QtWidgets.QLabel(label)
                lbl.setObjectName("dashboard-label")
                row.addWidget(lbl)

                # 中间弹簧：把数值推到右边
                row.addStretch()

                # 右侧：数值（MODULE STATUS 列用橙色，其他用荧光绿）
                val = QtWidgets.QLabel(value)
                if group_name == "MODULE STATUS":
                    val.setObjectName("status-warn")  # 橙色警告色
                else:
                    val.setObjectName("dashboard-value")
                    val.setStyleSheet("font-size: 16px;")  # 比标题小一点的数字
                row.addWidget(val)

                # 单位（有的话就显示）
                if unit:
                    u = QtWidgets.QLabel(unit)
                    u.setObjectName("dashboard-unit")
                    u.setStyleSheet("font-size: 10px;")
                    row.addWidget(u)

                group_layout.addLayout(row)

                # 用 "组名/标签名" 当作 key 存入字典，后续通过这个 key 更新数据
                self.data_widgets[f"{group_name}/{label}"] = val

            # 底部加一个弹簧，让内容靠上对齐
            group_layout.addStretch()
            grid.addWidget(group, 0, col)

        return container

    # ----- 对外接口：供外部（ROS 数据回调）更新仪表盘数值 -----

    def update_vehicle_state(self, speed, steering, gear):
        """更新车辆状态卡片：车速、方向盘角度、档位"""
        self.data_widgets["VEHICLE STATE/SPEED"].setText(f"{speed:.1f}")
        self.data_widgets["VEHICLE STATE/STEERING"].setText(f"{steering:.1f}")
        self.data_widgets["VEHICLE STATE/GEAR"].setText(str(gear))

    def update_detection(self, yolo_count, lidar_count, iou_count):
        """更新检测结果卡片：YOLO 检测数、激光雷达障碍物数、融合匹配数"""
        self.data_widgets["DETECTION/YOLO"].setText(str(yolo_count))
        self.data_widgets["DETECTION/LIDAR"].setText(str(lidar_count))
        self.data_widgets["DETECTION/I O U"].setText(str(iou_count))


# ================================================================
#  MainWindow — 主窗口
#  结构：顶部标题栏  |  中间面板区（QStackedWidget 可切换不同模块）
#       |  底部状态栏
# ================================================================

class MainWindow(QtWidgets.QMainWindow):
    """MyOS 主窗口，所有功能模块的容器"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyOS A03")
        self.resize(1280, 800)       # 默认窗口大小
        self.setMinimumSize(960, 600)  # 最小窗口尺寸，再小布局会挤
        self._setup_ui()

    def _setup_ui(self):
        """搭建主窗口的整体布局：头部 + 面板区 + 底部"""
        # QMainWindow 需要一个 centralWidget 作为容器
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        # 根布局：垂直方向，从上到下依次放 header、panel_stack、footer
        root_layout = QtWidgets.QVBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(16)

        # 顶部标题栏
        header = self._build_header()
        root_layout.addWidget(header)

        # QStackedWidget 是一个"卡片叠"，可以放多个面板，但只显示当前一个
        # 后续加调参面板、启动面板时，往这里面 add 就行
        self.panel_stack = QtWidgets.QStackedWidget()
        root_layout.addWidget(self.panel_stack, stretch=1)  # stretch=1 让它占满中间剩余空间

        # 第 0 页：启动画面（程序打开先显示这个）
        self.splash_page = SplashPage()
        self.panel_stack.addWidget(self.splash_page)

        # 第 1 页：仪表盘面板
        self.dashboard_panel = DashboardPanel()
        self.panel_stack.addWidget(self.dashboard_panel)

        # 默认显示 splash 页，等定时器到期后切换到仪表盘
        self.panel_stack.setCurrentIndex(0)
        QtCore.QTimer.singleShot(SPLASH_DURATION_MS, self._on_splash_finished)

        # 底部状态栏
        footer = self._build_footer()
        root_layout.addWidget(footer)

    def _build_header(self):
        """构建顶部标题栏：LOGO | 副标题 | ROS 连接状态"""
        header = QtWidgets.QWidget()
        header.setFixedHeight(40)  # 固定 40 像素高
        layout = QtWidgets.QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        # LOGO "MyOS"（荧光绿大粗字）
        logo = QtWidgets.QLabel("MyOS")
        logo.setStyleSheet("color: #00d4aa; font-size: 22px; font-weight: bold;")
        layout.addWidget(logo)

        # 分隔符 "|"
        separator = QtWidgets.QLabel("|")
        separator.setStyleSheet("color: #333333; font-size: 22px;")
        layout.addWidget(separator)

        # 副标题 "A03 无人系统操作面板"
        subtitle = QtWidgets.QLabel("A03 无人系统操作面板")
        subtitle.setStyleSheet("color: #888888; font-size: 13px;")
        layout.addWidget(subtitle)

        # 弹簧：把右边的 ROS 状态推到最右侧
        layout.addStretch()

        # ROS 连接状态指示（橙色 ● + "ROS 未连接"）
        status_led = QtWidgets.QLabel("\u25cf  ROS 未连接")
        status_led.setObjectName("status-warn")
        layout.addWidget(status_led)

        return header

    def _on_splash_finished(self):
        """splash 定时器到期：切换到仪表盘页面（索引 1）"""
        self.panel_stack.setCurrentIndex(1)

    def _build_footer(self):
        """构建底部状态栏：显示版本号"""
        footer = QtWidgets.QWidget()
        footer.setFixedHeight(24)
        layout = QtWidgets.QHBoxLayout(footer)
        layout.setContentsMargins(0, 0, 0, 0)

        # 版本号 "MyOS v0.1.0"（暗灰色小字）
        ver = QtWidgets.QLabel("MyOS v1.0(内测)")
        ver.setStyleSheet("color: #555555; font-size: 10px;")
        layout.addWidget(ver)

        layout.addStretch()

        return footer
