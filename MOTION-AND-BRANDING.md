# Logo và chuyển động giao diện

Logo giữ nguồn gốc 700×732 px. `src/parish-logo.js` dùng mặt nạ SVG để cắt đúng huy hiệu tròn. Nhận diện trên login và landing dùng 88 px desktop, 72 px mobile và 64 px ở điện thoại hẹp. Độ nét chi tiết bên trong phụ thuộc ảnh nguồn.

## Đăng nhập theo cảnh nhà thờ

Login và đổi mật khẩu được thiết kế lại hoàn toàn bằng cảnh đêm dùng chung với landing. `welcomeBackdrop()` và `welcomeIdentity()` trong `src/welcome-scene.js` cung cấp nhà thờ, trăng, đàn bồ câu và ba dòng nhận diện. Không mount nhân vật GLV, không tải atlas hoặc phát model ở các form này.

`src/auth-scene.css` tạo form kem chữ đậm ở bên trái trên desktop, phía dưới minh hoạ trên mobile. Nền tràn màn hình, không thêm thông điệp hoặc nút trang trí. Nhà thờ giữ hai chóp tháp; tháp chuông lớn là công trình độc lập bên phải, có bậc và bóng nền riêng, cách nhà thờ bằng khoảng sân rõ ràng. Tháp chuông nằm ngoài nhóm chuyển động của nhà thờ, có vòm mở, chuông đồng lớn, quả lắc, đồng hồ và cửa chớp. Landing mobile thu gọn bố cục để giữ cả hai công trình trong khung hình; login và landing dùng chung artwork.

Giữ nguyên autocomplete, mật khẩu ẩn, chính sách đổi mật khẩu, lỗi và trạng thái chờ. Mobile không tự focus khi mở để tránh kéo màn hình hoặc bật bàn phím ngoài ý muốn. Đổi mật khẩu tự chọn có nút quay lại; đổi mật khẩu tạm bắt buộc không cho bỏ qua. Đăng nhập thành công vẫn có lượt chim bay vào mới ở landing.

Nguồn model GLV cũ trong `design/mascot/` được giữ như tài liệu thiết kế; không còn là UI đăng nhập hiện tại.

`npm run test:motion` hiện kiểm tra cảnh login mới, desktop/mobile/ngang, tháp chuông, bàn phím, lỗi, đổi mật khẩu, logout, reduced motion và fallback. Tài khoản QA mới được đổi mật khẩu tạm; tài khoản đã thiết lập giữ nguyên mật khẩu. Các nhánh lỗi/đổi mật khẩu bổ sung được giả lập để không đổi mật khẩu QA đang dùng.

## Loading và landing

Landing dùng cảnh SVG nhà thờ và bồ câu trong `src/welcome-scene.js`. Loading dùng `Loader cat.lottie` do người dùng cung cấp, phản ánh thời gian đọc thật, với renderer SVG light tại máy chủ. Thống kê trên landing dùng dữ liệu thật đã lọc theo quyền.

## Nâng cấp chuyển động ngày 15/10/2026

Giữ nền kem, xanh lá, màu ngành, font Nunito/Baloo 2, logo và bố cục nghiệp vụ. Build giải nén ba file từ `../../animation` thành JSON để dùng cùng `lottie-web`, không thêm thư viện chạy trên trình duyệt. Các file nguồn cần được giữ cùng dự án khi build lại.

- `Cat playing animation.lottie`: minh họa nhỏ ở bước chọn buổi; trên điện thoại đặt dưới hướng dẫn để giữ chiều rộng chữ.
- `Loader cat.lottie`: mở sổ, tải bảng điểm, chuẩn bị tải Excel và chờ chốt buổi. Kết quả thật thay loading ngay khi yêu cầu hoàn tất, không thêm thời gian chờ giả.
- `success confetti.lottie`: phát một lần sau khi API chốt buổi trả thành công. Không phát khi lỗi, khi quét từng thẻ, khi xem lại buổi đã chốt, hoặc khi người dùng giảm chuyển động. Hiệu ứng không bắt sự kiện chuột; thông báo kết quả và dấu tích vẫn đọc được khi hiệu ứng dừng.

Nút có phản hồi nhấn 120 ms; tiêu đề khi đổi trang, bốn tác vụ ở Bắt đầu, hộp thoại và toast xuất hiện nhẹ trong 180 ms. Các lần cập nhật dữ liệu trong cùng trang không chạy lại hiệu ứng tiêu đề. Đã bỏ nút tạm dừng theo yêu cầu. Chuyển động tuân theo cài đặt giảm chuyển động của thiết bị; lựa chọn tạm dừng cũ không còn được áp dụng. Bộ điều khiển quan sát cả hộp thoại, tạm dừng khi tab ẩn/ngoài màn hình và hủy player khi nội dung bị gỡ. Mỗi Lottie có ảnh SVG tĩnh dự phòng.

## Cảnh chào nhà thờ và bồ câu

Đăng nhập thành công chuyển tới `#home`, kể cả sau bước đổi mật khẩu tạm lần
đầu. Tải lại một phiên đang đăng nhập vẫn giữ trang đang mở. Hero mới là SVG
minh họa nhà thờ Công giáo với hai tháp chuông, cửa sổ hoa hồng, sân vườn, bầu
trời xanh đêm và ánh vàng. Đây là minh họa, không xác nhận đúng kiến trúc thực
tế của nhà thờ Xuân Hoà.

Cảnh chào phủ trọn viewport, không có header hoặc khung bo góc phía trên. Chỉ
giữ logo gốc và ba dòng thông tin Giáo xứ Xuân Hoà, Giáo phận Xuân Lộc,
Giáo hạt Tân Mai ở góc trên trái; tiêu đề và nút vào cổng dùng cỡ chữ lớn hơn.
Đã bỏ nút xem đàn chim bay, dòng
“Bình an đến với bạn” và các câu dẫn phụ. Năm bồ câu bay từ góc dưới trái lên
bầu trời phía trên nhà thờ trong dưới năm giây, rồi ở lại lượn và vỗ cánh theo
nhịp riêng. Vị trí đàn chim tính theo artwork, điều chỉnh khi đổi kích thước,
tránh logo, tiêu đề và nút vào cổng. Bố cục dọc chừa khoảng trời trên điện thoại
thấp; bố cục ngang giữ các tháp trong khung hình.
Trăng trôi ngang 16px, lên 26px và tăng tỷ lệ 3,5% trong chu kỳ 8 giây;
nhà thờ dịch ngang 2px, lên 8px và tăng tỷ lệ 1,8% trong chu kỳ 10 giây.
Hai chiều đi/về đều chậm dần ở điểm đổi hướng để nối vòng liền mạch.
Sáu ngôi sao có nhịp sáng lệch nhau, halo thở theo chu kỳ 6 giây và cửa kính
có ánh vàng ấm. Hai chim ở xa nhỏ, dịu và chậm hơn; nhịp cánh xen ba lần đập
với một quãng lượn dài. Tám hạt sáng chỉ chạy trong lượt bay vào rồi kết thúc.
Chữ vàng dùng gradient tĩnh và lớp sáng lướt bằng transform, giữ nguyên vị trí
chữ; tiêu đề xuất hiện một lần. Nút kính vàng giữ tương phản chữ, focus bàn phím
và phản hồi hover ngắn. Parallax giới hạn 2–8px cho chuột chính xác, không áp
dụng cho chạm hoặc di chuyển chữ. Sóng kem tĩnh nối cảnh đêm với nội dung dưới;
các card hiện nhẹ một lần khi vào màn hình và hiện ngay khi được focus.
Tất cả lớp chuyển động giữ nhịp khi dữ liệu được cập nhật và dừng khi giảm
chuyển động. Chuyển động dùng Web Animations
API, chỉ animate transform/opacity, dừng khi ngoài màn hình hoặc tab ẩn, hủy khi
rời trang. Giảm chuyển động giữ hình nhà thờ tĩnh; API animation không khả dụng
vẫn vào cổng được. Chu kỳ cập nhật dữ liệu không phát lại cảnh chào.

`src/welcome-svg-motion.js` giữ nguyên vector, đặt các nhóm cảnh nền có chuyển
động vào lớp HTML trong foreignObject có kích thước vừa artwork. Riêng cánh
bồ câu giữ nhóm SVG gốc, dùng `transform-box:view-box` và điểm xoay `(84,84)`
trong hệ tọa độ của chim để tránh lệch cánh khi thu nhỏ trên điện thoại. Quy tắc
kích thước chim chỉ áp dụng cho SVG ngoài cùng. Đổi này ngày 16/10/2026 thay
thế cách bọc từng cánh bằng foreignObject; số đo 0 layout/paint của bản trước
không áp dụng cho cánh SVG hiện tại. `src/welcome-reveals.js` quản lý các card dưới hero riêng theo
visibility, không can thiệp cuộn trang.

`npm run test:welcome` kiểm tra đăng nhập sai/đúng, chuyển trang sau đăng nhập,
sáu kích thước màn hình và điện thoại ngang, đường bay vào hữu hạn, đàn chim
lơ lửng trên nhà thờ và tránh nội dung, loop nối vòng, offscreen, giảm chuyển động,
nhịp lượn, ánh sáng, shimmer không lệch chữ, parallax desktop/touch, focus card,
fallback và cleanup trên bản sao QA. Chạy sau `npm run test:motion` trên bộ QA
mới, hoặc cung cấp `XH_MOTION_QA_PASSWORD` của tài khoản QA đã đổi mật khẩu.

## Các lệnh kiểm tra

- `npm run build`: xuất animation sách, ba animation người dùng cung cấp, ảnh tĩnh dự phòng và bundle ứng dụng. Không còn đưa bộ điều khiển GLV vào bundle hoặc sao chép atlas mascot mới khi build.
- Bộ nguồn/test tỉ lệ mascot cũ phục vụ tham khảo thiết kế, không mô tả login hiện tại.
- `./tests/Start-Auth-QA.ps1`, `npm run test:motion`, `./tests/Start-Auth-QA.ps1 -Stop`: kiểm tra login nhà thờ mới và các luồng tài khoản. Đăng nhập/đổi mật khẩu chỉ thực hiện trên bản sao QA.
- Sau `npm run test:motion`, chạy `npm run test:motion-feedback` trước khi dừng QA: kiểm tra animation mới ở 320/375/768/1440 px và điện thoại ngang, reduced motion, lỗi tài nguyên, loading khi tải file Excel thật trên bản sao, dọn player và confetti một lần. Phản hồi API chốt buổi được giả lập riêng trong test để kiểm tra nhánh lỗi/thành công mà không ghi vắng vào sổ. Có thể dùng `XH_MOTION_QA_PASSWORD` nếu đổi mật khẩu tài khoản QA khác mật khẩu bộ test trước đó.

Các nguồn `generate-glv-lottie.mjs` và test `glv-lottie*` được giữ như thử nghiệm cũ, không mô tả nhân vật đang sử dụng.
