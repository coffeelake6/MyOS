cmake_minimum_required(VERSION 3.0.2)
project(param)

# 编译依赖
find_package(catkin REQUIRED COMPONENTS
  roscpp
  rospy
  std_msgs
)

# 构建目录
catkin_package(
#  INCLUDE_DIRS include
#  LIBRARIES param
#  CATKIN_DEPENDS roscpp rospy std_msgs
#  DEPENDS system_lib
)

# 安装启动文件
install(DIRECTORY launch/
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch
)

# 安装配置文件
install(DIRECTORY config/
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/config
)

# 安装 README
install(FILES README.md
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)