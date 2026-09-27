# base.py — MyOS 顶部标题栏 / 底部状态栏 / 主题切换胶囊
#
# 从 main_window.py 分离出来的通用栏组件：
#   HeaderBar   — 顶部标题栏（LOGO | 副标题 | 主题切换胶囊 | 右侧双 logo）
#   FooterBar   — 底部状态栏（版本号）
#   ThemeSwitch — 主题切换胶囊（浅色 / 深色，点击即切换并写回 config.yaml）
#
# 右侧双 logo（学校 / 车队）在启动过渡结束时由 show_logos() 淡入展示，
# 与 SplashPage 里的 logo 形成“从画面中心迁移到标题栏”的连续过渡。
#
# 颜色统一取自 theme.T 的 token（见 ui/theme.py），这里不写死色值；
# 自绘控件在 paintEvent 里实时取色，切换主题后自动跟着变。

import os

from PySide6 import QtCore, QtWidgets, QtGui

from theme import T, THEME_LABELS, THEME_NAMES

# 车队 logo 资源路径（学校 logo 有深/浅两套，走 theme.school_logo() 按主题取）
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEAM_LOGO_PATH = os.path.join(_ROOT, "style", "icon", "魅影方程式.png")

LOGO_H = 32   # 标题栏内 logo 高度

# 胶囊高亮块滑动用的柔性回弹曲线。
# Qt 6 的 QEasingCurve.OutBack 忽略了 setAmplitude(会固定 10% 过冲)，
# 这里自带一个可控过冲版本：_BACK 越大回弹越明显（0.6 ≈ 3.9% 过冲）。
_BACK = 0.6 * 1.70158


def _soft_back(t):
    """柔性回弹缓动：先略冲过终点，再收回，用于高亮块滑动"""
    u = t - 1.0
    return 1.0 + (_BACK + 1.0) * u ** 3 + _BACK * u ** 2


class _LogoLabel(QtWidgets.QLabel):
    """标题栏 logo：按当前主题取图，切换主题时自动换成对应的一套"""

    def __init__(self, path_fn, parent=None):
        super().__init__(parent)
        self._path_fn = path_fn      # () -> 当前主题下该用的图片路径
        self.setFixedHeight(LOGO_H)
        self._apply()
        T.on_change(self._apply)

    def _apply(self):
        img = QtGui.QImage(self._path_fn())
        if img.isNull():
            self.clear()
            return
        w = max(1, int(LOGO_H * img.width() / img.height()))
        self.setPixmap(QtGui.QPixmap.fromImage(img).scaled(
            w, LOGO_H, QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation))


class ThemeSwitch(QtWidgets.QWidget):
    """主题切换胶囊：浅色 | 深色

    自绘分段胶囊，选中段是一块滑动的绿色高亮块，用柔性回弹曲线做过渡
    （轻微回弹后收束），可中断，动画基于当前呈现值，切换途中再点也能平滑接管。
    点击立即生效：theme.T 会重新套用全局样式并写回 config/config.yaml。

    启动过渡动画期间不显示（透明度 0、也不接受点击），过渡结束后由 reveal() 淡入。
    """

    _PAD = 3     # 胶囊内边距
    _W = 104     # 胶囊总宽
    _H = 26      # 胶囊高度

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self._W, self._H)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip("切换界面主题（浅色 / 深色），选择会保存到 config.yaml")
        # 高亮块位置：0=浅色，1=深色（以 theme 的当前值为准，避免两处状态不一致）
        self._idx = 1.0 if T.is_dark() else 0.0
        self._hover_seg = -1
        self._anim = QtCore.QPropertyAnimation(self, b"idx", self)
        self._anim.setDuration(340)
        # 柔性过渡：带约 3.9% 过冲（≈1.9px），小于胶囊内边距 3px，
        # 高亮块不会顶出胶囊边缘；切到一半再点也能从当前值平滑接管
        curve = QtCore.QEasingCurve()
        curve.setCustomType(_soft_back)
        self._anim.setEasingCurve(curve)
        self._curve = curve          # 保住自定义曲线的引用

        # 启动过渡动画期间保持不可见（占位不变，所以标题栏其它元素不会跳位）
        self._armed = False
        self._effect = QtWidgets.QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)
        self._reveal_anim = QtCore.QPropertyAnimation(self._effect, b"opacity", self)
        self._reveal_anim.setDuration(420)
        self._reveal_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

    def reveal(self):
        """启动过渡结束后淡入，并开始接受点击"""
        if self._armed:
            return
        self._armed = True
        self._reveal_anim.stop()
        self._reveal_anim.setStartValue(self._effect.opacity())
        self._reveal_anim.setEndValue(1.0)
        self._reveal_anim.start()

    # ---- 动画属性（QPropertyAnimation 的目标） ----
    def _get_idx(self):
        return self._idx

    def _set_idx(self, v):
        self._idx = v
        self.update()

    idx = QtCore.Property(float, _get_idx, _set_idx)

    # ---- 几何 ----
    def _seg_rect(self, i):
        """第 i 个分段的矩形"""
        seg_w = (self._W - self._PAD * 2) / 2.0
        return QtCore.QRectF(self._PAD + i * seg_w, self._PAD,
                             seg_w, self._H - self._PAD * 2)

    def _seg_at(self, x):
        """x 坐标落在哪个分段上"""
        seg_w = (self._W - self._PAD * 2) / 2.0
        return 1 if x - self._PAD >= seg_w else 0

    # ---- 交互 ----
    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton and self._armed:
            self._select(self._seg_at(e.position().x()))
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        seg = self._seg_at(e.position().x())
        if seg != self._hover_seg:
            self._hover_seg = seg
            self.update()

    def leaveEvent(self, e):
        self._hover_seg = -1
        self.update()
        super().leaveEvent(e)

    def _select(self, i):
        """切到第 i 个主题：应用 + 写回配置，并让高亮块滑过去"""
        name = THEME_NAMES[i]
        T.set(name)
        self._anim.stop()
        self._anim.setStartValue(self._idx)
        self._anim.setEndValue(float(i))
        self._anim.start()

    # ---- 绘制 ----
    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        radius = (self._H - 1) / 2.0
        # 胶囊底
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(T.qcolor("press"))
        p.drawRoundedRect(QtCore.QRectF(0.5, 0.5, self._W - 1, self._H - 1),
                          radius, radius)

        # 未选中段的悬停提示（轻微加深）
        for i in range(2):
            if i == self._hover_seg and abs(self._idx - i) > 0.01:
                hi = (self._H - 8) / 2.0
                p.setBrush(T.qcolor("muted_line"))
                p.drawRoundedRect(self._seg_rect(i).adjusted(1, 1, -1, -1), hi, hi)

        # 滑动高亮块
        left, right = self._seg_rect(0), self._seg_rect(1)
        x = left.x() + (right.x() - left.x()) * self._idx
        thumb = QtCore.QRectF(x, left.y(), left.width(), left.height())
        p.setBrush(T.qcolor("accent"))
        p.drawRoundedRect(thumb, thumb.height() / 2.0, thumb.height() / 2.0)

        # 分段文字
        f = p.font()
        f.setPixelSize(11)
        f.setWeight(QtGui.QFont.DemiBold)
        p.setFont(f)
        active = 1 if self._idx >= 0.5 else 0
        for i, name in enumerate(THEME_NAMES):
            p.setPen(T.qcolor("on_accent") if i == active else T.qcolor("fg_dim"))
            p.drawText(self._seg_rect(i).toRect(), QtCore.Qt.AlignCenter,
                       THEME_LABELS[name])
        p.end()


class HeaderBar(QtWidgets.QWidget):
    """顶部标题栏：LOGO | 副标题 | 主题切换 | ROS 连接状态"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # LOGO
        logo = QtWidgets.QLabel("MyOS")
        T.styled(logo, "color: @accent; font-size: 22px; font-weight: 700; "
                       "letter-spacing: -0.02em;")
        layout.addWidget(logo)

        separator = QtWidgets.QLabel("|")
        T.styled(separator, "color: @muted_line; font-size: 22px;")
        layout.addWidget(separator)

        subtitle = QtWidgets.QLabel("A03 无人系统操作面板")
        T.styled(subtitle, "color: @fg_dim; font-size: 13px; "
                           "letter-spacing: 0.02em;")
        layout.addWidget(subtitle)

        layout.addStretch()

        # 主题切换胶囊
        self.theme_switch = ThemeSwitch()
        layout.addWidget(self.theme_switch)

        # ROS 连接状态指示（暂未启用，保留以备后续接入）
        status_led = QtWidgets.QLabel("\u25cf  ROS 未连接")
        status_led.setObjectName("status-warn")
        # layout.addWidget(status_led)

        # 右侧：学校 / 车队 logo（启动过渡结束时由 show_logos() 淡入展示）
        self._logos = QtWidgets.QWidget(self)
        logos_layout = QtWidgets.QHBoxLayout(self._logos)
        logos_layout.setContentsMargins(0, 0, 0, 0)
        logos_layout.setSpacing(12)
        logos_layout.addWidget(_LogoLabel(T.school_logo))
        #logos_layout.addWidget(_LogoLabel(lambda: TEAM_LOGO_PATH))
        layout.addWidget(self._logos)
        layout.addSpacing(12)
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

    def show_theme_switch(self):
        """启动过渡结束后淡入主题切换胶囊"""
        self.theme_switch.reveal()


class FooterBar(QtWidgets.QWidget):
    """底部状态栏：版本号"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        ver = QtWidgets.QLabel("MyOS v1.1")
        T.styled(ver, "color: @fg_faint; font-size: 10px; "
                      "letter-spacing: 0.04em;")
        layout.addWidget(ver)

        layout.addStretch()
