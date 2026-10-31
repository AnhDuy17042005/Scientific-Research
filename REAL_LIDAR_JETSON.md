# Xem LD06 thật trong RViz2 và quét map trên laptop

SSH chỉ dùng để mở terminal Jetson. Topic `/scan` truyền qua ROS 2 trên mạng
Tailscale. Jetson chạy driver LD06; laptop chạy RViz2 và RTAB-Map.

## 1. Jetson: chạy driver LD06

Trên Jetson host, vào container `ros_jazzy`:

```bash
docker exec -it ros_jazzy bash
source /opt/ros/jazzy/setup.bash
source /slam_ws/install/setup.bash
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
unset ROS_LOCALHOST_ONLY
ros2 launch ldlidar_ros2 ld06.launch.py
```

Giữ terminal này chạy. Jetson phát `/scan` với frame `base_laser` và TF tĩnh
`base_link → base_laser`.

## 2. Laptop: nhận `/scan` từ Jetson

Mở terminal **trên laptop**. Nếu trước đó chạy mô
phỏng ở domain `42`, các lệnh dưới đây đưa terminal về domain `0` của Jetson:

```bash
cd ~/ROS2/slam_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export ROS_STATIC_PEERS=100.97.65.56
unset ROS_LOCALHOST_ONLY
ros2 daemon stop
ros2 topic list --no-daemon --spin-time 5 -t
ros2 topic echo /scan sensor_msgs/msg/LaserScan \
  --once --field header --qos-reliability best_effort
```

Kết quả cần có `/scan [sensor_msgs/msg/LaserScan]` và `frame_id: base_laser`.
Nếu không thấy scan, kiểm tra driver Jetson và mạng giữa hai máy trước khi mở
RViz2. Các terminal ROS 2 khác trên laptop cũng cần cùng cấu hình domain/peer.

## 3. Chỉ xem scan thật trong RViz2

Trong terminal laptop đã cấu hình ở bước 2:

```bash
rviz2 -d "$(ros2 pkg prefix robot_slam)/share/robot_slam/rviz/mapping.rviz"
```

Trong RViz2 đặt **Global Options → Fixed Frame** = `base_laser`; **LaserScan →
Topic** = `/scan`, **Reliability Policy** = `Best Effort`. Chưa chạy SLAM thì
frame `map` chưa tồn tại. Đóng RViz2 trước khi chạy bước 4 để tránh mở hai cửa
sổ.

## 4. Quét map thật và hiển thị robot ảo trong Gazebo

Trong terminal laptop đã cấu hình ở bước 2, chạy:

```bash
ros2 launch robot_slam real_scan_gazebo_mapping.launch.py
```

Muốn định vị trên database đã quét, dừng launch bằng Ctrl+C rồi chạy:

```bash
ros2 launch robot_slam real_scan_gazebo_mapping.launch.py \
  reset_map:=false localization:=true
```
