# Các chức năng của Cổng Giáo Lý — Giáo Xứ Xuân Hoà

**Cập nhật hosting 16/10/2026:** bản Vercel + Supabase có backend độc lập Windows cho các nhóm chức năng; xem [hướng dẫn cloud](VERCEL-SUPABASE-SETUP.md). Mô tả môi trường Excel/localhost trong tài liệu này ghi lại bản chạy tại máy trước đó.

Cập nhật 13/10/2026. Bản chạy trên máy dùng dữ liệu thật từ 20 sổ lớp năm học 2026–2027. Trang chính: `http://localhost:8765/#start`. Các phần mới nằm tại **Sổ lớp & báo cáo**; thao tác quản lý sổ thực hiện trên máy Excel.

Trang **Bắt đầu** có bốn việc thường dùng, nhớ lớp đang chọn. Điểm danh hướng dẫn theo bước, đơn phép chia ba bước, điện thoại nhập từng loại điểm; vẫn có thể mở đầy đủ các chức năng bên dưới. Chi tiết: [USABILITY-CHANGES.md](USABILITY-CHANGES.md).

## 1. Điểm danh và mã QR

- Quét bằng camera máy tính/điện thoại, ảnh QR, máy quét USB hoặc nhập mã; tìm theo tên khi quên thẻ.
- Nhận diện QR mở hộp nổi có mã, tên thánh, họ tên, lớp và buổi đang điểm danh. Chỉ ghi nhận khi bấm **Xác nhận điểm danh**; bấm Hủy hoặc Escape không lưu.
- Thẻ lớp khác hiển thị **Gửi điểm danh giùm**; sau khi gửi, GLV của lớp duyệt yêu cầu. Tra cứu thẻ chỉ trả thông tin nhận diện, không trả liên hệ gia đình.
- Camera giữ khung QR trong suốt; tạm dừng đọc khi đang xác nhận và không tự mở lại cùng thẻ đang giữ trước camera. Kết quả đã lưu, trùng, chờ duyệt hoặc lỗi được giữ trong hộp nổi đến khi bấm **Quét tiếp**.
- Ghi X/P/O vào ngày và hoạt động tương ứng trong sổ lớp; các lượt chọn Có mặt cũng cần xác nhận đúng em trước khi lưu.
- Ngăn lượt trùng; xem trước và chốt vắng sau buổi; chỉnh buổi đã chốt trên máy quản lý với người xử lý/lý do.
- Giáo lý và lễ sớm vào Chủ Nhật; lễ sớm 06:00–06:20. Nhập bổ sung ngoài khung giờ phải xác nhận giờ đi thực tế và lý do.

## 2. Đơn phép, đổi ngày và lễ bổ sung

- Lập, duyệt, từ chối, hủy đơn nghỉ phép hoặc đổi ngày; xem lịch sử.
- Đổi lễ trong cùng tuần, thứ Hai–thứ Bảy. Quét ngày thay thế ghi X về ngày gốc, không cộng thêm một buổi khác.
- Lịch đổi lễ hằng tuần theo khoảng hiệu lực; dời riêng một buổi và giữ lịch các tuần tiếp theo.
- Chốt các lịch lễ bù chưa tham dự; không tự đánh vắng bằng một bộ hẹn giờ chạy nền.
- **Lễ bổ sung ngoài lịch:** ghi từng em, ngày thực tế, người xác nhận và lý do; xem trước số cộng vào cột Đi Lễ Bù và tính lại tổng kết.
- Mỗi em/ngày tối đa một lượt lễ bổ sung; từ chối ngày đã dùng cho điểm danh hoặc đơn đổi lễ. Hủy lượt có lịch sử; sửa ngày bằng hủy lượt cũ rồi lập lại.
- Giữ số lễ bù cũ trong Excel, không tự tạo ngày đi cho những số chưa có lịch sử chi tiết.

## 3. Hồ sơ, nhập học và lớp

- Xem/sửa tên thánh, họ tên, giới tính, ngày sinh, ngày rửa tội, cha mẹ, địa chỉ, giáo họ, điện thoại.
- Tìm thông tin gia đình và gọi phụ huynh từ số liên lạc.
- Trạng thái đang học/tạm nghỉ/nghỉ học theo ngày hiệu lực; giữ lịch sử cũ.
- Chuyển lớp có xem trước sức chứa và khả năng giữ điểm/chuyên cần; giữ mã, hồ sơ và dữ liệu liên quan.
- **Thêm thiếu nhi:** nhập hồ sơ, chọn lớp và tháng nhập học, xem trước rồi ghi vào Excel; kiểm tra liên kết danh sách, lý lịch, tháng và bảng điểm.
- **Mã mới:** sử dụng mã đã xác nhận cấp hoặc kiểm tra mã đề xuất tiếp theo. Không dùng lại mã đã có lịch sử; bộ năm mới giữ danh sách mã đã cấp, kể cả các em tốt nghiệp.
- Mẫu hiện tại tối đa 40 em/lớp và quản lý nhập học theo tháng. Sửa tháng nhập học có kiểm tra điểm, đơn và chuyên cần đã ghi.
- In QR từng em/cả lớp, in lại giữ mã; chọn In/Lưu PDF từ trình duyệt.

## 4. Điểm và tổng kết

- Nhập 20 cột khảo bài, kiểm tra 15 phút, một tiết, thi Kinh, thi học kỳ cho HK1/HK2.
- Kiểm tra điểm 0–10, số thập phân, P và ô trống; không coi P, 0 và chưa nhập là một trạng thái.
- Tính đúng công thức mẫu theo cột đã có điểm của cả lớp: trung bình, xếp loại, hạng, chuyên cần và tổng kết năm.
- **Tổng kết đầy đủ:** điểm HK1/HK2, Giáo Lý, xếp loại, chuyên cần lễ/giáo lý, Thánh Lễ tổng hợp, đánh giá đạt/không đạt, tổng điểm, hạng cả năm và lễ bổ sung.
- Hiển thị ngưỡng đạt của sổ; tìm theo tên/mã, lọc đánh giá và sắp xếp theo hạng mà không sắp xếp lại Excel.
- Nhập nhiều dòng bằng dữ liệu dán từ Excel/TSV, xem trước và xác nhận. Mẫu gồm mã + 20 khảo bài + 4 điểm kiểm tra/thi; ô trống thay thế sẽ xóa điểm đầu vào cũ.
- Tải `.xlsm` đã có kết quả, giữ công thức và VBA; không cần bấm Thêm điểm hoặc chạy macro để tính lại.
- Chặn phiên sửa cũ; giữ lượt chờ nếu file bị khóa, phát hiện sửa ngoài và cho đối chiếu. Lỗi thật của công thức được hiển thị, không thay bằng điểm 0.

## 5. Cấu hình, ghi chú và thao tác Excel

- **Cấu hình:** tháng thuộc HKI/HKII, số buổi cho phép nghỉ, ngưỡng đạt và lịch lễ theo khối trong sổ; áp dụng một lớp hoặc tất cả lớp.
- Xem trước ảnh hưởng; giữ Thánh lễ/giáo lý/lễ sớm Chủ Nhật và giới hạn 14 cột lễ mỗi tháng của mẫu. Chặn lịch vượt sức chứa hoặc làm mất chuyên cần, đơn, buổi đã chốt; di chuyển trạng thái theo ngày/mã khi cột thay đổi.
- Chuẩn bị toàn bộ file và SQLite trên bản sao trước khi thay dữ liệu; có bản gốc và journal để hoàn tác/phục hồi khi giao dịch gián đoạn.
- **Ghi chú sổ:** đọc và sửa ghi chú văn bản có sẵn, thêm tại dòng trống an toàn của sheet Ghi Chú, giữ phần còn lại và lưu người xử lý/lý do.
- **Điểm danh hàng loạt:** dán tối đa 40 mã của một lớp, chọn ngày/hoạt động, xem trước rồi ghi có mặt X; áp dụng đơn đổi lễ đã duyệt. P/O và buổi đã chốt cần điều chỉnh riêng từng em.
- Nếu nhập điểm danh hàng loạt gián đoạn, báo rõ em đã lưu và em bị lỗi; nhập lại không cộng thêm lượt trùng.
- **Vùng nhập DiemDanhAuto:** xóa hoặc khôi phục ba vùng K:L, R:S, Y:Z, hàng 4–503 theo vùng mẫu CL:CM. Không xóa điểm/chuyên cần đã ghi; khác chức năng phục hồi toàn bộ sao lưu.

## 6. Giáo lý viên, chuyên cần và chăm sóc

- Xem/cập nhật GLV1, GLV2, GLV3 và Soeur phụ trách từng lớp.
- Phân cấp lớp Chiên → Ấu → Thiếu → Nghĩa → Hiệp → Dự bị GLV, màu nhận diện riêng.
- Chuyên cần theo tháng/học kỳ/năm từ X/P/O thực tế, biểu đồ, bảng số liệu và lịch sử từng em; hiển thị ngày đi thực tế của đơn đổi lễ.
- Tỷ lệ chuyên cần và cảnh báo từ ba O liên tiếp theo từng hoạt động; ô trống không tự tính là vắng.
- Nhật ký liên hệ/thăm hỏi/theo dõi: nội dung, người phụ trách, ngày hẹn, tình trạng và lịch sử; so sánh điểm HK1/HK2.
- Xuất báo cáo chuyên cần CSV; xuất nhật ký chăm sóc của lớp thành CSV riêng. Nhật ký chăm sóc lưu trong dữ liệu web và bản sao lưu đầy đủ, không tự ghi đè sheet Ghi Chú.

## 7. File, báo cáo in, sao lưu và năm học

- Tải sổ `.xlsm` từng lớp hoặc ZIP các lớp; giữ các sheet, công thức, định dạng và VBA.
- **In/Lưu PDF:** danh sách lớp, chuyên cần tháng/học kỳ/năm, bảng điểm HK1/HK2 và tổng kết năm, có tên giáo xứ/lớp/năm học/ngày xuất. Lễ bổ sung cũ chưa có ngày chi tiết được ghi là số cả năm trong báo cáo chuyên cần.
- Sao lưu trước ghi; tạo/tải sao lưu đầy đủ Excel + SQLite và kiểm tra toàn vẹn; sao lưu định kỳ khi dịch vụ chạy.
- Phục hồi có xem trước, xác nhận, bản sao trước phục hồi và kiểm tra xung đột; giữ mã đã cấp để tránh tái sử dụng sau khi phục hồi bản cũ.
- Lưu trữ năm học, lập đề xuất lên lớp/tốt nghiệp, duyệt từng em, kiểm tra sức chứa và tạo bộ Excel năm mới riêng.
- Bộ mới giữ hồ sơ, mã, phân công, công thức/VBA; xóa điểm, chuyên cần và số lễ bổ sung năm cũ. Tải bộ ZIP; người quản lý kiểm tra/chọn bộ mới trước khi đổi năm đang dùng.

## Phạm vi vận hành hiện tại

- Dữ liệu lưu ở thư mục hiện tại và SQLite; phần điểm có adapter MySQL nhưng chưa triển khai server MySQL thật.
- Phần tính điểm/xuất kết quả không cần Excel COM/VBA; điểm danh và các thao tác quản lý sổ còn cần Windows/Excel Bridge.
- Điện thoại cùng Wi-Fi dùng HTTPS và tài khoản cá nhân. Admin cấp tài khoản/role và phân công lớp; GLV chỉ truy cập lớp được phân công, phải đổi mật khẩu tạm lần đầu. Chưa triển khai hosting truy cập từ mọi mạng/4G hoặc đồng bộ API Drive. Xem [tài khoản và phân quyền](ACCOUNTS-AND-ROLES.md).
- Tên người xử lý do người thao tác nhập, không phải danh tính đã được xác thực bằng tài khoản riêng.
