#!/bin/bash


#参数服务器
gnome-terminal --tab -- bash -c "\
sleep 0.1s;
source /home/a03/A03/perception/devel/setup.bash;\
roslaunch param load_params.launch; \
exec bash"

#4.DBSCAN聚类
gnome-terminal --tab -- bash -c "\
sleep 0.5s;
source ~/A03/perception/devel/setup.bash;\
rosrun lidar_processing lidar_publisher_line;\
exec bash"
:<<!
#3.Pointpillars聚类
gnome-terminal --tab -- bash -c "\
#sleep 0.5s;
whereis conda ;\
conda --help ;\
eval \"\$(/home/a03/anaconda3/condabin/conda shell.bash hook)\" ;\
conda init bash ; \
conda activate pcdet ; \
source ~/A03/perception/devel/setup.bash;\
roslaunch pointpillars pointpillars.launch  ; \
exec bash"
!


#5.FAST-LIO2建图
gnome-terminal --tab -- bash -c "\
sleep 2s;
source ~/A03/SLAM/devel/setup.bash;\
roslaunch fast_lio mapping_velodyne.launch; \
exec bash"

#6.局部锥桶点云转换全局坐标系
gnome-terminal --tab -- bash -c "\
sleep 3s;
source ~/A03/perception/devel/setup.bash;\
rosrun cluster_transform cluster_tf_sync_skidpad;\
exec bash"

#7.全局锥桶点云后聚类
gnome-terminal --tab -- bash -c "\
sleep 3s;
source ~/A03/perception/devel/setup.bash;\
roslaunch aft_lidar_cluster aft_lidar_cluster_skidpad.launch ; \
exec bash"

#8.ICP配准
gnome-terminal --tab -- bash -c "\
sleep 4s;
source ~/A03/Planning/devel/setup.bash;\
rosrun skidpad_detector bazi;\
exec bash"

#9.路径离散
gnome-terminal --tab -- bash -c "\
sleep 4s;
source ~/A03/Planning/devel/setup.bash;\
roslaunch path_generator_skidpad skidpad.launch ; \
exec bash"

#10.跟踪控制
gnome-terminal --tab -- bash -c "\
sleep 5s;
source ~/A03/Control/devel/setup.bash;\
roslaunch control_skidpad skidpad.launch ; \
exec bash"

