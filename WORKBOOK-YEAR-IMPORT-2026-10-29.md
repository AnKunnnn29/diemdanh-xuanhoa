# Nhập năm học bằng sổ Excel — 29/10/2026

- Tạm ẩn luồng tự động xét lên lớp. Các bản đề xuất cũ được giữ lại.
- Admin chọn năm bắt đầu, chọn nhiều sổ lớp `.xlsm`, xem trước rồi xác nhận tạo năm học riêng. Chưa kích hoạt năm mới và không ghi đè năm đã có.
- Nhận danh sách, hồ sơ, lịch, điểm và điểm danh từ sổ đã chuẩn bị. Kiểm tra đúng mẫu/năm, mã giữa các trang, trùng lớp/mã, giới hạn 40 em/lớp và macro khớp mẫu. Mỗi file tối đa 1,9 MB; tối đa 60 file.
- File tạm được lưu riêng trong PostgreSQL, gắn Admin và năm nguồn, có hạn dùng 24 giờ; không lưu workbook/auth trong trình duyệt qua lần mở lại. Nội dung file không vào nhật ký.
- Hiển thị danh sách các em năm cũ không có trong bộ sổ mới và yêu cầu xác nhận. Kiểm tra dữ liệu chưa thay đổi trước khi ghi; giao dịch lỗi được hoàn tác.
- Không tự sao chép quyền GLV từ năm cũ hoặc cấp quyền theo tên trong Excel. Kích hoạt bằng luồng quản trị năm học hiện có, sau đó Admin phân công GLV; GLV chưa được phân công không truy cập được lớp năm mới.

## Xác minh

- 6 kiểm thử API riêng: nhập nguyên sổ và giữ năm cũ, đúng mẫu/năm, danh tính, macro, trùng dữ liệu, xác nhận em bị bỏ, xung đột dữ liệu, hoàn tác khi lỗi, quyền Admin và thời hạn file.
- 19 kiểm thử nghiệp vụ cloud hiện có đạt.
- Chromium/WebKit trên gói public: chọn/bỏ nhiều file, sửa file trùng, xác nhận danh sách thiếu, xem trước, tạo năm chưa hoạt động, xoá bộ nhớ file khi mở lại; 390/768/1440px.
- Đọc bản sao trong bộ nhớ của sổ thật: cấu trúc hợp lệ, VBA không đổi. Không ghi vào sổ nguồn.
- Cloud build và kiểm tra cú pháp đạt. Không tạo/kích hoạt năm học hoặc đăng nhập tài khoản thật khi kiểm tra production.
