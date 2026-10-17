# Kết quả triển khai UI/UX

Ngày: 13/10/2026. Phạm vi: trải nghiệm giáo lý viên trong ứng dụng hiện tại; giữ quy tắc nghiệp vụ và cơ chế ghi sổ.

## Thay đổi đã triển khai

- **Tìm thiếu nhi:** tìm tên có/không dấu và các phần tên, mã thẻ hoặc thông tin liên lạc; giữ từ khóa qua xem hồ sơ, chuyển trang và làm mới giao diện. Không có kết quả thì có nút xóa từ khóa hoặc tìm trong tất cả lớp. Liên kết gọi phụ huynh có nhãn rõ và vùng bấm lớn hơn.
- **Điểm danh:** chọn quét camera hoặc nhập mã/tìm tên; nhớ phương thức trên thiết bị. Kết quả nhận diện nằm trong nội dung trang, có tên thánh, họ tên, mã, lớp và nút đóng; không che camera hoặc ô nhập. Máy quét USB/người nhập tay được trả focus về ô mã sau khi ghi nhận. Bảng buổi và bước kiểm tra trước chốt vẫn được giữ.
- **Nhập điểm từng em:** tìm tên/mã cả ở học kỳ; nhớ loại điểm; thêm “Lưu và nhập em tiếp theo”. Chỉ chuyển em sau khi lưu được và sổ không còn chờ cập nhật. Enter trong ô điểm thực hiện lưu thường. Điểm sai có thông báo cạnh ô và giữ nội dung.
- **Nhập cùng loại điểm:** nhập cho nhiều em trên một màn hình, hỗ trợ Enter sang em tiếp theo và Tab theo thứ tự tự nhiên; lưu các dòng thay đổi bằng API hiện tại. Bản nháp giữ trong bộ nhớ khi chuyển trang/loại điểm. Phiên cũ bị từ chối; có luồng đọc điểm mới, đối chiếu và xác nhận giữ các ô đã nhập trước khi lưu tiếp. Trong khi ghi, các ô đang lưu được khóa để tránh mất lượt nhập mới.
- **Kết nối:** tự thử lại với thời gian chờ tăng dần; banner giữ màn hình và bản nháp. Phiên hết hạn có ô nhập mã kết nối. Không tự gửi lại thao tác ghi. Với lượt điểm mất phản hồi, đọc lại và so khớp các điểm đã gửi để thông báo đã ghi nhận hoặc còn cần xử lý.
- **Trang bắt đầu:** giữ bốn công việc chính, thêm việc đang cần xử lý từ dữ liệu của lớp: tiếp tục buổi hôm nay, lịch lễ bù đến hạn và chăm sóc đến hẹn. Đơn chờ duyệt vẫn có lối mở nhanh.
- **Tải sổ:** hiển thị lớp và năm học của sổ; tiếp tục dùng file `.xlsm` và tên file lớp thật.
- **Giao diện điện thoại:** thống nhất tiêu đề, nút và khoảng cách theo token có sẵn; thông báo ngắn đặt trên thanh điều hướng; giữ focus/ô nhập khỏi bị thanh dưới che. Không thêm animation.

Bản nháp điểm nằm trong bộ nhớ của trang, không lưu điểm/hồ sơ vào localStorage. Bản nháp chưa lưu sẽ mất nếu tải lại hoặc đóng trang; lựa chọn lớp, loại điểm và phương thức quét được nhớ trên thiết bị.

Chế độ nhập cùng loại điểm dùng mã phiên bản của bộ tính portable hiện tại. Khi bảng điểm không có mã phiên bản, giao diện giữ cách nhập từng em và ẩn chế độ nhập cột để tránh đưa ra khả năng chống ghi đè mà backend chưa hỗ trợ.

## Kiểm tra

- `npm run build`: đạt, đã cập nhật bundle JavaScript/CSS trong `dist`.
- `npm test`: 20 kiểm thử JavaScript đạt, gồm tìm tiếng Việt, P/0/trống, việc đến hạn đúng lớp/ngày và đối chiếu lượt ghi mất phản hồi.
- `tests/ux-workflows.test.mjs`: đạt trên Bridge dùng một sổ sao chép có 22 em. Kiểm tra tìm kiếm và giữ ngữ cảnh; lưu rồi chuyển em; loại điểm được nhớ; nhập cột; P/0; giữ các loại điểm khác; xung đột phiên và đối chiếu; mất mạng; mất phản hồi sau server commit; điểm danh và focus.
- 12 trang × 5 chiều rộng 320/375/414/768/1440px: không tràn ngang ở cấp trang, không ghi nhận lỗi JavaScript. Có kiểm tra chữ lớn và viewport ngang 844×390px.
- Đã xem ảnh giao diện máy tính/điện thoại và sửa vị trí toast để không che thanh điều hướng.
- Kiểm tra bổ sung: nhập cột sai có lỗi cạnh ô; lượt nhập cột đã commit nhưng mất phản hồi được xác nhận bằng đọc lại, chỉ một yêu cầu ghi; Enter lưu thường; tải đúng lớp/năm học/tên `.xlsm`; ô mã sau quét có focus và nằm trên thanh điều hướng.
- Đo tương phản chữ trên nút chọn phương thức quét, ô mã và chi tiết nhận diện: tối thiểu 11,61:1 trong các phần tử được đo. Kết quả này không đại diện toàn bộ ứng dụng.
- Mô phỏng HTTP 401 khi đang nhập điểm: hộp kết nối native mở trên hộp điểm, giữ bản nháp, có thể đóng/mở lại và không tự gửi lại lượt ghi. Kiểm tra dữ liệu không có mã phiên bản: cách nhập từng em vẫn có, chế độ nhập cột được ẩn. Đây là kiểm tra UI bằng phản hồi mô phỏng, không phải nghiệm thu xác thực LAN thật.
- SHA-256 sổ gốc dùng để tạo QA được đối chiếu trước/sau; các lượt ghi thử và file tải chỉ nằm trong thư mục QA riêng. Dịch vụ QA được dừng sau kiểm tra.

Không chạy lại toàn bộ Python suite trong vòng UI này; backend Python không thay đổi. 84 kiểm thử Python đã đạt trong đợt rà soát trước.

Chưa thử camera/USB, bàn phím ảo trên điện thoại thật hoặc quan sát giáo lý viên thực tế. Bước nghiệm thu sử dụng vẫn cần làm tại giáo xứ; kiểm tra trình duyệt không thay thế đánh giá đó.

## Chạy và kiểm thử lại

Ứng dụng trên máy dùng `dist` mới sau khi tải lại trang. Nếu dịch vụ chưa chạy, mở PowerShell trong thư mục dự án rồi chạy:

```powershell
./Start-DiemDanh.ps1
```

Kiểm tra build và unit:

```powershell
npm run build
npm test
```

Kiểm tra luồng ghi chỉ trên Bridge riêng có thư mục dữ liệu sao chép chứa `ux-qa-` trong đường dẫn:

```powershell
$env:XUAN_HOA_QA_URL = 'http://localhost:<cổng-QA>'
npm run test:ux
```

Test từ chối ghi nếu `/api/system` không xác nhận thư mục QA. Không trỏ lệnh này vào dịch vụ sản xuất. Có thể đặt `PLAYWRIGHT_MODULE` để chỉ định Playwright trên máy khác.
