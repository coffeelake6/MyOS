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


def shutdown_ros_node_async(reason="myos shutdown"):
    """在后台线程里关闭 ROS 节点，绝不阻塞调用方。

    背景：没有 rosmaster 时 rospy.signal_shutdown() 会永久阻塞
    （内部要等 master 响应）。而本函数通常由 Qt 的 aboutToQuit 在主线程调用，
    一旦阻塞就会导致“窗口已关闭但进程不退出”的幽灵进程——桌面环境会一直
    认为应用仍在运行，图标显示已启动却再也点不开。所以这里只触发、不等待。
    """
    def _do():
        try:
            if not rospy.is_shutdown():
                rospy.signal_shutdown(reason)
        except Exception:
            pass

    threading.Thread(target=_do, daemon=True).start()
