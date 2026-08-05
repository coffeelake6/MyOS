# ros_bridge/__init__.py — 共享 ROS 工具
#
# 整个进程只初始化一个 ROS 节点（图像桥 / 数据桥等多个订阅线程共用），
# 避免 "rospy.init_node() has already been called with different arguments" 冲突。

import threading

import rospy

_init_lock = threading.Lock()
_node_ready = False


def ensure_ros_node(node_name="myos_node"):
    """线程安全地初始化 ROS 节点（进程内只调用一次 init_node）。

    Args:
        node_name: 节点名（anonymous=True 会自动加后缀避免冲突）

    Returns:
        bool: True 表示节点可用（可继续创建订阅者）
    """
    global _node_ready
    with _init_lock:
        if _node_ready:
            return True
        try:
            rospy.init_node(node_name, anonymous=True, disable_signals=True)
        except rospy.ROSInitException:
            # 已被其它线程抢先初始化，视为可用
            pass
        except Exception as e:
            print(f"[ros_bridge] rospy 初始化失败: {e}")
            return False
        _node_ready = True
        return True
