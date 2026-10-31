# LD06 trên Jetson, RTAB-Map và RViz trên laptop

Jetson hiện chỉ xuất `/scan` và TF tĩnh `base_link -> base_laser`. Chưa có
encoder, IMU, `/odom` hoặc TF động `odom -> base_link`. Vì vậy launch
`robot_slam mapping.launch.py` (SLAM Toolbox) không tạo được bản đồ từ cấu hình
hiện tại; RViz đặt Fixed Frame `map` sẽ báo thiếu TF.

Để thử SLAM chỉ với LD06, chạy RTAB-Map ICP odometry và RTAB-Map SLAM trên
laptop. ICP ước lượng chuyển động từ các scan liên tiếp, xuất `/odom` và TF
`odom -> base_link`; SLAM dùng chúng để tạo `/map` và TF `map -> odom`.
Đây là chế độ RTAB-Map **LiDAR-only**: không dùng camera, nên không có visual
odometry hay vòng lặp dựa trên hình ảnh. Nó phục vụ kiểm tra pipeline và quét
map 2D hiện tại; mục tiêu hợp nhất LiDAR + Depth camera vẫn chờ phần cứng.
Không khởi động `sim_mapping.launch.py` hoặc `sim_navigation.launch.py` trong
luồng dùng cảm biến thật. Nếu muốn xem robot ảo trong Gazebo, dùng chế độ ở
bước 5.

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
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
unset ROS_LOCALHOST_ONLY
```

Driver Jetson đang chạy trong phiên hiện tại dùng domain mặc định `0` (đã
kiểm tra laptop nhận được `/scan` ở domain này). Nếu sau này đổi domain,
đặt **cùng giá trị ở cả hai máy** và khởi động lại các node ROS 2.

Nếu nối qua Tailscale, multicast thường không đi qua mạng VPN. Thử khai báo
peer tĩnh ở cả hai phía (thay IP bằng địa chỉ Tailscale thực tế):

```bash
# Trên laptop (Jetson hiện có IP Tailscale 100.97.65.56):
export ROS_STATIC_PEERS=<JETSON_TAILSCALE_IP>

# Trong container Jetson:
export ROS_STATIC_PEERS=<LAPTOP_TAILSCALE_IP>
```

Container Jetson cần truy cập được mạng của host; kiểm tra network mode bằng
`docker inspect -f '{{.HostConfig.NetworkMode}}' <TEN_CONTAINER>` trên host.
`host` là cấu hình đơn giản nhất cho ROS 2 nhiều máy. Nếu dùng cùng mạng LAN
và ROS 2 tự tìm thấy nhau, không cần `ROS_STATIC_PEERS`. Sau khi đổi các biến
môi trường, chạy `ros2 daemon stop` hoặc dùng
`ros2 topic list --no-daemon --spin-time 5 -t` để tránh daemon cũ. Khi Jetson
dùng discovery `SUBNET`, khai báo Jetson làm peer trên laptop có thể đã đủ;
nếu chưa thấy dữ liệu, khai báo peer ngược lại trong container Jetson rồi
khởi động lại driver.

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
ros2 topic echo /scan sensor_msgs/msg/LaserScan --once --field header --qos-reliability best_effort
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
sudo apt install ros-jazzy-rtabmap-launch
```

Trên laptop, sau khi đặt các biến môi trường ở bước 2:

```bash
source ~/ROS2/slam_ws/install/setup.bash
# MVS camera SDK trên laptop chứa libusb cũ, gây lỗi khi chạy RTAB-Map.
# Loại riêng các thư mục MVS khỏi phiên terminal ROS 2 này.
export LD_LIBRARY_PATH="$(printf '%s' "$LD_LIBRARY_PATH" | tr ':' '\n' | grep -vE '^/opt/MVS/lib/(32|64)$' | paste -sd: -)"
ros2 daemon stop
ros2 topic echo /scan sensor_msgs/msg/LaserScan --once --field header --qos-reliability best_effort
ros2 run tf2_ros tf2_echo base_link base_laser
```

Nếu laptop chưa thấy `/scan` hoặc TF tĩnh, xử lý kết nối ROS 2 giữa hai máy
trước.

Lệnh lọc `LD_LIBRARY_PATH` ở trên cần chạy lại trong **terminal dùng để
launch** (kể cả khi vừa mở terminal mới). Nó chỉ thay đổi phiên terminal đó;
không sửa cài đặt MVS. Nếu RTAB-Map vẫn thoát với mã 127, thử chạy
`/opt/ros/jazzy/lib/rtabmap_odom/icp_odometry --help` để xem lỗi thư viện.
Sau đó chạy một launch duy nhất trên laptop:

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

## 5. Hiển thị robot ảo trong Gazebo khi quét bản đồ thật

Chế độ này giữ Gazebo làm **mô hình hiển thị**. World mới chỉ có mặt đất;
Gazebo không tạo `/scan`, `/odom`, `/tf` hoặc `/clock` trên ROS. LD06 trên
Jetson là nguồn `/scan` duy nhất. `icp_odometry` trên laptop tạo `/odom` và
TF `odom -> base_link`; robot trong Gazebo đi theo `/odom` qua service
`/world/real_scan_visualization/set_pose`. RTAB-Map tạo `/map` từ scan thật.
Do đó các vật thể trên bản đồ RViz là môi trường thật, không phải vật thể
Gazebo. Mô hình robot hiện tại là robot vi sai để hiển thị, chưa phải hình học
robot đa hướng ba bánh.

Trên laptop, cài các package cần thiết rồi build source mới:

```bash
sudo apt update
sudo apt install ros-jazzy-rtabmap-launch ros-jazzy-ros-gz \
  ros-jazzy-joint-state-publisher
cd ~/ROS2/slam_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select robot_description robot_simulation robot_slam --symlink-install
source install/setup.bash
```

Giữ driver LD06 trên Jetson chạy như bước 3. Trên laptop, trong terminal đã
cấu hình ROS 2 như bước 2, xác nhận `/scan` và TF tĩnh rồi chạy:

```bash
ros2 launch robot_slam real_scan_gazebo_mapping.launch.py
```

Launch mở Gazebo, robot ảo, RTAB-Map ICP odometry, RTAB-Map SLAM và RViz.
Di chuyển **cả robot và LiDAR thật** chậm trong phòng để quét map. Robot ảo
trong Gazebo sẽ đi theo chuyển động ước lượng từ scan. Chiều cao hình LiDAR
trên robot ảo mặc định là `0.18 m`; nếu TF `base_link -> base_laser` trên Jetson
có chiều cao khác, đặt `lidar_mount_height:=<so_met>` khi launch. Database của
chế độ này nằm ở `~/.ros/rtabmap_real_ld06.db`; để bắt đầu một bản đồ độc lập,
chọn tên file mới bằng `database_path:=/duong/dan/ban_do_moi.db`.

Không chạy đồng thời `sim_mapping.launch.py`, `lidar_sim.launch.py` hoặc
`mapping.launch.py`: chúng có thể thêm scan ảo, odometry ảo hoặc node SLAM thứ
hai. Cũng không chạy `sim_navigation.launch.py` với map Gazebo cũ. Khi Gazebo
trong chế độ này đã mở, kiểm tra trên laptop:

```bash
ros2 topic info /scan -v        # chỉ một publisher: driver Jetson
ros2 topic info /odom -v        # publisher: icp_odometry
ros2 topic echo /map --once --field info
ros2 run tf2_ros tf2_echo map base_laser
```

`tf2_echo` chạy liên tục, dừng bằng Ctrl+C. Sau khi map đã tạo xong, lưu bản
đồ 2D cho Nav2 vào một thư mục riêng trên laptop:

```bash
mkdir -p ~/ROS2/slam_ws/maps
ros2 run nav2_map_server map_saver_cli -f ~/ROS2/slam_ws/maps/real_ld06
```

Lệnh tạo `real_ld06.yaml` và ảnh bản đồ trong `~/ROS2/slam_ws/maps`. Nếu
Gazebo không di chuyển theo
robot thật, kiểm tra `/odom`, service `/world/real_scan_visualization/set_pose`
và log `follow_real_odom`. Gazebo không điều khiển robot thật qua `/cmd_vel`;
vị trí robot ảo chỉ là ước lượng từ scan, nên có thể trôi hoặc mất bám.

## Khi RViz báo `Frame [map] does not exist`

Thông báo này xuất hiện khi RTAB-Map chưa tạo TF `map`. Để **xem ngay scan
thật** mà không cần SLAM, đặt **Global Options → Fixed Frame** trong RViz thành
`base_laser`. Giữ **LaserScan → Topic** là `/scan`, và đặt **LaserScan → Topic →
Reliability Policy** thành `Best Effort`. Khi điểm scan đã xuất hiện, kiểm tra
terminal chạy SLAM: nếu `icp_odometry` và `rtabmap` đều thoát với mã `127` và
báo `libpcl_io.so.1.14: undefined symbol: libusb_set_option`, chạy lại lệnh
lọc `LD_LIBRARY_PATH` ở bước 4 trong chính terminal launch rồi khởi động lại
launch. Khi `/odom`, `/map` và TF `map -> odom` đã có, đổi Fixed Frame về
`map` để xem bản đồ.
