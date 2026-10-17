# Điểm danh ngoại tuyến và sinh nhật/bổn mạng

## Điểm danh khi mất mạng

Áp dụng cho bản cloud. Khi có mạng, đăng nhập và mở buổi điểm danh hôm nay.
Ứng dụng lưu bản dùng ngoại tuyến và danh sách cần thiết trên thiết bị. Mục
“Điểm danh khi mất mạng” báo khi danh sách đã được lưu.

Quét QR, chọn ảnh QR, tìm tên hoặc bấm Có mặt mở hộp xác nhận tên, lớp và mã thẻ.
Chỉ sau khi bấm **Xác nhận điểm danh** mới giữ lượt quét khi mất mạng; hủy hộp
không ghi vào hàng chờ. Mỗi lượt nằm trong IndexedDB riêng theo tài khoản, năm học và buổi; không
thay đổi số có mặt trước khi máy chủ xác nhận. Tải lại trang vẫn mở được buổi đã
lưu trong thời hạn 12 giờ kể từ lần xác thực. Không đăng nhập mới, tạo buổi mới,
sửa hồ sơ/điểm hoặc tải báo cáo khi ngoại tuyến.

Khi kết nối trở lại, ứng dụng xác thực phiên nếu đang dùng bản ngoại tuyến và
tự đồng bộ. Phiên hết hạn cần đăng nhập lại đúng tài khoản đã quét. Máy chủ
kiểm tra lại quyền hiện tại, năm học, ngày, lịch, trạng thái buổi, đơn lễ bù và
lượt trùng. Mã xác nhận riêng từng lượt ngăn ghi lại sau khi phản hồi bị mất.
Ngày/giờ thiết bị được giữ trong biên nhận và nhật ký đồng bộ; không dùng giờ
thiết bị để bỏ qua quy định lễ sớm.

Buổi đã chốt, năm học/lớp đã đổi hoặc dữ liệu không hợp lệ giữ trạng thái cần
kiểm tra trên thiết bị. Có thể thử lại sau khi xử lý hoặc chủ động bỏ lượt chờ
với xác nhận. Không chốt buổi khi tài khoản trên thiết bị còn lượt chờ liên quan.
Lượt lễ sớm gửi lại ngoài 06:00–06:20 cần Admin xác nhận giờ thực tế theo luồng
điều chỉnh hiện có. Sau khi đã có X được xác nhận, thử lại sẽ gỡ lượt chờ và
không cộng thêm lần nữa. Lượt quá 30 ngày cần Admin đối chiếu.

Đăng xuất xóa bản danh sách dùng ngoại tuyến, giữ lượt chưa đồng bộ theo tài
khoản để có thể tiếp tục sau khi đăng nhập lại. Tài khoản khác không xem hoặc
gửi các lượt đó. Xóa dữ liệu trình duyệt hoặc đổi thiết bị sẽ không mang theo
lượt chờ; hoàn tất đồng bộ trước khi làm việc này. Nếu thiết bị không lưu được
IndexedDB, điểm danh trực tuyến vẫn hoạt động và báo rõ cần giữ kết nối.

Service worker chỉ lưu giao diện công khai (HTML, JS, CSS, logo). Không lưu phản
hồi `/api/` trong CacheStorage. Bản danh sách IndexedDB chỉ giữ thông tin nhận
diện, lịch và trạng thái cần cho điểm danh; bỏ liên hệ gia đình, địa chỉ, ngày
sinh, ghi chú chăm sóc, điểm, nội dung đơn và các thông tin xác thực.

## Sinh nhật và bổn mạng

Mở “Sinh nhật & bổn mạng” trong nhóm Công việc lớp. Bộ chọn lớp chung giới hạn
danh sách theo quyền được phân công. Có thể xem 7 ngày tới hoặc chọn tháng,
lọc sinh nhật/bổn mạng và tìm tên/mã có hoặc không dấu. Công việc hôm nay có
liên kết nhắc các dịp trong 7 ngày tới khi có dữ liệu phù hợp.

Sinh nhật lấy từ ngày sinh đã có trong hồ sơ, chấp nhận ngày nguồn dd/mm/yyyy
và yyyy-mm-dd hợp lệ. Bổn mạng chỉ xuất hiện sau khi nhập ngày dd/mm trong hồ
sơ và đánh dấu đã kiểm tra/xác nhận. Không tự gán ngày từ tên thánh. Đổi ngày
sẽ yêu cầu xác nhận lại; xóa ngày sẽ bỏ xác nhận. Máy chủ lưu người/thời điểm
xác nhận cùng phiên bản hồ sơ; quyền lớp và kiểm tra xung đột vẫn áp dụng.

Nhắc 7 ngày tới đi qua ranh giới năm; dịp 29/02 được nhắc 28/02 trong năm không
nhuận và có ghi ngày gốc. Không suy diễn ngày thiếu hoặc tự gửi tin nhắn bên
ngoài ứng dụng.

## Kiểm tra

- `npm test`: ngày hợp lệ, giao năm, ngày nhuận, bộ lọc, xác nhận bổn mạng và dữ
  liệu tối thiểu trong danh sách ngoại tuyến.
- `.local/cloud-venv/Scripts/python -m unittest discover -s tests -p 'test_cloud_*.py' -q`:
  các nghiệp vụ cloud, replay/biên nhận, quyền bị thu hồi, buổi đã chốt, năm học,
  giờ thiết bị, xác nhận lễ sớm và phiên bản hồ sơ.
- `npm run test:offline-celebrations`: tạo database tổng hợp riêng, thử Chromium
  và WebKit, mất mạng/tải lại trang, phản hồi bị mất, đổi tài khoản, xung đột,
  hồ sơ bổn mạng, năm kích thước màn hình và kiểm tra cache không chứa API.

WebKit được thử bằng ngắt máy chủ proxy cục bộ vì chế độ giả lập `setOffline`
của Playwright có [lỗi service-worker navigation đã được ghi nhận](https://github.com/microsoft/playwright/issues/42775).
Proxy, tài khoản và database thử đều được dọn sau mỗi lượt. Các kiểm tra không
đọc hoặc sửa dữ liệu thiếu nhi thật.
