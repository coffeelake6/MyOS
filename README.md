# MyOS — 基于 PySide6 的无人系统操作面板

> 无人系统基于 ROS 开发，调试阶段需要频繁改参数、启动特定脚本、盯关键数据。
> 传统方式要在终端里手动敲多条指令、改参数还得反复开文件重新编译，效率很低。
> MyOS 把这些动作收进一个桌面面板，通过 ROS 作为中间件与车上程序交互：
> 看画面、跑脚本、录包、改参数、盯数据，都在一个窗口里完成。

面向 **Ubuntu 20.04 + ROS Noetic**。

---

## 功能模块

主界面从上到下分三段：顶部标题栏（LOGO / 主题切换 / 校徽）、中间功能面板区、底部状态栏（版本号）。
功能面板区上方横跨一条 **主配置条**，下面是三列：

### 1. 图像显示

- 左右两路相机画面同屏显示，各自带话题选择器，运行中随时切换订阅话题。
- 候选话题来自配置文件的 `camera.candidate_topics`，增删即自动同步。
- 超过 3 秒没有新帧自动回到「无信号」占位，避免留着过期画面误导判断。
- 无 ROS 环境时静默跳过订阅，界面照常可用。

### 2. 快捷启动

- **一键运行脚本**：下拉框列出配置好的 `.sh`，选中即执行。
- **一键打开 RViz**。
- **一键终止**：按关键词批量结束脚本拉起的进程（`roslaunch` / `rosrun` / `roscore` / `rviz` 及各节点可执行文件，关键词可在 `launch_panel.py` 的 `KILL_PATTERNS` 增删）。
- **rosbag 录制**：勾选要录的话题（候选来自 `bag.record_topics`），可指定保存目录。
- **bag 播放**：选一个 bag 文件直接 `rosbag play`。

### 3. 实时数据

- 竖向键值列表，监控关键话题的数值。
- 数据项完全由配置定义（`data_items`）：显示名、话题、单位、小数位。
- 值刷新时强调色短暂闪烁，反馈及时又不打扰。

### 4. 参数修改

- 按「模块 → 参数组 → 参数」三级结构展示和修改 yaml 参数。
- 模块：**感知、建图、规划、控制、驱动**。前三者按目录扫描：目录下每个 `*.yaml` 自动生成一张参数卡片，增删文件 UI 自动适配；控制 / 驱动暂为空态，待接入。
- **行级写回**：只改值所在位置，文件里的注释、键序、排版原样保留。
- 外部改动监控：文件被别的程序改了会感知到，写回前重新校验行号，避免写错位置。
- 每个模块独立的 yaml 目录，在 `param_dirs` 里配置。

### 5. 主配置条（页顶）

整个程序的配置来源可以换成另一份 yaml：

- 点「浏览」选一个 `config.yaml`，其中的 `camera` / `launch` / `bag` / `data_items` / `param_dirs` 段立刻作为全局配置生效，各面板即时刷新；**没写到的段沿用本项目 `config/config.yaml`**。
- 相对路径按主配置所在目录解析。
- 选择结果会写回本项目的 `param_panel.main_config`，下次启动仍然生效。
- 留空 = 全部使用本项目 `config/config.yaml`。
- 界面主题（`ui.theme`）与主配置路径本身是「引导项」，始终固定从本项目 `config/config.yaml` 读取。
- 切换主配置前会提示先保存 / 丢弃当前未保存的修改。

### 6. 界面主题

- 标题栏胶囊一键切换 **浅色 / 深色**，写回 `ui.theme`，下次启动仍是该主题。
- 两套配色集中定义在 `ui/theme.py`，界面各处一律引用语义化 token。

---

## 快速上手

### 方式一：源码运行（开发 / 调试）

需要系统先装好 ROS Noetic 与 PySide6。

```bash
# 1. ROS 相关依赖（通过 apt，不从 pip 装）
sudo apt install ros-noetic-ros-comm ros-noetic-cv-bridge \
                 ros-noetic-rosbag ros-noetic-rviz

# 2. Python 依赖（PySide6 / PyYAML）
pip3 install -r requirements.txt

# 3. 启动：先 source ROS 环境，再运行入口
source /opt/ros/noetic/setup.bash
python3 main.py
```

启动后会先播放约 2.2 秒的开机画面，然后自动进入主界面。
ROS master 没起来也能开界面，只是画面和数据会显示占位内容。

### 方式二：安装 deb 包（部署到车）

```bash
# 打包（版本号可选，默认见脚本内 VERSION）
bash packaging/build_deb.sh 1.2.1

# 安装
sudo dpkg -i packaging/build/myos_1.2.1_amd64.deb
sudo apt -f install        # 补齐缺失依赖

# 启动：应用菜单搜 "MyOS"，或终端直接
myos
```

若安装时提示缺少 PySide6（deb 不打包它），执行：

```bash
sudo pip3 install PySide6==6.2.4
```

用自带的 Python 环境（如 conda）启动：

```bash
MYOS_PYTHON=/home/xxx/miniconda3/envs/pcdet/bin/python myos
```

---

## 配置说明

**所有可调数据集中在 [`config/config.yaml`](config/config.yaml)**，改完重启程序生效：

| 配置段 | 作用 |
| --- | --- |
| `camera` | 两路相机的初始话题、下拉框候选话题 |
| `launch` | 脚本目录 `script_dir`、下拉框列出的脚本文件名 |
| `bag` | 录制面板可勾选的话题 |
| `data_items` | 实时数据面板的键、话题、单位、小数位 |
| `param_dirs` | 感知 / 建图 / 规划各模块的 yaml 目录 |
| `param_panel.main_config` | 主配置 yaml 路径（留空 = 用本项目配置，一般由界面写入） |
| `ui.theme` | 界面主题 `light` / `dark`（也可在界面顶部切换） |

写法宽容：漏写的键自动用代码内置默认值兜底，写错类型也不会崩。
话题名以 `/` 开头；脚本文件名需真实存在于 `script_dir` 目录。

> **部署提示**：deb 会把配置装到 `/opt/myos/config/`，且**没有注册 conffiles**，
> 因此 `sudo dpkg -i` 重装会覆盖这份配置（主配置选择与主题会丢一次），
> 重装前建议先备份。

---

## 目录结构

```
MyOS/
├── main.py                    # 程序入口（含唯一版本号常量 APP_VERSION）
├── myos_config.py             # 配置加载 / 合并 / 写回（唯一的配置来源实现）
├── requirements.txt           # Python 依赖
├── config/
│   ├── config.yaml            # 集中配置文件（所有可调数据）
│   ├── perception/            # 感知模块 yaml
│   ├── planning/              # 规划模块 yaml
│   └── slam/                  # 建图模块 yaml
├── ui/
│   ├── main_window.py         # 主窗口骨架，拼接全部面板
│   ├── SplashPage.py          # 开机画面
│   ├── base.py                # 顶部标题栏 / 底部状态栏 / 主题切换胶囊
│   ├── main_config_bar.py     # 页顶主配置条
│   ├── showImg.py             # 图像显示面板
│   ├── launch_panel.py        # 快捷启动面板
│   ├── showData.py            # 实时数据面板
│   ├── param_modification.py  # 参数修改面板
│   ├── param_widgets.py       # 参数面板的通用控件
│   └── theme.py               # 浅色 / 深色配色统一入口
├── ros_bridge/
│   ├── getImg.py              # ROS 图像订阅桥（sensor_msgs/Image → QImage）
│   └── getData.py             # ROS 数据订阅桥（std_msgs/Float32 → 数值）
├── param_store/
│   └── store.py               # 参数文件数据层（行级写回 + 外部修改监控）
├── sh/                        # 示例启动脚本
├── style/                     # QSS 主题文件与图标
└── packaging/                 # deb 打包脚本与产物
```

---

## 打包

```bash
bash packaging/build_deb.sh <版本号>     # 产物：packaging/build/myos_<版本号>_amd64.deb
bash packaging/build_deb.sh             # 不传版本号则用脚本内默认值
```

打包脚本负责：组装 `/opt/myos` 目录树、生成桌面入口与图标、写入 `DEBIAN/control`
（版本号、依赖、安装体积）、放开 `config/` 写权限，最后用 `dpkg-deb --build` 出包。

注意版本号有两处：打包脚本的 `VERSION`（写进 deb 的 `control`）与
[`main.py`](main.py) 的 `APP_VERSION`（界面底部状态栏与开机画面显示），发版时请保持一致。

---

## 常见问题

**装了 deb，界面里改的参数 / 选的主配置不生效？**
`/opt/myos` 默认属主是 root，普通用户写不进去。打包脚本已把 `config/` 放开为可写；
若你的包是旧版本，手动执行一次：

```bash
sudo chmod -R a+w /opt/myos/config
```

**界面能开，但画面和数据都是占位？**
ROS master 没起来或话题名不对。先 `roscore`，再核对 `config/config.yaml` 里的话题。

**改了 yaml 但界面没变？**
配置在启动时读取，改完请重启程序；界面内改参数则即时生效并写回文件。
