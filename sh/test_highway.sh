#!/bin/bash
#驱动
!<<:
gnome-terminal --tab -- bash -c "\
sleep 1s;
source ~/A03/SDK/devel/setup.bash;\
roslaunch hesai_lidar start.launch; \
exec bash"

gnome-terminal --tab -- bash -c "\
sleep 1.2s;
source ~/A03/SDK/devel/setup.bash;\
roslaunch pbox_node pbox_node.launch; \
exec bash"

gnome-terminal --tab -- bash -c "\
sleep 2s;
source ~/A03/SDK/devel/setup.bash;\
roslaunch pylon_camera pylon_camera_node_01.launch ; \
exec bash"

gnome-terminal --tab -- bash -c "\
sleep 2.5s;
source ~/A03/SDK/devel/setup.bash;\
roslaunch pylon_camera pylon_camera_node_02.launch ; \
exec bash"
:
#参数服务器
gnome-terminal --tab -- bash -c "\
sleep 0.1s;
source ~/A03/perception/devel/setup.bash;\
roslaunch param load_params.launch; \
exec bash"

#运动补偿
gnome-terminal --tab -- bash -c "\
sleep 2s;
source ~/A03/perception/devel/setup.bash;\
rosrun motionCompensation motionCompensation; \
exec bash"

#4.时间同步
gnome-terminal --tab -- bash -c "\
sleep 1s;
source ~/A03/perception/devel/setup.bash;\
rosrun sys_time main ; \
exec bash"

#5.FAST-LIO2建图
gnome-terminal --tab -- bash -c "\
sleep 2s;
source ~/A03/SLAM/devel/setup.bash;\
roslaunch fast_lio mapping_velodyne.launch; \
exec bash"

#6.Pointpillars聚类
gnome-terminal --tab -- bash -c "\
sleep 3s;
source ~/miniconda3/etc/profile.d/conda.sh; \
conda activate pcdet;\
source ~/A03/perception/devel/setup.bash;\
roslaunch pointpillars pointpillars.launch;\
exec bash"


:<<!
#7.匈牙利匹配（融合）
gnome-terminal --tab -- bash -c "\
sleep 1s;
source /home/coffeelake/A03/perception/devel/setup.bash;\
rosrun Fusion lidar_camera_fusion_node ; \
exec bash"
!
#IOU
gnome-terminal --tab -- bash -c "\
sleep 1s;
source ~/A03/perception/devel/setup.bash;\
rosrun iou_fusion iou_fusion_node ; \
exec bash"


#8.局部锥桶转全局坐标
gnome-terminal --tab -- bash -c "\
sleep 2s;
source ~/A03/perception/devel/setup.bash;\
rosrun cluster_transform cluster_tf_sync_highway ; \
exec bash"



#9.全局锥桶后聚类
gnome-terminal --tab -- bash -c "\
sleep 2s;
source ~/A03/perception/devel/setup.bash;\
roslaunch aft_lidar_cluster aft_lidar_cluster_highway.launch; \
exec bash"

#:<<!
#10.Delaunay三角剖分
gnome-terminal --tab -- bash -c "\
sleep 2s;
source ~/A03/Planning/devel/setup.bash;\
roslaunch delaunay_triangulation delaunay_triangulation.launch ; \
exec bash"

#11.Catmull-Rom插值
gnome-terminal --tab -- bash -c "\
sleep 1s;
source ~/A03/Planning/devel/setup.bash;\
rosrun cubic_spline2D cubicSpline ; \
#exec bash"

#12.路径离散
gnome-terminal --tab -- bash -c "\
sleep 1s;
source ~/A03/Planning/devel/setup.bash;\
roslaunch path_generator_highway skidpad.launch ; \
exec bash"
!<<:
#13.跟踪控制
gnome-terminal --tab -- bash -c "\
sleep 1s;
source ~/A03/Control/devel/setup.bash;\
roslaunch control_highway skidpad.launch ; \
exec bash"

#15.YOLO识别
gnome-terminal --tab -- bash -c "\
sleep 1.5s;
source ~/anaconda3/etc/profile.d/conda.sh;\
conda activate yolo	; \
source ~/A03/perception/devel/setup.bash; \
roslaunch YOLO11 left.launch; \
exec bash"

gnome-terminal --tab -- bash -c "\
sleep 6.6s;
source ~/anaconda3/etc/profile.d/conda.sh;\
conda activate yolo; \
source ~/A03/perception/devel/setup.bash; \
roslaunch YOLO11 right.launch; \
exec bash"
:
gnome-terminal --tab -- bash -c "\
sleep 2.0s;
source ~/miniconda3/etc/profile.d/conda.sh;\
conda activate yolo ;\
source ~/A03/perception/devel/setup.bash; \
roslaunch YOLO11 combined.launch; \
exec bash"


