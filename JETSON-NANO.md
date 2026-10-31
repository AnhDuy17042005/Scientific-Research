
# 📘 Hướng dẫn Setup & Kết nối NVIDIA Jetson (VNC, SSH, Remote)

## 1. Thông tin đăng nhập mặc định

- **Username:** duyanh  
- **Password:** 123  

---

## 2. Kết nối Jetson qua VNC (Remote Desktop)

### 2.1. Lấy địa chỉ IP của Jetson

Mở Terminal trên Jetson và chạy:

```bash
ifconfig
````

Tìm địa chỉ IP tại dòng `inet`, ví dụ:

```
inet 192.168.1.35
```

👉 Đây chính là IP để kết nối.

---

### 2.2. Kết nối bằng Remmina (trên laptop)

1. Mở ứng dụng **Remmina**
2. Chọn:

   * Protocol: **VNC**
3. Nhập:

   * Server: `192.168.1.35` *(hoặc `duyanh@192.168.1.35`)*
   * Password: `123`
4. Nhấn **Connect**

---

### ⚠️ Lưu ý quan trọng

* Laptop và Jetson **phải cùng mạng**
* Nếu không thấy IP → kiểm tra lại:

  * Jetson đã kết nối WiFi chưa
  * Dùng `ping` để test

---

## 3. Kết nối qua SSH (khuyến nghị dùng VSCode)

### 3.1. Cài SSH trên Jetson (nếu chưa có)

```bash
sudo apt update
sudo apt install openssh-server
```

Kiểm tra:

```bash
sudo systemctl status ssh
```

---

### 3.2. Kết nối bằng VSCode

#### Bước 1: Cài extension

* Mở VSCode
* Cài: **Remote - SSH**

#### Bước 2: Kết nối

* Nhấn vào góc trái dưới (biểu tượng `><`)
* Chọn: **Connect to Host**
* Nhập:

```bash
duyanh@192.168.1.35
```

* Nhập password: `123`

👉 Sau khi kết nối thành công, bạn có thể:

* Mở folder Jetson
* Code trực tiếp
* Run ROS, Python, AI model từ laptop

---

## 4. Kết nối mạng (WiFi / Hotspot)

### 4.1. Nguyên tắc

Jetson và laptop **phải chung mạng**

---

### 4.2. Khuyến nghị

✔ Dùng **Hotspot từ điện thoại**
✔ Sử dụng băng tần **2.4GHz**

👉 Lý do:

* Jetson thường không ổn định với 5GHz
* 2.4GHz có range xa hơn, ổn định hơn

---

### 4.3. Kiểm tra kết nối

Từ laptop:

```bash
ping 192.168.1.35
```

Nếu nhận được phản hồi → OK

---

## 5. Kết nối từ xa KHÔNG cùng mạng (Tailscale)

### 5.1. Giới thiệu

**Tailscale** cho phép:

* Kết nối Jetson từ bất kỳ đâu
* Không cần cùng WiFi
* Không cần port forwarding

---

### 5.2. Cài đặt Tailscale trên Jetson

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

👉 Đăng nhập bằng Google / GitHub

---

### 5.3. Cài trên laptop

* Cài Tailscale
* Login cùng account

---

### 5.4. Kết nối

Sau khi setup:

```bash
tailscale ip
```

Ví dụ:

```
100.x.x.x
```

👉 SSH:

```bash
ssh duyanh@100.x.x.x
```

👉 VNC cũng dùng IP này

---

### Ưu điểm

* Remote từ bất kỳ đâu 🌍
* Không phụ thuộc mạng nội bộ
* Bảo mật cao

---

## 6. Mở rộng - Multi User

Có thể:

* Nhiều người cùng SSH vào Jetson
* Mỗi người 1 terminal riêng

---

### Tạo user mới

```bash
sudo adduser username
```

---

## 7. Checklist nhanh (Debug khi không connect được)

### ❌ Không SSH được

* Kiểm tra SSH đã chạy chưa:

```bash
sudo systemctl status ssh
```

---

### ❌ Không ping được

* Sai IP
* Khác mạng
* WiFi lỗi

---

### ❌ VNC không vào được

* Kiểm tra VNC server có chạy không
* Kiểm tra firewall

---

## 8. Tips sử dụng

* Luôn check IP trước khi connect
* Dùng SSH thay vì VNC khi làm AI (nhẹ hơn)
* Dùng `htop` để monitor tài nguyên

```bash
sudo apt install htop
htop
```

---

## 9. Tổng kết

| Phương pháp | Ưu điểm         | Khi dùng         |
| ----------- | --------------- | ---------------- |
| VNC         | Có GUI          | Debug, visualize |
| SSH         | Nhanh, nhẹ      | Code, run AI     |
| Tailscale   | Remote toàn cầu | Làm việc từ xa   |

---

🚀 **Khuyến nghị:**

* Dev → dùng SSH (VSCode)
* Demo → dùng VNC
* Remote → dùng Tailscale
