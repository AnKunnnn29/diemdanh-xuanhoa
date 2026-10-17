# Điều hướng và phân công giáo lý viên

Trang chủ đứng đầu điều hướng và hiển thị giới thiệu giáo xứ ngay sau cảnh chào.
“Công việc hôm nay” là nơi bắt đầu điểm danh, tìm thiếu nhi, nhập điểm và tải sổ.

| Nhóm | Trang |
| --- | --- |
| Công việc lớp | Điểm danh, thiếu nhi, điểm học tập, đơn từ, theo dõi thiếu nhi, báo cáo và tải sổ |
| Theo dõi & GLV | Tổng quan, thông báo và nhắc việc, phân công GLV, hồ sơ GLV (Admin) |
| Quản trị | Tài khoản và phân quyền, quản lý sổ lớp, sao lưu và năm học, quản trị hệ thống |

Nhóm chứa trang đang xem tự mở. GLV không thấy nhóm quản trị. Bộ chọn lớp chung
chỉ xuất hiện ở các trang dùng lớp; trang phân công có bộ lọc và ô tìm riêng.
Các liên kết cũ giữ nguyên hash để bookmark tiếp tục hoạt động.

Nguồn phân công là bảng “Lớp / Địa điểm / Giáo Lý viên” trong `So sinh hoat.docx`
năm 2026–2027, được trích bằng `scripts/prepare-staff-plan.py`. Chỉ tên, vị trí
lớp và ghi chú học kỳ được đưa vào ứng dụng; không đưa số điện thoại, năm sinh
hoặc các bảng khác của tài liệu vào bundle.

Các tên được bỏ tiền tố Anh/Chị/Dì. Dì được đặt ở vị trí Soeur; GLV được giữ theo
thứ tự trong bảng. Theo quyết định của người dùng, Dì Maria Đỗ Thị Hồng Hạnh
phụ trách cả DB GLV 1 A và 2 A. Chị Maria Nguyễn Thị Thanh Nhàn ở Hiệp Sĩ 1 B
được ghi riêng cho HKII và chưa được cấp quyền lớp trong HKI. Việc kích hoạt
phân công HKII được thực hiện qua trang phân công, không tự động theo đồng hồ.

`scripts/import-staff-plan.py` mặc định chỉ xem trước. Khi dùng `--apply`, dịch vụ
của thư mục dữ liệu phải được dừng; script giữ cùng mutex với Bridge. Trước khi
ghi, script sao lưu các sổ lớp và cơ sở dữ liệu tài khoản. Các ô B3/E3/E4/B4 của
Danh Sách và cache công thức tham chiếu trực tiếp đến chúng được cập nhật bằng
bộ ghi OOXML hiện có. Kiểm tra từng thành phần ZIP chặn thay đổi VBA, công thức,
định dạng và dữ liệu khác. Phân quyền sử dụng nhật ký giao dịch của Accounts;
tài khoản trùng tên được giữ mật khẩu. Thông tin tạm của tài khoản tạo mới nằm
trong thư mục sao lưu riêng tại máy chủ, ngoài thư mục web.

Kiểm tra: `npm test`, `npm run test:staff-plan`, `npm run test:layout`,
`npm run test:auth-transition`, `npm run test:motion`, `npm run test:welcome`.
Kiểm tra layout dùng Bridge QA và dữ liệu sao chép: 15 trang × 5 độ rộng màn
hình, căn ô/nút, tràn ngang, điều hướng, tìm GLV, ghi chú HKII, tên chưa liên kết
và quyền truy cập của GLV. Không chạy bộ kiểm tra ghi trên dữ liệu thật.

Hồ sơ GLV có route `#staff` riêng, hỗ trợ tìm và cập nhật liên hệ/ngày sinh. Sr trong bảng phân công có quyền Admin. Xem ACCOUNTS-AND-ROLES.md về nguồn năm sinh, quyền và nhập dữ liệu riêng tư.
