# main_config_bar.py — 主配置条
#
# 整个程序的配置来源（主配置 yaml）单独成条，横跨在功能模块之上：
# 显示当前生效的主配置路径 + 「浏览」按钮选择一个 yaml。
# 相机话题 / 快捷启动脚本 / bag 录制话题 / 实时数据项 / 各模块参数目录
# 都来自这份主配置。
#
# 本组件只负责「显示路径 + 让用户发起选择」，实际的读取、写回与全局重载
# 由参数修改面板负责（切换前要先征询未保存的修改是否丢弃），
# 两者通过 browse_requested / set_path 对接。

from PySide6 import QtCore, QtWidgets, QtGui

from theme import T


class MainConfigBar(QtWidgets.QWidget):
    """主配置条：路径显示 + 浏览按钮（横跨页面上方）"""

    # 用户点了「浏览」：由外部（参数修改面板）弹文件对话框并应用
    browse_requested = QtCore.Signal()
    # 主配置路径变化（应用成功后由面板回填）
    path_changed = QtCore.Signal(str)

    def __init__(self, path="", parent=None):
        super().__init__(parent)
        self.setObjectName("main-config-bar")
        self._path = None

        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(16, 10, 16, 10)
        row.setSpacing(8)

        label = QtWidgets.QLabel("主配置")
        T.styled(label, "color: @fg_dim; font-size: 11px;")
        row.addWidget(label)

        self._edit = QtWidgets.QLineEdit()
        self._edit.setReadOnly(True)
        self._edit.setPlaceholderText("未指定（用本项目 config/config.yaml）")
        T.styled(
            self._edit,
            "QLineEdit { background: @input_bg; color: @fg_dim; border: 1px solid"
            " @input_border; border-radius: 6px; padding: 2px 6px; font-size: 11px; }"
            "QLineEdit:focus { border-color: @accent; }")
        row.addWidget(self._edit, stretch=1)

        self._browse_btn = QtWidgets.QPushButton("浏览")
        self._browse_btn.setFixedHeight(24)
        self._browse_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._browse_btn.setToolTip(
            "选择一个 config.yaml 作为整个程序的配置来源：\n"
            "相机话题 / 快捷启动脚本 / bag 录制话题 / 实时数据项 / 各模块参数目录。\n"
            "未写到的段沿用本项目 config；路径会记住（下次启动仍生效）。")
        T.styled(
            self._browse_btn,
            # min-height: 0 才能让 setFixedHeight(24) 生效（与左侧输入框同高）
            "QPushButton { background: @input_bg; color: @fg; border: 1px solid"
            " @input_border; border-radius: 6px; padding: 2px 10px; font-size: 11px;"
            " min-height: 0px; }"
            "QPushButton:hover { background: @hover; }"
            "QPushButton:pressed { background: @press; }"
            "QPushButton:disabled { color: @fg_disabled; }")
        self._browse_btn.clicked.connect(self.browse_requested)
        row.addWidget(self._browse_btn)

        self.set_path(path)

    # ----- 对外接口 -----

    def path(self):
        return self._path or ""

    def set_path(self, path):
        """更新显示的路径（不改配置，只刷新界面）"""
        path = path or ""
        if path == self._path:
            return
        self._path = path
        self._edit.setText(path)
        self._edit.setToolTip(path or "未指定（用本项目 config/config.yaml）")
        self.path_changed.emit(path)

    # ----- 外观 -----

    def paintEvent(self, e):
        """绘制圆角底 + 描边（与其余卡片一致）"""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtGui.QPen(T.qcolor("card_border"), 1))
        p.setBrush(T.qcolor("card_bg"))
        p.drawRoundedRect(QtCore.QRectF(0.5, 0.5,
                                        self.width() - 1, self.height() - 1), 12, 12)
        p.end()
