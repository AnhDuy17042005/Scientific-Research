# Mô phỏng robot, LiDAR và SLAM với ROS 2 Jazzy

Project hiện tại mô phỏng một robot vi sai trong Gazebo, cho phép điều khiển
robot qua topic `/cmd_vel`, đọc LiDAR 2D qua `/scan` và tạo bản đồ bằng
`slam_toolbox`.

Nếu LiDAR LD06 chạy trên Jetson còn RTAB-Map/RViz chạy trên laptop, xem
[hướng dẫn dùng LiDAR thật qua mạng](REAL_LIDAR_JETSON.md).
Hướng dẫn này cũng có chế độ hiển thị robot ảo trong Gazebo khi lập bản đồ
từ `/scan` thật.

Chế độ LD06 hiện tại là **RTAB-Map chỉ dùng LiDAR 2D** để thử quét bản đồ.
Phần kết hợp LiDAR với Depth camera, visual odometry và vòng lặp bằng hình ảnh
chưa thể thử nghiệm cho tới khi có camera và các topic ảnh/depth tương ứng.

## 1. Build workspace

Chạy khi build lần đầu hoặc sau khi thay đổi file trong package:

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ROS2/slam_ws

colcon build --symlink-install
source install/setup.bash
```

## 2. Chạy mô phỏng Gazebo

Terminal 1:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ROS2/slam_ws/install/setup.bash

ros2 launch robot_simulation lidar_sim.launch.py
```

## 3. Kiểm tra topic

Terminal 2:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ROS2/slam_ws/install/setup.bash

ros2 topic list
```

Kiểm tra thông tin topic điều khiển:

```bash
ros2 topic info /cmd_vel -v
```

## 4. Di chuyển robot bằng lệnh

Đi thẳng:

```bash
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

Đi lùi:

```bash
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: -0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

Quay trái tại chỗ:

```bash
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}"
```

Quay phải tại chỗ:

```bash
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: -0.5}}"
```

Nhấn `Ctrl+C` để ngừng phát lệnh. Sau đó gửi vận tốc bằng 0 để dừng robot:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

## 5. Điều khiển bằng bàn phím

```bash
source /opt/ros/jazzy/setup.bash
source ~/ROS2/slam_ws/install/setup.bash

ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

## 6. Kiểm tra dữ liệu LiDAR

LiDAR được khởi động cùng launch file và xuất dữ liệu trên `/scan`.

Kiểm tra tần số quét:

```bash
ros2 topic hz /scan
```

Đọc một bản tin `LaserScan`:

```bash
ros2 topic echo /scan --once
```

Chỉ đọc mảng khoảng cách `ranges`:

```bash
ros2 topic echo /scan --once --field ranges
```

Lưu một bản tin vào file:

```bash
ros2 topic echo /scan --once -f > ~/ROS2/slam_ws/scan_origin.yaml
```

Chỉ lưu khoảng cách

```bash
ros2 topic echo /scan --once --field ranges --full-length \
> ~/ROS2/slam_ws/scan_ranges_full.yaml
```

Trong mảng `ranges`, khoảng cách được tính bằng mét. Với robot ở vị trí ban đầu:

- Khoảng chỉ số `180`: vật thể phía trước, góc gần `0°`.
- Khoảng chỉ số `270`: vật thể bên trái, góc gần `+90°`.
- Khoảng chỉ số `90`: vật thể bên phải, góc gần `-90°`.

## 7. Kiểm tra dữ liệu Odometry

Lấy một bản tin:

```bash
ros2 topic echo /odom --once
```

Lấy vị trí:

```bash
ros2 topic echo /odom --field pose.pose.position
```

Lấy vận tốc:

```bash
ros2 topic echo /odom --field twist.twist
```

## 8. Hiển thị LiDAR bằng RViz

Mở RViz trong terminal riêng:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ROS2/slam_ws/install/setup.bash

rviz2
```

## 9. Chạy SLAM

Cách khuyến nghị: chạy Gazebo, robot, bridge, SLAM Toolbox và RViz bằng một
lệnh:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ROS2/slam_ws/install/setup.bash

ros2 launch robot_slam sim_mapping.launch.py
```

Nếu Gazebo đã được chạy riêng bằng `lidar_sim.launch.py`, chỉ chạy SLAM và
RViz bằng:

```bash
ros2 launch robot_slam mapping.launch.py
```

Mở lại RViz bằng cấu hình mapping đã lưu:

```bash
rviz2 -d ~/ROS2/slam_ws/src/slam_robot/robot_slam/rviz/mapping.rviz
```

## 10. Kiểm tra SLAM

Kiểm tra node SLAM:

```bash
ros2 node list | grep slam
ros2 lifecycle get /slam_toolbox
```

Kiểm tra bản đồ và TF:

```bash
ros2 topic echo /map --once --field info
ros2 run tf2_ros tf2_echo map odom
```

## 11. Lưu bản đồ

Giữ Gazebo và SLAM Toolbox hoạt động, dừng robot rồi chạy:

```bash
ros2 run nav2_map_server map_saver_cli \
    -t /map \
    -f ~/ROS2/slam_ws/src/slam_robot/robot_slam/maps/lidar_world \
    --ros-args \
    -p save_map_timeout:=10.0 \
    -p map_subscribe_transient_local:=true
```

Kết quả được lưu thành:

```text
robot_slam/maps/lidar_world.pgm
robot_slam/maps/lidar_world.yaml
```

Build lại package sau khi lưu bản đồ:

```bash
cd ~/ROS2/slam_ws
source /opt/ros/jazzy/setup.bash

colcon build --symlink-install --packages-select robot_slam
source install/setup.bash
```

## 12. Chạy Navigation với bản đồ đã lưu

Đảm bảo `robot_slam/maps/lidar_world.yaml` và `lidar_world.pgm` đã tồn tại.
Dừng SLAM Toolbox trước khi chạy Navigation để AMCL là node duy nhất phát TF
`map -> odom`.

Cách chạy Gazebo, robot, Nav2 và RViz bằng một lệnh:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ROS2/slam_ws/install/setup.bash

ros2 launch robot_navigation sim_navigation.launch.py
```

Nếu Gazebo đã được chạy riêng bằng `lidar_sim.launch.py`, chỉ chạy Nav2 và
RViz trong terminal khác:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ROS2/slam_ws/install/setup.bash

ros2 launch robot_navigation navigation.launch.py
```

Mặc định AMCL khởi tạo robot ở `(x=0, y=0, yaw=0)` trên bản đồ, tương ứng với
vị trí spawn trong `lidar_sim.launch.py`. Nếu robot được đặt ở vị trí khác,
chọn **2D Pose Estimate** trong RViz để đặt lại vị trí ban đầu. Sau khi robot
hiện đúng trên bản đồ, chọn **Nav2 Goal**, nhấp vào vùng trống rồi kéo mũi tên
theo hướng mong muốn tại điểm đích.

Kiểm tra các node Navigation và TF trong một terminal đã source môi trường:

```bash
ros2 lifecycle get /amcl
ros2 lifecycle get /bt_navigator
ros2 run tf2_ros tf2_echo map odom
ros2 action list
```

`/amcl` và `/bt_navigator` cần ở trạng thái `active`, TF `map -> odom` cần có,
và action `/navigate_to_pose` cần xuất hiện trước khi thử goal. Chọn điểm đích
gần robot, tránh tường và vùng chưa biết cho lần chạy đầu tiên.

### Chạy lộ trình zíc zắc bằng waypoint

File `robot_navigation/waypoints/zigzag_lower_left.yaml` chứa sáu điểm theo thứ
tự trong vùng trống phía dưới bên trái của bản đồ `lidar_world`. Sau khi chạy
Navigation và kiểm tra robot đã định vị đúng trên map:

1. Trong bảng **Navigation 2** của RViz, bấm **Waypoint / Nav Through Poses Mode**.
2. Bấm **Load WPs** và chọn file
   `~/ROS2/slam_ws/src/slam_robot/robot_navigation/waypoints/zigzag_lower_left.yaml`.
3. Kiểm tra các điểm đánh số nằm trong vùng trống, đặt **Num of loops** bằng `0`,
   rồi bấm **Start Waypoint Following**.

Waypoint đầu tiên ở `(0, -2.0)`; robot mặc định spawn gần `(0, 0)`. Nếu dùng bản
đồ hoặc vị trí xuất phát khác, cần chỉnh tọa độ waypoint theo frame `map`.
LiDAR cập nhật costmap để Nav2 tránh vật cản và tìm đường tới waypoint tiếp theo;
đường đi thực tế có thể khác các đoạn thẳng nối waypoint.
