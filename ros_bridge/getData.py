#!/usr/bin/env python

# getData.py — MyOS 关键话题数据桥
#
# 作用：按 DATA_ITEMS 列表订阅一组 ROS 话题，把解析出的值（键值对）
#       通过 Qt 信号 data_updated(键, 格式化文本) 送到 UI 线程显示。
#
# 增删数据项：直接修改 DATA_ITEMS 列表即可（键由用户定义，值来自订阅话题解析）。
# 每个数据项可配置：
#   key       显示键（用户自定义，如 "YOLO推理时间"）
#   topic     ROS 话题名（按实际修改）
#   msg_type  消息类型，如 "std_msgs/Float64"（支持 "包名/类型名" 格式）
#   field     取值字段路径（点分），如 "data"、"twist.linear.x"
#   unit      单位后缀，如 "ms"、"m/s"
#   decimals  保留小数位
#
# 线程模型：与 getImg.py 一致 —— rospy 在后台守护线程 spin，
#           回调里解析后经 Qt 信号跨线程（QueuedConnection）送到主线程。

import threading
import functools
from dataclasses import dataclass

import rospy
from roslib.message import get_message_class

from PySide6 import QtCore

from . import ensure_ros_node


@dataclass
class DataItem:
    """一条键值对数据的订阅描述（用户按需求增删 / 修改）"""

    key: str                # 显示键，如 "YOLO推理时间"
    topic: str              # ROS 话题名
    msg_type: str = "std_msgs/Float64"   # 消息类型，如 "std_msgs/Float64"
    field: str = "data"     # 取值字段路径（点分），如 "data" / "twist.linear.x"
    unit: str = ""          # 单位后缀，如 "ms" / "m/s" / "°"
    decimals: int = 2       # 保留小数位


# 监控的数据项列表（增删数据项改这里即可；话题 / 消息类型按实际修改）
DATA_ITEMS = [
    DataItem(key="YOLO推理时间", topic="/yolo_detect_time",
             msg_type="std_msgs/Float64", field="data", unit="ms"),
    DataItem(key="Pointpillars推理时间", topic="/perception/pointpillars/infer_time",
             msg_type="std_msgs/Float64", field="data", unit="ms"),
    DataItem(key="融合速度", topic="/fusion/velocity",
             msg_type="std_msgs/Float64", field="data", unit="m/s"),
    DataItem(key="当前发布转角", topic="/control/steering_angle",
             msg_type="std_msgs/Float64", field="data", unit="°"),
]


class DataSubscriber(QtCore.QObject):
    """订阅一组键值对话题，解析后发出 data_updated(键, 文本) 信号"""

    data_updated = QtCore.Signal(str, str)

    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self._items = list(items) if items is not None else list(DATA_ITEMS)
        self._subs = []
        self._started = False

    def items(self):
        """返回当前配置的数据项列表（供 UI 构建行）"""
        return list(self._items)

    # ------------------------------------------------------------------
    #  启动 / 关闭
    # ------------------------------------------------------------------

    def start(self):
        """在后台线程初始化 rospy 节点并订阅话题（仅生效一次）"""
        if self._started:
            return
        self._started = True
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def _run(self):
        """ROS 工作线程：共享节点初始化 → 逐项订阅 → spin"""
        # 与图像桥共用同一个 ROS 节点（进程内只 init 一次），线程安全
        if not ensure_ros_node():
            return

        for item in self._items:
            cls = get_message_class(item.msg_type)
            if cls is None:
                rospy.logwarn(f"[getData] 未知消息类型 {item.msg_type}，跳过 {item.key}")
                continue
            self._subs.append(rospy.Subscriber(
                item.topic, cls, functools.partial(self._on_msg, item), queue_size=1))
        rospy.loginfo("[getData] 订阅 %d 项数据: %s", len(self._subs),
                      ", ".join(i.key for i in self._items))
        rospy.spin()

    def shutdown(self):
        """关闭 ROS 节点"""
        try:
            if not rospy.is_shutdown():
                rospy.signal_shutdown("DataSubscriber shutdown")
        except Exception:
            pass

    # ------------------------------------------------------------------
    #  解析：msg → 值 → 格式化文本 → 发信号
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve(item, msg):
        """按 field 路径（点分）取字段值；失败返回 None"""
        try:
            for part in item.field.split("."):
                msg = getattr(msg, part)
            return msg
        except AttributeError:
            return None

    @staticmethod
    def _format(item, value):
        """把值格式化为显示文本（带单位）"""
        if value is None:
            return "—"
        try:
            num = float(value)          # 兼容数值 / rospy Duration 等
        except (TypeError, ValueError):
            return str(value)
        text = f"{num:.{item.decimals}f}"
        return f"{text} {item.unit}" if item.unit else text

    def _on_msg(self, item, msg):
        value = self._resolve(item, msg)
        self.data_updated.emit(item.key, self._format(item, value))


# ------------------------------------------------------------------
#  工厂函数：创建并启动数据桥
# ------------------------------------------------------------------

def setup_data_bridge(parent, slot):
    """创建并启动数据订阅桥，连接到 slot(键, 文本)；失败返回 None。

    把 DataSubscriber 的创建、信号连接、后台线程启动、退出清理统一封装。
    """
    try:
        bridge = DataSubscriber(parent=parent)
    except Exception as e:
        print(f"[getData] 创建数据桥失败: {e}")
        return None
    try:
        bridge.data_updated.connect(slot)
        bridge.start()
        app = QtCore.QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(bridge.shutdown)
        print(f"[getData] 数据桥已启动: {[i.key for i in bridge.items()]}")
        return bridge
    except Exception as e:
        print(f"[getData] 数据桥启动失败: {e}")
        return None
