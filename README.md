# Điểm danh Giáo Xứ Xuân Hoà

Mã nguồn ngày 25/10/2026 bổ sung tải hồ sơ theo lớp GLV phụ trách, bộ lọc dữ liệu trong file Excel, báo cáo và các cải tiến bảo mật/UX. Xem [ghi chú phiên bản](RELEASE-2026-10-25.md).

GLV được tải riêng từng lớp đang phụ trách và cần xác thực gần đây. Ghi chú trong file lấy từ ghi chú đã lưu riêng cho lớp trên ứng dụng. Bản ZIP backup rõ không còn tải từ web; sao lưu mã hóa dùng công cụ vận hành riêng. Các hướng dẫn ZIP cũ bên dưới được thay thế bằng chính sách này.

## Phạm vi mã nguồn trên GitHub

Kho này chứa mã nguồn frontend, backend cloud, cầu nối Excel, script vận hành, tài nguyên giao diện và tài liệu của dự án. Theo yêu cầu, không đưa bộ test vào kho này. Các lệnh npm dành riêng cho test cũng được bỏ khỏi bản công khai.

Không đưa `.env` thực, mật khẩu đã cấp, cơ sở dữ liệu, sổ Excel, danh sách thiếu nhi, hồ sơ phân công riêng hoặc kết quả kiểm thử lên GitHub. Cấu hình kết nối theo `.env.cloud.example` hoặc `.env.example`; dữ liệu vận hành được nhập riêng theo hướng dẫn triển khai bên dưới.

Script `scripts/grant-parish-admins.py` đọc danh sách người cần cấp quyền từ `.local/parish-admin-targets.json`. File riêng này là mảng các cặp `["Họ tên dân sự", "Tên thánh và họ tên đầy đủ"]`; chuẩn bị theo nhân sự thực tế trước khi chạy. Bản công khai không chứa tên người thật trong danh sách cấp quyền.


## Bản cloud Vercel + Supabase

Địa chỉ dùng thử: **https://giao-xu-xuan-hoa.vercel.app**. Bản này chạy độc lập máy Windows, lưu dữ liệu và sổ riêng tư trong PostgreSQL; dùng tài khoản, mã QR và phân quyền hiện có. Xem [hướng dẫn vận hành cloud](VERCEL-SUPABASE-SETUP.md).

Sau khi chuyển dữ liệu, nhập liệu tại địa chỉ cloud. Các hướng dẫn Windows/Excel bên dưới dành cho bản localhost cũ, có dữ liệu độc lập và không tự đồng bộ với cloud.

Điểm danh cloud hỗ trợ giữ lượt quét khi mất mạng và tải lại trang, tự đồng bộ khi kết nối lại. Mở buổi hôm nay khi có mạng để chuẩn bị; lượt chờ chưa được tính có mặt. Mục **Sinh nhật & bổn mạng** xem theo lớp/tuần/tháng; ngày bổn mạng nhập và xác nhận trong hồ sơ. Xem [hướng dẫn hai chức năng](OFFLINE-AND-CELEBRATIONS.md).

## Quản trị hệ thống và truy cập từ xa

Admin có mục **Quản trị hệ thống**: tạo/đổi tên/lưu trữ lớp, nhập hồ sơ Excel/CSV/TSV có xem trước, hồ sơ và lịch sử phân công GLV, nhật ký thao tác có lọc/xuất, xem lịch sử và chuyển năm làm việc. **Thông báo & nhắc việc** lọc theo các lớp được giao cho từng GLV.

Bản sao mới gồm tài khoản và phân quyền, dữ liệu năm hiện tại, các năm đã kích hoạt và bộ năm đã chuẩn bị. Khôi phục tài khoản cần xác nhận riêng; khôi phục dữ liệu lớp giữ nguyên mật khẩu. Xem [hướng dẫn 7 nhóm quản lý](MANAGEMENT-FEATURES.md) và [chuẩn bị HTTPS qua 4G](REMOTE-ACCESS.md).

Web đọc danh sách và mã QR thực tế từ 20 file `.xlsm` trong thư mục dữ liệu. Quét thành công hiển thị tên thánh, họ và tên, lớp, mã số; đánh dấu `X` đúng ngày/hoạt động, chạy macro điểm danh của mẫu, lưu lại file lớp. Không sử dụng danh sách hay lượt điểm danh giả lập.

## Mở trên máy tính

Cần Windows, Microsoft Excel bản desktop và Python. Máy này đã có các thư viện cần thiết. Khi chuyển máy, cài một lần:

```powershell
python -m pip install -r excel_bridge/requirements.txt
```

Trong thư mục dự án này, chạy:

```powershell
./Start-DiemDanh.ps1
```

Mở `http://localhost:8765`. Chọn ngày, hoạt động và phạm vi lớp trước khi quét. Dịch vụ phải chạy trên máy có Excel; bản web được lưu trữ trực tuyến mở màn hình kết nối và dẫn về dịch vụ này. Excel/VBA không chạy trực tiếp trên hosting.

Máy quét USB: đặt con trỏ vào ô **Mã thiếu nhi**, quét thẻ rồi Enter. Camera: bấm **Bật camera**, cấp quyền và đưa QR trên thẻ vào khung. Có thể chọn ảnh QR chụp từ thẻ. Các mã trong `Print Thẻ ALL.pdf` được tra cứu nguyên trạng, ví dụ `XH22008`.

## Điện thoại cùng Wi-Fi

Dừng chế độ máy tính trước, rồi mở chế độ HTTPS:

```powershell
./Start-DiemDanh.ps1 -Stop
./Start-DiemDanh.ps1 -Lan
```

Trình khởi động hiển thị địa chỉ `https://<IP-máy-Excel>:8765`. Cài chứng chỉ `.local/bridge/tls/XuanHoa-Certificate.cer` trên thiết bị, bật tin cậy chứng chỉ rồi mở địa chỉ và đăng nhập bằng tài khoản cá nhân do Admin cấp. iPhone cần bật tin cậy trong phần Certificate Trust Settings sau khi cài hồ sơ. Camera điện thoại chỉ hoạt động khi trang có HTTPS được thiết bị tin cậy. Nếu IP của máy thay đổi, khởi động lại; dịch vụ sẽ cấp lại chứng chỉ phù hợp và cần cài lại chứng chỉ mới.

Nếu Windows Firewall chặn, cho phép Python truy cập mạng **Private** hoặc mở TCP 8765 cho mạng riêng. Không cần mở cổng trên router. Chế độ mặc định chỉ lắng nghe trên máy tính; chế độ LAN yêu cầu đăng nhập, chặn yêu cầu từ website khác và giới hạn số lần nhập sai mã. Phiên kết nối điện thoại hết hạn sau 12 giờ.

## Dữ liệu, ghi Excel và tải về

- File gốc Thiếu Nhi 1B ở thư mục dữ liệu, 19 file còn lại ở `outputs/cac-lop-2026-2027`. Có thể chuyển cả thư mục sang OneDrive/Google Drive được đồng bộ về máy và chỉ định `-DataRoot 'đường-dẫn-thư-mục'`. File phải có sẵn trên máy, không ở trạng thái chỉ lưu trên đám mây.
- Đọc tên thánh từ cột **Tên Thánh, Họ** và tên từ cột **Tên**. Giữ nguyên cách viết trong nguồn; tên thánh thiếu không được tự bịa thêm. Lịch ngày lấy từ hàng 7 của từng tháng trong từng file. Học sinh nhập học muộn chỉ điểm danh từ tháng nhập học.
- Khi quét camera, chọn ảnh QR hoặc nhập mã, bong bóng hiển thị mã số, tên thánh, họ tên và lớp lấy từ Excel thật. Thông báo phân biệt đã nhận diện/đang lưu, đã lưu, quét trùng và chưa ghi nhận; có nút đóng và không tự biến mất. Kết quả vẫn nằm trong bảng thông báo của buổi. Camera giữ một thẻ liên tục chỉ nhận diện một lượt; đưa thẻ ra rồi quét lại để thử lại hoặc kiểm tra trùng. Danh sách và hồ sơ được cập nhật trên web theo chu kỳ 15 giây khi trang đang mở và không có thao tác ghi/hộp thoại.
- Mã học sinh là khóa tra cứu. Khi ghi điểm danh, lý lịch hoặc điểm học kỳ, dịch vụ tìm lại mã ngay trên sheet đích; mã thiếu hoặc trùng bị từ chối trước khi lưu. File đang mở/chỉ đọc, macro thay đổi hoặc lịch không hợp lệ sẽ bị từ chối.
- Mã nguồn VBA gốc được kiểm tra trước khi mở và sau khi lưu bản làm việc. Dịch vụ chạy macro `Module1.Diemdanhauto_…` bằng Excel COM khi điều kiện trong file cho phép; `vbaExecuted` chỉ là true khi macro thực sự được gọi. Macro này vốn điền `O` cho cả tháng, nên dịch vụ khôi phục các ô không được yêu cầu trước khi lưu. Chỉ **Chốt buổi** mới ghi `O` cho các em chưa điểm danh trong buổi đó. Nếu chốt nhiều lớp bị gián đoạn, bấm lại để tiếp tục các lớp chưa chốt. Lưu hồ sơ, điểm và GLV tính lại công thức bằng Excel, không chạy macro điểm danh.
- Mỗi thay đổi được xử lý lần lượt. Sau khi kiểm tra và lưu bản làm việc, dịch vụ sao lưu và thay file lớp bằng thao tác nguyên tử. Không thay đổi thiết lập bảo mật macro của Excel đang dùng; chỉ phiên Excel riêng mở các macro đã được kiểm tra.
- Điểm danh, hồ sơ, điểm và GLV dùng chung cơ chế staging: khôi phục bảo vệ sheet cùng quyền sắp xếp/lọc, kiểm tra ô đã ghi, kiểm tra VBA và mã băm file gốc trước khi thay thế. Nếu file gốc thay đổi trong lúc xử lý, bản làm việc bị từ chối để giữ thay đổi bên ngoài. Số điện thoại được lưu dạng văn bản để giữ số 0 đầu; ngày sinh/rửa tội chấp nhận dd/mm/yyyy hoặc yyyy-mm-dd.
- Điểm được kiểm tra ở cả API và bộ ghi Excel: từ 0 đến 10, P (nghỉ phép theo công thức mẫu), hoặc để trống; không chấp nhận số âm, NaN/Infinity, mã sai lớp, mã trùng hay quá 20 cột khảo bài. Một dòng lỗi làm cả lượt cập nhật bị từ chối trước khi mở Excel.

- Đi lễ sớm quét trực tiếp đúng Chủ Nhật đang diễn ra trong khung 06:00–06:20. Nhập tay trong khung giờ được ghi bình thường; ngoài khung giờ cần người quản lý trên máy Excel xác nhận giờ đi thực tế, tên và lý do. Không ghi nhận một thời điểm tương lai. Chỉnh có mặt qua bảng điểm danh cũng áp dụng quy định này.
- Theo dõi chuyên cần và lịch sử tổng hợp trực tiếp X/P/O từ các sheet tháng, không phụ thuộc các phiên đã mở trên web. Có thể chọn cả năm học hoặc từng tháng; ô trống chưa tính là vắng, em chưa có dữ liệu hiển thị riêng. Lễ bù tính về ngày gốc trong Excel; lịch sử hiển thị thêm ngày đi thực tế. Bảng tổng kết hiển thị điểm chuyên cần lễ/giáo lý theo thang của mẫu, không gọi nhầm là số buổi.
- Sao lưu trước mỗi lần ghi tại `.local/bridge/backups/<mã-lớp>/`. Nhật ký lượt ghi và buổi điểm danh tại `.local/bridge/attendance.sqlite3`. Excel là nguồn trạng thái chính, kể cả dữ liệu được sửa trực tiếp bên ngoài web. Web cập nhật lại mỗi 15 giây.
- Tải từng lớp trả về đúng file `.xlsm` cả năm học với đầy đủ sheet, công thức và VBA. Tải tất cả trả về ZIP các file lớp. Không tạo bản `.xlsx` rút gọn. Giờ quét được lưu trong nhật ký dịch vụ, không thêm cột vào mẫu Excel.
- Mã trùng `X` không ghi lại và không chạy macro lại. Nếu đã có `P` hoặc `O`, giáo lý viên cần chỉnh trạng thái thủ công. Chốt lớp khóa ngày/hoạt động ở mọi phạm vi buổi.

Giữ máy Excel và dịch vụ đang chạy khi điểm danh bằng điện thoại. Chế độ hiện tại phục vụ cùng mạng Wi-Fi; truy cập từ mạng khác và đồng bộ trực tiếp qua API OneDrive/Google Drive chưa được triển khai.

## Nhập điểm và tải Excel có sẵn kết quả

Bộ tính điểm mặc định là **portable**: nhập điểm trên web, lưu, rồi chọn **Tải Excel lớp đang xem** ngay trong Bảng điểm. Trung bình HK, xếp loại, xếp hạng, điểm chuyên cần và tổng kết năm đã có giá trị trong file tải xuống; không cần bấm “Thêm điểm”, chạy VBA hoặc tính lại thủ công. Các lượt tải tại File Excel cũng chuẩn bị kết quả điểm trước khi xuất.

- Server đọc và tính chính các công thức của mẫu, không áp dụng hệ số phỏng đoán. Cột khảo bài/kiểm tra được kích hoạt theo dữ liệu của cả lớp, nên thay một em sẽ tính lại cả lớp và hạng. Hệ số kiểm tra, điều kiện nhập học, quy tắc P/trống/0, xếp loại và tổng kết năm đều theo file thật. Xếp hạng dùng điểm chưa làm tròn.
- Bộ ghi cập nhật ô nhập và giá trị kết quả đi kèm công thức trong gói `.xlsm`; không lưu lại workbook bằng openpyxl. Công thức, VBA, hình ảnh, controls, styles và các phần ngoài worksheet được giữ. Phần VBA nhị phân được đối chiếu SHA-256, ngoài kiểm tra mã nguồn VBA đang có. Công thức được giữ để Excel desktop tiếp tục tính khi người dùng sửa trực tiếp.
- Kết quả trên web và giá trị có sẵn trong file dùng cùng một bộ tính. Hàm ngoài tập đã kiểm thử bị từ chối; lỗi thực sự như `#DIV/0!` được hiển thị và lưu đúng dạng lỗi, không biến thành 0. Ví dụ nếu một em có toàn bộ cột khảo bài là P, mẫu có thể chia cho 0; cần đối chiếu đầu điểm/hệ số thay vì báo một điểm giả.
- Điểm và kết quả được lưu vào database trước khi cập nhật file, kèm lượt chờ xuất bền vững. Nếu file đang mở, web báo **đã lưu điểm, Excel chờ cập nhật**. Đóng file rồi tải lại để hoàn tất. Lượt tải không trả về file cũ khi còn điểm chờ. File bị sửa ngoài trong thời gian này được giữ, bản chờ không tự ghi đè; người quản lý có thể xác nhận giữ file hiện tại, lưu bản chờ ở `.local/bridge/grade-conflicts/` để đối chiếu/nhập lại.
- Mỗi lớp có khóa ghi và mỗi bảng điểm có mã phiên bản. Một phiên web cũ không được ghi đè điểm vừa sửa ở phiên khác; bấm Làm mới bảng điểm để đọc bản mới. Mỗi lần thay Excel vẫn có backup và kiểm tra file gốc thay đổi bên ngoài.

Phần **điểm** không dùng Excel COM/VBA. Các thao tác điểm danh, hồ sơ, GLV, chuyển lớp và tạo năm mới hiện vẫn dùng Bridge Windows. Hosting công khai, chuyển toàn bộ nghiệp vụ sang MySQL và truy cập qua 4G chưa được triển khai chỉ bằng thay đổi phần điểm này.

Nếu cần quay lại bộ tính qua Excel desktop, dừng dịch vụ rồi chạy `./Start-DiemDanh.ps1 -GradeEngine native`. Mặc định là `-GradeEngine portable`.

### Lưu điểm vào MySQL khi đã có hosting

Hiện chưa cấu hình MySQL theo lựa chọn của người dùng; điểm được lưu cùng SQLite hiện tại, không dùng dữ liệu giả lập. Adapter MySQL dành cho phần điểm đã có, nhưng chưa được xác nhận với một server MySQL thật.

Thiết lập các biến môi trường server trong `.env.example`: `XH_MYSQL_HOST`, `XH_MYSQL_PORT`, `XH_MYSQL_DATABASE`, `XH_MYSQL_USER`, `XH_MYSQL_PASSWORD`, và CA khi nhà cung cấp yêu cầu TLS. Không đưa mật khẩu vào giao diện. File `.env.example` chỉ là hướng dẫn, không tự nạp biến môi trường. Khi có `XH_MYSQL_DATABASE`, bộ lưu dùng MySQL/InnoDB/utf8mb4 và không tự quay về SQLite nếu kết nối lỗi.

Ba bảng riêng cho điểm: `xh_grade_books` (đầu điểm/kết quả cả hai HK và tổng kết, tách theo năm học/lớp), `xh_grade_changes` (lượt sửa), `xh_grade_jobs` (file chờ xuất để tiếp tục sau khi khởi động lại). Đơn từ, lịch hằng tuần, ghi chú và buổi điểm danh vẫn dùng SQLite trong giai đoạn này. File `.xlsm` vẫn phải nằm trên ổ lưu bền vững của server; sao lưu MySQL và file Excel riêng khi triển khai MySQL.

Nhập dữ liệu điểm thật từ tất cả file lớp vào database đang chọn, không thay file Excel và không ghi đè các lớp đã có trong database:

```powershell
python -X utf8 excel_bridge/import_grade_data.py --root 'D:/GiaoLy/DiemDanh-ThieuNhi' --state-dir '.local/bridge'
```

Kiểm thử trên bản sao:

```powershell
python -X utf8 -m unittest discover -s tests -p test_portable_grades.py -v
python -X utf8 tests/native_grade_calculation_comparison.py
```

Kiểm thử trình duyệt `tests/portable-grades-ui.test.mjs` yêu cầu `XUAN_HOA_QA_URL` trỏ tới Bridge riêng dùng **file sao chép**. Không chạy ca nhập điểm thử trên dữ liệu sản xuất.

## Xin phép và đổi ngày Thánh lễ

Mở **Xin phép & đổi lễ**, hoặc bấm **Xin phép / Đổi lễ** ngay ở dòng học sinh. Chọn học sinh, ngày gốc, hoạt động, lý do và tên người nhập. **Gửi chờ duyệt** giữ đơn để xử lý sau; **Lưu và duyệt** duyệt ngay theo thông tin đã nhập. Tên người xử lý được nhập và ghi nhật ký, chưa phải tài khoản riêng cho từng giáo lý viên.

- Nghỉ phép có thể áp dụng cho Thánh lễ, giáo lý, cả hai hoặc đi lễ sớm. Duyệt hoạt động nào thì ghi P cho hoạt động đó. Cả hai được xử lý chung; nếu ghi Excel bị gián đoạn, mục đã duyệt được giữ và lần duyệt tiếp theo chỉ xử lý mục còn chờ.
- Đổi ngày chỉ áp dụng cho Thánh lễ. Cả ngày gốc và ngày thay thế phải trong cùng tuần **thứ Hai đến thứ Bảy**, khác nhau; **Chủ nhật không được đổi và không được dùng làm ngày bù**. Ngày gốc phải có trong lịch Excel của lớp. Ngày bù có thể không có cột trong Excel.
- Sau khi duyệt đổi lễ, ô ngày gốc giữ trống và web hiện **Chờ lễ bù**. Chốt buổi gốc không ghi O cho em đó. Mở buổi Thánh lễ vào ngày đã hẹn, quét thẻ: web tự ghi X vào ngày gốc, lưu ngày đi thực tế và chạy VBA. Có thể quét lễ bù dù buổi gốc đã chốt.
- Quét đúng ngày thay thế sẽ tự áp dụng đơn đổi lễ đã duyệt và ghi X vào ô ngày gốc, kể cả khi ngày thay thế cũng có lễ theo lịch lớp. Ví dụ đổi từ thứ Ba sang thứ Hai: quét vào thứ Hai ghi X cho thứ Ba; nhật ký giữ ngày đi thực tế là thứ Hai. Không có đơn đã duyệt khớp ngày quét thì không tự suy ra lễ bù từ các ô trống trong tuần. Một lượt quét không được cộng cho hai buổi; lượt quét lại không được chuyển sang một nghĩa vụ khác. Em đến đúng ngày gốc thì lịch bù được hoàn thành tại ngày gốc và không còn chờ quét ngày thay thế.
- Khi **Chốt buổi lễ bù**, em chưa quét được ghi O vào ngày gốc. Trang quản lý đơn có nút **Chốt lễ bù đến hôm nay** để xử lý các lịch bù đã đến hạn. Đây là thao tác xác nhận sau khi buổi bù kết thúc; dịch vụ không tự chạy nền để đánh vắng theo giờ. Các đơn quá ngày hẹn vẫn hiển thị để giáo lý viên chốt.
- Trước khi chốt, web cho xem số có mặt, nghỉ phép, chờ lễ bù và sẽ đánh vắng. Đơn chưa duyệt phải được duyệt hoặc từ chối trước khi chốt. Nếu chốt nhiều lớp bị gián đoạn, các lớp đã lưu giữ kết quả và có thể bấm lại để tiếp tục.
- **Lịch sử** của đơn lưu đầy đủ lần lập, duyệt, từ chối, huỷ và quét. Sau khi chốt, chỉ người thao tác trực tiếp trên máy Excel qua localhost được sửa từng em hoặc xử lý đơn bổ sung, có tên và lý do bắt buộc. Kết nối điện thoại qua LAN có thể lập / duyệt đơn trước khi chốt, không được sửa buổi đã chốt. Quyền hiện tại phân biệt máy Excel với thiết bị LAN; phân quyền bằng tài khoản riêng chưa được triển khai.
- Huỷ phép đã duyệt trả trạng thái về trống nếu buổi còn mở, hoặc O nếu đã chốt. Điều chỉnh thủ công sẽ huỷ đơn liên quan để không còn một lịch bù chờ sai trạng thái. Không được dùng quét lại để ghi đè một lượt đã được điều chỉnh.
- **Dời riêng buổi này** trên đơn đổi lễ đã duyệt giữ nguyên ngày đã xin và lưu thêm ngày ngoại lệ cho đúng buổi gốc. Ví dụ lễ gốc thứ Ba đã xin đi thứ Hai, riêng tuần này đi thứ Tư: quét thứ Tư ghi X cho thứ Ba; các đơn ở tuần sau vẫn giữ thứ Hai. Cả ngày gốc và ngày ngoại lệ phải cùng tuần, từ thứ Hai đến thứ Bảy. Lịch sử lưu ngày trước, ngày mới, người xác nhận và lý do.
- Trong hộp thoại ngoại lệ, chọn **Em đã đi lễ vào ngày này** để nhập bổ sung và ghi X ngay về ngày gốc; không chọn thì chỉ lưu ngày hẹn, chưa đánh có mặt. Không ghi X cho ngày tương lai. Đơn đã chốt vắng hoặc buổi đã chốt chỉ được người quản lý qua localhost xử lý có tên và lý do. Chốt lễ bù dùng ngày ngoại lệ hiện tại, không dùng ngày đã xin trước đó. Đơn đã hoàn thành không được dời tiếp hoặc cộng thêm lượt.

## Checklist và chức năng mở rộng

Danh sách chức năng hiện tại: [FUNCTIONS.md](FUNCTIONS.md). Các đợt hoàn thiện tương ứng sổ Excel: [DEVELOPMENT-PLAN-EXCEL-PARITY.md](DEVELOPMENT-PLAN-EXCEL-PARITY.md).

## Giao diện dễ dùng

Đợt cải tiến UI/UX mới: tìm tên không dấu và giữ từ khóa; nhớ loại điểm; **Lưu và nhập em tiếp theo**; **Nhập cùng loại điểm** có bản nháp và đối chiếu phiên mới; tự kết nối lại và kiểm tra lượt điểm mất phản hồi. Kết quả quét nằm trong nội dung trang để không che camera/ô nhập. Chi tiết và phạm vi kiểm thử: [UX-IMPLEMENTATION-2026-10-13.md](UX-IMPLEMENTATION-2026-10-13.md).

Trang mặc định `http://localhost:8765/#start` có bốn việc chính: điểm danh hôm nay, tìm thiếu nhi, nhập điểm và tải sổ lớp. Chọn lớp một lần để dùng trên các màn hình; giao diện dùng cỡ chữ mặc định. Điểm danh có bước kiểm tra trước khi kết thúc, đơn phép chia ba bước, điện thoại nhập từng loại điểm. Các thao tác quản lý khác nằm trong menu hoặc mục mở rộng.

Chi tiết thay đổi và kiểm thử: [USABILITY-CHANGES.md](USABILITY-CHANGES.md). Giao diện mới áp dụng cho bản chạy trên máy; trang giới thiệu giáo xứ vẫn ở `#home`.

Mục **Sổ lớp & báo cáo** trên máy Excel có tiếp nhận thiếu nhi, sửa tháng nhập học, ghi/hủy lễ bổ sung ngoài lịch, cấu hình một lớp/tất cả lớp, ghi chú thật trong sổ, nhập điểm/điểm danh hàng loạt, xóa/khôi phục vùng nhập DiemDanhAuto và các báo cáo In/Lưu PDF. Mỗi thao tác quản lý sổ có xem trước, người xử lý và lý do; bản gốc Excel/SQLite cùng journal nằm tại `.local/bridge/parity-transactions/`. Thư mục này phục vụ phục hồi giao dịch, không phải dữ liệu mẫu.

Lễ đổi ngày ghi X ngày gốc; lễ bổ sung ngoài lịch tăng cột O của Tổng kết. Một lượt không được dùng cả hai cách. Mã mới cần xác nhận cấp; mẫu giới hạn 40 em/lớp, nhập học theo tháng và 14 cột lễ mỗi tháng. Điểm danh hàng loạt chỉ nhập X; P/O và buổi chốt chỉnh riêng. Ghi chú chăm sóc vẫn lưu riêng ở SQLite/CSV, còn ghi chú chung được ghi vào sheet Ghi Chú.

Theo dõi các task nhỏ tại [DEVELOPMENT-CHECKLIST.md](DEVELOPMENT-CHECKLIST.md). Đăng nhập/tài khoản riêng được hoãn.

Lựa chọn hiện tại: tiếp tục dùng `D:\GiaoLy\DiemDanh-ThieuNhi`, đồng bộ đám mây để sau. Khi lên lớp phải lập danh sách đề xuất và duyệt từng em trước khi tạo bộ năm mới; không tự chuyển theo tên lớp.

- **Xin phép & đổi lễ → Lịch đổi lễ hằng tuần:** chọn em, thứ gốc/thứ thay thế và khoảng hiệu lực; xem trước toàn bộ các buổi từ Excel rồi xác nhận. Có xung đột thì chưa tạo lịch. Lịch tạo đơn đã duyệt cho từng tuần, không ghi X; camera đúng ngày thay thế mới ghi ngày gốc. “Dời riêng buổi này” giữ các tuần còn lại. Dừng lịch chỉ huỷ các đơn tương lai chưa xử lý; các buổi trước và lịch sử được giữ.
- **Hồ sơ:** sửa tên thánh/họ tên trong sổ và các sheet liên quan, giữ mã. Tên thánh được lưu thêm trong thuộc tính workbook để đọc đúng cả tên nhiều từ. Tạm nghỉ/nghỉ học có ngày hiệu lực từ hôm nay, không xoá dữ liệu cũ và không bị chốt O từ ngày nghỉ; xử lý các đơn tương lai trước khi cho nghỉ. Trạng thái này lưu ở dữ liệu web và được sao lưu cùng SQLite.
- **In thẻ:** tại danh sách chọn lớp rồi “In thẻ QR”, hoặc in lại từng em trong hồ sơ. Mã QR giữ nguyên mã đã cấp; cửa sổ in cho chọn máy in hoặc Lưu PDF.
- **Chuyển lớp:** thực hiện trên máy Excel, xem trước sức chứa và khả năng giữ các ngày đã điểm danh. Nếu lớp đích không có cột cho một ngày/hoạt động đã ghi thì từ chối, chưa làm mất lịch sử. Hai file được chuẩn bị trên bản sao, kiểm tra mã/VBA/chuyên cần, có bản sao đầy đủ và journal để hoàn tác khi thay file lỗi hoặc dịch vụ bị gián đoạn. Cần xử lý đơn chưa hoàn thành trước khi chuyển.
- **Theo dõi:** lọc tháng/học kỳ/năm; học kỳ đọc từ sheet OPTION của từng lớp. Biểu đồ có bảng số liệu. Cảnh báo từ 3 O liên tiếp riêng từng hoạt động trong các buổi đã ghi nhận, đến hôm nay; P hoặc X ngắt chuỗi, ô trống không tính. Trong chi tiết từng em có so sánh điểm HK1/HK2 từ Excel. Nhật ký đồng hành lưu người xử lý, nội dung, ngày hẹn, tình hình và lịch sử cập nhật; tải báo cáo chuyên cần CSV cho phạm vi đang xem.
- **Sao lưu & năm học:** trên máy Excel, tạo/tải bản sao đầy đủ gồm Excel + SQLite + manifest SHA-256. Lịch định kỳ mặc định mỗi 24 giờ khi dịch vụ đang chạy, có thể tắt/12 giờ/7 ngày. Bản sao từng file trước mỗi lượt ghi vẫn được giữ. Phục hồi kiểm tra hash, VBA, SQLite, danh sách file, yêu cầu xem trước và nhập “KHÔI PHỤC”; tạo bản sao hiện tại trước khi thay dữ liệu. Phục hồi cả Excel và SQLite để giữ nhất quán đơn/chốt/lịch sử. Không tự báo đám mây đã đồng bộ: mục này chỉ xác nhận file có sẵn trên máy.
- **Năm mới:** lưu dự thảo lên lớp, chọn lớp hoặc kết thúc chương trình và duyệt từng em; xem trước sức chứa rồi tạo bộ `.xlsm` riêng. Tháng/năm được cập nhật trong OPTION để công thức lịch tính lại theo quy tắc của mẫu, giữ VBA, GLV, mã và hồ sơ, xoá điểm/chuyên cần năm cũ. Không thay năm hiện tại. Tải bộ ZIP hoặc dùng thư mục bộ mới trên máy sau khi kiểm tra lịch và danh sách. Chưa tự thay đổi những quy định lịch lễ của mẫu.

Để chuyển sang bộ năm mới đã duyệt: dừng dịch vụ, rồi chạy `./Start-DiemDanh.ps1 -DataRoot 'đường-dẫn-bộ-Excel-mới'`. Mỗi thư mục khác thư mục mặc định dùng SQLite/sao lưu riêng; không mang đơn và lượt quét của năm trước sang năm mới. Dữ liệu năm cũ cùng các bản sao vẫn giữ nguyên. Khi chuyển dữ liệu cùng năm sang OneDrive/Google Drive, cần chuyển cả trạng thái web hoặc phục hồi bản sao đầy đủ trên thư mục mới; chỉ chuyển Excel sẽ không mang theo đơn và ghi chú.

Các kiểm tra mở rộng:

```powershell
python -X utf8 -m unittest discover -s tests -v
node --test tests/attendance-metrics.test.mjs tests/care-insights.test.mjs
python -X utf8 tests/native_development_integration.py
```

Kiểm thử trình duyệt `tests/development-ui.test.mjs` yêu cầu `XUAN_HOA_QA_URL` trỏ đến dịch vụ riêng sử dụng **file sao chép**, không dùng dịch vụ dữ liệu gốc. Cần Playwright đã cài hoặc chỉ định `PLAYWRIGHT_MODULE`.

## Kiểm thử hồi quy Excel

Chạy từ thư mục dự án trên Windows. Các kiểm tra nghiệp vụ dùng danh sách thật với SQLite và bộ ghi thử riêng; kiểm tra native tạo bản sao tạm của lớp Ấu Nhi 1A để thử sắp xếp lại hàng, lưu hồ sơ/điểm/GLV, giữ bảo vệ sheet và chặn ghi đè khi có thay đổi bên ngoài. Các lệnh này không ghi vào workbook gốc. Đặt `XUAN_HOA_DATA_ROOT` nếu dữ liệu nằm ở thư mục khác.

```powershell
python -X utf8 -m unittest discover -s tests -v
node --test tests/attendance-metrics.test.mjs
python -X utf8 tests/native_workbook_integration.py
```

## Dừng dịch vụ

```powershell
./Start-DiemDanh.ps1 -Stop
```

Dịch vụ chờ các lượt đang ghi hoàn tất rồi đóng phiên Excel riêng. Không tắt máy trong lúc thông báo đang ghi. Nếu cần khôi phục, dừng dịch vụ, đóng file Excel và thay file lớp bằng bản sao lưu tương ứng; mở lại dịch vụ để đọc lại trạng thái.
# Tài khoản cá nhân và quyền theo lớp

Hệ thống yêu cầu đăng nhập kể cả trên localhost. Admin cấp tài khoản cho GLV/ban trị sự, người dùng đổi mật khẩu tạm ở lần đăng nhập đầu. GLV chỉ quản lý lớp được phân công; Admin xem toàn bộ. Xem [hướng dẫn tài khoản và phân quyền](ACCOUNTS-AND-ROLES.md) để thiết lập, cấp lại mật khẩu và sao lưu dữ liệu quyền.

Login, đổi mật khẩu và landing dùng chung cảnh SVG nhà thờ ánh vàng tràn màn hình. Tháp chuông đồng có đồng hồ đứng riêng bên phải nhà thờ, với khoảng sân và bậc tháp riêng. Form đăng nhập màu kem đặt bên trái desktop và dưới minh hoạ trên mobile; đã bỏ nhân vật/model GLV động. Đàn bồ câu bay từ góc dưới trái lên bầu trời nhà thờ rồi ở lại lượn và vỗ cánh; trăng và nhà thờ chuyển động loop. Đăng nhập thành công vẫn mở lượt chào mới ở landing. Giao diện hỗ trợ giảm chuyển động và hình tĩnh dự phòng; Lottie loading giữ ở các tác vụ đang xử lý. Xem [logo và chuyển động giao diện](MOTION-AND-BRANDING.md) để chỉnh artwork và chạy kiểm tra.

Điều hướng, căn chỉnh các trang và phân công 2026–2027 theo Sổ sinh hoạt được mô tả trong [luồng công việc và phân công GLV](WORKSPACE-FLOW-2026-10-15.md).
