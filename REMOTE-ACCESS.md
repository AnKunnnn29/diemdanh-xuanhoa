# Chuẩn bị GLV truy cập qua 4G

Hiện hệ thống chạy tại `http://localhost:8765`; chưa có tên miền/tunnel công khai. Phần chuẩn bị đã có: nhận đúng tên miền HTTPS, cookie Secure trên tên miền, kiểm tra Origin/CSRF, mẫu tunnel, script tạo cấu hình. GLV vẫn chỉ truy cập các lớp được Admin phân công.

## Phương án phù hợp với ứng dụng hiện tại

Dùng máy Windows đang quản lý Excel làm máy phục vụ và nối Cloudflare Tunnel đến `127.0.0.1:8765`. Người dùng ngoài mạng truy cập tên miền HTTPS. Máy cần bật, có Internet, Microsoft Excel và phiên Windows của người vận hành để các thao tác Excel COM hoạt động. Một VPS Linux riêng chưa thay thế được phần ghi Excel hiện tại; bộ tính điểm portable chỉ là một phần hệ thống.

Tunnel thiết lập kết nối đi ra từ máy quản lý. Quy tắc cuối trả 404 cho tên miền ngoài cấu hình. Mẫu và các bước tạo tunnel dựa trên [tài liệu tạo tunnel](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/create-local-tunnel/) và [cấu hình Cloudflare](https://developers.cloudflare.com/tunnel/configuration/).

## Khi đã có tên miền

1. Tạo tài khoản Cloudflare, thêm tên miền và cấu hình nameserver. Cài `cloudflared` từ [trang tải chính thức](https://developers.cloudflare.com/tunnel/downloads/).
2. Đăng nhập và tạo tunnel trên máy Windows:

```powershell
cloudflared tunnel login
cloudflared tunnel create xuan-hoa-diem-danh
```

3. Ghi lại UUID và đường dẫn file credentials do lệnh trên tạo. Chạy từ thư mục dự án, thay toàn bộ giá trị ví dụ:

```powershell
./deploy/Prepare-RemoteAccess.ps1 -Hostname diem-danh.ten-mien-cua-ban.vn -TunnelId UUID-CUA-TUNNEL -CredentialsFile 'C:/Users/TenWindows/.cloudflared/UUID-CUA-TUNNEL.json'
```

Script tạo `.local/remote/config.yml`, kiểm tra ingress nếu có cloudflared. Không tự tạo DNS hoặc xuất dữ liệu. File credentials giữ ngoài git; không gửi file này qua nhóm GLV.

4. Dừng dịch vụ cũ và chạy chế độ tên miền:

```powershell
./Start-DiemDanh.ps1 -Stop
./Start-DiemDanh.ps1 -PublicOrigin https://diem-danh.ten-mien-cua-ban.vn
```

Dịch vụ vẫn chỉ nghe loopback. Cloudflare chuyển tiếp Host đúng tên miền qua `httpHostHeader`; ứng dụng kiểm tra chính xác Origin HTTPS. Không dùng `-Lan` cùng chế độ này.

5. Tạo DNS rồi chạy tunnel:

```powershell
cloudflared tunnel route dns xuan-hoa-diem-danh diem-danh.ten-mien-cua-ban.vn
cloudflared tunnel --config .local/remote/config.yml ingress validate
cloudflared tunnel --config .local/remote/config.yml run xuan-hoa-diem-danh
```

## Kiểm tra trước khi cấp link cho GLV

- Tạo/tải một bản sao mới từ **Sao lưu & năm học**; ZIP có tài khoản, phân quyền và các năm đã kích hoạt.
- Dùng điện thoại qua 4G: đăng nhập Admin, đăng nhập GLV, đổi mật khẩu lần đầu, quét QR, nhập điểm, đăng xuất. Thử mã QR/lớp ngoài phân công phải bị từ chối.
- Mở trình duyệt kiểm tra cookie trên tên miền có HttpOnly, Secure và SameSite=Strict; yêu cầu từ Origin khác và thiếu CSRF phải bị chặn.
- Kiểm tra camera trên HTTPS. Thử mất mạng rồi nối lại; giữ bản nhập và xem kết quả trước khi gửi lại lượt ghi chưa nhận xác nhận.
- Giữ máy bật trong giờ điểm danh. Sao lưu ZIP ra một nơi độc lập với máy phục vụ; ZIP chứa thông tin cá nhân và mật khẩu đã băm.

Ứng dụng có thể khởi chạy trong phiên người dùng Windows bằng Task Scheduler lúc đăng nhập. Chưa tự cài dịch vụ Windows hoặc lịch khởi động. Tunnel có hướng dẫn [chạy như dịch vụ Windows](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/as-a-service/windows/); tiến trình Excel cần được kiểm thử riêng dưới tài khoản vận hành, không chạy mặc định LocalSystem.

## Phục hồi sang máy khác

Giữ nguyên ZIP. Trích `workbooks/` vào thư mục dữ liệu mới, `attendance.sqlite3` vào thư mục trạng thái, `accounts.sqlite3` vào thư mục trạng thái tài khoản. Các thư mục `years/<id>/` chứa Excel/DB của năm lưu trữ. `prepared-years/<id>/` là bộ năm đã tạo nhưng chưa kích hoạt: trích vào `year_exports/<id>/` của thư mục trạng thái năm đã tạo bộ đó. `school-years.json` trong ZIP dùng đường dẫn của máy nguồn: chỉnh `root`, `state` của từng năm về vị trí mới trước khi chạy, không dùng đường dẫn cũ. Chọn năm làm việc ở trường `active`.

Bản ZIP không chứa phiên đăng nhập. Sao lưu dữ liệu lớp và khôi phục tài khoản là hai thao tác xác nhận riêng trên web; khôi phục dữ liệu không tự khôi phục mật khẩu. Khi thiếu thông tin tài khoản Admin của bản sao, kiểm tra quyền truy cập file trên máy vận hành trước khi khôi phục tài khoản.
