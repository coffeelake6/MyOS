# showImg.py — MyOS 图像显示模块
#
# 单张画面大卡片：标题栏 + 左右两路画面 + 各自话题选择器。
# 构造时自动接入 ROS 图像桥（ros_bridge.getImg），无 ROS 时静默跳过。
# 每路画面下方各有一个话题选择器，可随时切换该路相机的订阅话题。
#
# 话题选择器为自绘按钮 + 自定义弹层，交互动画参考 Apple 设计原则：
#   - 响应在 pointer-down（按下即反馈）
#   - 菜单从触发源下方浮现，收起沿同一路径（空间一致性）
#   - 展开临界阻尼无回弹；箭头旋转带轻微回弹（阻尼 ~0.8）
#   - 弹层从触发源“展开”逐项显露（级联效果），悬停/按压背景平滑过渡

from PySide6 import QtCore, QtWidgets, QtGui

from myos_config import CONFIG

# ---------------------------------------------------------------------------
#  候选订阅话题：来自 config/config.yaml 的 camera.candidate_topics，
#  在 yaml 里增删即可，选择器自动同步
# ---------------------------------------------------------------------------
CAMERA_TOPICS = CONFIG.camera_candidate_topics()

COMBO_HEIGHT = 28   # 话题选择器高度
COMBO_GAP = 8       # 选择器与画面之间的间距

# 画面“无新帧”看门狗阈值（毫秒）：超过该时长没有新帧即回到“无信号”占位
STALE_FRAME_MS = 3000

# ---------------------------------------------------------------------------
#  动画常量（Apple 风格：默认临界阻尼，旋转可带轻微回弹）
# ---------------------------------------------------------------------------
_MS_FAST = 120      # 悬停 / 轻量反馈
_MS_MENU = 300      # 菜单展开
_MS_CLOSE = 200     # 菜单收起（更快）
_MS_CHEVRON = 240   # 箭头旋转
_ITEM_H = 34        # 弹层单项高度
_PANEL_PAD = 6      # 弹层内边距
_MARGIN = 16        # 弹层留白（软阴影 + 呼吸空间）


def _lerp_color(c1, c2, t):
    """按 t(0~1) 在两种颜色间线性插值"""
    return QtGui.QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
    )


class _TopicItem(QtWidgets.QPushButton):
    """弹层里的单个话题项：悬停/按压/键盘高亮背景平滑过渡，选中项强调色"""

    def __init__(self, text, selected=False, parent=None):
        super().__init__(text, parent)
        self._hover = 0.0
        self._press = 0.0
        self._active = 0.0
        self._selected = selected
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedHeight(_ITEM_H)
        self._hover_anim = QtCore.QPropertyAnimation(self, b"hover", self)
        self._hover_anim.setDuration(_MS_FAST)
        self._hover_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._press_anim = QtCore.QPropertyAnimation(self, b"press", self)
        self._press_anim.setDuration(90)
        self._press_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._active_anim = QtCore.QPropertyAnimation(self, b"active", self)
        self._active_anim.setDuration(_MS_FAST)
        self._active_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

    def _get_hover(self):
        return self._hover

    def _set_hover(self, v):
        self._hover = v
        self.update()

    hover = QtCore.Property(float, _get_hover, _set_hover)

    def _get_press(self):
        return self._press

    def _set_press(self, v):
        self._press = v
        self.update()

    press = QtCore.Property(float, _get_press, _set_press)

    def _get_active(self):
        return self._active

    def _set_active(self, v):
        self._active = v
        self.update()

    active = QtCore.Property(float, _get_active, _set_active)

    def set_active(self, on):
        """键盘高亮状态（平滑切换）"""
        self._active_anim.stop()
        self._active_anim.setStartValue(self._active)
        self._active_anim.setEndValue(1.0 if on else 0.0)
        self._active_anim.start()

    def enterEvent(self, e):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._press_anim.stop()
        self._press_anim.setStartValue(self._press)
        self._press_anim.setEndValue(1.0)
        self._press_anim.start()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._press_anim.stop()
        self._press_anim.setStartValue(self._press)
        self._press_anim.setEndValue(0.0)
        self._press_anim.start()
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        # 背景：透明 → 悬停 → 键盘高亮 → 按压加深
        bg = _lerp_color(QtGui.QColor(0, 0, 0, 0), QtGui.QColor("#232837"), self._hover)
        bg = _lerp_color(bg, QtGui.QColor("#2b3140"), self._active)
        bg = _lerp_color(bg, QtGui.QColor("#1a1d26"), self._press)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(self.rect(), 6, 6)
        # 文字
        f = self.font()
        f.setPixelSize(12)
        p.setFont(f)
        p.setPen(QtGui.QColor("#5ee8c8") if self._selected else QtGui.QColor("#e5e5ea"))
        elided = p.fontMetrics().elidedText(self.text(), QtCore.Qt.ElideRight,
                                            self.width() - 34)
        p.drawText(QtCore.QRect(12, 0, self.width() - 34, self.height()),
                   QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, elided)
        # 选中标记
        if self._selected:
            p.setPen(QtGui.QColor("#00d4aa"))
            f2 = self.font()
            f2.setPixelSize(11)
            p.setFont(f2)
            p.drawText(QtCore.QRect(self.width() - 26, 0, 20, self.height()),
                       QtCore.Qt.AlignCenter, "\u2713")
        p.end()


class TopicPopup(QtWidgets.QWidget):
    """话题选择弹层：从触发源下方展开，软阴影 + 淡入 + 级联展开

    绘制策略：阴影与面板全部由 paintEvent 手绘，避免
    “父级透明度特效压扁子级阴影/子级特效”的 Qt 限制。
    """

    topic_selected = QtCore.Signal(str)

    def __init__(self, selector, parent=None):
        super().__init__(parent, QtCore.Qt.FramelessWindowHint
                         | QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self._selector = selector
        self._items = []          # [(item, text)]
        self._highlight = -1
        self._closing = False
        self._dir = 1             # 展开方向：1 向下 / -1 向上
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        # 整体淡入淡出
        self._opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)
        # 项列表容器（纯布局，无特效）
        self._list = QtWidgets.QWidget(self)
        self._list_layout = QtWidgets.QVBoxLayout(self._list)
        self._list_layout.setContentsMargins(_PANEL_PAD, _PANEL_PAD,
                                             _PANEL_PAD, _PANEL_PAD)
        self._list_layout.setSpacing(2)
        # 动画
        self._fade_anim = QtCore.QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._geom_anim = QtCore.QPropertyAnimation(self, b"geometry", self)
        self._geom_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._fade_anim.finished.connect(self._on_anim_finished)

    # ------------------------------------------------------------------
    #  数据
    # ------------------------------------------------------------------

    def set_topics(self, topics, current):
        """重建项列表（每次打开前调用，保证候选话题最新）"""
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._items = []
        self._highlight = -1
        for text in topics:
            it = _TopicItem(text, selected=(text == current))
            it.clicked.connect(lambda _=False, t=text: self._choose(t))
            self._list_layout.addWidget(it)
            self._items.append((it, text))
        # 键盘高亮初始定位到当前项
        for i, (it, text) in enumerate(self._items):
            if text == current:
                self._set_highlight(i)
                break

    def _set_highlight(self, idx):
        if 0 <= self._highlight < len(self._items):
            self._items[self._highlight][0].set_active(False)
        self._highlight = idx
        if 0 <= idx < len(self._items):
            self._items[idx][0].set_active(True)

    # ------------------------------------------------------------------
    #  打开 / 关闭
    # ------------------------------------------------------------------

    def open_animated(self, global_anchor, width, bounds=None):
        """从按钮锚点展开弹层

        Args:
            global_anchor: 按钮左下角（全局坐标，含下方间距）
            width:         面板宽度（= 按钮宽度）
            bounds:        允许面板出现的全局区域；面板始终限制在其内，
                          优先向下展开，放不下则向上翻转。
        """
        n = len(self._items)
        panel_w = width
        panel_h = n * (_ITEM_H + 2) - 2 + 2 * _PANEL_PAD
        x = global_anchor.x()
        y = global_anchor.y()
        self._dir = 1
        if bounds is not None:
            b = bounds
            # 水平限位
            x = max(b.left() + 2, min(x, b.right() - panel_w - 2))
            # 垂直：优先向下，放不下则向上翻转
            if y + panel_h > b.bottom() - 2:
                self._dir = -1
                y = global_anchor.y() - panel_h - (COMBO_HEIGHT + 12)
                if y < b.top() + 2:
                    y = b.top() + 2
        else:
            scr = QtGui.QGuiApplication.screenAt(global_anchor)
            if scr is None:
                scr = QtGui.QGuiApplication.primaryScreen()
            avail = scr.availableGeometry()
            x = min(x, avail.right() - panel_w - 8)
            if y + panel_h > avail.bottom():
                self._dir = -1
                y = global_anchor.y() - panel_h + 8
        pop_w = panel_w + 2 * _MARGIN
        pop_h = panel_h + 2 * _MARGIN
        start_h = _ITEM_H + 2 * _PANEL_PAD  # 展开起始高度（单行）
        final = QtCore.QRect(x - _MARGIN, y - _MARGIN, pop_w, pop_h)
        if self._dir > 0:
            start = QtCore.QRect(final.x(), final.y(), pop_w, start_h)          # 顶部锚定，向下展开
        else:
            start = QtCore.QRect(final.x(), final.y() + pop_h - start_h, pop_w, start_h)  # 底部锚定
        self.setGeometry(final)
        self._list.setGeometry(_MARGIN, _MARGIN, panel_w, panel_h)
        self._closing = False
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()
        # 展开（临界阻尼，无回弹）+ 淡入；重置缓动，避免复用收起时的 InCubic
        self._geom_anim.stop()
        self._geom_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._geom_anim.setStartValue(start)
        self._geom_anim.setEndValue(final)
        self._geom_anim.setDuration(_MS_MENU)
        self._geom_anim.start()
        self._fade_anim.stop()
        self._fade_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setDuration(_MS_MENU)
        self._fade_anim.start()

    def close_animated(self):
        """沿同一路径收起（镜像缓动，更快）"""
        if self._closing or not self.isVisible():
            return
        self._closing = True
        self._geom_anim.stop()
        cur = self.geometry()
        start_h = _ITEM_H + 2 * _PANEL_PAD
        if self._dir > 0:
            end = QtCore.QRect(cur.x(), cur.y(), cur.width(), start_h)
        else:
            end = QtCore.QRect(cur.x(), cur.y() + cur.height() - start_h,
                               cur.width(), start_h)
        self._geom_anim.setStartValue(cur)
        self._geom_anim.setEndValue(end)
        self._geom_anim.setDuration(_MS_CLOSE)
        self._geom_anim.setEasingCurve(QtCore.QEasingCurve.InCubic)
        self._geom_anim.start()
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setDuration(_MS_CLOSE)
        self._fade_anim.setEasingCurve(QtCore.QEasingCurve.InCubic)
        self._fade_anim.start()

    def _on_anim_finished(self):
        if self._closing:
            self._closing = False
            self.hide()

    # ------------------------------------------------------------------
    #  选择 / 键盘
    # ------------------------------------------------------------------

    def _choose(self, text):
        if self._closing:
            return
        self.topic_selected.emit(text)
        self.close_animated()

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.close_animated()
            e.accept()
            return
        if e.key() in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
            n = len(self._items)
            if n:
                d = 1 if e.key() == QtCore.Qt.Key_Down else -1
                self._set_highlight((self._highlight + d) % n)
            e.accept()
            return
        if e.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            if 0 <= self._highlight < len(self._items):
                self._choose(self._items[self._highlight][1])
            e.accept()
            return
        super().keyPressEvent(e)

    # ------------------------------------------------------------------
    #  绘制：软阴影 + 面板（手绘，避免特效相互压制）
    # ------------------------------------------------------------------

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = QtCore.QRectF(_MARGIN, _MARGIN,
                             self.width() - 2 * _MARGIN,
                             self.height() - 2 * _MARGIN)
        # 软阴影：多层半透明圆角矩形下移堆叠
        p.setPen(QtCore.Qt.NoPen)
        for i in range(6):
            alpha = int(42 * (1.0 - i / 6.0))
            p.setBrush(QtGui.QColor(0, 0, 0, alpha))
            p.drawRoundedRect(rect.translated(0, 3 + i * 2), 10, 10)
        # 面板本体
        p.setBrush(QtGui.QColor("#16181f"))
        p.setPen(QtGui.QPen(QtGui.QColor("#2b2f3a"), 1))
        p.drawRoundedRect(rect, 10, 10)
        p.end()

    # ------------------------------------------------------------------
    #  点击外部关闭
    # ------------------------------------------------------------------

    def showEvent(self, e):
        super().showEvent(e)
        QtWidgets.QApplication.instance().installEventFilter(self)

    def hideEvent(self, e):
        super().hideEvent(e)
        QtWidgets.QApplication.instance().removeEventFilter(self)

    def eventFilter(self, obj, ev):
        if ev.type() == QtCore.QEvent.MouseButtonPress and not self._closing:
            gp = ev.globalPosition().toPoint()
            sel = self._selector
            inside_btn = sel.isVisible() and \
                sel.geometry().contains(sel.mapFromGlobal(gp))
            if not self.geometry().contains(gp) and not inside_btn:
                self.close_animated()
                return True  # 吞掉该点击，避免再触发底层控件
        return False


class TopicSelector(QtWidgets.QPushButton):
    """自绘话题选择按钮：按下展开自定义弹层，交互动画见类注释

    行为对齐 Apple 设计原则：
      - 按下（pointer-down）即反馈并展开，不是等 release
      - 箭头旋转带轻微回弹（Rotation: damping ~0.8）
      - 弹层从触发源展开 / 沿同路径收起
    """

    topic_selected = QtCore.Signal(str)

    def __init__(self, topics=None, parent=None):
        super().__init__(parent)
        self._topics = list(topics or [])
        self._current = self._topics[0] if self._topics else ""
        self._hover = 0.0
        self._press = 0.0
        self._chevron = 0.0
        self._popup = None
        self._bounds_getter = None
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedHeight(COMBO_HEIGHT)
        self._hover_anim = QtCore.QPropertyAnimation(self, b"hover", self)
        self._hover_anim.setDuration(_MS_FAST)
        self._hover_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._press_anim = QtCore.QPropertyAnimation(self, b"press", self)
        self._press_anim.setDuration(90)
        self._press_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._chev_anim = QtCore.QPropertyAnimation(self, b"chevron", self)
        self._chev_anim.setDuration(_MS_CHEVRON)
        self._chev_anim.setEasingCurve(QtCore.QEasingCurve.OutBack)  # 轻微回弹

    # ----- 动画属性 -----

    def _get_hover(self):
        return self._hover

    def _set_hover(self, v):
        self._hover = v
        self.update()

    hover = QtCore.Property(float, _get_hover, _set_hover)

    def _get_press(self):
        return self._press

    def _set_press(self, v):
        self._press = v
        self.update()

    press = QtCore.Property(float, _get_press, _set_press)

    def _get_chevron(self):
        return self._chevron

    def _set_chevron(self, v):
        self._chevron = v
        self.update()

    chevron = QtCore.Property(float, _get_chevron, _set_chevron)

    # ----- 数据 -----

    def set_topics(self, topics):
        self._topics = list(topics)

    def set_popup_bounds(self, getter):
        """设置弹层允许出现的全局区域获取器（无参、返回 QRect）"""
        self._bounds_getter = getter

    def set_current(self, text):
        if not text:
            return
        if text not in self._topics:
            self._topics.insert(0, text)
        self._current = text
        self.update()

    def current_text(self):
        return self._current

    # ----- 交互 -----

    def enterEvent(self, e):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            # 响应在 pointer-down：按下立即反馈并展开
            self._press_anim.stop()
            self._press_anim.setStartValue(self._press)
            self._press_anim.setEndValue(1.0)
            self._press_anim.start()
            self.toggle()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._press_anim.stop()
        self._press_anim.setStartValue(self._press)
        self._press_anim.setEndValue(0.0)
        self._press_anim.start()
        super().mouseReleaseEvent(e)

    def toggle(self):
        if self._popup is not None and self._popup.isVisible():
            self._popup.close_animated()
            self._animate_chevron(0.0)
        else:
            self._open_popup()

    def _open_popup(self):
        if self._popup is None:
            self._popup = TopicPopup(self, self.window())
            self._popup.topic_selected.connect(self._on_popup_choice)
        self._popup.set_topics(self._topics, self._current)
        gp = self.mapToGlobal(QtCore.QPoint(0, self.height() + 6))
        bounds = self._bounds_getter() if self._bounds_getter is not None else None
        self._popup.open_animated(gp, self.width(), bounds)
        self._animate_chevron(180.0)

    def _on_popup_choice(self, text):
        self.set_current(text)
        self.topic_selected.emit(text)

    def _animate_chevron(self, target):
        self._chev_anim.stop()
        self._chev_anim.setStartValue(self._chevron)
        self._chev_anim.setEndValue(target)
        self._chev_anim.start()

    # ----- 绘制 -----

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = self.rect()
        # 背景：悬停提亮、按压加深
        bg = _lerp_color(QtGui.QColor("#14161d"), QtGui.QColor("#1c1f28"), self._hover)
        bg = _lerp_color(bg, QtGui.QColor("#0f1116"), self._press)
        p.setPen(QtGui.QPen(QtGui.QColor("#2a2b36"), 1))
        p.setBrush(bg)
        p.drawRoundedRect(QtCore.QRectF(0.5, 0.5, r.width() - 1, r.height() - 1), 6, 6)
        # 当前话题（过长省略号）
        f = p.font()
        f.setPixelSize(12)
        p.setFont(f)
        p.setPen(QtGui.QColor("#e5e5ea"))
        text_r = QtCore.QRect(10, 0, r.width() - 34, r.height())
        elided = p.fontMetrics().elidedText(self._current, QtCore.Qt.ElideRight,
                                            text_r.width())
        p.drawText(text_r, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, elided)
        # 箭头（旋转动画）
        p.save()
        p.translate(r.width() - 15, r.height() / 2.0)
        p.rotate(self._chevron)
        tri = QtGui.QPolygonF([QtCore.QPointF(0, -2.5), QtCore.QPointF(4, 3.5),
                               QtCore.QPointF(-4, 3.5)])
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor("#8e8e93"))
        p.drawPolygon(tri)
        p.restore()
        p.end()


class _ImageCard(QtWidgets.QWidget):
    """画面大卡片：标题栏 + 左右两路画面 + 各自话题选择器（合并为一张卡片）

    卡片表面由 paintEvent 自绘（圆角 + 描边），风格与实时数据 / 参数修改面板一致。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("image-card")

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(10)

        # 标题栏
        header = QtWidgets.QHBoxLayout()
        title_label = QtWidgets.QLabel("相机画面")
        title_label.setStyleSheet("color: #e5e5ea; font-size: 13px; font-weight: 600;")
        header.addWidget(title_label)
        header.addStretch(1)
        root.addLayout(header)

        # 两路画面（无缝衔接：无间隔、无边框、无圆角，融合为一块连续视窗）
        images = QtWidgets.QHBoxLayout()
        images.setSpacing(0)
        self.img1_label = self._make_view_label("CAM1 无信号")
        self.img2_label = self._make_view_label("CAM2 无信号")
        images.addWidget(self.img1_label, stretch=1)
        images.addWidget(self.img2_label, stretch=1)
        root.addLayout(images, stretch=1)

        # 两个话题选择器（并排）
        selectors = QtWidgets.QHBoxLayout()
        selectors.setSpacing(12)
        self.topic_selector1 = TopicSelector(CAMERA_TOPICS, self)
        self.topic_selector2 = TopicSelector(CAMERA_TOPICS, self)
        selectors.addWidget(self.topic_selector1, stretch=1)
        selectors.addWidget(self.topic_selector2, stretch=1)
        root.addLayout(selectors)

    @staticmethod
    def _make_view_label(text):
        """画面标签：纯深底（无边框/圆角，便于两路无缝衔接）"""
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setStyleSheet(
            "background-color: #0a0b10;"
            "color: #6c6c70;"
            "font: 13px 'SF Pro Text', 'Segoe UI', sans-serif;"
        )
        label.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                            QtWidgets.QSizePolicy.Expanding)
        label.setMinimumSize(2, 2)
        return label

    def paintEvent(self, e):
        """绘制卡片圆角底 + 描边"""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtGui.QPen(QtGui.QColor("#1f232d"), 1))
        p.setBrush(QtGui.QColor("#12141a"))
        p.drawRoundedRect(QtCore.QRectF(0.5, 0.5,
                                        self.width() - 1, self.height() - 1), 12, 12)
        p.end()


class showImg(QtWidgets.QWidget):
    """图像显示模块：一张画面大卡片（左右两路画面 + 各自话题选择器）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboard-panel")
        # 让父布局正确分配尺寸（无自身布局时需显式声明可扩展，否则 resizeEvent 不触发）
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)

        # 缓存最新 QImage，供窗口缩放时按比例刷新
        self._img1 = None
        self._img2 = None

        # 画面“无新帧”看门狗：暂停 bag / 数据停止后超过 STALE_FRAME_MS
        # 没有新帧，画面自动回到“无信号”占位；新帧到达立即恢复（实时刷新）
        self._cam_had1 = False
        self._cam_had2 = False
        self._cam_last1 = QtCore.QElapsedTimer()
        self._cam_last2 = QtCore.QElapsedTimer()
        self._stale_timer = QtCore.QTimer(self)
        self._stale_timer.setInterval(500)
        self._stale_timer.timeout.connect(self._check_stale)
        self._stale_timer.start()

        # 画面大卡片：限定在原占位区域内（窗口宽高的一半，水平居中偏左、置顶）
        self.card = _ImageCard(self)
        self.img1_label = self.card.img1_label
        self.img2_label = self.card.img2_label
        self.card.setGeometry(self._frame_rect().toRect())

        # ROS 图像桥：订阅两路相机话题，图像送至两张卡片的画面区
        # 无 ROS 时静默跳过，UI 仍可独立运行
        try:
            from ros_bridge.getImg import setup_image_bridge
            self._bridge = setup_image_bridge(self, self.set_image1, self.set_image2)
        except Exception as e:
            print(f"[showImg] 未启用 ROS 图像桥: {e}")
            self._bridge = None

        # 话题选择器（弹层限定在本模块区域内）
        self.cam1_combo = self.card.topic_selector1
        self.cam2_combo = self.card.topic_selector2
        self.cam1_combo.set_popup_bounds(self._global_bounds)
        self.cam2_combo.set_popup_bounds(self._global_bounds)
        if self._bridge is not None:
            cur = self._bridge.topics()
            self.cam1_combo.set_current(cur.get("cam1"))
            self.cam2_combo.set_current(cur.get("cam2"))
        self.cam1_combo.topic_selected.connect(self._on_cam1_topic_changed)
        self.cam2_combo.topic_selected.connect(self._on_cam2_topic_changed)

        self._entrance_anims = []

    def _frame_rect(self):
        """计算卡片区域（窗口宽高的一半，水平居中偏左、置顶）

        宽度钳制在本模块宽度内；高度钳制在本模块可用空间内
        （预留 6px 底边距），保证卡片永远不会越出 showImg 区域，
        避免被下方快捷启动面板遮挡。
        """
        win = self.window()
        win_w = win.width() if win is not None else self.width()
        win_h = win.height() if win is not None else self.height()
        rw = min(win_w / 2, self.width())
        rh = min(win_h / 2 - 100, self.height() - 6)
        x = (self.width() - rw) / 16
        y = 0
        return QtCore.QRectF(x, y, rw, rh)

    def _global_bounds(self):
        """卡片区域在全局坐标系下的范围（用于限定弹层）"""
        r = self._frame_rect()
        tl = self.mapToGlobal(QtCore.QPoint(int(r.x()), int(r.y())))
        return QtCore.QRect(tl.x(), tl.y(), int(r.width()), int(r.height()))

    def resizeEvent(self, event):
        """窗口尺寸变化时重新定位卡片区域并按新尺寸重贴图像"""
        super().resizeEvent(event)
        self.card.setGeometry(self._frame_rect().toRect())
        QtCore.QTimer.singleShot(0, self._refresh_pixmaps)

    # ----- 话题切换 -----

    def _on_cam1_topic_changed(self, topic):
        self._switch_topic("cam1", topic, self.img1_label)

    def _on_cam2_topic_changed(self, topic):
        self._switch_topic("cam2", topic, self.img2_label)

    def _switch_topic(self, camera, topic, label):
        """把指定相机的订阅切到新话题，并清掉旧画面"""
        if self._bridge is None:
            print("[showImg] ROS 图像桥未启用，无法切换话题")
            return
        if not topic or self._bridge.topics().get(camera) == topic:
            return  # 与当前一致，无需切换
        if not self._bridge.set_topic(camera, topic):
            print(f"[showImg] 切换话题失败: {camera} -> {topic}")
            return
        # 清掉旧话题的画面，回到占位提示，并重置看门狗状态
        if camera == "cam1":
            self._img1 = None
            self._cam_had1 = False
            self._cam_last1.restart()
        else:
            self._img2 = None
            self._cam_had2 = False
            self._cam_last2.restart()
        label.clear()
        label.setText("CAM1 无信号" if camera == "cam1" else "CAM2 无信号")

    # ----- 对外接口：ImageSubscriber 信号槽 -----

    @QtCore.Slot(QtGui.QImage)
    def set_image1(self, qimg):
        """接收 camera1 图像并显示（重置该路“无新帧”计时）"""
        self._img1 = qimg
        self._cam_had1 = True
        self._cam_last1.restart()
        self._refresh_label(self.img1_label, qimg)

    @QtCore.Slot(QtGui.QImage)
    def set_image2(self, qimg):
        """接收 camera2 图像并显示（重置该路“无新帧”计时）"""
        self._img2 = qimg
        self._cam_had2 = True
        self._cam_last2.restart()
        self._refresh_label(self.img2_label, qimg)

    # ----- 画面“无新帧”看门狗 -----

    def _check_stale(self):
        """周期检查两路画面：超过 STALE_FRAME_MS 无新帧则回到“无信号”占位"""
        self._mark_stale(1, self._cam_had1, self._cam_last1,
                         self.img1_label, "CAM1")
        self._mark_stale(2, self._cam_had2, self._cam_last2,
                         self.img2_label, "CAM2")

    def _mark_stale(self, n, had, timer, label, name):
        if not had or timer.elapsed() <= STALE_FRAME_MS:
            return
        if (n == 1 and self._img1 is None) or (n == 2 and self._img2 is None):
            return  # 已处于占位态
        if n == 1:
            self._img1 = None
        else:
            self._img2 = None
        label.setPixmap(QtGui.QPixmap())
        label.setText("%s 无信号" % name)

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
        """大卡片淡入（Apple 式）"""
        eff = QtWidgets.QGraphicsOpacityEffect(self.card)
        eff.setOpacity(0.0)
        self.card.setGraphicsEffect(eff)
        anim = QtCore.QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(420)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        anim.start()
        anim.finished.connect(lambda: self.card.setGraphicsEffect(None))
        self._entrance_anims.append(anim)
