# Vận hành Vercel + Supabase

Cập nhật: 16/10/2026. Địa chỉ dự án: https://giao-xu-xuan-hoa.vercel.app

## Kiến trúc

Frontend và API FastAPI chạy cùng tên miền HTTPS trên Vercel, vùng Sydney (syd1), gần database Supabase hiện tại. PostgreSQL là nguồn dữ liệu chính: tài khoản, phân công, hồ sơ, điểm danh, điểm, đơn, chăm sóc, thông báo, cấu hình, các năm học và bản sao lưu. Máy Windows và Microsoft Excel không tham gia xử lý yêu cầu cloud.

14 bảng xh_* bật RLS và thu hồi quyền trực tiếp của anon/authenticated. Sổ mẫu nằm trong xh_blobs riêng tư, khử trùng lặp bằng SHA-256; bản thử nghiệm không cần thêm Supabase Storage hoặc khóa Storage. API kiểm tra phiên đăng nhập, quyền lớp và CSRF. Secret chỉ đặt phía máy chủ, không nằm trong JavaScript hoặc Git.

Các chức năng đã có backend cloud: tài khoản/đổi mật khẩu/phân quyền, hồ sơ và phân công GLV, QR/điểm danh/chốt buổi, đơn/nghỉ phép/lễ bù, điểm và tổng kết, xuất sổ, thêm/chuyển thiếu nhi, nhập hàng loạt, quản lý lớp/lịch/ghi chú, chuẩn bị/kích hoạt năm học, lịch sử, chăm sóc/thông báo, sao lưu và khôi phục. Thao tác có bước xem trước tiếp tục kiểm tra phiên bản trước khi ghi; giao dịch lỗi được rollback.

Sổ xuất giữ định dạng và VBA của mẫu, cập nhật dữ liệu và kết quả tính ở phía server. Cloud không chạy macro Excel. Các trường hợp trống, 0 và P được giữ riêng. File xuất được kiểm tra đối chiếu với bộ tính của dự án; điều này không thay thế việc kiểm thử từng macro trong Microsoft Excel.

## Dữ liệu và chuyển sang sử dụng

Gói nguồn ngày 16/10 có 44 tài khoản, 20 lớp, 442 thiếu nhi và 20 sổ. Công cụ giữ ID/QR, hash mật khẩu, yêu cầu đổi mật khẩu lần đầu, vai trò, phân công, hồ sơ và lịch sử nguồn. Không nhập phiên đăng nhập cũ. Các bản ZIP sao lưu trước đây trên Windows vẫn ở máy cũ; cloud có bộ sao lưu riêng từ lúc chuyển.

Chỉ dùng bản cloud làm nơi ghi sau khi chuyển dữ liệu. Bản localhost cũ lưu độc lập, không tự đồng bộ những thay đổi mới lên cloud hoặc ngược lại. Khi cần quay về bản cũ phải đối soát dữ liệu phát sinh trên cloud trước.

GET /api/health công khai chỉ trả trạng thái, không trả thông tin cá nhân. GET /api/cloud/readiness dành cho Admin; chỉ báo sẵn sàng khi có đúng một năm hoạt động và đầy đủ sổ riêng tư cho các lớp. Backend chặn mở trang nghiệp vụ và ghi khi gói dữ liệu chưa đầy đủ.

## Tên đăng nhập

Tài khoản quản trị `admin` giữ nguyên. GLV dùng `glv-` + hai từ cuối của họ tên, bỏ dấu và viết liền: Thuỷ Tiên → `glv-thuytien`, Trần Minh Mẫn → `glv-minhman`. Trùng tên thì thêm `2`, `3`…; các tài khoản ngừng hoạt động vẫn giữ tên đã cấp để tránh nhầm người. Sr dùng tiền tố `sr-`, ví dụ `sr-honghanh`; tiền tố không thay đổi vai trò hoặc quyền lớp.

Tạo tài khoản mới tự áp dụng quy tắc này. Với Sr mới, nhập họ tên có tiền tố `Sr.`/`Soeur` và chọn quyền Admin theo phân quyền giáo xứ. Tài khoản cũ chỉ ghi `Sr. Maria` được giữ nguyên khi chưa có họ tên đầy đủ. Đổi tên đăng nhập giữ ID, hash mật khẩu, cờ đổi mật khẩu lần đầu, phân công và phiên hiện tại; tên đăng nhập cũ ngừng dùng sau khi đổi.

Công cụ chuyển đổi có xem trước: `python -m cloud_backend.rename_accounts`. Ghi thật yêu cầu `--commit --expected-digest ...`; có snapshot trước/sau và kiểm tra không thay đổi các trường ngoài username/revision. Danh sách tên đăng nhập lưu trong `.local/account-usernames/danh-sach-dang-nhap.md`, không đưa lên web công khai.

## Sao lưu và tải sổ

Admin có thể tạo bản sao, tải ZIP và xem trước khôi phục trong **Sao lưu & năm học**. Khôi phục nghiệp vụ giữ mật khẩu hiện tại; khôi phục tài khoản là thao tác riêng. Cả hai yêu cầu xem trước, nhập xác nhận và kết thúc phiên đăng nhập để tải lại quyền/dữ liệu.

Chu kỳ sao lưu tự động kích hoạt ở lần cập nhật dữ liệu tiếp theo khi đến hạn, không phải tác vụ chạy đúng giờ khi không có truy cập. Không cần bật máy cá nhân. Nên tải định kỳ một bản ZIP ra nơi lưu riêng. Bản sao trong cùng database không bảo vệ được trường hợp mất cả project Supabase.

File lớn được tải qua các phần có xác thực, dưới 4 MB/phần, rồi ghép ZIP trong trình duyệt. Không đưa bản sao lưu vào thư mục công khai hoặc tạo URL file không cần đăng nhập. Giới hạn tệp nhị phân của bản thử nghiệm là 300 MB; cần theo dõi cả dung lượng database, gồm dữ liệu và lịch sử sao lưu.

## Cấu hình riêng

Hai biến bắt buộc trên Vercel: XH_DATABASE_URL, XH_SESSION_SECRET. Dùng URI Transaction pooler từ **Supabase → Connect**, SSL, cổng 6543; password phải percent-encode. Kết nối không dùng prepared statements tồn tại qua nhiều giao dịch. Tên miền Vercel được lấy từ cấu hình nền tảng; thêm tên miền riêng thì đặt XH_PUBLIC_ORIGIN=https://ten-mien.

File .env.cloud.local, .env.local, .local/, workbook, gói chuyển đổi và cấu hình CLI nằm ngoài Git và gói deploy. Không gửi secret vào chat. Đổi password database trên Supabase rồi cập nhật cục bộ bằng deploy/Update-CloudDatabasePassword.ps1. Sau khi đổi, cập nhật cả biến tương ứng trên Vercel và redeploy.

## Build, kiểm tra và triển khai lại

Chạy từ thư mục ứng dụng sites/giao-xu-xuan-hoa:

~~~powershell
npm ci
npm test
npm run build:cloud
.local/cloud-venv/Scripts/python -m unittest discover -s tests -p 'test_cloud_*.py' -q
npx --yes vercel@64.3.1 --global-config .local/vercel-cli deploy --prod --yes
~~~

Schema tái tạo bằng: python -m cloud_backend.manage schema --output deploy/supabase-schema.sql. Chỉ cài schema bằng kết nối server đã xác minh; không chạy migration tự động trên mỗi request.

Để xuất nguồn Windows chỉ đọc và kiểm tra trước khi nhập một database mới:

~~~powershell
python scripts/export-cloud-source.py --root D:/GiaoLy/DiemDanh-ThieuNhi --state-dir .local/bridge
.local/cloud-venv/Scripts/python -m cloud_backend.manage import --source .local/cloud-source-THU-MUC/source.json
~~~

Lệnh nhập thật cần --commit --expected-digest DIGEST_TU_BUOC_XEM_TRUOC. Công cụ từ chối ghi đè database đã có dữ liệu và phát hiện dữ liệu nguồn thay đổi trong lúc xuất. Không dùng lại gói cũ để cập nhật dữ liệu đang vận hành.

Kiểm tra riêng PostgreSQL dùng schema ngẫu nhiên và dữ liệu giả qua tests/cloud-postgres-check.py, cần XH_RUN_POSTGRES_QA=1. Kiểm tra trình duyệt desktop/mobile dùng fixture tests/serve-cloud-qa.py --full và tests/cloud-office-ui.test.mjs; không chạy kiểm tra có ghi lên tài khoản thật.

## Giới hạn thử nghiệm

Gói miễn phí dùng cho giai đoạn thử; khả năng sẵn sàng phụ thuộc Vercel/Supabase và hạn mức tài khoản. Chưa nghiệm thu camera trên mọi điện thoại hoặc tải đồng thời cả giáo xứ; cần một buổi thử thực tế qua Wi-Fi/4G trước khi dùng cho buổi điểm danh chính thức. Kiểm tra điều kiện Hobby của Vercel trước khi vận hành lâu dài cho tổ chức; Supabase Free có thể tạm dừng project ít hoạt động và không có bộ backup tự động như gói trả phí.

Tài liệu chính thức: [FastAPI trên Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [vùng Functions](https://vercel.com/docs/functions/configuring-functions/region), [giới hạn Functions](https://vercel.com/docs/functions/limitations), [kết nối Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres), [Supabase billing](https://supabase.com/docs/guides/platform/billing-on-supabase), [Vercel Hobby](https://vercel.com/docs/plans/hobby).
