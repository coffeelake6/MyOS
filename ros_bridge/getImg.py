#!/usr/bin/env python

# getImg.py — MyOS ROS 图像订阅桥
#
# 作用：订阅 ROS 的 sensor_msgs/Image 话题，把图像转成 QImage，
#       通过 Qt 信号送至 UI 线程，显示在 DashboardPanel 的占位矩形里。
#
# 话题来源：config/param/config/sys_time.yaml
#           camera1_sub_topic / camera2_sub_topic
#
# 线程模型：rospy 的回调运行在 rospy 内部线程，不在 Qt 主线程。
#           Qt 信号跨线程默认走 QueuedConnection，因此 slot 会在 Qt 主线程执行，
#           可以安全更新 UI。QImage 是隐式共享类，跨线程拷贝安全。
#
# ROS 在后台守护线程 spin，避免阻塞 Qt 事件循环；无 ROS master 时也不卡 UI。

import os
import threading

import yaml
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from PySide6 import QtCore, QtGui

from . import ensure_ros_node


class ImageSubscriber(QtCore.QObject):
    """订阅两路相机 Image 话题，转 QImage 后发出信号

    信号：
        image1_received(QImage)  — camera1 的新图像
        image2_received(QImage)  — camera2 的新图像
    """

    image1_received = QtCore.Signal(QtGui.QImage)
    image2_received = QtCore.Signal(QtGui.QImage)

    def __init__(self, yaml_path=None, parent=None):
        super().__init__(parent)
        # 默认 yaml 路径：项目根/config/param/config/sys_time.yaml
        if yaml_path is None:
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            yaml_path = os.path.join(root, "config", "param", "config", "sys_time.yaml")
        self._yaml_path = yaml_path
        self._bridge = CvBridge()
        self._topics = self._load_topics()
        self._subs = {}   # camera -> Subscriber，供运行时切换话题
        self._started = False

    def _load_topics(self):
        """从 yaml 读取 camera1 / camera2 订阅话题"""
        with open(self._yaml_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return {
            "cam1": cfg.get("camera1_sub_topic", "/01/image_rect_color"),
            "cam2": cfg.get("camera2_sub_topic", "/02/image_rect_color"),
        }

    def topics(self):
        """返回当前读取到的话题，便于外部打印确认"""
        return dict(self._topics)

    def set_topic(self, camera, topic):
        """运行时切换某一路相机的订阅话题

        Args:
            camera: "cam1" 或 "cam2"
            topic:  新的 ROS 话题名

        Returns:
            bool: 是否切换成功
        """
        if camera not in ("cam1", "cam2"):
            return False
        old = self._topics.get(camera)
        if old == topic:
            return True  # 话题未变化
        sub = self._subs.get(camera)
        if sub is not None:
            try:
                sub.unregister()
            except Exception as e:
                print(f"[getImg] 注销旧订阅失败: {e}")
        handler = self._on_cam1 if camera == "cam1" else self._on_cam2
        try:
            self._topics[camera] = topic
            self._subs[camera] = rospy.Subscriber(topic, Image, handler, queue_size=1)
        except Exception as e:
            print(f"[getImg] 订阅 {topic} 失败: {e}")
            self._topics[camera] = old  # 回滚
            return False
        print(f"[getImg] {camera} 已切换话题 -> {topic}")
        return True

    # ------------------------------------------------------------------
    #  启动 / 关闭
    # ------------------------------------------------------------------

    def start(self):
        """在后台线程初始化 rospy 节点并订阅话题（仅生效一次）

        放到后台线程是为了避免 rospy.init_node 在无 master 时阻塞 UI。
        """
        if self._started:
            return
        self._started = True
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def _run(self):
        """ROS 工作线程：共享节点初始化 → 订阅 → spin"""
        # 与数据桥共用同一个 ROS 节点（进程内只 init 一次），线程安全；
        # disable_signals=True 避免在非主线程调用 signal.signal() 报错。
        if not ensure_ros_node():
            return

        self._subs["cam1"] = rospy.Subscriber(self._topics["cam1"], Image,
                                              self._on_cam1, queue_size=1)
        self._subs["cam2"] = rospy.Subscriber(self._topics["cam2"], Image,
                                              self._on_cam2, queue_size=1)
        rospy.loginfo("[getImg] 订阅: cam1=%s cam2=%s",
                      self._topics["cam1"], self._topics["cam2"])
        rospy.spin()

    def shutdown(self):
        """关闭 ROS 节点"""
        try:
            if not rospy.is_shutdown():
                rospy.signal_shutdown("ImageSubscriber shutdown")
        except Exception:
            pass

    # ------------------------------------------------------------------
    #  回调：sensor_msgs/Image → QImage → 发信号
    # ------------------------------------------------------------------

    def _to_qimage(self, msg):
        """把 sensor_msgs/Image 转成 QImage（失败返回 None）

        统一转成 rgb8，再用 Format_RGB888 构造 QImage；
        .copy() 让 QImage 拥有独立缓冲区，避免 numpy 数组被回收后悬空。
        """
        try:
            cv_img = self._bridge.imgmsg_to_cv2(msg, desired_encoding="rgb8")
        except Exception as e:
            rospy.logwarn(f"[getImg] 图像转换失败: {e}")
            return None
        h, w = cv_img.shape[:2]
        bytes_per_line = 3 * w
        # cv_img.data 是 numpy 缓冲区，.copy() 立即深拷贝，安全跨线程传递
        qimg = QtGui.QImage(cv_img.data, w, h, bytes_per_line,
                            QtGui.QImage.Format_RGB888).copy()
        return qimg

    def _on_cam1(self, msg):
        qimg = self._to_qimage(msg)
        if qimg is not None:
            self.image1_received.emit(qimg)

    def _on_cam2(self, msg):
        qimg = self._to_qimage(msg)
        if qimg is not None:
            self.image2_received.emit(qimg)


# ------------------------------------------------------------------
#  工厂函数：创建并启动图像订阅桥
# ------------------------------------------------------------------

def setup_image_bridge(parent, slot1, slot2):
    """创建并启动图像订阅桥，连接到 slot1/slot2；失败返回 None。

    把 ImageSubscriber 的创建、信号连接、后台线程启动、退出清理
    统一封装在此，调用方只需提供父对象与两个槽函数即可。

    Args:
        parent: QObject 父对象（用于内存管理）
        slot1:  camera1 图像到达时的回调（QImage）
        slot2:  camera2 图像到达时的回调（QImage）

    Returns:
        ImageSubscriber 实例；创建或启动失败时返回 None。
    """
    try:
        bridge = ImageSubscriber(parent=parent)
    except Exception as e:
        print(f"[getImg] 创建图像订阅桥失败: {e}")
        return None
    try:
        bridge.image1_received.connect(slot1)
        bridge.image2_received.connect(slot2)
        bridge.start()
        app = QtCore.QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(bridge.shutdown)
        print(f"[getImg] 图像桥已启动: {bridge.topics()}")
        return bridge
    except Exception as e:
        print(f"[getImg] 图像桥启动失败: {e}")
        return None
