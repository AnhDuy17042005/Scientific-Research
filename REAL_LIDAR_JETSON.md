# LiDAR trên Jetson, SLAM và RViz trên laptop

Luồng chạy: Jetson xuất `/scan`, `/odom` và TF; laptop chạy `slam_toolbox`
và RViz. Không khởi động Gazebo hoặc `sim_mapping.launch.py` trong luồng này.

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

## 3. Jetson chạy driver và odometry

Vào container ROS 2, source `/opt/ros/jazzy/setup.bash` và workspace
`/slam_ws/install/setup.bash`, rồi chạy lệnh driver LiDAR và odometry đang dùng.
Chỉ cần build lại workspace Jetson khi source của package chạy trên Jetson
thay đổi.

Kiểm tra các topic và frame trên Jetson:

```bash
ros2 topic info /scan -v
ros2 topic echo /scan --once --field header --qos-reliability best_effort
ros2 topic echo /odom --once --field header
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo base_link base_laser
```

`/scan` phải là `sensor_msgs/msg/LaserScan`. Frame trong `header.frame_id`
phải nối được tới `base_link` qua TF. `/odom` cần đi cùng TF
`odom -> base_link`. Đồng hồ hai máy phải được đồng bộ vì dữ liệu LiDAR,
odometry và TF đều có timestamp.

## 4. Laptop nhận dữ liệu và chạy SLAM/RViz

Trên laptop, sau khi đặt các biến môi trường ở bước 2:

```bash
source ~/ROS2/slam_ws/install/setup.bash
ros2 daemon stop
ros2 topic info /scan -v
ros2 topic echo /scan --once --field header --qos-reliability best_effort
ros2 topic echo /odom --once --field header
ros2 run tf2_ros tf2_echo odom base_link
```

Khi laptop đã nhận được `/scan`, `/odom` và TF từ Jetson, chạy:

```bash
ros2 launch robot_slam mapping.launch.py use_sim_time:=false
```

Launch này mở `slam_toolbox` và RViz. Kiểm tra `/map` và TF `map -> odom`:

```bash
ros2 topic echo /map --once --field info
ros2 run tf2_ros tf2_echo map odom
```

Bản đồ `lidar_world.yaml` đi kèm project thuộc world Gazebo. Khi dùng LiDAR
thật, hãy tạo bản đồ mới từ môi trường thật trước khi dùng AMCL/Nav2; không
chạy `sim_navigation.launch.py` với bản đồ Gazebo.
