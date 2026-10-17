# Mascot GLV · bản 1

Hình mẫu nhân vật GLV dựa trên ảnh người dùng cung cấp: mũ nâu, tóc đen, mắt lấp lánh, áo trắng, khăn đỏ viền vàng, quần xanh đậm, ba lô và bản đồ cuộn. Tư thế bước đi và chỉ tay sang phải.

- Asset: `glv-mascot-v1.png`, 1024×1536, PNG RGBA có nền trong suốt.
- Tạo bằng công cụ imagegen tích hợp, có ảnh tham chiếu của người dùng.
- Prompt đầy đủ: `glv-mascot-v1.prompt.txt`.
- Đây là bản thiết kế hình ảnh để xem trước và làm nguồn cho việc dựng nhân vật chuyển động tiếp theo.

Mascot đăng nhập hiện tại dùng hai atlas RGBA trong suốt, tạo bằng công cụ imagegen tích hợp, giữ phong cách các bản đã chọn:

- `glv-cover-sequence-v5.png`: 1254×1254, 12 tư thế từ tay ở thắt lưng đến che kín mắt. Prompt: `glv-cover-sequence-v5.prompt.txt`.
- `glv-expression-sequence-v5.png`: 1254×1254, 16 tư thế gồm các bước quay mặt, khép mắt một phần, nhắm mắt và nâng/vẫy tay chào. Prompt: `glv-expression-sequence-v5.prompt.txt`.
- `glv-sequences-v5.json`: vị trí cắt và căn tỉ lệ từng khung trong SVG. `scripts/inspect-glv-sprites.py` phân tích alpha, cổ và khóa thắt lưng, lấy `expression2` đứng yên làm chuẩn cho chiều rộng đầu/thân, chiều dài cổ–thắt lưng và vị trí khóa. Các vùng đầu/thân được căn riêng, chuyển dần chiều rộng quanh cổ để tránh đường nối. Chỉ thay tọa độ hiển thị SVG, không sửa bitmap PNG.

Đây là animation vẽ từng khung hình: phát chuỗi khung trung gian, hạ tay bằng chuỗi ngược, có thể đảo chiều ở khung đang hiện khi đổi focus. Chỉ một hình nhân vật hiện mỗi lần, không crossfade thành bóng đôi. Bộ phát chỉ dùng rAF trong chuỗi hữu hạn; khi nghỉ không có vòng lặp rAF. Dừng khi ngoài màn hình/tab ẩn, tạm dừng hoặc giảm chuyển động; huỷ timer/rAF/animation khi rời trang. Web Animations API giữ nhịp thở nhẹ. Các atlas v2/v3/v4 là bản nguồn và thử nghiệm trước, không dùng trong build hiện tại.

Đã khôi phục bộ ảnh V5 sau thử nghiệm vector. Nhịp nâng/hạ tay chậm hơn ở hai đầu, nhanh hơn ở giữa. Nếu trình duyệt khựng, bộ phát vẫn đi qua từng tư thế kế tiếp thay vì nhảy qua các khung tay. Khi ngắt chào để nhập mật khẩu, đi qua tư thế hạ tay trước khi che mắt. Đây vẫn là hoạt hình từ ảnh có sẵn, không nội suy hình học như Rive. `scripts/generate-glv-lottie.mjs` và các test `glv-lottie*` chỉ là thử nghiệm cũ, không được dùng trong build hoặc hai lệnh kiểm tra hiện tại.

`glv-rig-atlas-v1.png` và prompt tương ứng giữ lại như bản thiết kế cũ, không được build vào mascot đăng nhập hiện tại.

Biểu cảm khuôn mặt v3 (`glv-face-v3.png`, prompt tương ứng) là ảnh tham chiếu đã được người dùng chọn. V5 thêm khung trung gian cho chính các hành vi đó. Ánh nhìn vẫn phản hồi vị trí con trỏ trong tên đăng nhập, không đọc giá trị mật khẩu. Form luôn thao tác được trong lúc tay chuyển động.

`npm run test:mascot-proportions` đo pixel ảnh chụp thực tế của cả 28 tư thế, so sánh chiều rộng đầu/thân, cổ, chiều dài thân và tâm khóa thắt lưng với tư thế đứng yên. Chỉ đọc trang đăng nhập công khai ở localhost; không gửi đăng nhập hoặc ghi dữ liệu. Ảnh so sánh và số đo nằm trong `.local/glv-proportions/`.
