# Tài khoản, phân công lớp và đăng nhập

## Sử dụng

1. Mở http://localhost:8765, đăng nhập bằng tài khoản `admin` trong file `.local/bridge/tai-khoan-ban-dau-*.csv` được tạo ở lần khởi động đầu tiên.
2. Sau lần đăng nhập đầu bằng mật khẩu tạm, chỉ nhập mật khẩu mới và nhập lại để xác nhận; không cần nhập lại mật khẩu tạm. Mật khẩu mới dài 15–128 ký tự, chấp nhận tiếng Việt và khoảng trắng, phải khác mật khẩu tạm. Khi chủ động đổi mật khẩu về sau, vẫn cần mật khẩu hiện tại.
3. Vào **Tài khoản & phân quyền** để tạo người dùng theo họ tên. Chọn **Admin** cho thành viên ban trị sự; chọn **GLV** cho giáo lý viên/Soeur. Hệ thống tự tạo tên đăng nhập `admin001`, `glv005`… và mật khẩu tạm.
4. Lưu thông tin cấp mới trước khi đóng cửa sổ, rồi gửi riêng cho đúng người. Mật khẩu tạm của tài khoản tạo/cấp lại trên giao diện chỉ hiển thị một lần.
5. Vào **Theo dõi & GLV → Phân công GLV → Chỉnh phân công**, chọn tài khoản cho từng vị trí GLV1, GLV2, GLV3 và Soeur. Lưu để cập nhật cả tên trong Excel và quyền truy cập. Một người có thể phụ trách nhiều lớp.

Phân công năm 2026–2027 được đối chiếu theo Sổ sinh hoạt: 20 lớp, 42 GLV và Soeur đang phụ trách. Các tài khoản mới phải đổi mật khẩu tạm khi đăng nhập lần đầu; tài khoản đã có giữ nguyên mật khẩu. Tài khoản quản trị được cấp riêng theo vai trò.

Không tự gán người vào lớp trống. Đổi tên người phụ trách trực tiếp trong Excel sau lần nhập đầu không tự cấp quyền đăng nhập; phân công quyền qua giao diện Admin.

## Phạm vi quyền

| Chức năng | GLV | Admin |
| --- | --- | --- |
| Danh sách thiếu nhi, hồ sơ, điểm, chuyên cần, QR | Các lớp được phân công | Toàn bộ |
| Mở buổi, quét/điểm danh, chốt buổi | Từng lớp được phân công | Từng lớp hoặc toàn bộ |
| Đơn phép, đổi lễ, ghi chú chăm sóc | Thiếu nhi thuộc lớp được phân công | Toàn bộ |
| Tải sổ lớp | Các lớp được phân công | Toàn bộ, có ZIP |
| Phân công lớp, tạo/đổi role/khoá/cấp lại mật khẩu | Không | Có |
| Chuyển lớp, thiết lập sổ, sao lưu/phục hồi, năm học | Không | Có |
| Sửa buổi đã chốt, ghi trực tiếp nghỉ phép | Lập đơn theo quy trình | Theo quy trình quản lý hiện có |

Máy chủ kiểm tra quyền ở mỗi yêu cầu, cả tải file và API. Không có quyền Admin tự động từ localhost hoặc địa chỉ IP. Mọi phản hồi chứa trạng thái đều được lọc trước khi trả cho GLV. Thay phân công có hiệu lực ở yêu cầu tiếp theo; đổi role, khoá, cấp lại hoặc đổi mật khẩu thu hồi các phiên của người đó. Một Admin không thể tự khoá/hạ quyền mình bằng tài khoản đang đăng nhập.

## Lưu trữ và vận hành

- Mật khẩu lưu dưới dạng scrypt có salt riêng, theo [hướng dẫn lưu mật khẩu của OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html); không lưu mật khẩu thật trong cơ sở dữ liệu. File CSV ban đầu chứa mật khẩu tạm để chủ máy cấp tài khoản, nằm ngoài thư mục web. Sau khi cấp xong và người dùng đổi mật khẩu, chủ máy có thể xoá file này.
- Phiên dùng cookie HttpOnly, SameSite=Strict; HTTPS LAN thêm Secure. Token lưu trên máy chủ dưới dạng SHA-256. Thao tác ghi yêu cầu CSRF token. Thiết kế tham chiếu [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).
- Phiên hết hạn tối đa 12 giờ hoặc sau 1 giờ không hoạt động. Trang đang mở tự làm mới dữ liệu; đăng xuất khi hoàn tất công việc trên máy dùng chung. Sai mật khẩu 5 lần/tên đăng nhập trong 5 phút sẽ tạm chặn; giới hạn tổng 30 lượt/IP trong cùng khoảng này.
- Dữ liệu quyền nằm ở `.local/bridge/accounts.sqlite3`, tách khỏi `attendance.sqlite3`. Khôi phục sổ điểm danh không khôi phục mật khẩu/role/phân công cũ. **Bản sao lưu sổ hiện có không chứa cơ sở dữ liệu tài khoản.** Khi sao lưu toàn bộ hoặc chuyển máy, dừng dịch vụ và sao chép cả thư mục `.local/bridge` cùng các file Excel. Không công khai hoặc gửi thư mục này cho GLV.
- Phân công dùng nhật ký giao dịch: chỉ cấp quyền sau khi ghi Excel thành công; nếu tiến trình dừng giữa chừng, lần khởi động sau đối chiếu tên đã ghi trước khi hoàn tất quyền. File đang bị khoá/ghi thất bại không cấp quyền trước.
- Launcher dừng dịch vụ bằng token điều khiển riêng trên máy chủ, không mở endpoint dừng vô danh cho người truy cập localhost.
- Đăng xuất xoá dữ liệu/điểm nháp đang hiển thị; tuỳ chọn giao diện lưu riêng theo tài khoản. Khi phiên hết hạn, đăng nhập lại trước khi nhập/lưu tiếp.

## Kiểm tra

`python -X utf8 -m unittest discover -s tests -p test_access.py -v` kiểm tra mật khẩu thật, đổi mật khẩu bắt buộc, CSRF, giới hạn đăng nhập, lọc dữ liệu, chặn ID lớp/học sinh/buổi/đơn khác, giả mạo người thao tác, role và thu hồi phiên. Các test quyền dùng fixture riêng; không thay file Excel sản xuất.

Chạy `./tests/Start-Auth-QA.ps1` để tạo bộ Excel sao chép, build riêng và mở Bridge QA tại cổng 8876; cấu hình được ghi vào `.local/auth-qa.json`. Sau đó chạy `node tests/auth-ui.test.mjs` một lần trên bộ mới. Ca trình duyệt tạo tài khoản, phân công qua Excel thật, nhập điểm, điểm danh, cấp lại mật khẩu và kiểm tra giao diện desktop/điện thoại. Dừng bằng `./tests/Start-Auth-QA.ps1 -Stop`; tạo bộ mới trước lần chạy lại. Không chạy bộ này trên dữ liệu chính hoặc database MySQL dùng chung.

Các bộ kiểm tra trình duyệt hiện có dùng `XUAN_HOA_QA_URL`, thêm `XUAN_HOA_QA_ADMIN_PASSWORD` (và `XUAN_HOA_QA_ADMIN_USERNAME` nếu khác `admin`) của Admin thử nghiệm đã đổi mật khẩu lần đầu. Helper đăng nhập và cấp CSRF cho các yêu cầu; từ chối cổng sản xuất 8765 và thư mục dữ liệu không phải bản sao QA.

## Phân công từ sổ sinh hoạt 2026–2027

Xem [luồng công việc và nguồn phân công](WORKSPACE-FLOW-2026-10-15.md). Có 20 lớp và 42 GLV/Soeur đang phụ trách; chị Thanh Nhàn được ghi riêng cho HKII. Tài khoản mới cần đổi mật khẩu tạm ở lần đăng nhập đầu. Thông tin cấp mới được lưu trong `.local/bridge/staff-import-*/tai-khoan-glv-moi.csv`, ngoài thư mục web.

## Quyền Sr và thông tin liên hệ

Năm Sr có tên trong bảng phân công được cấp Admin theo yêu cầu của người dùng, truy cập toàn bộ lớp và hồ sơ. Giữ nguyên tên đăng nhập và mật khẩu; phiên cũ của người được đổi quyền hết hiệu lực. Cột quyền trong file cấp tài khoản mới được cập nhật tương ứng.

Mục **Theo dõi & GLV → Hồ sơ GLV** (`#staff`) hiển thị số điện thoại, ngày sinh/năm sinh và cho phép cập nhật hồ sơ. Sổ sinh hoạt có 43 số điện thoại (38 GLV và 5 Sr), 38 năm sinh GLV; không có ngày sinh đầy đủ. Cột bổn mạng không dùng để suy ra ngày sinh. Người phụ trách HKII có hồ sơ liên hệ riêng, chưa tạo tài khoản hoặc cấp quyền lớp. Hồ sơ riêng tư chỉ được trả qua API quản trị; không đưa số điện thoại vào bundle công khai.

`scripts/prepare-staff-profiles.py` trích thông tin vào `.local`, ngoài thư mục web; `scripts/import-staff-profiles.py` áp dụng khi dịch vụ đã dừng, sao lưu database trước khi cập nhật và dùng các hàm phân quyền/lưu hồ sơ hiện có. Bổ sung `birth_year` giữ riêng năm sinh chưa đủ ngày/tháng và tương thích với hồ sơ cũ.
