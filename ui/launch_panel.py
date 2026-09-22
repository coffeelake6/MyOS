# launch_panel.py — 快捷启动面板（MyOS）
#
# 功能：图像卡片下方的一站式启动面板：
#   - 一键运行 sh 脚本（下拉框扫描 sh/ 目录，可自由增删）
#   - 一键打开 RViz
#   - 一键终止所有脚本启动的进程（按 KILL_PATTERNS 关键词 pkill）
#   - 勾选话题录制 rosbag（候选话题来自配置的 bag.record_topics，可自由增删）
#   - 可指定 rosbag 保存目录（默认 ~/bags，可浏览选择）
#   - 选择 bag 文件播放（rosbag play）
#
# 当前进度：sh 运行 / RViz / 一键终止 / rosbag 录制 / 播放均已实现。
#
# 设计（Apple Fluid Interface）：
#   - 反馈在 pointer-down：按下即加深、悬停提亮
#   - 状态切换零延迟：录制态立即变色/改字
#   - 层级与留白：分区小标题（灰）+ 内容行（紧凑），状态用胶囊标签
#
# 颜色统一取自 theme.T 的 token（见 ui/theme.py），本文件不写死色值。

import os
import shutil
import signal
import subprocess
import time

from PySide6 import QtCore, QtWidgets, QtGui

from theme import T

from myos_config import CONFIG

# 脚本目录（launch.script_dir）与录制候选话题（bag.record_topics）都在用的时候
# 实时向 CONFIG 取：切换主配置后 apply_config() 能立即刷新，不再固化在模块常量里。

# rosbag 默认保存目录
DEFAULT_BAG_DIR = os.path.expanduser("~/bag")

# 一键终止时按关键词匹配的进程（pkill -f，可自由增删）。
# 覆盖 sh 脚本启动的 roslaunch/rosrun/roscore 等通用进程与节点可执行文件。
# 注意：请勿加入会命中本程序自身命令行（python main.py）的关键词。
KILL_PATTERNS = [
    "roslaunch",
    "rosrun",
    "roscore",
    "rosmaster",
    "rviz",
    "motionCompensation",
    "cubicSpline",
    "iou_fusion",
    "cluster_transform",
    "fast_lio",
]


def _find_binary(name):
    """优先从 PATH 查找命令；找不到再尝试常见 ROS 安装路径，返回绝对路径或 None"""
    p = shutil.which(name)
    if p:
        return p
    for d in ("/opt/ros/noetic/bin", "/opt/ros/melodic/bin",
              "/opt/ros/kinetic/bin"):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return None

# 分区子卡片样式模板（两个功能区域做视觉隔离；@token 由 T.styled 翻译）
_ZONE_QSS = ("QFrame { background-color: @zone_bg;"
             " border: 1px solid @divider; border-radius: 10px; }")


def _shade(hex_color, factor):
    """按 factor 提亮(>1) 或加深(<1) 一个 #rrggbb 颜色"""
    c = QtGui.QColor(hex_color)
    c = c.lighter(factor) if factor > 1 else c.darker(int(1 / factor * 100))
    return c.name()


def _rgba(hex_color, alpha):
    """把任意 #rrggbb 颜色 + 透明度转成 QSS 的 rgba() 写法。

    Qt 的样式表不支持 #RRGGBBAA 八位色（会被整条忽略），
    想让胶囊底/描边按钮的 hover 底色真正生效必须用 rgba()。
    参数是任意颜色字符串（如 T.color("accent") 的结果）。
    """
    return T.rgba_of(hex_color, alpha)


class _Btn(QtWidgets.QPushButton):
    """带强调色切换的按钮：悬停提亮、按下加深（pointer-down 反馈）
    outline=True 时为描边样式（透明底 + 彩色描边，用于危险操作）

    高度统一由 sizeHint/minimumSizeHint 强制为 _HEIGHT：
    全局主题的 QPushButton 规则（padding / min-height）会在样式合并时
    重置 setFixedHeight 设下的最小高度，只有重写尺寸提示才稳定可靠。
    """

    _HEIGHT = 28

    def __init__(self, text, accent=None, outline=False, parent=None):
        super().__init__(text, parent)
        self._accent = accent          # 语义色名（如 "accent" / "danger"），None = 中性按钮
        self._outline = outline
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._apply_qss()
        # 换主题时按新配色重套一遍（accent 存的是色名，这里才会取到新色值）
        T.on_change(self._apply_qss)
        self.setFixedHeight(self._HEIGHT)

    def sizeHint(self):
        hint = super().sizeHint()
        return QtCore.QSize(hint.width(), self._HEIGHT)

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        return QtCore.QSize(hint.width(), self._HEIGHT)

    def _apply_qss(self):
        # 注意：必须显式写 padding + min-height:0，否则会继承全局主题
        # QPushButton 的 padding:9px 22px / min-height:26px，
        # 把 setFixedHeight(28) 撑破导致按钮被裁切
        accent = T.color(self._accent) if self._accent else T.color("track")
        if self._outline:
            T.styled(
                self,
                "QPushButton { background: transparent; color: %s;"
                " border: 1px solid %s; border-radius: 8px;"
                " font-size: 12px; font-weight: 600;"
                " padding: 0 10px; min-height: 0px; }"
                "QPushButton:hover { background-color: %s; }"
                "QPushButton:pressed { background-color: %s; }"
                % (accent, accent, _rgba(accent, 0.13), _rgba(accent, 0.20)))
            return
        T.styled(
            self,
            "QPushButton { background-color: %s; color: %s; border: none;"
            " border-radius: 8px; font-size: 12px; font-weight: 600;"
            " padding: 0 10px; min-height: 0px; }"
            "QPushButton:hover { background-color: %s; }"
            "QPushButton:pressed { background-color: %s; }"
            % (accent,
               T.color("on_accent") if self._accent else T.color("fg"),
               _shade(accent, 118),
               _shade(accent, 82)))

    def set_accent(self, accent):
        """切换强调色（传语义色名，如 "accent" / "danger"）"""
        self._accent = accent
        self._apply_qss()


class _Pill(QtWidgets.QLabel):
    """状态胶囊标签（圆角浅底）

    记住语义色名而不是具体色值，换主题时自动按新配色重套样式。
    """

    def __init__(self, text, token, parent=None):
        super().__init__(text, parent)
        self._token = token
        self._apply()
        T.on_change(self._apply)

    def set_state(self, text, token):
        """更新胶囊文字与语义色（token 如 "accent" / "fg_faint"）"""
        self._token = token
        self.setText(text)
        self._apply()

    def _apply(self):
        color = T.color(self._token)
        T.styled(
            self,
            "background-color: %s; color: %s; border: 1px solid %s;"
            " border-radius: 9px; padding: 1px 8px; font-size: 10px;"
            % (_rgba(color, 0.13), color, _rgba(color, 0.33)))


class LaunchPanel(QtWidgets.QWidget):
    """快捷启动面板：两个隔离的功能区域（快捷启动 / Bag 工具：录制 + 播放）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("launch-panel")
        # 高度自适应内容（不固定），保证任何窗口尺寸下都不裁切/遮挡；
        # 左侧 VBox 中 showImg 占满剩余空间
        self._recording = False
        self._playing = False
        self._save_dir = DEFAULT_BAG_DIR
        self._play_file = ""
        self._record_proc = None
        self._play_proc = None
        self._topic_boxes = []

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(8)

        # ============ 区域 1：快捷启动（脚本 / RViz / 终止） ============
        zone1 = QtWidgets.QFrame()
        T.styled(zone1, _ZONE_QSS)
        z1 = QtWidgets.QVBoxLayout(zone1)
        z1.setContentsMargins(10, 6, 10, 6)
        z1.setSpacing(4)

        t1 = QtWidgets.QLabel("快捷启动")
        T.styled(t1, "color: @fg; font-size: 12px; font-weight: 600;")
        z1.addWidget(t1)

        self.script_combo = QtWidgets.QComboBox()
        self.script_combo.addItems(self._scan_scripts())
        T.styled(
            self.script_combo,
            "QComboBox { background-color: @input_bg; color: @fg;"
            " border: 1px solid @input_border;"
            " border-radius: 6px; padding: 3px 8px; font-size: 12px; }"
            "QComboBox:hover { border-color: @accent; }"
            "QComboBox::drop-down { border: none; width: 20px; }"
            "QComboBox QAbstractItemView { background-color: @popup_bg; color: @fg;"
            " border: 1px solid @input_border; selection-background-color: @accent;"
            " selection-color: @on_accent; }")
        row1 = QtWidgets.QHBoxLayout()
        row1.setSpacing(8)
        run_btn = _Btn("\u25b6 运行脚本", "accent")
        run_btn.clicked.connect(self._run_script)
        rviz_btn = _Btn("RViz", None)
        rviz_btn.clicked.connect(self._open_rviz)
        kill_btn = _Btn("\u2715 终止全部", "danger", outline=True)
        kill_btn.clicked.connect(self._kill_all)
        row1.addWidget(self.script_combo, stretch=1)
        row1.addWidget(run_btn)
        row1.addWidget(rviz_btn)
        row1.addWidget(kill_btn)
        z1.addLayout(row1)
        root.addWidget(zone1)

        # ============ 区域 2：Bag 工具（录制 + 播放） ============
        zone2 = QtWidgets.QFrame()
        T.styled(zone2, _ZONE_QSS)
        z2 = QtWidgets.QVBoxLayout(zone2)
        z2.setContentsMargins(10, 6, 10, 6)
        z2.setSpacing(4)

        # 标题行：标题 + 状态胶囊 + 全选/清空
        bag_head = QtWidgets.QHBoxLayout()
        bag_head.setSpacing(6)
        bag_title = QtWidgets.QLabel("Rosbag 录制")
        T.styled(bag_title, "color: @fg; font-size: 12px; font-weight: 600;")
        bag_head.addWidget(bag_title)
        bag_head.addStretch(1)
        self.bag_status = self._make_pill("未录制", "fg_faint")
        bag_head.addWidget(self.bag_status)
        self._sel_all_btn = self._make_small_btn("全选", self._select_all)
        self._sel_none_btn = self._make_small_btn("清空", self._select_none)
        bag_head.addWidget(self._sel_all_btn)
        bag_head.addWidget(self._sel_none_btn)
        z2.addLayout(bag_head)

        # 保存目录行：标签 + 输入框 + 浏览
        path_row, self.save_dir_edit = self._make_path_row(
            "保存目录", self._browse_dir, self._save_dir)
        self.save_dir_edit.editingFinished.connect(self._sync_save_dir)
        z2.addLayout(path_row)

        # 话题勾选区（滚动，高度随话题数自适应）
        self._topics_w = QtWidgets.QWidget()
        # 背景透明，避免全局主题的 QWidget 底色盖住 zone 卡片底色
        T.styled(self._topics_w, "background: transparent;")
        self._topics_lay = QtWidgets.QVBoxLayout(self._topics_w)
        self._topics_lay.setContentsMargins(2, 0, 2, 0)
        self._topics_lay.setSpacing(1)

        self._topics_scroll = QtWidgets.QScrollArea()
        self._topics_scroll.setWidgetResizable(True)
        self._topics_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        T.styled(self._topics_scroll,
                 "QScrollArea { background: transparent; border: none; }")
        T.styled(self._topics_scroll.viewport(), "background: transparent;")
        self._topics_scroll.setWidget(self._topics_w)
        z2.addWidget(self._topics_scroll)
        self._rebuild_topic_boxes()

        # 录制控制
        self.record_btn = _Btn("\u25cf 开始录制", "accent")
        self.record_btn.clicked.connect(self._toggle_record)
        z2.addWidget(self.record_btn)

        # ---- 播放分区（与录制区域分隔） ----
        play_div = QtWidgets.QFrame()
        play_div.setFixedHeight(1)
        T.styled(play_div, "background-color: @divider; border: none;")
        z2.addWidget(play_div)

        # 播放文件行：标签 + 输入框 + 浏览
        play_row, self.play_file_edit = self._make_path_row(
            "播放文件", self._browse_play_file, self._play_file)
        self.play_file_edit.editingFinished.connect(self._sync_play_file)
        z2.addLayout(play_row)

        # 播放控制行：按钮 + 状态胶囊
        play_ctrl = QtWidgets.QHBoxLayout()
        play_ctrl.setSpacing(6)
        self.play_btn = _Btn("\u25b6 播放", "accent")
        self.play_btn.clicked.connect(self._toggle_play)
        play_ctrl.addWidget(self.play_btn, stretch=1)
        self.play_status = self._make_pill("未播放", "fg_faint")
        play_ctrl.addWidget(self.play_status)
        z2.addLayout(play_ctrl)
        root.addWidget(zone2)

    # ------------------------------------------------------------------
    #  工具
    # ------------------------------------------------------------------

    @staticmethod
    def _make_pill(text, token):
        """状态胶囊标签（圆角浅底；token 为语义色名）"""
        return _Pill(text, token)

    @staticmethod
    def _make_small_btn(text, slot):
        b = QtWidgets.QPushButton(text)
        b.setCursor(QtCore.Qt.PointingHandCursor)
        T.styled(
            b,
            "QPushButton { background: transparent; color: @fg_dim; border: none;"
            " font-size: 11px; padding: 0 6px; min-height: 0px; }"
            "QPushButton:hover { color: @fg; }")
        b.setFixedHeight(18)
        b.setMinimumWidth(30)
        b.clicked.connect(slot)
        return b

    @staticmethod
    def _make_topic_box(text):
        cb = QtWidgets.QCheckBox(text)
        T.styled(
            cb,
            "QCheckBox { color: @fg_secondary; font-size: 12px; spacing: 6px;"
            " background: transparent; }"
            "QCheckBox:hover { color: @fg; }"
            "QCheckBox::indicator { width: 15px; height: 15px;"
            " border-radius: 4px; border: 1px solid @field_border;"
            " background-color: @input_bg; }"
            "QCheckBox::indicator:hover { border-color: @fg_faint; }"
            "QCheckBox::indicator:checked { background-color: @accent;"
            " border-color: @accent; }")
        return cb

    def _rebuild_topic_boxes(self, checked=None):
        """按当前配置重建 bag 录制候选话题复选框

        默认保留重建前的勾选状态（切换主配置时话题没变的话不会丢勾选）。
        """
        keep = set(checked) if checked is not None else set(self._checked_topics())
        while self._topics_lay.count():
            item = self._topics_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)      # 脱离布局后必须断开父子，否则仍会显示
                w.deleteLater()
        self._topic_boxes = []
        for t in CONFIG.bag_record_topics():
            cb = self._make_topic_box(t)
            cb.setChecked(t in keep)
            self._topics_lay.addWidget(cb)
            self._topic_boxes.append(cb)
        self._topics_lay.addStretch(1)
        # 高度贴合内容（话题多到超过上限才滚动），不浪费空间也不裁切
        self._topics_lay.invalidate()
        content_h = self._topics_lay.sizeHint().height()
        self._topics_scroll.setFixedHeight(max(min(content_h, 100), 24))
        self._set_topics_enabled(not self._recording)

    def apply_config(self):
        """主配置切换后刷新：脚本目录 + 脚本列表 + 录制候选话题立即生效"""
        cur = self.script_combo.currentText()
        names = self._scan_scripts()
        self.script_combo.clear()
        self.script_combo.addItems(names)
        if cur in names:
            self.script_combo.setCurrentText(cur)   # 尽量保持原来的选择
        self._rebuild_topic_boxes()

    @staticmethod
    def _scan_scripts():
        """从配置的 launch.scripts 读取脚本文件名列表，
        只保留真实存在于脚本目录的文件（yaml 里增删即自动同步）"""
        sh_dir = CONFIG.launch_script_dir()
        names = []
        for n in CONFIG.launch_scripts():
            if os.path.isfile(os.path.join(sh_dir, n)):
                names.append(n)
        return names or ["（未找到脚本）"]

    def save_dir(self):
        """当前 rosbag 保存目录"""
        return self._save_dir

    def _sync_save_dir(self):
        d = self.save_dir_edit.text().strip()
        if d:
            self._save_dir = os.path.expanduser(d)

    def _browse_dir(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, "选择 rosbag 保存目录", self._save_dir)
        if d:
            self._save_dir = d
            self.save_dir_edit.setText(d)

    def _sync_play_file(self):
        f = self.play_file_edit.text().strip()
        if f:
            self._play_file = os.path.expanduser(f)

    def _browse_play_file(self):
        f, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择要播放的 bag 文件", "", "Rosbag 文件 (*.bag)")
        if f:
            self._play_file = f
            self.play_file_edit.setText(f)

    @staticmethod
    def _make_path_row(label_text, on_browse, default_text=""):
        """构建「标签 + 路径输入框 + 浏览」行；返回 (layout, edit)"""
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(6)
        lbl = QtWidgets.QLabel(label_text)
        T.styled(lbl, "color: @fg_dim; font-size: 11px;")
        row.addWidget(lbl)
        edit = QtWidgets.QLineEdit(default_text)
        T.styled(
            edit,
            "QLineEdit { background-color: @input_bg; color: @fg;"
            " border: 1px solid @input_border;"
            " border-radius: 6px; padding: 1px 8px; font-size: 11px; }"
            "QLineEdit:hover { border-color: @accent; }"
            "QLineEdit:focus { border-color: @accent; }")
        edit.setFixedHeight(22)
        row.addWidget(edit, stretch=1)
        browse = QtWidgets.QPushButton("浏览")
        browse.setCursor(QtCore.Qt.PointingHandCursor)
        T.styled(
            browse,
            "QPushButton { background-color: @input_bg; color: @fg;"
            " border: 1px solid @input_border;"
            " border-radius: 6px; font-size: 11px; padding: 0 8px;"
            " min-height: 0px; }"
            "QPushButton:hover { background-color: @accent_soft; border-color: @accent; }"
            "QPushButton:pressed { background-color: @press; }")
        browse.setFixedHeight(22)
        browse.setMinimumWidth(44)
        browse.clicked.connect(on_browse)
        row.addWidget(browse)
        return row, edit

    def _checked_topics(self):
        return [cb.text() for cb in self._topic_boxes if cb.isChecked()]

    def _set_topics_enabled(self, on):
        for cb in self._topic_boxes:
            cb.setEnabled(on)
        self._sel_all_btn.setEnabled(on)
        self._sel_none_btn.setEnabled(on)

    def _select_all(self):
        for cb in self._topic_boxes:
            cb.setChecked(True)

    def _select_none(self):
        for cb in self._topic_boxes:
            cb.setChecked(False)

    @staticmethod
    def _set_pill(lbl, text, token):
        """更新状态胶囊（未录制灰 / 录制中绿 / 播放中绿；token 为语义色名）"""
        lbl.set_state(text, token)

    def _set_status(self, text, token):
        """更新录制状态胶囊"""
        self._set_pill(self.bag_status, text, token)

    # ------------------------------------------------------------------
    #  动作（sh 运行 / RViz / 一键终止 / 录制 / 播放均已实现）
    # ------------------------------------------------------------------

    def _run_script(self):
        """在 gnome-terminal 新标签中运行所选 sh 脚本（不阻塞 UI）

        运行方式与 sh/test_highway.sh 自身一致：
            gnome-terminal --tab -- bash -c "<cd 脚本目录 && bash 脚本; exec bash>"
        """
        name = self.script_combo.currentText()
        if not name or name == "（未找到脚本）":
            print("[launch] 没有可运行的脚本")
            return
        sh_dir = CONFIG.launch_script_dir()
        path = os.path.join(sh_dir, name)
        if not os.path.isfile(path):
            print("[launch] 脚本不存在: %s" % path)
            return
        if shutil.which("gnome-terminal") is None:
            print("[launch] 未找到 gnome-terminal，无法弹出终端")
            return
        # cd 到脚本目录，保证脚本内的相对路径/源码环境生效；
        # 结束后 exec bash 保持终端窗口不关闭，便于查看节点输出
        cmd = 'cd "%s" && bash "%s"; exec bash' % (sh_dir, name)
        try:
            subprocess.Popen(["gnome-terminal", "--tab", "--", "bash", "-c", cmd])
            print("[launch] 已在终端中启动: %s" % name)
        except Exception as e:
            print("[launch] 启动终端失败: %s" % e)

    def _open_rviz(self):
        """在 gnome-terminal 新标签中打开 RViz（先 source ROS 环境）"""
        if shutil.which("gnome-terminal") is None:
            print("[launch] 未找到 gnome-terminal，无法弹出终端")
            return
        cmd = "source /opt/ros/noetic/setup.bash; rviz; exec bash"
        try:
            subprocess.Popen(["gnome-terminal", "--tab", "--", "bash", "-c", cmd])
            print("[launch] 已启动 RViz")
        except Exception as e:
            print("[launch] 启动 RViz 失败: %s" % e)

    def _kill_all(self):
        """一键终止所有脚本启动的进程（按 KILL_PATTERNS 关键词 pkill -f）

        危险操作：执行前弹出确认框；按关键词逐个 pkill，
        只统计实际命中的进程类别数。
        """
        if QtWidgets.QMessageBox.question(
                self, "终止全部",
                "将终止所有 ROS 节点 / 脚本启动的进程，\n确认继续？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Cancel) != QtWidgets.QMessageBox.Yes:
            return
        killed = 0
        for pat in KILL_PATTERNS:
            try:
                r = subprocess.run(["pkill", "-f", pat],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                if r.returncode == 0:
                    killed += 1
            except Exception as e:
                print("[launch] 终止 %s 失败: %s" % (pat, e))
        print("[launch] 已终止 %d 类进程" % killed)

    def _toggle_record(self):
        if not self._recording:
            self._start_record()
        else:
            self._stop_record()

    @staticmethod
    def _terminate_proc(name, proc):
        """优雅终止子进程：SIGINT 让 rosbag 正常收尾，超时再 SIGTERM"""
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.terminate()
            print("[launch] %s进程已停止" % name)
        except Exception as e:
            print("[launch] 停止%s进程失败: %s" % (name, e))

    def _start_record(self):
        """开始录制：rosbag record -O <保存目录>/myos_时间戳.bag <勾选话题>"""
        topics = self._checked_topics()
        if not topics:
            print("[launch] 请先勾选要录制的话题")
            return
        if not os.path.isdir(self._save_dir):
            try:
                os.makedirs(self._save_dir, exist_ok=True)
            except OSError as e:
                print("[launch] 无法创建保存目录 %s: %s" % (self._save_dir, e))
                return
        bag_bin = _find_binary("rosbag")
        if bag_bin is None:
            print("[launch] 未找到 rosbag 命令（需先 source /opt/ros/noetic/setup.bash）")
            return
        bag_path = os.path.join(self._save_dir,
                                "myos_%s.bag" % time.strftime("%Y%m%d_%H%M%S"))
        try:
            proc = subprocess.Popen([bag_bin, "record", "-O", bag_path] + topics,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        except Exception as e:
            print("[launch] 启动录制失败: %s" % e)
            return
        self._record_proc = proc
        self._recording = True
        self.record_btn.setText("\u25a0 停止录制")
        self.record_btn.set_accent("danger")
        self._set_status("\u25cf 录制中", "accent")
        self._set_topics_enabled(False)
        print("[launch] 录制中 → %s\n      话题: %s" % (bag_path, topics))

    def _stop_record(self):
        self._recording = False
        self.record_btn.setText("\u25cf 开始录制")
        self.record_btn.set_accent("accent")
        self._set_status("未录制", "fg_faint")
        self._set_topics_enabled(True)
        self._terminate_proc("录制", self._record_proc)
        self._record_proc = None

    def _toggle_play(self):
        if not self._playing:
            self._start_play()
        else:
            self._stop_play()

    def _start_play(self):
        """播放 bag 文件：rosbag play <文件>"""
        f = self._play_file
        if not f or not os.path.isfile(f):
            print("[launch] 播放文件不存在: %s" % f)
            return
        bag_bin = _find_binary("rosbag")
        if bag_bin is None:
            print("[launch] 未找到 rosbag 命令（需先 source /opt/ros/noetic/setup.bash）")
            return
        try:
            proc = subprocess.Popen([bag_bin, "play", f],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        except Exception as e:
            print("[launch] 启动播放失败: %s" % e)
            return
        self._play_proc = proc
        self._playing = True
        self.play_btn.setText("\u25a0 停止播放")
        self.play_btn.set_accent("danger")
        self._set_pill(self.play_status, "\u25cf 播放中", "accent")
        print("[launch] 播放中: %s" % f)

    def _stop_play(self):
        self._playing = False
        self.play_btn.setText("\u25b6 播放")
        self.play_btn.set_accent("accent")
        self._set_pill(self.play_status, "未播放", "fg_faint")
        self._terminate_proc("播放", self._play_proc)
        self._play_proc = None

    # ------------------------------------------------------------------
    #  外观
    # ------------------------------------------------------------------

    def paintEvent(self, e):
        """绘制卡片圆角底 + 描边（与实时数据/参数面板风格一致）"""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtGui.QPen(T.qcolor("card_border"), 1))
        p.setBrush(T.qcolor("card_bg"))
        p.drawRoundedRect(QtCore.QRectF(0.5, 0.5,
                                        self.width() - 1, self.height() - 1), 12, 12)
        p.end()
