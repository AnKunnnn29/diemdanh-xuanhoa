# Rà soát và đề xuất phát triển dự án Điểm danh Thiếu nhi

Ngày rà soát: 13/10/2026. Phạm vi: mã nguồn hiện tại, tài liệu nghiệp vụ, build, kiểm thử Python/JavaScript và trình duyệt trên dữ liệu sao chép.

## 1. Nhận định chính

Dự án đã vượt phạm vi một ứng dụng quét QR: hiện là cổng quản lý giáo lý có điểm danh, xin phép/đổi lễ, hồ sơ, bảng điểm, chăm sóc, sổ Excel và chuyển năm học. Theo yêu cầu cập nhật của người dùng, **ưu tiên UI/UX và trải nghiệm giáo lý viên trước**, tập trung vào điểm danh, tìm thiếu nhi, nhập điểm và tải sổ. Chi tiết công việc và tiêu chí nghiệm thu tại [Kế hoạch ưu tiên UI/UX](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/UX-PRIORITIES-2026-10-13.md).

Chưa có đủ bằng chứng để kết luận toàn bộ hệ thống đã sẵn sàng cho hosting công khai hoặc tải đồng thời lớn. Các kiểm thử trong đợt này xác nhận những phạm vi cụ thể ở mục 3.

Tài liệu hiện có ghi rõ đăng nhập cá nhân, phân quyền theo lớp và đồng bộ Drive đã được hoãn theo lựa chọn trước đó. Báo cáo giữ các phần này trong lộ trình có điều kiện; không đề xuất triển khai ngay.

## 2. Hiện trạng và nền tảng nên giữ

| Thành phần | Hiện trạng |
|---|---|
| Giao diện | JavaScript thuần, các module ES, Tailwind CSS, esbuild; điều hướng theo hash |
| Backend | Python, HTTP server, hàng đợi một worker dành cho Excel và các thao tác dữ liệu |
| Sổ lớp | 20 file `.xlsm`: một file ở thư mục gốc và 19 file trong `outputs/cac-lop-2026-2027` |
| Nguồn dữ liệu | Excel giữ trạng thái nghiệp vụ chính; SQLite giữ buổi, đơn, lịch sử và dữ liệu quản lý; điểm có bản lưu và lượt chờ xuất |
| Bộ tính điểm | Có chế độ portable, tính theo công thức của mẫu và cập nhật giá trị kết quả trong gói `.xlsm` |
| Ghi nghiệp vụ khác | Điểm danh và nhiều thao tác quản lý còn cần Windows, Excel desktop và COM |
| Kết nối | Máy quản lý qua localhost; thiết bị cùng Wi-Fi qua HTTPS và mã kết nối |
| MySQL | Có adapter cho phần điểm; tài liệu ghi chưa kiểm chứng với server MySQL thật |

Các điểm mạnh có bằng chứng trong mã và kiểm thử:

- Phân biệt X/P/O và ô trống; P, điểm 0, chưa nhập và lỗi công thức không bị gộp thành một giá trị.
- Tra cứu lại mã trên sheet đích, chống mã trùng và giữ công thức/VBA khi ghi sổ.
- Có staging, sao lưu, kiểm tra hash và phát hiện thay đổi Excel bên ngoài.
- Điểm có lượt chờ xuất bền vững, phiên bản chống ghi đè và luồng đối chiếu xung đột.
- Quét có reservation lưu trước khi ghi Excel; cơ chế này hỗ trợ tránh cộng trùng khi tiến trình bị gián đoạn.
- Đã có nhiều nghiệp vụ thường bị bỏ sót: ngoại lệ lễ bù, trạng thái học theo ngày hiệu lực, phục hồi và lập bộ năm mới.
- Giao diện có bốn công việc chính, chọn lớp dùng chung, chữ lớn, thông báo trạng thái và bước kiểm tra trước khi chốt.

Nguồn: [Store và API](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/excel_bridge/server.py:45), [ghi Excel](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/excel_bridge/native.py:49), [điểm portable](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/excel_bridge/portable_grades.py:155), [reservation quét](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/excel_bridge/exceptions.py:474), [phạm vi chức năng](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/FUNCTIONS.md).

## 3. Kết quả kiểm tra thực hiện trong đợt này

| Kiểm tra | Kết quả | Phạm vi |
|---|---|---|
| Python unittest | 84/84 đạt, 227,192 giây | Nghiệp vụ, validation, phục hồi giao dịch, lễ bù và điểm portable; dùng bản sao hoặc bộ ghi được thay thế trong test |
| JavaScript unit test | 16/16 đạt | Chuyên cần, chăm sóc, giao diện hướng dẫn và tổng kết điểm |
| Build JavaScript | Đạt | Bundle nguồn bằng esbuild, giữ kết quả trong bộ nhớ |
| Build CSS | Đạt | Tailwind CLI, ghi kết quả vào file tạm |
| Trình duyệt | 36/36 lượt không tràn ngang; không ghi nhận `pageerror` | 12 trang × chiều rộng 320, 375 và 1440px; Edge headless, một lớp sao chép có 22 em |
| Mất mạng/phục hồi | Tái hiện hạn chế | Khi mất mạng, trang chuyển về kết nối; 17 giây sau khi có mạng trở lại vẫn chưa tự phục hồi; bấm kết nối lại hoạt động |
| Toàn vẹn sổ gốc dùng cho QA | SHA-256 giữ nguyên | So sánh trước/sau đối với file gốc được sao chép cho kiểm tra trình duyệt; các test liên quan cũng có kiểm tra hash nguồn |

Đã xem ảnh trang bắt đầu ở chiều rộng 375px: chữ và nút chính rõ, các công việc được trình bày dễ nhận biết. Không có lý do từ đợt kiểm tra này để thay toàn bộ thiết kế.

Các giới hạn cần đọc cùng kết quả:

- Trình duyệt kiểm tra bản `dist` hiện có; build nguồn được kiểm tra riêng. Đây chưa phải quy trình phát hành tự động từ checkout sạch.
- Chưa chạy lại các script tích hợp Excel COM hoặc đối chiếu toàn bộ công thức với Excel desktop trong đợt này. Kết quả cũ được ghi trong checklist không được tính là kết quả mới của báo cáo.
- Chưa đo tải trên đủ 20 lớp với nhiều thiết bị, chưa thử QR bằng camera vật lý hoặc máy quét USB và chưa kiểm chứng LAN/TLS trên điện thoại thật.
- Hai script `development-ui.test.mjs` và `excel-parity-ui.test.mjs` không chạy độc lập khi thiếu `XUAN_HOA_QA_URL`. Lần chạy chung ban đầu dừng ở yêu cầu cấu hình này; bộ unit đã được chạy lại riêng và đạt. Kiểm tra trình duyệt trong bảng là script QA riêng, không thay thế nghiệm thu toàn bộ các luồng ghi của hai script đó.
- Chưa có kết quả kiểm thử MySQL thật hoặc khảo sát sử dụng với giáo lý viên.

## 4. Những việc nên ưu tiên

### A. Khôi phục kết nối và làm rõ trạng thái lưu — ưu tiên đầu tiên

**Đã tái hiện:** vòng làm mới 15 giây chuyển `connected=false` khi một yêu cầu lỗi; các lần sau bỏ qua khi chưa kết nối. Mạng trở lại không tự kích hoạt bootstrap. Người dùng phải bấm kết nối lại.

**Đề xuất:**

- Có trạng thái đang kết nối lại, thử lại với thời gian chờ tăng dần và phản ứng khi trình duyệt báo có mạng.
- Giữ lớp, ngày, hoạt động và nội dung đang nhập khi kết nối gián đoạn.
- Đặt thời hạn phù hợp cho yêu cầu API và hiển thị rõ thao tác đang chờ. Thời hạn phía trình duyệt không có nghĩa backend đã hủy thao tác.
- Khi mất phản hồi sau một thao tác ghi, đối chiếu trạng thái server trước khi gửi lại; tận dụng reservation quét và lượt điểm chờ hiện có.
- Cho người quản lý xem các lượt điểm đang chờ, xung đột và lỗi sao lưu từ một nơi.

**Nghiệm thu:** mạng trở lại tự phục hồi; không mất bản nháp; mất phản hồi sau ghi không cộng thêm lượt; không báo thành công trước khi xác nhận trạng thái lưu.

Nguồn: [API phía trình duyệt](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/src/app.js:86), [màn hình kết nối](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/src/app.js:130), [vòng làm mới](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/src/app.js:1449).

### B. Chuẩn hóa khởi động và kiểm tra vận hành

**Quan sát từ mã:** khi dịch vụ đã chạy, launcher kiểm tra thư mục dữ liệu và bộ tính điểm rồi mở URL đã lưu; chưa đối chiếu yêu cầu `-Lan` và `-Port`. Đây là hành vi cần cải thiện để tránh việc tham số mới bị bỏ qua. Chưa chạy lại kịch bản này với dịch vụ sản xuất.

**Đề xuất:** lưu và so sánh chế độ LAN/cổng; thông báo chính xác cách đổi chế độ; thêm kiểm tra trước buổi gồm dịch vụ, Excel, quyền ghi, thư mục dữ liệu, dung lượng và lần sao lưu gần nhất. Đóng gói hướng dẫn cài máy mới với các phiên bản đã kiểm chứng.

**Nghiệm thu:** mỗi cách khởi động hiển thị đúng chế độ; tham số khác phiên đang chạy được báo rõ; giáo lý viên biết phải xử lý gì khi một điều kiện chưa đạt.

Nguồn: [launcher](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/Start-DiemDanh.ps1:13).

### C. Theo dõi hàng đợi và kiểm chứng hiệu năng

**Quan sát từ mã:** các API đọc/ghi và sao lưu định kỳ dùng chung executor một worker. Cách này giúp bảo vệ COM và việc ghi, nhưng một thao tác lâu có thể làm các yêu cầu tiếp theo chờ. Đợt này chưa đo mức chờ trong một buổi thực tế.

**Đề xuất:** đo thời gian chờ và thực thi theo loại thao tác, số việc đang chờ và lỗi; kiểm tra tải trên bộ 20 lớp sao chép. Sau khi có số liệu, cân nhắc phục vụ các yêu cầu đọc từ snapshot nhất quán, gom lượt đọc trùng và lên lịch tác vụ nặng ngoài thời gian điểm danh. Giữ cơ chế tuần tự cho ghi COM và các giao dịch cần tính nhất quán.

**Nghiệm thu:** có số liệu p50/p95 và độ dài hàng đợi ở mức tải được thống nhất; tải báo cáo hoặc sao lưu không làm giao diện mất thông tin về các lượt đang ghi.

Nguồn: [executor](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/excel_bridge/server.py:350), [sao lưu định kỳ](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/excel_bridge/server.py:361).

### D. Chuẩn hóa kiểm thử và phiên bản phát hành

**Quan sát:** `package.json` mới có `build` và `dev`; chưa có lệnh test chung hoặc cấu hình CI trong repo. Bộ test trình duyệt phụ thuộc URL QA, một số script phụ thuộc đường dẫn Playwright của máy hiện tại. Git đang có nhiều thay đổi và các module/test mới chưa được theo dõi.

**Đề xuất:** tách rõ unit, browser và native integration; viết lệnh tạo bộ QA từ sổ sao chép, khởi động server trên cổng riêng, chạy test và dừng server. Thêm kiểm tra build từ checkout sạch; đưa HTML shell vào quy trình nguồn/build thay vì chỉ phụ thuộc file có sẵn trong `dist`. Phát hành một phiên bản gồm đủ mã nguồn, test, dependency và hướng dẫn phục hồi.

**Nghiệm thu:** máy mới chạy được quy trình theo README; kiểm thử không cần đường dẫn cá nhân; artifact build từ checkout sạch có đủ HTML/assets; chỉ công bố một bản sau khi toàn bộ file cần thiết được đưa vào phiên bản đó. COM integration chạy trên máy Windows có Excel trước các bản đổi cấu trúc sổ hoặc công thức.

Nguồn: [các script hiện có](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/package.json:6), [build](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/build.mjs:1), [browser integration](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/tests/development-ui.test.mjs:1).

### E. Quản lý dung lượng sao lưu và thử phục hồi định kỳ

**Quan sát từ mã:** sổ được sao lưu trước các lượt ghi, đồng thời có snapshot toàn hệ thống; chưa thấy chính sách giữ/xóa bản sao theo tuổi hoặc tổng dung lượng. Bản sao đều nằm trên máy vận hành trừ khi người dùng chủ động tải ra.

**Đề xuất:** thống kê dung lượng; cảnh báo ngưỡng; cấu hình giữ bản theo ngày/tuần/tháng; bảo vệ bản trước phục hồi và bản được đánh dấu quan trọng. Thêm quy trình sao chép sang ổ khác và diễn tập phục hồi trên thư mục riêng. Việc xóa bản sao phải là chức năng quản lý có xem trước và xác nhận.

**Nghiệm thu:** người quản lý thấy dung lượng và thời điểm bản sao; khôi phục thử được Excel cùng SQLite; chính sách không xóa bản cần đối chiếu hoặc rollback.

Nguồn: [backup trước ghi Excel](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/excel_bridge/native.py:96), [snapshot](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/excel_bridge/development.py:249), [lịch backup](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/excel_bridge/development.py:556).

### F. Tách module khi bổ sung chức năng

`src/app.js` khoảng 128 KB và 1.450 dòng, giữ chung state, API, điều hướng, camera, điểm, hồ sơ và nhiều sự kiện. Các module `easy-ui`, `requests-ui`, `development-ui` và `excel-parity-ui` đã tạo nền tảng để tách tiếp.

**Đề xuất:** lần lượt tách API/kết nối, state/chọn lớp, luồng quét, bảng điểm và hồ sơ; giữ nguyên hành vi bằng các test hiện có. Gom CSS theo phạm vi trang và token, giảm các lần ghi đè giữa stylesheet. Chưa có bằng chứng cần chuyển framework; tách module trong stack hiện tại là bước nhỏ hơn.

**Nghiệm thu:** mỗi phần có giao diện module rõ, test nghiệp vụ vẫn đạt, không thay quy tắc Excel khi tái cấu trúc.

## 5. Chức năng mở rộng có giá trị thực tế

Các chức năng dưới đây là đề xuất, chưa được triển khai trong đợt rà soát.

| Ưu tiên | Chức năng | Giá trị và tiêu chí |
|---|---|---|
| Cao | Bảng công việc hôm nay | Gom buổi cần chốt, đơn cần duyệt, lễ bù đến hạn, lịch chăm sóc đến hẹn và điểm chờ cập nhật; tính từ dữ liệu thật, bấm vào mở đúng lớp/ngày |
| Cao | Bảng kiểm trước và sau buổi | Kiểm tra thiết bị/dịch vụ trước quét; đối chiếu lượt lỗi, đơn còn chờ, trạng thái chốt và bản sao sau buổi |
| Vừa | Báo cáo định kỳ cho người phụ trách | Báo cáo tuần/tháng theo lớp, thay đổi chuyên cần, các em cần theo dõi; có thể in/xuất, chưa tự gửi thông tin ra ngoài |
| Vừa | Lịch sử hồ sơ tập trung | Xem chuyển lớp, thay đổi trạng thái học, liên hệ và điểm danh theo một dòng thời gian, giữ người xử lý và lý do |
| Vừa | Chuyển năm học có kiểm tra đầu vào | Bổ sung hướng dẫn rà soát danh sách thực tế, sức chứa, lịch, mã đã cấp và bản sao; tận dụng luồng năm mới đã có |
| Sau | Chế độ phụ huynh | Nếu được yêu cầu: xem dữ liệu của con, xin phép và nhận kết quả; cần xác thực, liên kết phụ huynh–thiếu nhi và phân quyền trước |

Nên thử với 3–5 giáo lý viên bằng các việc cụ thể: điểm danh một em, tìm số phụ huynh, lập phép, nhập điểm và tải sổ. Ghi lại thời gian, lỗi và chỗ phải nhờ trợ giúp, sau đó sửa các bước gây vướng. Tài liệu hiện tại cũng ghi chưa thử trực tiếp với giáo lý viên lớn tuổi.

## 6. Điều kiện trước khi tiếp tục MySQL, hosting hoặc 4G

Phần điểm portable là bước tiến hữu ích, nhưng đổi database hoặc đưa frontend lên hosting chưa làm các nghiệp vụ COM chạy được từ mọi mạng.

Một điểm cần xử lý khi bật MySQL: repository đưa dữ liệu điểm vào MySQL, trong khi snapshot/restore hiện chỉ sao chép Excel và `attendance.sqlite3`. README đã yêu cầu sao lưu MySQL riêng. Do đó bản sao toàn hệ thống hiện không bao phủ dữ liệu MySQL; cần quy trình sao lưu/phục hồi phối hợp trước khi dùng cấu hình này trong vận hành thật.

Lộ trình có điều kiện:

1. Thống nhất nơi vận hành: tiếp tục LAN, hay cần truy cập từ mạng khác.
2. Nếu mở truy cập ngoài LAN, triển khai danh tính và quyền thao tác phù hợp; vị trí localhost không còn đủ để đại diện người quản lý. Quyền xem hồ sơ và tải sổ phải được kiểm tra ở server.
3. Chọn nguồn dữ liệu có thẩm quyền cho từng nghiệp vụ; mô tả rõ khi người dùng sửa Excel trực tiếp thì dữ liệu database và web được đối chiếu thế nào.
4. Kiểm thử MySQL thật, migration, TLS, mất kết nối, xung đột, sao lưu và phục hồi cùng file.
5. Thí điểm một lớp; chỉ mở rộng sau khi xác nhận công thức, chuyên cần, đơn phép và lịch sử không bị lệch.
6. Nếu muốn bỏ phụ thuộc máy Excel, chuyển từng nghiệp vụ sang bộ xử lý độc lập COM và đối chiếu với mẫu hiện hành trước khi thay cơ chế ghi.

Nguồn: [repository MySQL/SQLite](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/excel_bridge/grade_repository.py:12), [snapshot SQLite](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/excel_bridge/development.py:269), [hướng dẫn MySQL](D:/GiaoLy/DiemDanh-ThieuNhi/sites/giao-xu-xuan-hoa/README.md:69).

## 7. Thứ tự triển khai đề xuất

| Đợt | Công việc | Điều kiện hoàn thành |
|---|---|---|
| 1 — UI/UX cho điểm danh và tìm kiếm | Tìm tên không dấu nhất quán, giữ lớp/buổi/từ khóa, thông báo không che thao tác, phục hồi kết nối | Điểm danh liên tiếp thuận tiện; tìm đúng em; hiểu trạng thái lưu; mất mạng không làm mất ngữ cảnh |
| 2 — UI/UX cho nhập điểm và tải sổ | Tìm em nhanh, nhớ loại điểm, lưu và nhập em tiếp theo, lỗi tại chỗ và tải đúng lớp | Giảm thao tác lặp; P/0/trống đúng; lỗi lưu giữ nội dung; file tải khớp lớp |
| 3 — Đồng nhất trải nghiệm và nghiệm thu | Cỡ chữ/khoảng cách/nút thống nhất, công việc cần xử lý, thử với giáo lý viên và điều chỉnh | Có số liệu trước/sau; kiểm tra điện thoại/bàn phím/chữ lớn; không đổi nghiệp vụ sổ |
| Sau UI/UX — Củng cố kỹ thuật | Launcher, quản lý sao lưu, bộ QA/phát hành, tách module và đo tải | Máy mới chạy được; phục hồi thử đạt; có số liệu tải; build/test từ checkout sạch |
| 4 — Mở rộng theo nhu cầu | Tài khoản, quyền theo lớp, MySQL thật, hosting/4G hoặc phụ huynh | Chỉ bắt đầu khi tiếp tục các phần đã hoãn; có nghiệm thu bảo mật, dữ liệu và phục hồi |

Ước lượng thời gian nên thực hiện sau khi chốt thiết bị và người nghiệm thu. Các phần kỹ thuật trực tiếp phục vụ trải nghiệm như khôi phục kết nối và kiểm thử UI được thực hiện cùng đợt UI/UX; phần hạ tầng tổng thể theo sau. Các phát hiện ở mục 4 vẫn giữ giá trị làm backlog kỹ thuật.

## 8. Thay đổi trong đợt rà soát

Đợt này bổ sung báo cáo này, không sửa mã nghiệp vụ hoặc sổ sản xuất. Build dùng bộ nhớ/file tạm; dịch vụ QA dùng thư mục sao chép riêng, cổng 8876 và đã được dừng. Các thay đổi Git có sẵn được giữ nguyên.
