# LD06 trên Jetson, RTAB-Map và RViz trên laptop

Jetson hiện chỉ xuất `/scan` và TF tĩnh `base_link -> base_laser`. Chưa có
encoder, IMU, `/odom` hoặc TF động `odom -> base_link`. Vì vậy launch
`robot_slam mapping.launch.py` (SLAM Toolbox) không tạo được bản đồ từ cấu hình
hiện tại; RViz đặt Fixed Frame `map` sẽ báo thiếu TF.

Để thử SLAM chỉ với LD06, chạy RTAB-Map ICP odometry và RTAB-Map SLAM trên
laptop. ICP ước lượng chuyển động từ các scan liên tiếp, xuất `/odom` và TF
`odom -> base_link`; SLAM dùng chúng để tạo `/map` và TF `map -> odom`.
Không khởi động Gazebo, `sim_mapping.launch.py` hoặc
`sim_navigation.launch.py` trong luồng dùng cảm biến thật.

## 1. Đồng bộ source bằng Git

Sửa và commit trong `~/ROS2/slam_ws/src/slam_robot` trên laptop, sau đó push
lên `origin`. Trên Jetson, pull bản mới vào `~/slam_ws/src/slam_robot`.

Nếu trước đây đã chép `slam_robot` bằng `rsync --exclude='.git/'`, thư mục trên
Jetson không phải Git checkout. Kiểm tra trước:

```bash
git -C ~/slam_ws/src/slam_robot rev-parse --is-inside-work-tree
```

Nếu lệnh báo lỗi, tạo checkout một lần trên **Jetson host**. Bản đã chép được
giữ lại để đối chiếu:

```bash
cd ~/slam_ws/src
mv slam_robot "$HOME/slam_robot_backup_$(date +%Y%m%d_%H%M%S)"
git clone https://github.com/AnhDuy17042005/Scientific-Research.git slam_robot
```

Những lần sau dùng `git -C ~/slam_ws/src/slam_robot pull --ff-only`. Nếu
`/slam_ws` trong container không được gắn từ `~/slam_ws` trên host, cần gắn
workspace vào container trước khi build hoặc chạy code mới.

## 2. Cấu hình ROS 2 trên cả hai máy

Chạy các lệnh sau trong **mỗi terminal ROS 2**, gồm terminal chạy driver trên
Jetson và terminal chạy SLAM/RViz trên laptop:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
unset ROS_LOCALHOST_ONLY
```

Nếu nối qua Tailscale, multicast thường không đi qua mạng VPN. Thử khai báo
peer tĩnh ở cả hai phía (thay IP bằng địa chỉ Tailscale thực tế):

```bash
# Trên laptop:
export ROS_STATIC_PEERS=<JETSON_TAILSCALE_IP>

# Trong container Jetson:
export ROS_STATIC_PEERS=<LAPTOP_TAILSCALE_IP>
```

Container Jetson cần truy cập được mạng của host; kiểm tra network mode bằng
`docker inspect -f '{{.HostConfig.NetworkMode}}' <TEN_CONTAINER>` trên host.
`host` là cấu hình đơn giản nhất cho ROS 2 nhiều máy. Nếu dùng cùng mạng LAN
và ROS 2 tự tìm thấy nhau, không cần `ROS_STATIC_PEERS`. Sau khi đổi các biến
môi trường, chạy `ros2 daemon stop` trước khi dùng `ros2 topic list`.

## 3. Jetson chạy driver LD06

Trong container ROS 2, source workspace rồi chạy driver:

```bash
source /opt/ros/jazzy/setup.bash
source /slam_ws/install/setup.bash
ros2 launch ldlidar_ros2 ld06.launch.py
```

Kiểm tra ở terminal khác trong container:

```bash
ros2 topic info /scan -v
ros2 topic echo /scan --once --field header --qos-reliability best_effort
ros2 run tf2_ros tf2_echo base_link base_laser
```

`/scan` phải là `sensor_msgs/msg/LaserScan`. Frame trong `header.frame_id`
phải là `base_laser` và nối được tới `base_link` qua TF. `tf2_echo` chạy liên
tục; dừng bằng Ctrl+C trước khi nhập lệnh khác. Chỉ build lại workspace
Jetson khi source của package chạy trên Jetson thay đổi.

## 4. Laptop chạy RTAB-Map ICP odometry, SLAM và RViz

Cài RTAB-Map trên **laptop** nếu chưa có:

```bash
sudo apt update
sudo apt install ros-jazzy-rtabmap-ros
```

Trên laptop, sau khi đặt các biến môi trường ở bước 2:

```bash
source ~/ROS2/slam_ws/install/setup.bash
ros2 daemon stop
ros2 topic echo /scan --once --field header --qos-reliability best_effort
ros2 run tf2_ros tf2_echo base_link base_laser
```

Nếu laptop chưa thấy `/scan` hoặc TF tĩnh, xử lý kết nối ROS 2 giữa hai máy
trước. Sau đó chạy một launch duy nhất trên laptop:

```bash
ros2 launch rtabmap_launch rtabmap.launch.py \
  depth:=false subscribe_rgb:=false visual_odometry:=false \
  icp_odometry:=true subscribe_scan:=true scan_topic:=/scan \
  frame_id:=base_link odom_topic:=/odom vo_frame_id:=odom \
  odom_frame_id:=odom map_topic:=/map qos:=2 use_sim_time:=false \
  rtabmap_viz:=false rviz:=true \
  rviz_cfg:="$(ros2 pkg prefix robot_slam)/share/robot_slam/rviz/mapping.rviz"
```

Kiểm tra trên laptop trong terminal khác, cùng môi trường ROS 2:

```bash
ros2 topic echo /odom --once --field header
ros2 run tf2_ros tf2_echo odom base_link
# Ctrl+C trước khi chạy lệnh tiếp theo
ros2 run tf2_ros tf2_echo map odom
# Ctrl+C trước khi chạy lệnh tiếp theo
ros2 topic echo /map --once --field info
```

Nếu `/odom` không xuất hiện, xem log `icp_odometry`, QoS của `/scan`, TF
`base_link -> base_laser` và timestamp giữa hai máy. Nếu `/odom` có nhưng
`/map` không có, xem log `rtabmap` và di chuyển robot đủ xa. Đồng hồ hai máy
phải được đồng bộ vì scan và TF có timestamp. Database RTAB-Map mặc định ở
`~/.ros/rtabmap.db` trên laptop.

ICP odometry chỉ dựa vào hình học từ LD06: hành lang dài, tường trống, vật thể
di động hoặc robot di chuyển nhanh có thể làm mất khớp scan. Cấu hình này dùng
để thử SLAM; cần odometry đáng tin cậy hơn và kiểm tra robot thật trước khi
chạy Nav2. Khi có encoder/IMU, tích hợp chúng rồi kiểm tra lại chuỗi TF.

Bản đồ `lidar_world.yaml` đi kèm project thuộc world Gazebo. Khi dùng LiDAR
thật, hãy tạo bản đồ mới từ môi trường thật trước khi dùng AMCL/Nav2; không
chạy `sim_navigation.launch.py` với bản đồ Gazebo.
