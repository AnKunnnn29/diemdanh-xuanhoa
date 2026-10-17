# Checklist phát triển — Giáo Xứ Xuân Hoà

Ngày bắt đầu: 12/10/2026. Dữ liệu thật từ Excel; thử ghi trên bản sao trước khi áp dụng. Đăng nhập và tài khoản cá nhân hoãn theo yêu cầu.

## Lựa chọn đã thống nhất
- Dùng thư mục dữ liệu hiện tại `D:\GiaoLy\DiemDanh-ThieuNhi`; đồng bộ đám mây để sau.
- Lên lớp theo luồng: lập danh sách đề xuất → duyệt từng em → kiểm tra sức chứa/lịch → tạo bộ Excel năm mới. Không tự chuyển lớp theo tên lớp hiện tại.

## 1. Lịch đổi lễ hằng tuần
- [x] 1.1 Lập lịch theo thiếu nhi, thứ gốc, thứ thay thế, ngày bắt đầu/kết thúc.
- [x] 1.2 Xem trước các buổi từ lịch Excel; báo xung đột trước khi lưu.
- [x] 1.3 Xác nhận một lần, tạo các đơn đã duyệt cho từng tuần; chưa ghi có mặt.
- [x] 1.4 Quét ngày thay thế ghi đúng ngày gốc; ngoại lệ chỉ thay một buổi.
- [x] 1.5 Dừng các buổi tương lai chưa xử lý, giữ lịch sử và buổi đã hoàn thành.
- [x] 1.6 Kiểm thử tuần, Chủ Nhật, trùng lịch, chốt buổi, ngoại lệ và dừng lịch.

## 2. Hồ sơ và thẻ
- [x] 2.1 Sửa tên thánh/họ tên trong Excel và cập nhật kết quả quét.
- [x] 2.2 Trạng thái đang học/tạm nghỉ/nghỉ học với ngày hiệu lực; giữ dữ liệu cũ.
- [x] 2.3 In QR từng em hoặc cả lớp bằng mã đã cấp; in lại giữ mã.
- [x] 2.4 Xem trước chuyển lớp, kiểm tra lịch đích và sức chứa.
- [x] 2.5 Chuyển lớp có sao lưu, giữ mã, hồ sơ, điểm và chuyên cần.
- [x] 2.6 Kiểm thử sắp xếp lại hàng, tên, QR và chuyển lớp trên bản sao.

## 3. Theo dõi và chăm sóc
- [x] 3.1 Chuyên cần theo tháng/học kỳ/năm, biểu đồ kèm số liệu đọc được.
- [x] 3.2 Cảnh báo vắng liên tiếp từ O thực tế, không coi ô trống là vắng.
- [x] 3.3 Nhật ký liên hệ phụ huynh/thăm hỏi, người phụ trách, ngày hẹn.
- [x] 3.4 Trạng thái cần xử lý/đang theo dõi/đã hoàn tất, lịch sử xử lý.
- [x] 3.5 Xuất báo cáo tổng hợp; điểm HK1/HK2 lấy từ Excel.
- [x] 3.6 Kiểm thử bộ lọc, cảnh báo, ghi chú và số liệu.

## 4. Sao lưu và phục hồi
- [x] 4.1 Tạo bản sao đầy đủ Excel + SQLite + manifest kiểm tra toàn vẹn.
- [x] 4.2 Danh sách bản sao, tải ZIP, sao lưu định kỳ khi dịch vụ đang chạy.
- [x] 4.3 Xem trước khôi phục, kiểm tra VBA/đường dẫn/hash, sao lưu trước phục hồi.
- [x] 4.4 Khôi phục có kiểm tra file đang mở, phát hiện sửa ngoài và rollback khi lỗi.
- [x] 4.5 Hiển thị thư mục dữ liệu và trạng thái có sẵn trên máy.
- [x] 4.6 Kiểm thử thiếu file, sai hash, bản sao hỏng và phục hồi trên bản sao.

## 5. Năm học mới
- [x] 5.1 Lưu trữ năm học hiện tại gồm Excel và lịch sử web.
- [x] 5.2 Lập danh sách đề xuất lên lớp, duyệt từng em và kiểm tra sức chứa.
- [x] 5.3 Tạo bộ Excel năm mới từ mẫu, cập nhật lịch và giữ công thức/VBA.
- [x] 5.4 Xem trước/kiểm thử bộ mới; trình khởi động tách SQLite theo thư mục năm học.
- [ ] 5.5 Áp dụng cho năm học sản xuất: người dùng duyệt danh sách thực tế, kiểm tra lịch và chọn bộ mới; chưa chuyển năm đang sử dụng.

## Phần chờ cấu hình / hoãn

Các phần Excel chưa có giao diện web được chia thành task nhỏ tại [Kế hoạch hoàn thiện nghiệp vụ Excel trên web](DEVELOPMENT-PLAN-EXCEL-PARITY.md). Kế hoạch gồm tổng kết đầy đủ, quy tắc cột Đi Lễ Bù, tiếp nhận thiếu nhi, cấu hình, ghi chú/báo cáo và thao tác hàng loạt; đã hoàn thành và kiểm thử sáu đợt vào 13/10/2026.

- [ ] OneDrive/Google Drive: hoãn theo lựa chọn của người dùng, tiếp tục dùng thư mục hiện tại.
- [ ] Đồng bộ trực tiếp bằng API đám mây: hoãn; chỉ cấu hình khi người dùng yêu cầu tiếp tục.
- [ ] Đăng nhập, tài khoản và phân quyền theo lớp: hoãn, giữ cơ chế máy Excel/LAN hiện tại.

## 6. Nhập điểm trên web, tải Excel có sẵn kết quả
- [x] 6.1 Bộ tính server theo công thức mẫu, đủ hai HK và tổng kết, hệ số cả lớp, P/0/trống, xếp loại và hạng.
- [x] 6.2 Bộ ghi `.xlsm` giữ VBA nhị phân, công thức, controls và định dạng; ghi sẵn giá trị kết quả.
- [x] 6.3 Database lưu điểm/kết quả và lượt chờ xuất, tiếp tục được sau khi file bị khóa hoặc dịch vụ khởi động lại.
- [x] 6.4 Khóa theo lớp, phát hiện phiên sửa cũ và xung đột với Excel bên ngoài, lưu bản chờ để đối chiếu.
- [x] 6.5 Nút tải Excel ngay trong Bảng điểm; xuất theo lớp đang xem, độc lập phạm vi buổi điểm danh.
- [x] 6.6 Adapter MySQL cho điểm, cấu hình môi trường và lệnh nhập dữ liệu thật; chạy SQLite hiện tại khi chưa cấu hình MySQL.
- [ ] 6.7 Kết nối/kiểm thử server MySQL thật và hosting/4G: chưa có hosting theo người dùng; các nghiệp vụ ngoài điểm chưa chuyển khỏi Bridge.
- [x] 6.8 Hoàn tất kiểm thử giao diện, file tải và hồi quy; dịch vụ trên máy chạy bộ tính portable.

## Tiêu chí hoàn thành
- Checklist chỉ đánh dấu khi mã đã chạy và kiểm thử liên quan đạt.
- Không ghi dữ liệu mẫu vào file gốc; giữ các chỉnh sửa hiện có của người dùng.
- Kết quả quét phân biệt nhận diện/đang lưu/đã lưu/trùng/lỗi.
- Các thao tác ghi Excel giữ VBA, bảo vệ sheet, công thức và sao lưu.

## Kết quả kiểm tra
- 55 kiểm tra Python (39 hồi quy + 16 mở rộng) và 10 kiểm tra JavaScript đạt.
- Trình duyệt trên 2 lớp sao chép: tạo/dừng lịch, tạo/sửa ghi chú, QR giải mã đúng, sao lưu/khôi phục xem trước, duyệt dự thảo, 4 kích thước màn hình, không lỗi JavaScript.
- Excel COM trên bản sao: chuyển lớp, lỗi thay file thứ hai và rollback, phục hồi Excel + SQLite, chặn bản sao hỏng/thiếu file/VBA sai, bộ năm 2027–2028 với 54 em, công thức/VBA giữ nguyên.
- Sổ gốc của các lớp tham gia kiểm thử giữ nguyên SHA-256.

## Kiểm tra bổ sung phần điểm
- 72 kiểm tra Python (55 hồi quy + 17 phần điểm) và 10 kiểm tra JavaScript đạt.
- 20 mẫu lớp thật tính được; đối chiếu 2.618 ô mỗi lượt với Excel COM qua HK1/HK2, xếp hạng đồng điểm, hàng đã sắp xếp lại và nhập học muộn.
- File tải thực tế qua trình duyệt mở được trong Excel desktop với macro bị tắt và Calculation Manual: đã có TB/xếp loại/hạng/tổng kết; VBA nhị phân giữ nguyên.
- Đã nhập dữ liệu điểm thật của 20 lớp/442 em vào bộ lưu SQLite hiện tại; chưa có server MySQL để kiểm thử kết nối thật.

## 7. Hoàn thiện nghiệp vụ Excel trên web

- [x] 7.1 Tổng kết đủ cột K–O, ngưỡng đạt, tìm/lọc/sắp xếp; tính sẵn kết quả K–N khi xuất.
- [x] 7.2 Lễ bổ sung ngoài lịch theo từng ngày, cộng/hủy có lịch sử, chống cộng trùng và giữ số cũ.
- [x] 7.3 Tiếp nhận thiếu nhi, mã đã cấp, tháng nhập học, kiểm tra sức chứa/liên kết và bảng đã sắp xếp.
- [x] 7.4 Cấu hình sổ một/tất cả lớp, xem trước lịch, giữ chuyên cần/đơn/buổi chốt, giao dịch Excel + SQLite có rollback.
- [x] 7.5 Ghi chú thật trong sổ, nhật ký chăm sóc CSV riêng, bốn loại báo cáo In/Lưu PDF.
- [x] 7.6 Nhập điểm/điểm danh hàng loạt, phục hồi/xóa vùng nhập Excel và nghiệm thu toàn bộ.

84 kiểm tra Python + 12 kiểm tra JavaScript đạt; đối chiếu Excel desktop 2.818 ô/lượt, native integration và trình duyệt trên bản sao đạt. Danh sách chức năng: [FUNCTIONS.md](FUNCTIONS.md).
