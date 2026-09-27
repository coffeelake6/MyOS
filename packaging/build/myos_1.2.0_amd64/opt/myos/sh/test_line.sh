#!/bin/bash

#参数服务器
gnome-terminal --tab -- bash -c "\
sleep 0.1s;
source /home/a03/A03/perception/devel/setup.bash;\
roslaunch param load_params.launch; \
exec bash"

#3.FAST-LIO2建图
gnome-terminal --tab -- bash -c "\
sleep 1s;
source ~/A03/SLAM/devel/setup.bash;\
roslaunch fast_lio mapping_velodyne.launch; \
exec bash"
:<<!
#4.Pointpillars聚类
gnome-terminal --tab -- bash -c "\
#sleep 1s;
whereis conda ;\
conda --help ;\
eval \"\$(/home/a03/anaconda3/condabin/conda shell.bash hook)\" ;\
conda init bash ; \
conda activate pcdet ; \
source ~/A03/perception/devel/setup.bash;\
roslaunch pointpillars pointpillars.launch  ; \
exec bash"
!

#4.DBSCAN聚类
gnome-terminal --tab -- bash -c "\
sleep 1s;
source ~/A03/perception/devel/setup.bash;\
rosrun lidar_processing lidar_publisher_line ; \
exec bash"


#5.RANSAC拟合
gnome-terminal --tab -- bash -c "\
sleep 1s;
source ~/A03/Planning/devel/setup.bash;\
rosrun line_detector new  ; \
exec bash"

#6.路径离散
gnome-terminal --tab -- bash -c "\
sleep 1s;
source ~/A03/Planning/devel/setup.bash;\
roslaunch path_generator_line acceleration.launch ; \
exec bash"

#7.跟踪控制
gnome-terminal --tab -- bash -c "\
sleep 1s;
source ~/A03/Control/devel/setup.bash;\
roslaunch control_line skidpad.launch ; \
exec bash"
