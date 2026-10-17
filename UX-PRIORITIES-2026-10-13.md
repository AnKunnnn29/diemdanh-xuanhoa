# Ưu tiên UI/UX và trải nghiệm giáo lý viên

Cập nhật 13/10/2026 theo yêu cầu ưu tiên UI/UX trước. Các luồng chính đã được triển khai và kiểm tra trên bản sao; chi tiết tại [Kết quả triển khai](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/UX-IMPLEMENTATION-2026-10-13.md). Checklist bên dưới giữ vai trò nghiệm thu, các mục chưa đánh dấu cần đánh giá sử dụng thực tế hoặc hoàn thiện tiếp.

## Mục tiêu

Giáo lý viên nhận biết đúng lớp/buổi, hoàn thành công việc với ít thao tác, hiểu dữ liệu đã lưu hay chưa và tiếp tục được khi gặp lỗi. Ưu tiên điện thoại và người ít dùng công nghệ; máy tính cần hỗ trợ thao tác liên tiếp bằng bàn phím.

Giao diện hiện có bốn công việc chính, lựa chọn lớp dùng chung, chữ lớn, nút lớn, bước kiểm tra trước chốt và đơn phép ba bước. Giữ các nền tảng này; đánh giá cải tiến bằng công việc hoàn thành được.

## 1. Điểm danh và tìm thiếu nhi — đợt đầu tiên

### Tìm kiếm nhất quán

Quan sát từ mã: tìm khi điểm danh dùng hàm `searchable` loại dấu tiếng Việt; tìm trong danh sách thiếu nhi mới chuyển chữ thường và dùng `includes`. Vì vậy hai màn hình có thể cho kết quả khác nhau với cùng cách gõ không dấu. Đây là phát hiện từ mã, chưa có quan sát sử dụng thực tế.

- [x] Dùng chung cách tìm theo tên có/không dấu, mã thẻ và số liên lạc; giữ nguyên tên gốc khi hiển thị.
- [x] Giữ từ khóa và lớp khi xem hồ sơ rồi quay lại hoặc dữ liệu được làm mới.
- [x] Khi không có kết quả, cho biết lớp đang tìm và có hành động xóa từ khóa hoặc mở rộng phạm vi lớp.
- [x] Khi trùng tên, hiển thị tên, lớp và mã trước khi người dùng chọn em.
- [x] Đưa gọi phụ huynh và mở hồ sơ vào vị trí dễ nhận biết; chức năng gọi hiện đã có, cần kiểm tra mức dễ tìm.

### Điểm danh liên tiếp

- [ ] Luôn hiển thị rõ lớp, ngày và hoạt động trong quá trình quét; phân biệt lớp đang xem với phạm vi của buổi khi hai giá trị khác nhau.
- [x] Tổ chức camera, nhập mã USB và tìm tên sao cho phương thức đang dùng nổi bật; các phương thức khác vẫn dễ chuyển sang.
- [x] Giữ tên thánh, họ tên, mã và lớp trong kết quả nhận diện; dùng chữ và biểu tượng để phân biệt đang lưu, đã lưu, trùng và lỗi.
- [x] Kiểm tra thông báo kết quả trên điện thoại, bố trí để không che ô nhập/nút đang thao tác. Kết quả vẫn được giữ đến khi người dùng đóng và có trong danh sách buổi.
- [x] Giữ focus phù hợp cho máy quét USB và người nhập tay; giáo lý viên có thể điểm danh em tiếp theo mà không phải chọn lại buổi.
- [ ] Đưa các em chưa điểm danh và đơn còn chờ vào bước kiểm tra trước kết thúc; tận dụng dữ liệu xem trước hiện có.

Nghiệm thu trên bản sao: quét/nhập liên tiếp nhiều em, lượt trùng, mã không tồn tại, hai em trùng tên và lễ bù. Thông báo không che điều khiển; người dùng biết lượt nào đã lưu; bàn phím và camera không bị ngắt ngoài ý muốn.

Nguồn: [tìm khi điểm danh](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/src/app.js:211), [tìm danh sách](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/src/app.js:1425), [kết quả quét](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/src/scan-notification.js:6).

## 2. Nhập điểm và tải sổ — đợt thứ hai

Quan sát từ mã: điện thoại chọn em bằng dropdown, mở hộp nhập và mặc định bắt đầu ở kiểm tra 15 phút; khi lưu, hộp nhập đóng. Luồng này phù hợp sửa một em nhưng chưa thuận tiện khi nhập cùng loại điểm cho nhiều em. Chưa đo số thao tác hoặc thời gian với giáo lý viên.

- [x] Thêm tìm tên/mã trong chọn em trên điện thoại.
- [x] Giữ loại điểm vừa nhập trong lượt tiếp theo; hiển thị rõ học kỳ và tên em ở vùng nhập.
- [x] Có thao tác “Lưu và nhập em tiếp theo”; chỉ chuyển sau khi xác nhận kết quả lưu, giữ nguyên dữ liệu khi lỗi.
- [x] Thiết kế chế độ nhập cùng loại điểm cho cả lớp trên máy tính, hỗ trợ Enter/Tab và chỉ rõ dòng đã thay đổi. Tiếp tục dùng cơ chế chống ghi đè phiên cũ.
- [x] Thông báo ngay tại ô sai; phân biệt rõ chưa nhập, điểm 0 và nghỉ phép. Không thay quy tắc tính của sổ.
- [x] Tải sổ đặt cạnh kết quả công việc, ghi rõ lớp và năm học của file; khi Excel còn chờ cập nhật, hướng dẫn một bước xử lý cụ thể.

Nghiệm thu: nhập cùng loại điểm cho nhiều em không phải chọn lại loại điểm; lưu thất bại giữ dữ liệu; trường hợp P/0/trống và phiên sửa cũ vẫn đúng. File tải về khớp lớp và học kỳ/ngữ cảnh đang xem.

Nguồn: [chọn em trên điện thoại](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/src/app.js:604), [hộp nhập điểm](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/src/easy-ui.js:17), [lưu điểm](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/src/app.js:724).

## 3. Điều hướng, hình thức và phản hồi — áp dụng xuyên suốt

- [ ] Mỗi màn hình có một hành động chính rõ; các thao tác quản lý ít dùng nằm trong phần mở rộng.
- [ ] Trang bắt đầu vẫn giữ bốn công việc chính; bổ sung một vùng ngắn cho việc cần xử lý của lớp, tránh biến thành bảng thống kê dày đặc.
- [ ] Thống nhất khoảng cách, cỡ tiêu đề, nút chính/phụ và các màu trạng thái; chữ lớn tăng cỡ chữ mà vẫn giữ thao tác quan trọng trong tầm nhìn.
- [ ] Giao diện điện thoại ưu tiên nội dung cần dùng trước; bảng rộng có cách xem phù hợp và không bắt người dùng tìm hành động ở ngoài màn hình.
- [ ] Nút cố định và thông báo không che trường có focus; đã kiểm tra viewport và focus trên trình duyệt, còn kiểm tra bàn phím ảo trên điện thoại thật.
- [ ] Lời nhắc thường dùng mô tả kết quả và bước tiếp theo bằng ngôn ngữ của giáo lý viên. Chi tiết file/công thức nằm trong vùng đối chiếu khi cần.
- [x] Khôi phục kết nối tự động và giữ lớp/buổi/bản nháp khi mạng gián đoạn. Đây là phần kỹ thuật trực tiếp phục vụ trải nghiệm, đưa vào đợt UI/UX đầu.
- [x] Nếu mất phản hồi sau thao tác ghi, hiển thị đang kiểm tra kết quả và đối chiếu server trước khi gửi lại.

Nghiệm thu: điều hướng bằng bàn phím; đọc trạng thái bằng trình đọc màn hình; kiểm tra 320/375/414/768/1440px, chế độ chữ lớn, bàn phím điện thoại và kết nối gián đoạn. Kiểm tra độ tương phản bằng đo màu; không kết luận đạt toàn bộ tiêu chuẩn chỉ từ việc nhìn ảnh.

Trong đợt rà soát trước, đã kiểm chứng 12 trang ở ba chiều rộng không tràn ngang và không có lỗi JavaScript; chưa thử camera thật, bàn phím điện thoại thật hoặc khảo sát người dùng.

## 4. Kiểm chứng với người dùng trước khi chốt thiết kế

Mời 3–5 giáo lý viên, gồm người ít dùng điện thoại, thực hiện các việc sau trên bản sao:

| Công việc | Quan sát cần ghi |
|---|---|
| Điểm danh một em bằng tên khi quên thẻ | Có tìm đúng em không; có hiểu đã lưu không |
| Điểm danh liên tiếp bằng QR/USB | Có thao tác lặp lại không cần thiết; có bị thông báo che không |
| Tìm số phụ huynh và mở cuộc gọi | Có tìm thấy hành động mà không được hướng dẫn không |
| Nhập cùng loại điểm cho nhiều em | Số lần chọn lại em/loại điểm; sai dòng, sai học kỳ, bỏ sót lượt lưu |
| Lập đơn phép và chốt buổi | Có hiểu ngày, hoạt động, đơn đang chờ và số sẽ bị đánh vắng không |
| Tải sổ của lớp | Có chọn đúng file; có nhận biết điểm chờ cập nhật không |
| Tiếp tục sau khi mạng gián đoạn | Có giữ được ngữ cảnh và biết cần làm gì tiếp không |

Ghi thời gian, số thao tác, lỗi và số lần cần trợ giúp trước/sau thay đổi. Các mục tiêu định lượng được chốt sau khi đo phiên bản hiện tại. Chỉ đánh dấu hoàn thành sau khi kiểm chứng; kế hoạch này chưa đại diện kết quả khảo sát.

## 5. Thứ tự công việc

1. Tìm kiếm không dấu nhất quán; giữ ngữ cảnh; cải thiện thông báo điểm danh và phục hồi kết nối.
2. Luồng nhập điểm liên tiếp, tải đúng sổ và phản hồi lỗi tại chỗ.
3. Đồng nhất giao diện các trang, vùng công việc cần xử lý và kiểm chứng với giáo lý viên.
4. Điều chỉnh theo kết quả thử nghiệm, rồi tiếp tục các hạng mục hạ tầng trong báo cáo tổng thể.

Đây là thứ tự đề xuất theo tác động đến công việc thường ngày. Chưa bắt đầu hosting/4G, MySQL hoặc thay framework trong đợt ưu tiên này.
