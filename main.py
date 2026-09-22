# main.py — MyOS 程序入口文件
# 双击运行这个文件即可启动整个软件

import os
import sys
from PySide6 import QtWidgets

# 获取当前文件所在目录的绝对路径（即 MyOS 项目根目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# UI 模块目录
UI_DIR = os.path.join(BASE_DIR, "ui")

# 把 ui 目录加入 Python 搜索路径，这样 main() 里才能 from main_window import MainWindow
sys.path.insert(0, UI_DIR)


def main():
    # ===== 第一步：创建 Qt 应用程序 =====
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("MyOS")
    app.setApplicationVersion("1.0")
    # 关联到 /usr/share/applications/myos.desktop：
    # 桌面环境靠这个（配合 .desktop 里的 StartupWMClass）把窗口认成 MyOS 应用，
    # 否则图标无法正确显示运行状态，点图标也可能重新拉起一个实例。
    app.setDesktopFileName("myos")

    # ===== 第二步：加载主题（浅色 / 深色，取自 config.yaml 的 ui.theme）=====
    # 两套主题的配色在 ui/theme.py 统一管理，QSS 文件按主题名加载
    from theme import T

    T.apply(app)

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
