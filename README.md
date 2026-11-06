# Nha Khoa Thạnh Phú — phần mềm quản lý đa chi nhánh (MVP giai đoạn 1)

Ứng dụng chạy được trên máy tính: FastAPI + SQLAlchemy + SQLite (có hỗ trợ cấu hình PostgreSQL). Có giao diện tiếng Việt và website giới thiệu cơ bản.

## Cài đặt

Yêu cầu Python 3.11+.

### Windows (PowerShell)
```powershell
cd thanh_phu_dental
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
python -m uvicorn app.main:app --reload
```

### macOS / Linux
```bash
cd thanh_phu_dental
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed.py
python -m uvicorn app.main:app --reload
```

`seed.py` yêu cầu nhập mật khẩu quản trị, không có mật khẩu mặc định. Truy cập `http://127.0.0.1:8000` (website), `http://127.0.0.1:8000/login` (quản trị). Tài khoản `admin`, mật khẩu do bạn đặt. Tài liệu API: `/docs`.

## Đã có trong MVP

- Đăng nhập bằng PBKDF2, session cookie HttpOnly, CSRF cho các form ghi dữ liệu, phân quyền theo vai trò.
- Đa chi nhánh: chủ phòng khám có thể tạo và chuyển chi nhánh, nhân viên giới hạn theo chi nhánh.
- Bệnh nhân, lịch hẹn, ghế nha với kiểm tra trùng lịch, dịch vụ và giá.
- Hồ sơ điều trị dạng ghi chú và mã răng FDI (chưa có sơ đồ răng đồ họa).
- Hóa đơn, thu tiền nhiều lần, công nợ; kho vật tư và lịch sử nhập/xuất; chi phí.
- Danh sách nhắc tái khám (chưa tự động gửi SMS/Zalo); CMS nháp; nhật ký thao tác tạo mới.
- Dashboard số liệu tổng thu, chi, công nợ cho chi nhánh đang chọn.

## Cấu hình PostgreSQL (tùy chọn)

Đặt biến môi trường `DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/thanhphu` trước khi chạy `seed.py` và ứng dụng. **Không** trỏ trực tiếp vào database thật trước khi thiết lập migration, backup và kiểm thử.

## Sao lưu SQLite (thử nghiệm)

Dừng ứng dụng và sao chép `dental.db` đến nơi an toàn. Có thể dùng script `backup.py` để tạo bản sao nhất quán khi ứng dụng đang chạy. Cần kiểm tra khôi phục định kỳ. Với PostgreSQL, dùng `pg_dump`/`pg_restore` theo lịch.

## Cấu trúc

- `app/models.py`: các bảng database
- `app/main.py`: API + nghiệp vụ + HTML server-rendered
- `static/style.css`: giao diện đỏ/trắng
- `seed.py`: tạo tài khoản chủ và dữ liệu mẫu
- `backup.py`: sao lưu SQLite
- `tests/test_app.py`: kiểm thử smoke

## Giới hạn và việc cần làm trước khi dùng dữ liệu bệnh nhân thật

Đây là **MVP giai đoạn 1, không phải phần mềm bệnh án điện tử đạt chuẩn triển khai y tế**. Chưa có: migration Alembic, khóa bản ghi giao dịch đa người dùng, kiểm tra xung đột lịch ở mức database, biểu đồ răng tương tác, lưu file X-quang an toàn, đơn thuốc, gói điều trị, sửa/xóa với audit đầy đủ, phát hành hóa đơn điện tử, nhắc lịch tự động, gửi email/SMS/Zalo, nội dung CMS xuất bản, phân quyền chi tiết theo thao tác, giới hạn đăng nhập, MFA, HTTPS, quản trị phiên, giám sát, cơ chế backup tập trung và kiểm thử bảo mật. Không đưa dữ liệu bệnh nhân thật vào bản thử nghiệm này. Cần bổ sung quy trình bảo mật, quyền riêng tư, lưu trữ và tuân thủ pháp luật trước khi triển khai thực tế.

Lưu ý: `SESSION_SECRET` nên được đặt thành chuỗi ngẫu nhiên cố định khi chạy lâu dài. Khi chạy qua HTTPS, đặt `COOKIE_SECURE=1`.

## Giai đoạn 3: Chuẩn bị chạy thử online từ iPhone

Xem `DEPLOY_IPHONE.md` để biết các bước triển khai, `render.yaml` là mẫu cấu hình Web Service, `.env.example` là danh sách biến môi trường. PostgreSQL đã được hỗ trợ bởi `DATABASE_URL`; bộ source **chưa được triển khai lên Internet** và không có tài khoản hosting nào được tạo tự động. Không nhập dữ liệu bệnh nhân thật.
