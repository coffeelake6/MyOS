# showImg.py — MyOS 图像显示模块
#
# 在红色虚线高亮的矩形区域内，左右并排显示两路相机图像。
# 矩形尺寸：窗口宽度的一半 × 窗口高度的一半；水平居中、垂直置顶。
# 构造时自动接入 ROS 图像桥（ros_bridge.getImg），无 ROS 时静默跳过。

from PySide6 import QtCore, QtWidgets, QtGui


class showImg(QtWidgets.QWidget):
    """图像显示面板：红色虚线矩形内左右并排显示两路相机图像

    矩形宽 = 主窗口宽度 / 2，高 = 主窗口高度 / 2，
    水平居中、垂直置顶；内部左右两半分别显示 camera1 / camera2。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboard-panel")

        # 两路视频窗口（QLabel 充当显示屏）：
        # 深色底 + 细边框 + 圆角，即便没有画面也能看到窗口轮廓
        self.img1_label = QtWidgets.QLabel(self)
        self.img2_label = QtWidgets.QLabel(self)
        for lbl in (self.img1_label, self.img2_label):
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setStyleSheet(
                "background-color: #0a0b10;"
                "border: 1px solid #2a2b36;"
                "border-radius: 6px;"
                "color: #6c6c70;"
                "font: 13px 'SF Pro Text', 'Segoe UI', sans-serif;"
            )
            lbl.setMinimumSize(2, 2)

        # 无画面时显示占位提示（首帧到达后由 _refresh_label 清空）
        self.img1_label.setText("CAM1\n无信号")
        self.img2_label.setText("CAM2\n无信号")

        # 缓存最新 QImage，供窗口缩放时按比例刷新
        self._img1 = None
        self._img2 = None

        # ROS 图像桥：订阅两路相机话题，图像送至本面板的两个 QLabel
        # 无 ROS 时静默跳过，UI 仍可独立运行
        try:
            from ros_bridge.getImg import setup_image_bridge
            self._bridge = setup_image_bridge(self, self.set_image1, self.set_image2)
        except Exception as e:
            print(f"[showImg] 未启用 ROS 图像桥: {e}")
            self._bridge = None

    # ----- 几何 -----

    def _frame_rect(self):
        """计算占位矩形（窗口宽高的一半，居中置顶）"""
        win = self.window()
        win_w = win.width() if win is not None else self.width()
        win_h = win.height() if win is not None else self.height()
        rw = win_w / 2
        rh = win_h / 2 - 100
        x = (self.width() - rw) / 16
        y = 0
        return QtCore.QRectF(x, y, rw, rh)

    def _layout_images(self):
        """根据矩形区域定位两路图像标签（左右各半，留边距给虚线边框）"""
        r = self._frame_rect()
        inset = 6   # 留出红色虚线边框 + 间距
        gap = 0     # 两路图像之间的间隔
        x = int(r.x() + inset)
        y = int(r.y() + inset)
        w = int(r.width() - 2 * inset)  # 图像宽度为矩形宽度去边距
        h = int(r.height() - 2 * inset)  # 图像高度为矩形高度去边距
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
        label.setText("")  # 清掉占位提示，避免与画面重叠
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
