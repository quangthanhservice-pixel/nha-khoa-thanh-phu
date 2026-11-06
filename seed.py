import os, getpass
from app.main import Base,engine,SessionLocal,password_hash
from app.models import Branch,User,Service,Chair
from sqlalchemy import select

def run():
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        if s.scalar(select(User).limit(1)):
            print('Đã có tài khoản. Không tạo lại để tránh ghi đè dữ liệu.'); return
        password=os.getenv('ADMIN_PASSWORD') or getpass.getpass('Đặt mật khẩu chủ phòng khám (ít nhất 10 ký tự): ')
        if len(password)<10: raise SystemExit('Mật khẩu cần ít nhất 10 ký tự')
        b=Branch(name='Nha Khoa Thạnh Phú - Cơ sở 1',address='Cập nhật địa chỉ tại trang quản trị'); s.add(b); s.flush()
        s.add(User(username='admin',full_name='Quản trị hệ thống',password_hash=password_hash(password),role='owner',branch_id=b.id))
        s.add(Chair(name='Ghế nha 01',branch_id=b.id))
        for name,price in [('Khám tổng quát và tư vấn',100000),('Cạo vôi và đánh bóng toàn hàm',200000),('Chụp X-quang quanh chóp',80000)]: s.add(Service(name=name,price=price))
        s.commit(); print('Khởi tạo xong! Tài khoản: admin | http://127.0.0.1:8000/login')
if __name__=='__main__': run()
