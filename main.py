# main.py — MyOS 程序入口文件
# 双击运行这个文件即可启动整个软件

import os
import sys
from PySide6 import QtWidgets

# 获取当前文件所在目录的绝对路径（即 MyOS 项目根目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 主题样式目录和 UI 模块目录
STYLE_DIR = os.path.join(BASE_DIR, "style")
UI_DIR = os.path.join(BASE_DIR, "ui")

# 把 ui 目录加入 Python 搜索路径，这样 main() 里才能 from main_window import MainWindow
sys.path.insert(0, UI_DIR)


def _load_theme(app):
    """加载 QSS 主题样式文件并应用到整个应用程序"""
    theme_path = os.path.join(STYLE_DIR, "theme.qss")
    if os.path.exists(theme_path):
        with open(theme_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())  # 全局应用样式表
    else:
        print(f"[MyOS] 警告: 未找到主题文件 {theme_path}")


def main():
    # ===== 第一步：创建 Qt 应用程序 =====
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("MyOS")
    app.setApplicationVersion("1.0")

    # ===== 第二步：加载 QSS 主题，给所有控件穿上"赛车仪表盘"皮肤 =====
    _load_theme(app)

    # ===== 第三步：创建并显示主窗口 =====
    # splash 画面已嵌入到主窗口内部，不需要额外的 QSplashScreen
    from main_window import MainWindow

    window = MainWindow()
    window.show()

    # ===== 第四步：进入 Qt 事件循环，程序开始运行 =====
    # 主窗口打开后先显示 splash 页，1.5 秒后自动切换到仪表盘
    sys.exit(app.exec())


# Python 标准入口：只有直接运行 main.py 时才执行 main()，被 import 时不执行
if __name__ == "__main__":
    main()
