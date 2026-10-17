# Kiểm chứng bản cloud — 17/10/2026

Địa chỉ sử dụng: https://giao-xu-xuan-hoa.vercel.app

Production hiện tại: dpl_GSZBQXBbXrYnUF9pSmmMmQybJe8H. Tên miền chính trỏ đúng bản này; đã bật lại tự gán tên miền cho các lần deploy production tiếp theo sau rollback.

## Quét QR và xác nhận tên trước khi điểm danh — 17/10/2026

- Nhận diện mở hộp nổi có tên thánh, họ tên, lớp, mã và ngày/hoạt động. Chỉ bấm Xác nhận điểm danh hoặc Gửi điểm danh giùm mới lưu; Hủy và Escape không lưu.
- Thẻ lớp khác được tra cứu qua scan-preview, chỉ trả thông tin nhận diện; không ghi điểm danh, tạo yêu cầu chờ duyệt hay trả liên hệ gia đình trong bước xem trước.
- Camera có khung trong suốt, không có hình QR hoặc mảng màu che giữa. Tạm dừng đọc khi hộp đang mở; giữ cùng thẻ trước camera không tự mở lại sau khi đóng.
- 33 kiểm thử frontend và 77 kiểm thử backend qua. Chromium và WebKit qua QR ảnh thật, xác nhận, hủy, gửi điểm danh giùm, mã lạ, chống bấm hai lần, bàn phím và ba kích thước màn hình. Chromium thử thêm camera bằng video QR tổng hợp và xác nhận khi mất mạng.
- Chạy lại đủ luồng ngoại tuyến/sinh nhật trên Chromium và WebKit với bước xác nhận mới: mất mạng và tải lại, mất phản hồi sau lưu, buổi đã chốt, tách tài khoản, hết hạn dữ liệu ngoại tuyến, thiết bị không có IndexedDB, hồ sơ bổn mạng và giao diện đều qua.
- Dữ liệu QA hoàn toàn tổng hợp. Ảnh và thông tin kiểm tra tại `.local/scan-confirmation-qa/`; không điểm danh thử trên thiếu nhi thật.

## Điểm danh ngoại tuyến và lịch sinh nhật/bổn mạng — 17/10/2026

- Đã triển khai outbox IndexedDB theo tài khoản/năm học/buổi, giao diện công khai dùng khi mất mạng, tự đồng bộ và biên nhận chống ghi lại. Giữ quy tắc xác nhận lễ sớm; không tự ghi đè buổi đã chốt, quyền bị thu hồi, năm/lớp đã đổi hoặc buổi chưa diễn ra kể cả đồng hồ thiết bị lệch qua nửa đêm.
- Lịch theo lớp, 7 ngày tới hoặc tháng, lọc sinh nhật/bổn mạng và tìm tên/mã; hồ sơ có ngày bổn mạng do GLV/Admin xác nhận. Công việc hôm nay nhắc các dịp sắp tới.
- Đã qua 33 kiểm thử frontend và 74 kiểm thử backend toàn bộ. Sau bổ sung chặn ngày tương lai, chạy lại đủ 7 ca chuyên biệt ngoại tuyến/bổn mạng: qua. Chromium và WebKit qua các luồng mất mạng/tải lại trang, mất phản hồi sau lưu, đổi tài khoản, buổi đã chốt, hết hạn danh sách ngoại tuyến, thiết bị không có IndexedDB, hồ sơ bổn mạng và năm kích thước màn hình.
- Kiểm tra production chỉ đọc: JavaScript khớp bản build, worker khớp logic nguồn (mã cache phụ thuộc CSS từng môi trường), cache không chứa API, health sẵn sàng và dữ liệu nghiệp vụ vẫn yêu cầu đăng nhập. Giao diện đăng nhập Chromium/WebKit ở 390×844, 812×375 và 1440×900; Chromium tải lại giao diện công khai khi ngoại tuyến. Không ghi dữ liệu nghiệp vụ thật.
- Hướng dẫn: [OFFLINE-AND-CELEBRATIONS.md](OFFLINE-AND-CELEBRATIONS.md). Kết quả và ảnh QA ở `.local/offline-celebrations-qa/`; xác minh production ở `.local/offline-celebrations-production.json`.

## Bản sửa cánh bồ câu — 16/10/2026

- Đã triển khai production và xác nhận JavaScript trên tên miền chính khớp bản build đã kiểm tra. CSS khớp sau khi bỏ hai quy tắc utility chỉ sinh từ fixture QA cục bộ.
- Trước deploy: 27 kiểm thử frontend và 68 kiểm thử backend qua; build cloud thành công.
- Sau deploy: Chromium và WebKit tại 390×844, 812×375 và 1440×900 hiển thị đủ 10 cánh gắn đúng thân, giữ chế độ giảm chuyển động, không lỗi JavaScript hoặc tràn ngang. API health sẵn sàng; dữ liệu nghiệp vụ vẫn yêu cầu đăng nhập. Kiểm tra chỉ đọc, không ghi dữ liệu nghiệp vụ.
- Kết quả và ảnh kiểm tra nằm trong `.local/dove-production-verification.json` và `.local/dove-production-*.png`.

## Dữ liệu

- Đã nhập gói nguồn mới lúc 13:33 ngày 16/10: 44 tài khoản, 20 lớp, 442 thiếu nhi, 43 phân công, 44 hồ sơ GLV và 20 sổ mẫu riêng tư.
- Đối chiếu ID, tên đăng nhập, hash mật khẩu, cờ đổi mật khẩu và vai trò của đủ 44 tài khoản với nguồn: khớp.
- Đã tạo snapshot đầu tiên trước khi kiểm thử tài khoản tạm. Không nhập phiên đăng nhập cũ; các ZIP backup Windows trước đó vẫn ở máy cũ.
- 14 bảng bật RLS; không cấp SELECT/INSERT/UPDATE/DELETE trực tiếp cho anon hoặc authenticated. Không còn schema QA sau các lượt thử PostgreSQL.

## Kiểm thử

- Backend: 39 kiểm thử qua; gồm đăng nhập/đổi mật khẩu lần đầu, CSRF, phân quyền lớp, giao dịch rollback, điểm danh/quét trùng/lễ bù/khóa buổi, hồ sơ GLV, điểm trống/0/P, nhập và chuyển lớp, năm học, sao lưu/khôi phục và thông báo.
- PostgreSQL thực: 25 lượt kiểm tra qua trong các schema riêng với dữ liệu giả. Có kiểm tra việc đọc bảng điểm khi giao dịch ghi đang giữ khóa; không dùng dữ liệu giáo xứ để thử sửa/xóa.
- Frontend: 27 kiểm thử qua; build cloud thành công. Các trang nghiệp vụ, lưu điểm và tải backup ZIP đã kiểm tra bằng Edge trên fixture desktop/mobile.
- Đã đối chiếu điểm và tổng kết đủ 20 sổ với bộ tính của bridge Windows. Một lượt xuất đủ 20 sổ trước tối ưu giữ nguyên VBA và cache điểm; sau giới hạn bộ nhớ, tiếp tục đối chiếu đủ 20 sổ và kiểm tra lại xuất sổ đại diện.
- Website thật: đăng nhập bằng tài khoản QA tạm, đọc đủ danh sách, đọc điểm, xuất XLSM, đọc backup theo phần, lưu tùy chọn thông báo với CSRF hợp lệ; xác nhận GLV không truy cập lớp và màn hình Admin ngoài quyền. Tài khoản và tùy chọn QA được gỡ trong finally; không sửa điểm/hồ sơ thiếu nhi thật.
- Trang đăng nhập công khai: Edge 390×844 và 1440×1000; không lỗi JavaScript, không tràn ngang mobile. Không tìm thấy tên riêng GLV trong JavaScript công khai. Các đường dẫn env, cấu hình CLI, staff-plan và mã Python riêng trả 404.

## Hiệu năng và giới hạn

Mẫu đo cuối trên tên miền production sau giới hạn cache: đăng nhập khoảng 1,55 giây, đọc bảng điểm 1,87 giây, xuất sổ 66,25 giây. Lượt preview trước đó đo được 1,35 / 2,01 / 67,09 giây. Đây là các phép đo riêng lẻ, không phải SLA hoặc kiểm tra tải. File xuất khoảng 1,49 MB, backup gồm 21 phần có xác thực.

Một bản tối ưu trung gian từng vượt RAM trên Vercel và đã được rollback. Bản thay thế giới hạn cache vùng và vị trí lọc; đã xuất thành công trên runtime Vercel trước khi đưa sang production.

Chưa nghiệm thu quét camera trên mọi điện thoại hoặc tải đồng thời cả giáo xứ. Cần buổi thử trên thiết bị thật qua Wi-Fi/4G trước buổi điểm danh chính thức. Localhost cũ có dữ liệu độc lập; từ thời điểm chuyển nên nhập liệu ở link cloud.

Log, ảnh và gói nguồn phục vụ kiểm tra nằm trong .local riêng tư, không đưa vào Git hoặc gói web.
