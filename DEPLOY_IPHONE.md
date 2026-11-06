# Thạnh Phú — triển khai bản demo từ iPhone

## Phạm vi
Bộ source này là MVP thử nghiệm, không phù hợp nhập dữ liệu bệnh nhân thật. PostgreSQL được hỗ trợ qua biến `DATABASE_URL`. File `render.yaml` chỉ khai báo dịch vụ web, **không tự tạo database hay triển khai**.

## Chuẩn bị
1. Tải ZIP, giải nén bằng ứng dụng Tệp trên iPhone.
2. Đưa toàn bộ thư mục `thanh_phu_dental` vào một repository GitHub riêng tư bằng công cụ hỗ trợ upload file; nếu trình duyệt di động không hỗ trợ tải cả thư mục, thực hiện trên máy tính sau.
3. Tạo PostgreSQL ở nhà cung cấp hosting hỗ trợ; sao chép connection string (không chia sẻ công khai).
4. Tạo Web Service Python từ repository, dùng lệnh build `pip install -r requirements.txt` và start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Thiết lập `DATABASE_URL`, `SESSION_SECRET` (ngẫu nhiên dài), `COOKIE_SECURE=1` trong dashboard hosting. Chỉ sử dụng HTTPS.
6. **Khởi tạo tài khoản quản trị:** `seed.py` có bước hỏi mật khẩu tương tác; cần chạy từ terminal/shell của nhà cung cấp, hoặc khởi tạo tại máy tính. Không chạy seed với dữ liệu thật. Không thể đăng nhập khi chưa seed.
7. Truy cập URL hosting cung cấp và `/login`. Kiểm tra bằng dữ liệu giả.

## Giới hạn
- Miễn phí và khả năng truy cập shell/PostgreSQL phụ thuộc nhà cung cấp, không bảo đảm có gói miễn phí.
- Chưa có migration schema, backup PostgreSQL tự động, kiểm thử bảo mật, rate limiting và chuẩn quản lý hồ sơ y tế.
- `Base.metadata.create_all` không thay thế migration; thay đổi cấu trúc bảng sau này cần Alembic.
- Không đưa thông tin bệnh nhân thật, hình ảnh X-quang, số điện thoại thật lên bản demo công khai.
