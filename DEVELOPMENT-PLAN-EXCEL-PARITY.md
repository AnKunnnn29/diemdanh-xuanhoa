# Kế hoạch hoàn thiện nghiệp vụ Excel trên web

Ngày lập: 12/10/2026. Phạm vi: hoàn thiện các thao tác quản lý trong mẫu sổ hiện tại; chưa làm hosting, MySQL thực tế, đăng nhập hoặc đồng bộ Drive. Đã triển khai và kiểm thử đủ sáu đợt vào 13/10/2026; danh sách chức năng hiện tại xem FUNCTIONS.md.

## Nguyên tắc

- Tiếp tục dùng dữ liệu thật và thư mục hiện tại. Thử ghi trên bộ Excel sao chép trước khi dùng với sổ gốc.
- Giữ mã học sinh hiện có, VBA, công thức, định dạng, bảo vệ sheet và lịch sử. Mỗi thao tác ghi có sao lưu và kiểm tra thay đổi ngoài web.
- Tính và hiển thị theo chính công thức mẫu; không tự đặt hệ số, ngưỡng đạt hoặc quy tắc cộng lễ bù mới.
- Tách kết quả nghiệp vụ khỏi nút VBA: xây chức năng web có kết quả được kiểm chứng; không tạo nút chạy tùy ý mọi macro.
- Một lượt tham dự chỉ ghi nhận một nghĩa vụ. Không cộng thêm chuyên cần cho lượt đã ghi X vào ngày gốc bằng đơn đổi lễ.
- Khi thay đổi Excel ảnh hưởng bảng điểm, làm mới hoặc vô hiệu hóa dữ liệu điểm đã tính trong database; giữ và đối chiếu các lượt điểm đang chờ xuất trước khi thay file.

## Đợt 1 — Hiển thị đủ tổng kết năm (ưu tiên đầu tiên)

- [x] 1.1 Lập bảng đối chiếu ô/cột của `Tổng kết`: E–O, ngưỡng D3/D4, ô nhập và ô công thức.
- [x] 1.2 Bổ sung API trả Điểm Thánh Lễ tổng hợp (K), Đánh Giá (L), Tổng Điểm (M), Hạng (N), giá trị Đi Lễ Bù (O). Hỗ trợ cả hai chế độ tính portable/native.
- [x] 1.3 Bổ sung các cột trên màn hình tổng kết; giải thích ĐẠT/KHÔNG ĐẠT theo ngưỡng trong file, phân biệt chưa có dữ liệu với điểm 0 hoặc lỗi công thức.
- [x] 1.4 Cho tìm theo tên/mã, lọc theo đánh giá và sắp xếp theo hạng; không thay đổi thứ tự học sinh trong Excel.
- [x] 1.5 Đối chiếu web, giá trị có sẵn trong file tải và Excel desktop: điểm đồng hạng, thiếu một học kỳ, nghỉ phép, nhập học muộn, lỗi công thức.

Hoàn thành khi: mọi kết quả tổng kết có trong sổ đều đọc được trên web và khớp file tải về; chưa cho nhập trực tiếp vào ô công thức.

## Đợt 2 — Hoàn thiện ý nghĩa và xử lý Đi Lễ Bù

- [x] 2.1 Rà hướng dẫn, công thức, dữ liệu thực tế để xác định cột O là số buổi cộng bổ sung hay dùng để theo dõi đổi ngày. Xác nhận quy tắc với người quản lý nếu nguồn không đủ rõ; chưa ghi cột O trước khi thống nhất.
- [x] 2.2 Giữ luồng đã chốt: đổi ngày → quét ngày thay thế → ghi X ngày gốc; ngoại lệ một buổi không đổi các tuần tiếp theo.
- [x] 2.3 Nếu cột O dùng cho lễ bổ sung: thiết kế sổ ghi nhận có mã học sinh, ngày đi thực tế, nghĩa vụ được bù, người xác nhận, lý do và liên kết lượt điểm danh; không chỉ nhập một con số không có nguồn gốc.
- [x] 2.4 Xây kiểm tra chống trùng giữa lượt bổ sung, X ngày gốc, đơn đổi lễ và dữ liệu cũ. Giữ số đã có trong sổ, thể hiện riêng phần cũ chưa có lịch sử chi tiết; không tự tạo lịch sử cho số đó.
- [x] 2.5 Cho xem trước thay đổi tổng kết, xác nhận, điều chỉnh/hủy có lịch sử; ghi đúng cột O nếu quy tắc đã duyệt yêu cầu và tính lại các kết quả liên quan.
- [x] 2.6 Kiểm thử đặc biệt: thứ Ba đổi sang thứ Hai không tăng O; ngoại lệ thứ Tư vẫn chỉ ghi thứ Ba; nhập lại không cộng lần hai; sửa/hủy không làm mất các buổi khác.

Hoàn thành khi: phân biệt rõ đổi ngày với lễ cộng bổ sung, số chuyên cần trên web và Excel khớp, không tính hai lần một lượt đi lễ.

## Đợt 3 — Thêm thiếu nhi và quản lý nhập học

- [x] 3.1 Thêm form chọn lớp, tên thánh/họ tên, ngày nhập học và thông tin gia đình; kiểm tra trường bắt buộc, ngày và sức chứa 40 em của mẫu hiện tại.
- [x] 3.2 Cho dùng mã đã được cấp trước. Chỉ đề xuất mã mới theo quy tắc đã xác minh từ danh sách hiện tại; kiểm tra trùng toàn bộ các lớp và lịch sử trước khi lưu, không tái cấp mã của em nghỉ học.
- [x] 3.3 Xem trước dòng đích và những sheet sẽ cập nhật; kiểm tra công thức liên kết theo mã, không chỉ ghi vào một sheet.
- [x] 3.4 Ghi trên bản làm việc, kiểm tra danh sách/lý lịch/tháng/học kỳ/tổng kết, VBA và bảo vệ sheet rồi mới thay file; cập nhật lại catalog và dữ liệu điểm đã lưu.
- [x] 3.5 Cho xem/sửa ngày nhập học của em hiện có; báo ảnh hưởng đến chuyên cần/học kỳ, chặn thay đổi làm mất hoặc vô hiệu hóa dữ liệu đã ghi nếu chưa có cách xử lý được duyệt.
- [x] 3.6 Sau khi lưu thành công, em xuất hiện trên web, quét QR nhận đúng thông tin và in được thẻ; không tính vắng trước ngày nhập học.
- [x] 3.7 Kiểm thử lớp đầy, mã trùng, hai phiên cùng tạo mã, file khóa, hàng đã sắp xếp, lỗi giữa quá trình và phục hồi.

Hoàn thành khi: tiếp nhận một em hoàn toàn qua web mà các sheet vẫn liên kết đúng và không sửa dữ liệu của em khác.

## Đợt 4 — Quản lý cấu hình từ OPTION và ngưỡng tổng kết

- [x] 4.1 Lập danh mục cấu hình có thể sửa: lịch lễ/giáo lý theo khối, tháng thuộc HKI/HKII, số buổi cho phép nghỉ và ngưỡng đạt trong `Tổng kết`. Ghi rõ cấu hình nào riêng từng lớp, cấu hình nào dùng chung.
- [x] 4.2 Tạo màn hình đọc cấu hình thực tế, giải thích tác dụng và chỉ cho sửa các ô nhập đã xác định; không mở sửa tùy ý công thức.
- [x] 4.3 Xem trước lịch và kết quả sẽ đổi trên từng lớp. Giữ quy định đã thống nhất: giáo lý/lễ sớm Chủ Nhật, đổi lễ chỉ thứ Hai–thứ Bảy cùng tuần.
- [x] 4.4 Với thay lịch đang có dữ liệu: liệt kê ngày bị mất, X/P/O, buổi đã chốt và đơn liên quan; chặn thay đổi làm mất lịch sử. Ưu tiên áp dụng cho năm mới khi không thể giữ dữ liệu năm hiện tại.
- [x] 4.5 Sao lưu toàn bộ phạm vi, kiểm tra và ghi theo giao dịch có journal/rollback khi áp dụng nhiều lớp; tính lại, làm mới catalog và xử lý nhất quán dữ liệu điểm trong database.
- [x] 4.6 Kiểm thử thay học kỳ, ngưỡng đạt, lịch lễ, xung đột đơn, file bị sửa ngoài và lỗi khi đang cập nhật nhiều lớp.

Hoàn thành khi: chỉnh các cấu hình đã hỗ trợ trên web tạo kết quả giống chỉnh các ô tương ứng trong Excel, giữ được dữ liệu đã ghi.

## Đợt 5 — Ghi chú và báo cáo in

- [x] 5.1 Kiểm tra bố cục, mục đích và giới hạn sheet `Ghi Chú`; tách ghi chú chung của sổ với nhật ký chăm sóc theo em.
- [x] 5.2 Chọn vùng ghi an toàn trong mẫu để xuất ghi chú; nếu mẫu không phù hợp, đề xuất sheet xuất riêng và thống nhất trước khi thay cấu trúc. Không ghi đè ghi chú hiện có, không âm thầm lưu dữ liệu web vào vùng tùy ý.
- [x] 5.3 Cho xem/sửa ghi chú chung, giữ lịch sử; xuất nhật ký chăm sóc theo bộ lọc và xác định rõ dữ liệu nào có trong Excel, dữ liệu nào chỉ nằm trong bản sao lưu đầy đủ.
- [x] 5.4 Làm bản in danh sách lớp, chuyên cần tháng/học kỳ/năm, bảng điểm và tổng kết; tên giáo xứ/lớp/năm học, ngày xuất, lặp tiêu đề và ngắt trang hợp lý.
- [x] 5.5 Hỗ trợ in/Lưu PDF từ trình duyệt; kiểm tra tiếng Việt, A4, bảng nhiều trang và hiển thị trên điện thoại. File `.xlsm` tiếp tục giữ bố cục gốc.

Hoàn thành khi: người dùng biết chính xác ghi chú được lưu ở đâu và có báo cáo đọc/in được mà không phải chỉnh bố cục Excel thủ công.

## Đợt 6 — Thao tác hàng loạt và nghiệm thu

- [x] 6.1 Đối chiếu từng macro trong mẫu với kết quả cần đạt: điểm danh tháng, điểm danh hàng loạt, thêm điểm, khôi phục vùng nhập. Ghi rõ phần đã được web thay thế và phần còn cần thao tác riêng.
- [x] 6.2 Nếu còn nhu cầu nhập hàng loạt: cho dán danh sách mã/trạng thái/ngày hoặc nhiều dòng điểm, xem trước lỗi và phạm vi; tái sử dụng quy tắc ghi hiện tại, không chạy macro tùy ý.
- [x] 6.3 Với vùng `DiemDanhAuto`, cung cấp thao tác xóa/khôi phục vùng nhập riêng nếu cần; không gọi nhầm chức năng phục hồi toàn bộ bản sao lưu.
- [x] 6.4 Nghiệm thu một vòng trên sổ sao chép: thêm em → cập nhật hồ sơ → điểm danh/đổi lễ → chốt → nhập điểm → tổng kết → tải Excel/in → sao lưu/phục hồi.
- [x] 6.5 Kiểm tra cả 20 mẫu lớp, công thức/VBA/bảo vệ sheet, bảng điểm có sẵn khi mở file với macro tắt, sửa Excel bên ngoài và dữ liệu web sau khởi động lại.
- [x] 6.6 Cập nhật hướng dẫn và bảng đối chiếu Excel–web; chỉ đánh dấu tính năng đã có khi mã và kiểm thử liên quan hoàn tất. Các mục phụ thuộc quy tắc chưa rõ vẫn để chờ.

Hoàn thành khi: các thao tác được chọn từ sổ Excel có luồng web rõ ràng, không còn phải đoán một nút web tương đương macro nào.

## Thứ tự thực hiện và giới hạn

1. Tổng kết năm trước vì bộ tính đã có, chủ yếu bổ sung dữ liệu trả về và giao diện.
2. Chốt ý nghĩa lễ bù trước khi cho ghi cột O; phần này có thể chờ xác nhận trong khi tiếp tục làm quản lý nhập học.
3. Thêm thiếu nhi và ngày nhập học.
4. Cấu hình, ghi chú/báo cáo, rồi thao tác hàng loạt và nghiệm thu toàn bộ.

Không tự kích hoạt năm mới, đổi quy tắc phụng vụ, cấp lại mã cũ hoặc thay đổi dữ liệu sản xuất trong giai đoạn lập kế hoạch. Các nghiệp vụ ngoài điểm tiếp tục cần Bridge Windows/Excel; kế hoạch này không tự làm web truy cập được qua 4G.

## Kết quả nghiệm thu ngày 13/10/2026

- 84 kiểm tra Python và 12 kiểm tra JavaScript đạt.
- Tổng kết đầy đủ của 20 mẫu lớp tính được, không có lỗi công thức trong dữ liệu nền. Đối chiếu 2.818 ô mỗi lượt với Excel desktop qua HK1/HK2/tổng kết, hàng đã sắp xếp và nhập học muộn.
- Giao diện trên sổ sao chép: thêm em, ghi chú, cộng/hủy lễ bổ sung, cấu hình, nhập điểm nhiều dòng, tìm tổng kết, tải Excel và bốn báo cáo in. Kiểm tra 320/375/768/1440 px, hộp thoại và bàn phím, không có lỗi JavaScript.
- Excel native trên bản sao: thêm em sau khi sắp xếp bảng, giữ điểm của em khác, sửa tháng nhập học, cấu hình nhiều lớp, từ chối mất lịch sử, phục hồi vùng nhập và rollback cả Excel/SQLite khi thay file lỗi.
- Bộ năm mới xóa điểm/chuyên cần/lễ bổ sung và giữ mã đã cấp của em tốt nghiệp. Kiểm tra hồi quy chuyển lớp, sao lưu/khôi phục và tạo năm học mới đạt.
- SHA-256 của 20 sổ sản xuất không đổi trong kiểm thử. Chưa đổi năm học thật, chưa triển khai hosting/MySQL/Drive/tài khoản.
- Quy tắc đã xác nhận: cột Đi Lễ Bù cộng lễ bổ sung ngoài lịch; đổi ngày vẫn ghi X ngày gốc. Ghi chú chung dùng vùng có sẵn, không cần tạo sheet mới; nhật ký chăm sóc xuất CSV riêng. Điểm danh hàng loạt nhập X, P/O và buổi chốt điều chỉnh riêng có lý do.
