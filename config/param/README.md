# Param - 感知系统参数配置模块

## 概述

本模块用于集中管理感知系统中所有节点的参数配置。通过 ROS 参数服务器，可以在启动时统一加载参数，便于参数的维护和修改。

## 目录结构

```
param/
├── config/                    # 参数配置文件
│   ├── lidar_cluster.yaml    # 激光雷达聚类参数
│   ├── yolo.yaml             # YOLO检测参数
│   ├── pointpillars.yaml     # Pointpillars参数
│   ├── reprojection.yaml     # 重投影参数
│   └── topics.yaml           # 公共话题名称配置
├── launch/                    # 启动文件
│   ├── perception.launch     # 主启动文件
│   └── load_params.launch    # 仅加载参数的启动文件
├── CMakeLists.txt
├── package.xml
└── README.md
```

## 使用方法

### 1. 仅加载参数（推荐用于调试）

当需要单独启动节点进行调试时，可以仅加载参数：

```bash
# 加载参数到参数服务器
roslaunch param load_params.launch

# 然后手动启动需要的节点
rosrun aft_lidar_cluster five_color_highway
rosrun YOLO11 detect.py
```

### 2. 加载参数并启动所有节点

```bash
roslaunch param perception.launch load_params:=true start_nodes:=true
```

### 3. 选择性启动模块

```bash
# 仅启动激光雷达聚类和YOLO
roslaunch param perception.launch start_nodes:=true \
    enable_lidar_cluster:=true \
    enable_yolo:=true \
    enable_pointpillars:=false \
    enable_reprojection:=false
```

### 4. 选择不同场景

```bash
# 高速场景
roslaunch param perception.launch start_nodes:=true scene_type:=highway

# 八字环场景
roslaunch param perception.launch start_nodes:=true scene_type:=skidpad

# 耐久赛场景
roslaunch param perception.launch start_nodes:=true scene_type:=trackdrive
```

## 参数命名空间

所有参数都按照模块划分命名空间，便于管理：

| 命名空间 | 配置文件 | 说明 |
|---------|---------|------|
| `/topics` | topics.yaml | 公共话题名称 |
| `/lidar_cluster` | lidar_cluster.yaml | 激光雷达聚类参数 |
| `/yolo` | yolo.yaml | YOLO检测参数 |
| `/pointpillars` | pointpillars.yaml | Pointpillars参数 |
| `/reprojection` | reprojection.yaml | 重投影参数 |

## 获取参数

节点中可以通过以下方式获取参数：

### C++ 节点

```cpp
// 从对应命名空间获取参数
ros::NodeHandle nh("~");
ros::NodeHandle param_nh("/lidar_cluster");

double distance_threshold;
param_nh.param("distance_to_car_threshold", distance_threshold, 3.0);
```

### Python 节点

```python
import rospy

# 从命名空间获取参数
distance_threshold = rospy.get_param("/lidar_cluster/distance_to_car_threshold", 3.0)
```

## 修改参数

1. 直接编辑对应的 YAML 配置文件
2. 运行时使用 `rosparam set` 命令修改：
   ```bash
   rosparam set /lidar_cluster/distance_to_car_threshold 5.0
   ```

## 查看当前参数

```bash
# 查看所有参数
rosparam list

# 查看特定命名空间的参数
rosparam get /lidar_cluster

# 导出当前参数
rosparam dump params_backup.yaml
```

## 注意事项

1. 修改参数后需要重启节点才能生效（除非节点支持动态参数更新）
2. 建议在修改参数前备份原配置文件
3. 路径参数支持使用 `$(find package_name)` 语法引用 ROS 包路径