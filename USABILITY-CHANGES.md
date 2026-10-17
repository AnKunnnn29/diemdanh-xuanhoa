# Giao diện dành cho người ít dùng công nghệ

Đợt cải tiến tiếp theo 13/10/2026 đã bổ sung tìm kiếm không dấu nhất quán, nhớ loại điểm, lưu và chuyển em, nhập cùng loại điểm, giữ ngữ cảnh khi mất mạng và đối chiếu lượt lưu mất phản hồi. Xem [Kết quả triển khai UI/UX](UX-IMPLEMENTATION-2026-10-13.md) để biết phạm vi và kiểm thử mới nhất.

Cập nhật 13/10/2026. Áp dụng vào bản chạy trên máy; các route và nghiệp vụ Excel hiện có được giữ.

- Mặc định mở **Bắt đầu**, có bốn việc: điểm danh hôm nay, tìm thiếu nhi, nhập điểm, tải sổ lớp. Giới thiệu giáo xứ vẫn ở `#home`.
- Menu chính theo công việc; theo dõi, GLV, cấu hình sổ, sao lưu/năm học và tổng quan nằm trong mục quản lý. Điện thoại có bốn nút dưới màn hình và menu cho các việc khác.
- Lớp được nhớ trên thiết bị, dùng cho danh sách, bảng điểm, điểm danh và tải sổ. Đây là lựa chọn giao diện, không phải phân quyền tài khoản.
- Chữ chính 18px, nút chính tối thiểu 52px. Đã bỏ nút Chữ lớn theo yêu cầu; giao diện dùng cỡ chữ mặc định. Giảm khung/đổ bóng trên các màn hình quản lý, giữ logo và màu nhận diện.
- Điểm danh theo bước: chọn lớp/ngày/hoạt động → quét/nhập tên → kiểm tra trước kết thúc → tải sổ. Chưa chọn buổi thì chưa hiển thị ô ghi nhận; giao diện không cho chọn ngày tương lai để ghi có mặt.
- Kết thúc buổi vẫn gọi xem trước của backend, giữ phép/lễ bù và chặn đơn chưa xử lý. Sau khi hoàn tất, hiển thị kết quả và nút tải sổ.
- Đơn phép/đổi lễ chia ba bước; nhận tên/mã, kiểm tra lịch của em và tuần trước khi gửi. Các quy tắc duyệt và ghi Excel vẫn được kiểm tra ở backend.
- Điện thoại chọn từng em để xem điểm; hộp nhập mặc định hiện một loại điểm, có nút nghỉ phép và chuyển sang nhập nhiều loại. Các giá trị khác, gồm P/0/trống, được giữ khi lưu; kiểm tra phiên bản chống ghi đè vẫn hoạt động.
- Tải sổ lớp trực tiếp theo lớp đang chọn, độc lập buổi điểm danh; các cách tải nhiều lớp/theo buổi nằm trong mục mở rộng.
- Sổ lớp chia thao tác theo nội dung; thông tin gia đình khi tiếp nhận và thao tác nâng cao được thu gọn. Các tính năng vẫn truy cập được khi mở mục tương ứng.
- Sửa lời nhắc đã lỗi thời, hạn chế thuật ngữ kỹ thuật trên màn hình thường dùng; thông báo lưu điểm có dòng xác nhận trên trang.

Kiểm tra trên dữ liệu sao chép: quét có mặt, duyệt phép, chốt vắng, tải đúng lớp, nhập điểm một/nhiều loại và nghỉ phép; tên/lớp được kiểm tra từ dữ liệu thật. Các thao tác ghi thử không chạy trên sổ gốc.

Kiểm tra hồi quy bảng điểm: kết quả có sẵn trong file tải về, phân biệt P/0/trống và chặn phiên sửa cũ. Kiểm tra cả 12 trang ở chiều rộng 320, 375, 414, 768 và 1440px, trả focus khi đóng hộp thoại bằng bàn phím, thao tác nâng cao và bốn nút dưới màn hình. Đã xem ảnh giao diện máy tính/điện thoại và sửa các chỗ chữ nhạt hoặc nút bị chật.

Chưa thử trực tiếp với giáo lý viên lớn tuổi. Bước đánh giá thực tế tiếp theo là quan sát họ điểm danh một em, tìm số phụ huynh và tải sổ, rồi điều chỉnh các chỗ còn vướng.
