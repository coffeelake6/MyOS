# theme.py — MyOS 主题（浅色 / 深色）统一入口
#
# 两套主题的配色只写在这一个文件里，UI 各处一律引用语义化 token，
# 不再出现十六进制色值，切换主题时所有界面自动跟着换。
#
# 用法：
#   from theme import T
#   T.color("fg")           → 当前主题的 "#rrggbb" 字符串（拼 QSS 用）
#   T.qcolor("card_bg")     → QtGui.QColor（自绘控件在 paintEvent 里实时取色）
#   T.rgba("accent", 0.13)  → QSS 的 rgba() 写法（透明底/描边必须用它）
#   T.qss(INPUT_QSS)        → 把模板里的 @token 翻译成真实色值
#   T.styled(w, "color: @fg_dim;")   → 给控件套样式，并登记到换肤表
#                                      （切主题时自动重新套用）
#
# 自绘控件只要在 paintEvent 里用 T.qcolor(...) 取色，切换后重绘即可变色；
# 走 setStyleSheet 的控件必须用 T.styled(...)，否则切主题后仍是旧色。
#
# 主题名持久化在 config/config.yaml 的 ui.theme，用 T.set("dark") 切换，
# 会立即写回配置文件，下次启动仍是这个主题。

import os
import re
import weakref

from PySide6 import QtGui

STYLE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "style")

DEFAULT_THEME = "light"
THEME_NAMES = ("light", "dark")
THEME_LABELS = {"light": "浅色", "dark": "深色"}

# 学校 LOGO 也分浅色 / 深色两套：浅色主题用深色字标，深色主题用浅色字标
# （SZPU_.png 是给深底用的浅色版，PNG 自带透明背景）
SCHOOL_LOGOS = {
    "light": os.path.join(STYLE_DIR, "icon", "SZPU.png"),
    "dark":  os.path.join(STYLE_DIR, "icon", "SZPU_.png"),
}

# ---------------------------------------------------------------------------
#  配色表：token → (浅色, 深色)
#  浅色 = 灰底黑字；深色 = 原来的黑底白字（与改造前的深色主题一致）
# ---------------------------------------------------------------------------
_TOKENS = {
    # 基底 / 表面
    "bg":            ("#f0f0f2", "#0c0d12"),   # 窗口底
    "surface":       ("#ffffff", "#16171f"),   # 面板 / 卡片表面
    "card_bg":       ("#ffffff", "#12141a"),   # 自绘卡片填充
    "zone_bg":       ("#f6f6f8", "#15171e"),   # 快捷启动分区底
    "input_bg":      ("#ffffff", "#1b1f29"),   # 输入框 / 下拉框底
    "popup_bg":      ("#ffffff", "#1c1e26"),   # 下拉列表浮层底
    "chip_bg":       ("#e6e6ea", "#0a0b10"),   # 小徽标底

    # 文字
    "fg":            ("#000000", "#e5e5ea"),   # 主文字
    "fg_secondary":  ("#000000", "#c7c7cc"),   # 次级文字
    "fg_dim":        ("#5f5f66", "#8e8e93"),   # 说明文字
    "fg_faint":      ("#8a8a90", "#6c6c70"),   # 更弱的说明 / 版本号
    "fg_disabled":   ("#b0b0b8", "#3a3e49"),   # 禁用态文字
    "on_accent":     ("#04241d", "#0c0d12"),   # 强调色上的文字
    "on_muted":      ("#8a8a90", "#5b6a75"),   # 灰底按钮上的文字

    # 强调色
    "accent":        ("#00a884", "#00d4aa"),   # 荧光绿（浅底压深一档）
    "accent_hi":     ("#00a884", "#5ee8c8"),   # 深色下选中的高亮绿
    "accent_light":  ("#00c194", "#2ee0bd"),   # 强调色 hover 提亮
    "accent_soft":   ("#eef7f5", "#242938"),   # 强调色淡底（hover）
    "active_soft":   ("#dff2ec", "#182a26"),   # 选中淡绿底
    "active_soft2":  ("#dff2ec", "#2b3140"),   # 选中淡底（图像页）

    # 交互态
    "hover":         ("#f2f2f5", "#1b1f29"),   # 悬停底
    "hover_accent":  ("#eef7f5", "#232837"),   # 悬停底（带绿调）
    "press":         ("#e6e6ea", "#14161d"),   # 按压底
    "press_alt":     ("#e0e0e6", "#1a1d26"),   # 按压底（图像页）

    # 边框 / 分隔
    "card_border":   ("#dcdce2", "#1f232d"),   # 卡片描边
    "divider":       ("#e4e4e9", "#1f232d"),   # 分隔线
    "input_border":  ("#d0d0d6", "#262a35"),   # 输入框描边
    "field_border":  ("#c0c0c8", "#363c4d"),   # 勾选框描边
    "track":         ("#d0d0d6", "#2a2d38"),   # 开关轨道（关）
    "muted_line":    ("#c9c9d0", "#2a2b36"),   # 装饰性灰线 / 滚动条
    "muted_fill":    ("#c9c9d0", "#22303c"),   # 禁用态灰底

    # 警示 / 提醒
    "danger":        ("#e5484d", "#ff453a"),
    "warn":          ("#e8590c", "#ff6b35"),
    "warn_text":     ("#d2571f", "#ff6b35"),
    "notify_bg":     ("#fff4ea", "#2a1d14"),   # 外部修改提醒条底
    "notify_hover":  ("#ffe9d8", "#35251a"),
    "notify_press":  ("#fbe0cc", "#1f150e"),
    "notify_border": ("#f0c9a8", "#4a2e1c"),
    "notify_fg":     ("#8a4b18", "#ffb28a"),
}

_TOKEN_RE = re.compile(r"@([a-z_]+)")


def _config_theme():
    """从 config.yaml 读取主题名（读不到 / 写错 → 用默认浅色）"""
    try:
        from myos_config import CONFIG
        name = CONFIG.ui_theme()
    except Exception:
        return DEFAULT_THEME
    return name if name in THEME_NAMES else DEFAULT_THEME


class _Theme:
    """主题管理器（全局唯一实例 T）"""

    def __init__(self):
        self._name = None          # None = 还没解析，按需从 config 读
        self._styled = []          # [(weakref(widget), 模板)]
        self._callbacks = []       # 主题切换后的额外回调

    # ------------------------------------------------------------------
    #  当前主题
    # ------------------------------------------------------------------
    @property
    def name(self):
        if self._name is None:
            self._name = _config_theme()
        return self._name

    def is_dark(self):
        return self.name == "dark"

    def school_logo(self):
        """当前主题对应的学校 LOGO 图片路径"""
        return SCHOOL_LOGOS[self.name]

    # ------------------------------------------------------------------
    #  取色
    # ------------------------------------------------------------------
    def color(self, token):
        """token 在当前主题下的 #rrggbb 颜色字符串"""
        pair = _TOKENS.get(token)
        if pair is None:
            return "#ff00ff"        # 未登记的 token → 洋红，便于一眼看出来
        return pair[1] if self.is_dark() else pair[0]

    def qcolor(self, token, alpha=255):
        """token 在当前主题下的 QColor（可指定 alpha）"""
        c = QtGui.QColor(self.color(token))
        if alpha != 255:
            c.setAlpha(alpha)
        return c

    def rgba(self, token, alpha):
        """token 在当前主题下的 QSS rgba() 写法（适合透明底 / 描边）"""
        return self.rgba_of(self.color(token), alpha)

    @staticmethod
    def rgba_of(color, alpha):
        """把任意 #rrggbb + 透明度转成 QSS 的 rgba() 写法

        想让胶囊底、描边按钮的 hover 底色真正生效必须用 rgba()，
        直接给十六进制色值是看不出叠加效果的。
        """
        c = QtGui.QColor(color)
        return "rgba(%d, %d, %d, %.2f)" % (c.red(), c.green(), c.blue(), alpha)

    # ------------------------------------------------------------------
    #  QSS 模板翻译 / 套用
    # ------------------------------------------------------------------
    def qss(self, template):
        """把模板里的 @token 换成当前主题色值，返回可直接用的 QSS 字符串"""
        return _TOKEN_RE.sub(lambda m: self.color(m.group(1)), template)

    def styled(self, widget, template):
        """给控件套一段带 @token 的 QSS，并登记换肤

        控件存活期间有效（弱引用登记，控件销毁后自动移出）。
        """
        widget._myos_qss_template = template
        widget.setStyleSheet(self.qss(template))
        self._styled.append((weakref.ref(widget), template))
        return widget

    def on_change(self, callback):
        """登记主题切换回调（控件按新配色重算 / 重套样式时用）

        绑定方法（如 self._apply_qss）按弱引用登记：控件销毁后回调自动失效，
        不会积压僵尸回调；普通函数按强引用登记。
        """
        if getattr(callback, "__self__", None) is not None:
            self._callbacks.append(weakref.WeakMethod(callback))
        else:
            self._callbacks.append(callback)

    # ------------------------------------------------------------------
    #  切换 / 应用
    # ------------------------------------------------------------------
    def set(self, name, persist=True):
        """切换主题：立即刷新界面，并把选择写回 config/config.yaml"""
        if name not in THEME_NAMES or name == self.name:
            return False
        self._name = name
        if persist:
            self.save(name)
        self.apply()
        return True

    @staticmethod
    def save(name):
        """把主题名写回 config/config.yaml（行级改写，保留其余注释与内容）"""
        try:
            from myos_config import save_ui_theme
            save_ui_theme(name)
        except Exception as e:
            print("[theme] 主题写回 config.yaml 失败: %s" % e)

    def stylesheet(self):
        """当前主题的 QSS 文件内容（找不到就退回空串）"""
        path = os.path.join(STYLE_DIR, "theme_%s.qss" % self.name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print("[theme] 读取主题文件 %s 失败: %s" % (path, e))
            return ""

    def apply(self, app=None):
        """把当前主题应用到界面：换全局 QSS + 重新套用登记过的内联样式 + 重绘"""
        from PySide6 import QtWidgets

        if app is None:
            app = QtWidgets.QApplication.instance()
        if app is None:
            return

        app.setStyleSheet(self.stylesheet())

        # 内联样式表是字符串快照，换主题后必须按模板重新套一遍
        alive = []
        for ref, template in self._styled:
            w = ref()
            if w is None:
                continue
            alive.append((ref, template))
            w.setStyleSheet(self.qss(template))
        self._styled = alive

        alive = []
        for item in self._callbacks:
            cb = item() if isinstance(item, weakref.ref) else item
            if cb is None:
                continue
            alive.append(item)
            try:
                cb()
            except Exception as e:
                print("[theme] 换肤回调失败: %s" % e)
        self._callbacks = alive

        # 自绘控件在 paintEvent 里实时取色，重绘即可。
        # 这里显式走 QWidget.update：QAbstractItemView 的 update(QModelIndex)
        # 会把基类无参 update() 隐藏掉，直接 w.update() 会报参数数量错误。
        for w in app.allWidgets():
            QtWidgets.QWidget.update(w)


# 全局唯一实例：UI 各处统一 `from theme import T`
T = _Theme()
