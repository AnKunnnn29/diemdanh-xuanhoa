# Bảy nhóm quản lý đã bổ sung

Vào **Quản lý khác → Quản trị hệ thống** bằng tài khoản Admin. GLV dùng **Thông báo & nhắc việc** và các màn hình lớp đã phân công; các API quản trị cũng kiểm tra quyền trên server.

| Nhóm | Cách sử dụng | Dữ liệu được giữ |
|---|---|---|
| Sao lưu đầy đủ | **Sao lưu & năm học → Tạo bản sao ngay**, tải ZIP | Excel, DB nghiệp vụ, tài khoản/phân quyền, hồ sơ GLV, nhật ký, thông báo, các năm đã kích hoạt và bộ năm đã chuẩn bị |
| Nhật ký | Tab **Nhật ký**, lọc người/ngày/thao tác/nội dung, xuất CSV | Người thực hiện lấy từ phiên đăng nhập; trước/sau cho các thay đổi được bổ sung; nhật ký cũ vẫn giữ chi tiết ban đầu |
| Quản lý lớp | Tab **Quản lý lớp**, tạo từ bản mẫu/đổi tên/lưu trữ/mở lại; xem trước rồi xác nhận | Macro, công thức, lịch bản mẫu. Đổi tên giữ mã định danh và phân công; lưu trữ giữ hồ sơ và lịch sử |
| Nhập danh sách | Tab **Nhập danh sách**, tải mẫu, dùng .xlsx/CSV/TSV hoặc dán bảng; kiểm tra rồi nhập | Tên thánh, họ tên, giới tính, ngày sinh/rửa tội, phụ huynh, địa chỉ, giáo khu, điện thoại, tháng nhập học |
| Hồ sơ GLV | Tab **Hồ sơ GLV**, thêm/sửa hồ sơ độc lập, liên kết tài khoản tùy chọn; phân công ở **Giáo lý viên** | Liên hệ, ngày phục vụ, trạng thái, ghi chú; lịch sử nhận/kết thúc phân công theo năm học |
| Nhắc việc | **Thông báo & nhắc việc**, đọc từng việc/tất cả, lưu tùy chọn | Đơn chờ duyệt, buổi chưa chốt, theo dõi đến hạn, thiếu điểm thi khi kỳ đã kết thúc; mỗi người có trạng thái đọc riêng |
| Nhiều năm học | Tab **Năm học**, chọn năm/mã thiếu nhi để xem; tạo năm mới trong **Sao lưu & năm học**, sau đó kích hoạt | Mỗi năm giữ riêng chuyên cần, điểm, hồ sơ, đơn từ, ghi chú, trạng thái học tập và phân công |

## Nhập hồ sơ

Dùng tên cột trong file mẫu: `classId,code,saintName,fullName,gender,birthDate,baptismDate,parents,address,subParish,phone,enrolledFrom`. `classId` nhận mã/tên lớp; bỏ trống để dùng lớp mặc định. `enrolledFrom` là ngày đầu tháng thuộc năm đang làm việc. Ngày sinh/rửa tội nhận `yyyy-mm-dd` hoặc `dd/mm/yyyy`, được chuẩn hóa trước khi đối chiếu.

Mỗi lượt tối đa 800 dòng và 2 MB; mỗi lớp tối đa 40 em theo mẫu Excel. Để điện thoại ở dạng văn bản trong Excel để giữ số 0 đầu. CSV/TSV dùng UTF-8. Hệ thống từ chối mã đang dùng, mã đã có lịch sử, mã trùng trong file, lớp lưu trữ hoặc dữ liệu không hợp lệ. Họ tên/ngày sinh trùng cần kiểm tra và xác nhận riêng. Cả lượt được chuẩn bị trên bản sao; chỉ ghi khi mọi dòng hợp lệ, có sao lưu và có thể phục hồi giao dịch gián đoạn.

Chỉnh nội dung sau xem trước sẽ hủy xác nhận; cần xem trước lại. Không tự bỏ qua dòng lỗi. Hệ thống không tự thay hồ sơ đang có khi mã trùng: dùng màn hình sửa hồ sơ cho trường hợp đó.

## Khôi phục

**Khôi phục dữ liệu lớp** thay Excel và DB nghiệp vụ; có thể trở về bản trước khi tạo lớp mới. Màn hình xem trước liệt kê file thêm/bỏ. Tài khoản và mật khẩu hiện hành được giữ nguyên. Mã QR đã cấp được giữ để không tái cấp nhầm mã, kể cả sau chuyển/khôi phục năm.

**Khôi phục tài khoản** ở tab **Sao lưu & truy cập** là thao tác riêng: xem danh sách tài khoản trong bản sao, nhập `KHÔI PHỤC TÀI KHOẢN`. Mật khẩu, quyền, hồ sơ GLV và tùy chọn nhắc việc quay về bản sao; tất cả phiên đăng nhập kết thúc. Nhật ký sau thời điểm sao lưu được giữ và thêm sự kiện khôi phục. Bản sao cũ chưa có accounts.sqlite3 vẫn dùng để khôi phục dữ liệu lớp, nhưng không dùng để khôi phục tài khoản.

## Chuyển năm làm việc

Tạo bộ năm mới bằng kế hoạch đã duyệt, rồi chọn bộ đó ở tab **Năm học**. Xem trước và nhập đúng năm đích để kích hoạt. Hệ thống sao lưu năm hiện tại, giữ bộ cũ, chuyển các yêu cầu đến bộ đích và kết thúc phiên đăng nhập. Năm mới kế thừa phân công hợp lệ; sau đó Admin rà soát/phân công lại. Chuyển về năm đã dùng sẽ lấy phân công đã lưu của năm đó. Khởi động lại dịch vụ vẫn mở năm đã chọn.

Lịch sử là chế độ xem; chỉnh sửa năm khác cần chuyển năm làm việc có xác nhận. Hồ sơ/điểm/đơn/ghi chú của thiếu nhi được xem theo mã thẻ xuyên các năm đã đăng ký. Giáo lý viên vẫn chỉ xem các lớp được giao trong năm đang làm việc.

## Phạm vi truy cập từ xa

Đã có cấu hình tên miền HTTPS và tunnel đến máy Windows, cùng kiểm tra Origin, cookie Secure, CSRF và phân quyền. Chưa kết nối công khai vì chưa có domain/tunnel. Xem [REMOTE-ACCESS.md](REMOTE-ACCESS.md). Không triển khai cổng phụ huynh, gửi tin nhắn tự động hay thu chi trong đợt này.

## Kiểm tra trên dữ liệu sao chép

Các lệnh chạy từ thư mục dự án:

```powershell
python -m unittest discover -s tests -p 'test_*.py'
python tests/native_management_integration.py
npm test
./tests/Start-Auth-QA.ps1
node tests/management-ui.test.mjs
./tests/Start-Auth-QA.ps1 -Stop
npm run build
```

Kiểm tra Excel thật: tạo lớp trống, giữ VBA, đổi tên giữ mã lớp, nhập nhiều hồ sơ và liên kết các bảng, archive/reopen, tạo/kích hoạt/trở về năm cũ, đọc lịch sử, ZIP chứa các năm, khôi phục bỏ lớp mới, giữ mã đã cấp và so sánh hash nguồn thực. Kiểm tra server/proxy: Admin/GLV, CSRF, HTTPS cookie, Origin/Host, phiên hết hiệu lực, rollback/crash recovery. Kiểm tra trình duyệt: 6 tab, giữ bản nhập, hủy xem trước khi sửa, nhật ký, lịch sử, nhắc việc và không tràn màn hình điện thoại.
