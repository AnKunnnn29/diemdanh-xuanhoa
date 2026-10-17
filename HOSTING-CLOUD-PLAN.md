# Hosting cho cổng giáo lý Xuân Hoà

Cập nhật 16/10/2026. Phương án được chọn: Vercel + Supabase để thử nghiệm, không phụ thuộc máy Windows.

Frontend, API FastAPI và HTTPS trên Vercel; dữ liệu, sổ mẫu riêng tư và snapshot trong PostgreSQL Supabase. API bảo toàn hợp đồng với UI hiện tại và thay các nhánh COM/Excel bằng quy tắc Python. Tài liệu vận hành, sao lưu, triển khai lại và giới hạn ở [VERCEL-SUPABASE-SETUP.md](VERCEL-SUPABASE-SETUP.md).

| Nhóm | Cách chạy trên cloud |
| --- | --- |
| Tài khoản, Sr/Admin, phân công, hồ sơ GLV | PostgreSQL, hash mật khẩu hiện có, kiểm tra vai trò và phạm vi lớp |
| Thiếu nhi, liên hệ phụ huynh, QR | Hồ sơ theo mã cũ, quyền theo lớp, QR do API có xác thực tạo |
| Điểm danh, đơn, lễ bù, khóa buổi | Giao dịch database, chống quét trùng, cùng quy tắc nghiệp vụ |
| Điểm, tổng kết, xuất sổ | Bộ tính công thức Python, ghi gói OOXML giữ VBA, không chạy Excel |
| Quản lý lớp, cấu hình, nhập và chuyển lớp | Xem trước, kiểm tra phiên bản, giao dịch nguyên khối |
| Chăm sóc và thông báo | Dữ liệu và trạng thái đọc lưu trên server theo người dùng |
| Các năm học | Chuẩn bị/kích hoạt theo bước xác nhận, giữ lịch sử các năm |
| Sao lưu/khôi phục | Snapshot database, dùng chung blob bất biến, ZIP ghép ở trình duyệt |

Sau khi chuyển dữ liệu, mọi người dùng cùng địa chỉ cloud. Localhost cũ là bản dữ liệu độc lập; không tiếp tục nhập liệu ở hai nơi. Tắt máy Windows không dừng website cloud.

Cần thử một buổi trên điện thoại thật và mạng 4G, theo dõi số truy cập đồng thời, dung lượng và thời gian xuất sổ. Nếu chạm hạn mức hoặc cần vận hành chính thức ổn định, nâng gói Vercel/Supabase; backend cũng có thể đặt trên máy chủ Linux với PostgreSQL mà không quay lại phụ thuộc Office.
