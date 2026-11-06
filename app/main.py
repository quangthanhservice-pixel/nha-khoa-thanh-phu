import os, secrets, hashlib, hmac, html
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session
from .models import *

ROOT=Path(__file__).resolve().parent.parent
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
DB_URL=os.getenv('DATABASE_URL',f'sqlite:///{ROOT / "dental.db"}')
engine=create_engine(DB_URL,connect_args={'check_same_thread':False} if DB_URL.startswith('sqlite') else {},pool_pre_ping=True)
SessionLocal=sessionmaker(bind=engine,expire_on_commit=False)
app=FastAPI(title='Nha Khoa Thạnh Phú')
app.add_middleware(SessionMiddleware,secret_key=os.getenv('SESSION_SECRET',secrets.token_hex(32)),same_site='lax',https_only=os.getenv('COOKIE_SECURE','0')=='1')
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
templates=Jinja2Templates(directory=str(ROOT/'templates'))
ROLES={'owner','manager','reception','doctor','cashier','inventory'}
PERMISSIONS={'branches':{'owner'},'users':{'owner','manager'},'patients':{'owner','manager','reception','doctor'},'appointments':{'owner','manager','reception','doctor'},'services':{'owner','manager','reception'},'treatments':{'owner','manager','doctor'},'invoices':{'owner','manager','cashier'},'inventory':{'owner','manager','inventory'},'expenses':{'owner','manager','cashier'},'reminders':{'owner','manager','reception'},'pages':{'owner','manager'},'audit':{'owner','manager'}}

PERMISSIONS['booking_requests'] = {
    'owner',
    'manager',
    'reception',
}

def password_hash(p):
    salt=secrets.token_bytes(16); key=hashlib.pbkdf2_hmac('sha256',p.encode(),salt,260000)
    return 'pbkdf2_sha256$260000$'+salt.hex()+'$'+key.hex()
def verify_password(p,encoded):
    try:
        _,iters,salt,stored=encoded.split('$'); calculated=hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),int(iters)); return hmac.compare_digest(calculated,bytes.fromhex(stored))
    except Exception: return False

def db():
    with SessionLocal() as s: yield s

def user_from_request(request,s):
    uid=request.session.get('uid'); return s.get(User,uid) if uid else None

def require(request,s,module=None):
    user=user_from_request(request,s)
    if not user or not user.active: raise HTTPException(401,'Bạn cần đăng nhập')
    if module and user.role not in PERMISSIONS[module]: raise HTTPException(403,'Không có quyền truy cập')
    return user

def branch_id(request,user):
    if user.role=='owner':
        try: return int(request.session.get('branch_id') or user.branch_id)
        except (TypeError,ValueError): raise HTTPException(400,'Chi nhánh không hợp lệ')
    return user.branch_id

def csrf(request,token):
    if not token or not hmac.compare_digest(str(token),str(request.session.get('csrf',''))): raise HTTPException(403,'CSRF token không hợp lệ')

def esc(value): return html.escape(str(value if value is not None else ''),quote=True)
def money(value): return f'{Decimal(value):,.0f} đ'
def redirect(path): return RedirectResponse(path,status_code=303)
def audit(s,user,action,entity,entity_id,bid=None): s.add(AuditLog(actor_id=user.id,branch_id=bid or user.branch_id,action=action,entity=entity,entity_id=entity_id))
def page(title,body,request=None,user=None,active=''):
    menu=[('dashboard','Tổng quan','/admin'),('patients','Bệnh nhân','/admin/patients'),('appointments','Lịch hẹn','/admin/appointments'),('booking_requests','Yêu cầu đặt lịch','/admin/booking-requests'),('treatments','Điều trị','/admin/treatments'),('services','Dịch vụ','/admin/services'),('invoices','Thu ngân','/admin/invoices'),('inventory','Kho vật tư','/admin/inventory'),('expenses','Chi phí','/admin/expenses'),('reminders','Tái khám','/admin/reminders'),('pages','Nội dung web','/admin/pages'),('users','Nhân viên','/admin/users'),('branches','Chi nhánh','/admin/branches'),('audit','Nhật ký','/admin/audit')]
    nav=''; top=''
    if user:
        nav='<aside><div class="brand">✚ THẠNH PHÚ <small>DENTAL MANAGEMENT</small></div>'+''.join(f'<a class="{"selected" if active==k else ""}" href="{url}">{esc(label)}</a>' for k,label,url in menu if k=='dashboard' or user.role in PERMISSIONS.get(k,set()))+'</aside>'
        token=request.session.get('csrf','')
        top=f'<header><b>{esc(title)}</b><div>{esc(user.full_name)} · {esc(user.role)} <form method="post" action="/logout" class="inline"><input type="hidden" name="csrf_token" value="{esc(token)}"><button class="outline">Đăng xuất</button></form></div></header>'
    return HTMLResponse(f'<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)} | Nha Khoa Thạnh Phú</title><link rel="stylesheet" href="/static/style.css"></head><body><div class="layout">{nav}<main>{top}<div class="content">{body}</div></main></div></body></html>')
def form_open(request,action): return f'<form method="post" action="{esc(action)}"><input type="hidden" name="csrf_token" value="{esc(request.session["csrf"])}">'
def field(label,name,typ='text',required=True,extra=''): return f'<label>{esc(label)}<input name="{esc(name)}" type="{esc(typ)}" {"required" if required else ""} {extra}></label>'
def select_field(label,name,rows,selected=None): return f'<label>{esc(label)}<select name="{esc(name)}">'+''.join(f'<option value="{r[0]}" {"selected" if str(r[0])==str(selected) else ""}>{esc(r[1])}</option>' for r in rows)+'</select></label>'
def card_form(request,action,fields,button='Lưu'): return '<section class="card"><h3>Thêm mới</h3>'+form_open(request,action)+'<div class="fields">'+fields+'</div><button>'+esc(button)+'</button></form></section>'
def table(headers,rows): return '<div class="card scroll"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(cell)+'</td>' for cell in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def scoped(s,model,bid): return s.scalars(select(model).where(model.branch_id==bid).order_by(model.id.desc())).all()
def patient_options(s,bid): return [(p.id,p.full_name+' · '+p.phone) for p in scoped(s,Patient,bid)]
def validate_patient(s,pid,bid):
    p=s.get(Patient,pid)
    if not p or p.branch_id!=bid: raise HTTPException(400,'Bệnh nhân không thuộc chi nhánh này')
    return p

def admin_view(request,s,module,title,content):
    u=require(request,s,module if module!='dashboard' else None)
    return page(title,content,request,u,module)

@app.on_event('startup')
def startup(): Base.metadata.create_all(engine)

@app.get('/')
def home(request: Request, s: Session = Depends(db)):
    if 'csrf' not in request.session:
        request.session['csrf'] = secrets.token_urlsafe(32)

    services = s.scalars(
        select(Service)
        .where(Service.active == True)
        .limit(8)
    ).all()

    branches = s.scalars(
        select(Branch)
        .where(Branch.active == True)
    ).all()

    return templates.TemplateResponse(
        request=request,
        name='home.html',
        context={
            'services': services,
            'branches': branches,
            'csrf_token': request.session['csrf'],
        },
    )

@app.post('/booking')
def submit_booking(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(...),
    branch_id: int = Form(...),
    preferred_date: str = Form(...),
    preferred_time: str = Form(...),
    csrf_token: str = Form(...),
    website: str = Form(''),
    s: Session = Depends(db),
):
    # Kiem tra CSRF
    csrf(request, csrf_token)

    # Kiem tra honeypot
    if website.strip():
        raise HTTPException(
            400, 'Yêu cầu không hợp lệ'
        )


    # Gioi han gui yeu cau trong moi phien
    last_booking = request.session.get('last_booking_at')
    current_time = datetime.now(timezone.utc).timestamp()

    if last_booking is not None:
        try:
            elapsed = current_time - float(last_booking)
        except (TypeError, ValueError):
            elapsed = 0

        if elapsed < 60:
            raise HTTPException(
                429,
                'Vui lòng đợi 60 giây trước khi gửi yêu cầu tiếp theo'
            )

    # Kiem tra ho ten
    full_name = ' '.join(full_name.split())
    if not 2 <= len(full_name) <= 150:
        raise HTTPException(
            400, 'Họ tên phải có từ 2 đến 150 ký tự'
        )

    # Kiem tra so dien thoai Viet Nam
    import re
    phone = re.sub(r'[\s.\-()]', '', phone.strip())

    if not re.fullmatch(r'(?:\+84|0)[35789]\d{8}', phone):
        raise HTTPException(
            400, 'Số điện thoại không hợp lệ'
        )

    # Kiem tra chi nhanh
    branch = s.get(Branch, branch_id)
    if not branch or not branch.active:
        raise HTTPException(
            400, 'Chi nhánh không hợp lệ'
        )

    # Kiem tra ngay gio kham theo gio Viet Nam
    try:
        local_dt = datetime.strptime(
            preferred_date + ' ' + preferred_time,
            '%Y-%m-%d %H:%M'
        ).replace(tzinfo=VN_TZ)
    except ValueError:
        raise HTTPException(
            400, 'Ngày giờ khám không hợp lệ'
        )

    now_vn = datetime.now(VN_TZ)

    if local_dt <= now_vn:
        raise HTTPException(
            400, 'Vui lòng chọn thời gian trong tương lai'
        )

    if local_dt > now_vn + timedelta(days=90):
        raise HTTPException(
            400, 'Chỉ nhận lịch trong vòng 90 ngày'
        )

    # Luu thoi gian UTC dang naive
    preferred_utc = local_dt.astimezone(
        timezone.utc
    ).replace(tzinfo=None)

    booking = AppointmentRequest(
        branch_id=branch.id,
        full_name=full_name,
        phone=phone,
        preferred_at=preferred_utc,
        status='pending',
    )


    s.add(booking)
    s.commit()

    request.session['last_booking_at'] = current_time

    return redirect('/?booking=success#dat-lich')


@app.get('/login')
def login_form(request:Request):
    if 'csrf' not in request.session: request.session['csrf']=secrets.token_urlsafe(24)
    body='<div class="login card"><h2>Đăng nhập quản trị</h2>'+form_open(request,'/login')+field('Tên đăng nhập','username')+field('Mật khẩu','password','password')+'<button>Đăng nhập</button></form></div>'
    return page('Đăng nhập',body)
@app.post('/login')
def login(request:Request,username:str=Form(...),password:str=Form(...),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token)
    u=s.scalar(select(User).where(User.username==username))
    if not u or not u.active or not verify_password(password,u.password_hash): return HTMLResponse('Sai tên đăng nhập hoặc mật khẩu. <a href="/login">Thử lại</a>',status_code=401)
    request.session.clear(); request.session['uid']=u.id; request.session['branch_id']=u.branch_id; request.session['csrf']=secrets.token_urlsafe(24)
    return redirect('/admin')

@app.post('/logout')
def logout(request:Request,csrf_token:str=Form(...)):
    csrf(request,csrf_token); request.session.clear(); return redirect('/login')
@app.get('/admin')
def dashboard(request:Request,s:Session=Depends(db)):
    u=require(request,s); bid=branch_id(request,u)
    if not s.get(Branch,bid): raise HTTPException(400,'Chưa cấu hình chi nhánh')
    patients=scoped(s,Patient,bid); appts=scoped(s,Appointment,bid); invoices=scoped(s,Invoice,bid); expenses=scoped(s,Expense,bid)
    revenue=sum((i.paid or 0 for i in invoices),Decimal(0)); cost=sum((e.amount for e in expenses),Decimal(0))
    stats=[('Bệnh nhân',len(patients)),('Lịch hẹn',len(appts)),('Đã thu',money(revenue)),('Chi phí',money(cost)),('Công nợ',money(sum((i.total-i.paid for i in invoices),Decimal(0)))),('Chênh lệch thu - chi',money(revenue-cost))]
    content='<div class="stats">'+''.join(f'<div class="card"><small>{esc(k)}</small><h2>{esc(v)}</h2></div>' for k,v in stats)+'</div>'
    if u.role=='owner':
        branches=s.scalars(select(Branch)).all(); content+=form_open(request,'/admin/switch-branch')+select_field('Chi nhánh đang xem','branch_id',[(b.id,b.name) for b in branches],bid)+'<button>Chuyển chi nhánh</button></form>'
    content+='<h3>Lịch hẹn gần đây</h3>'+table(['Bệnh nhân','Bắt đầu','Trạng thái'],[(esc(s.get(Patient,a.patient_id).full_name),esc(a.starts_at),esc(a.status)) for a in appts[:10]])
    return page('Tổng quan',content,request,u,'dashboard')
@app.post('/admin/switch-branch')
def switch_branch(request:Request,branch_id_value:int=Form(None,alias='branch_id'),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token); u=require(request,s,'branches')
    if not s.get(Branch,branch_id_value): raise HTTPException(400,'Chi nhánh không tồn tại')
    request.session['branch_id']=branch_id_value; return redirect('/admin')

@app.get('/admin/booking-requests')
def booking_requests(request: Request, s: Session = Depends(db)):
    u = require(request, s, 'booking_requests')
    bid = branch_id(request, u)

    requests = scoped(s, AppointmentRequest, bid)

    rows = []
    for item in requests:
        vn_time = item.preferred_at.replace(
            tzinfo=timezone.utc
        ).astimezone(VN_TZ)


        actions = 'Đã xử lý'

        if item.status == 'pending':
            token = esc(request.session['csrf'])
            action_url = f'/admin/booking-requests/{item.id}/status'

            actions = (
                f'<form method="post" action="{action_url}">'
                f'<input type="hidden" name="csrf_token" value="{token}">'
                '<input type="hidden" name="status" value="confirmed">'
                '<button type="submit">Xác nhận</button>'
                '</form>'
                f'<form method="post" action="{action_url}">'
                f'<input type="hidden" name="csrf_token" value="{token}">'
                '<input type="hidden" name="status" value="rejected">'
                '<button type="submit" class="outline">Từ chối</button>'
                '</form>'
            )

        rows.append((
            item.id,
            esc(item.full_name),
            esc(item.phone),
            esc(vn_time.strftime('%d/%m/%Y %H:%M')),
            esc(item.status),
            actions,
        ))


    content = (
        '<h3>Danh sách yêu cầu đặt lịch trực tuyến</h3>'
        '<p>Đây là yêu cầu chờ nhân viên liên hệ, '
        'chưa phải lịch khám được xác nhận.</p>'
    )


    content += table(
        [
            'Mã',
            'Họ tên',
            'Số điện thoại',
            'Ngày giờ mong muốn',
            'Trạng thái',
            'Thao tác',
        ],
        rows
    )

    return page(
        'Yêu cầu đặt lịch',
        content,
        request,
        u,
        'booking_requests'
    )

@app.post('/admin/booking-requests/{request_id}/status')
def update_booking_request_status(
    request_id: int,
    request: Request,
    status: str = Form(...),
    csrf_token: str = Form(...),
    s: Session = Depends(db),
):
    csrf(request, csrf_token)
    u = require(request, s, 'booking_requests')
    bid = branch_id(request, u)

    booking = s.get(AppointmentRequest, request_id)

    if not booking or booking.branch_id != bid:
        raise HTTPException(404, 'Không tìm thấy yêu cầu đặt lịch')

    if status not in {'confirmed', 'rejected'}:
        raise HTTPException(400, 'Trạng thái không hợp lệ')

    if booking.status != 'pending':
        raise HTTPException(409, 'Yêu cầu này đã được xử lý')

    booking.status = status

    audit(
        s,
        u,
        'update_status',
        'appointment_request',
        booking.id,
        bid
    )

    s.commit()

    return redirect('/admin/booking-requests')

@app.get('/admin/patients')
def patients(request:Request,s:Session=Depends(db)):
    u=require(request,s,'patients'); bid=branch_id(request,u)
    f=field('Họ tên','full_name')+field('Số điện thoại','phone',required=False)+field('Ngày sinh','birth_date','date',False)+field('Địa chỉ','address',required=False)+field('Ghi chú y khoa','medical_note',required=False)
    content=card_form(request,'/admin/patients',f)+table(['Mã','Họ tên','Điện thoại','Ngày sinh','Ghi chú'],[(p.id,esc(p.full_name),esc(p.phone),esc(p.birth_date),esc(p.medical_note)) for p in scoped(s,Patient,bid)])
    return page('Bệnh nhân',content,request,u,'patients')
@app.post('/admin/patients')
def add_patient(request:Request,full_name:str=Form(...),phone:str=Form(''),birth_date:str=Form(''),address:str=Form(''),medical_note:str=Form(''),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token); u=require(request,s,'patients'); bid=branch_id(request,u)
    p=Patient(branch_id=bid,full_name=full_name.strip(),phone=phone,birth_date=birth_date,address=address,medical_note=medical_note); s.add(p); s.flush(); audit(s,u,'create','patient',p.id,bid); s.commit(); return redirect('/admin/patients')

@app.get('/admin/appointments')
def appointments(request:Request,s:Session=Depends(db)):
    u=require(request,s,'appointments'); bid=branch_id(request,u)
    chairs=scoped(s,Chair,bid)
    f=select_field('Bệnh nhân','patient_id',patient_options(s,bid))+select_field('Ghế nha','chair_id',[(0,'Chưa phân ghế')]+[(c.id,c.name) for c in chairs])+field('Bắt đầu','starts_at','datetime-local')+field('Kết thúc','ends_at','datetime-local')+field('Ghi chú','note',required=False)
    addchair=card_form(request,'/admin/chairs',field('Tên ghế nha','name'),'Thêm ghế')
    content=card_form(request,'/admin/appointments',f)+addchair+table(['Bệnh nhân','Ghế','Bắt đầu','Kết thúc','Trạng thái'],[(esc(s.get(Patient,a.patient_id).full_name),esc(s.get(Chair,a.chair_id).name if a.chair_id else '—'),esc(a.starts_at),esc(a.ends_at),esc(a.status)) for a in scoped(s,Appointment,bid)])
    return page('Lịch hẹn và ghế nha',content,request,u,'appointments')
@app.post('/admin/chairs')
def add_chair(request:Request,name:str=Form(...),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token); u=require(request,s,'appointments'); bid=branch_id(request,u); c=Chair(name=name,branch_id=bid); s.add(c); s.flush(); audit(s,u,'create','chair',c.id,bid); s.commit(); return redirect('/admin/appointments')
@app.post('/admin/appointments')
def add_appointment(request:Request,patient_id:int=Form(...),chair_id:int=Form(0),starts_at:str=Form(...),ends_at:str=Form(...),note:str=Form(''),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token); u=require(request,s,'appointments'); bid=branch_id(request,u); validate_patient(s,patient_id,bid)
    try: start=datetime.fromisoformat(starts_at); end=datetime.fromisoformat(ends_at)
    except ValueError: raise HTTPException(400,'Ngày giờ không hợp lệ')
    if end<=start: raise HTTPException(400,'Giờ kết thúc phải sau giờ bắt đầu')
    if chair_id:
        c=s.get(Chair,chair_id)
        if not c or c.branch_id!=bid: raise HTTPException(400,'Ghế không hợp lệ')
        conflict=s.scalar(select(Appointment).where(Appointment.chair_id==chair_id,Appointment.status!='cancelled',Appointment.starts_at<end,Appointment.ends_at>start))
        if conflict: raise HTTPException(409,'Ghế đã có lịch trong khoảng thời gian này')
    a=Appointment(branch_id=bid,patient_id=patient_id,chair_id=chair_id or None,starts_at=start,ends_at=end,note=note); s.add(a); s.flush(); audit(s,u,'create','appointment',a.id,bid); s.commit(); return redirect('/admin/appointments')

@app.get('/admin/services')
def services(request:Request,s:Session=Depends(db)):
    u=require(request,s,'services'); content=card_form(request,'/admin/services',field('Tên dịch vụ','name')+field('Giá (VNĐ)','price','number',extra='min="0" step="1000"')+field('Số phút','duration_minutes','number',extra='min="1"'))+table(['Tên dịch vụ','Giá','Thời gian'],[(esc(x.name),money(x.price),f'{x.duration_minutes} phút') for x in s.scalars(select(Service).order_by(Service.id.desc())).all()]); return page('Bảng giá dịch vụ',content,request,u,'services')
@app.post('/admin/services')
def add_service(request:Request,name:str=Form(...),price:Decimal=Form(...),duration_minutes:int=Form(30),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token); u=require(request,s,'services')
    if price<0 or duration_minutes<1: raise HTTPException(400,'Giá hoặc thời gian không hợp lệ')
    x=Service(name=name,price=price,duration_minutes=duration_minutes); s.add(x); s.flush(); audit(s,u,'create','service',x.id); s.commit(); return redirect('/admin/services')

@app.get('/admin/treatments')
def treatments(request:Request,s:Session=Depends(db)):
    u=require(request,s,'treatments'); bid=branch_id(request,u)
    f=select_field('Bệnh nhân','patient_id',patient_options(s,bid))+field('Số răng (FDI)','tooth_number',required=False)+field('Chẩn đoán','diagnosis',required=False)+field('Kế hoạch điều trị','plan',required=False)
    content=card_form(request,'/admin/treatments',f)+table(['Bệnh nhân','Răng','Chẩn đoán','Kế hoạch'],[(esc(s.get(Patient,t.patient_id).full_name),esc(t.tooth_number),esc(t.diagnosis),esc(t.plan)) for t in scoped(s,Treatment,bid)]); return page('Hồ sơ điều trị',content,request,u,'treatments')
@app.post('/admin/treatments')
def add_treatment(request:Request,patient_id:int=Form(...),tooth_number:str=Form(''),diagnosis:str=Form(''),plan:str=Form(''),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token); u=require(request,s,'treatments'); bid=branch_id(request,u); validate_patient(s,patient_id,bid)
    t=Treatment(branch_id=bid,patient_id=patient_id,doctor_id=u.id if u.role=='doctor' else None,tooth_number=tooth_number,diagnosis=diagnosis,plan=plan); s.add(t); s.flush(); audit(s,u,'create','treatment',t.id,bid); s.commit(); return redirect('/admin/treatments')

@app.get('/admin/invoices')
def invoices(request:Request,s:Session=Depends(db)):
    u=require(request,s,'invoices'); bid=branch_id(request,u)
    f=select_field('Bệnh nhân','patient_id',patient_options(s,bid))+field('Tổng tiền (VNĐ)','total','number',extra='min="0" step="1000"')+field('Ghi chú','note',required=False)
    rows=[]
    for i in scoped(s,Invoice,bid):
        pay=form_open(request,f'/admin/invoices/{i.id}/pay')+f'<input name="amount" type="number" min="1" max="{i.total-i.paid}" placeholder="Số tiền" required><button>Thu</button></form>' if i.total>i.paid else 'Đã thanh toán'
        rows.append((i.id,esc(s.get(Patient,i.patient_id).full_name),money(i.total),money(i.paid),money(i.total-i.paid),pay))
    return page('Thu ngân và công nợ',card_form(request,'/admin/invoices',f)+table(['Mã','Bệnh nhân','Tổng','Đã thu','Còn nợ','Thanh toán'],rows),request,u,'invoices')
@app.post('/admin/invoices')
def add_invoice(request:Request,patient_id:int=Form(...),total:Decimal=Form(...),note:str=Form(''),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token); u=require(request,s,'invoices'); bid=branch_id(request,u); validate_patient(s,patient_id,bid)
    if total<0: raise HTTPException(400,'Tổng tiền không hợp lệ')
    i=Invoice(branch_id=bid,patient_id=patient_id,total=total,paid=0,note=note); s.add(i); s.flush(); audit(s,u,'create','invoice',i.id,bid); s.commit(); return redirect('/admin/invoices')
@app.post('/admin/invoices/{invoice_id}/pay')
def pay_invoice(invoice_id:int,request:Request,amount:Decimal=Form(...),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token); u=require(request,s,'invoices'); bid=branch_id(request,u); i=s.get(Invoice,invoice_id)
    if not i or i.branch_id!=bid: raise HTTPException(404,'Không tìm thấy hóa đơn')
    if amount<=0 or i.paid+amount>i.total: raise HTTPException(400,'Số tiền thu không hợp lệ')
    i.paid+=amount; s.add(Payment(invoice_id=i.id,amount=amount)); audit(s,u,'payment','invoice',i.id,bid); s.commit(); return redirect('/admin/invoices')

@app.get('/admin/inventory')
def inventory(request:Request,s:Session=Depends(db)):
    u=require(request,s,'inventory'); bid=branch_id(request,u)
    f=field('Tên vật tư','name')+field('SKU','sku')+field('Đơn vị','unit',required=False)+field('Tồn đầu kỳ','quantity','number',extra='min="0"')+field('Tồn tối thiểu','minimum_quantity','number',extra='min="0"')
    rows=[]
    for x in scoped(s,InventoryItem,bid):
        move=form_open(request,f'/admin/inventory/{x.id}/move')+'<input type="number" name="delta" placeholder="+ nhập / - xuất" required><button>Cập nhật</button></form>'
        rows.append((esc(x.sku),esc(x.name),x.quantity,esc(x.unit),x.minimum_quantity,'⚠ Thấp' if x.quantity<=x.minimum_quantity else 'Đủ',move))
    return page('Kho vật tư',card_form(request,'/admin/inventory',f)+table(['SKU','Vật tư','Tồn','ĐVT','Tối thiểu','Cảnh báo','Nhập/Xuất'],rows),request,u,'inventory')
@app.post('/admin/inventory')
def add_item(request:Request,name:str=Form(...),sku:str=Form(...),unit:str=Form('cái'),quantity:int=Form(0),minimum_quantity:int=Form(0),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token); u=require(request,s,'inventory'); bid=branch_id(request,u)
    if quantity<0 or minimum_quantity<0: raise HTTPException(400,'Số lượng không hợp lệ')
    if s.scalar(select(InventoryItem).where(InventoryItem.branch_id==bid,InventoryItem.sku==sku)): raise HTTPException(409,'SKU đã tồn tại')
    x=InventoryItem(branch_id=bid,name=name,sku=sku,unit=unit,quantity=quantity,minimum_quantity=minimum_quantity); s.add(x); s.flush(); s.add(StockMovement(branch_id=bid,item_id=x.id,delta=quantity,reason='Tồn đầu kỳ')); audit(s,u,'create','inventory',x.id,bid); s.commit(); return redirect('/admin/inventory')
@app.post('/admin/inventory/{item_id}/move')
def move_item(item_id:int,request:Request,delta:int=Form(...),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token); u=require(request,s,'inventory'); bid=branch_id(request,u); x=s.get(InventoryItem,item_id)
    if not x or x.branch_id!=bid: raise HTTPException(404,'Không tìm thấy vật tư')
    
    if delta == 0 or x.quantity + delta < 0:
        if delta < 0 and x.quantity + delta < 0:
            title = "Không thể xuất kho"
            message = "Số lượng yêu cầu vượt quá số lượng hiện có."
        else:
            title = "Số lượng không hợp lệ"
            message = "Vui lòng nhập số lượng khác 0."

        content = f"""
        <section class="card" style="max-width:620px;margin:35px auto">
            <h2 style="color:#a51f2e">⚠ {title}</h2>
            <p>{message}</p>
            <p><strong>Vật tư:</strong> {esc(x.name)}</p>
            <p><strong>Tồn kho hiện tại:</strong>
               {x.quantity} {esc(x.unit)}</p>
            <p><strong>Số lượng yêu cầu xuất:</strong>
               {abs(delta) if delta < 0 else 0} {esc(x.unit)}</p>
            <p style="color:#16803c">
                Dữ liệu tồn kho không thay đổi.
            </p>
            <a class="button" href="/admin/inventory">
                Quay lại kho vật tư
            </a>
        </section>
        """
        response = page(
            title, content, request, u, "inventory"
        )
        response.status_code = 400
        return response
    x.quantity+=delta; s.add(StockMovement(branch_id=bid,item_id=x.id,delta=delta,reason='Điều chỉnh thủ công')); audit(s,u,'stock_move','inventory',x.id,bid); s.commit(); return redirect('/admin/inventory')

@app.get('/admin/expenses')
def expenses(request:Request,s:Session=Depends(db)):
    u=require(request,s,'expenses'); bid=branch_id(request,u); f=field('Nhóm chi phí','category')+field('Số tiền','amount','number',extra='min="1" step="1000"')+field('Ghi chú','note',required=False)
    return page('Chi phí',card_form(request,'/admin/expenses',f)+table(['Nhóm','Số tiền','Ghi chú'],[(esc(e.category),money(e.amount),esc(e.note)) for e in scoped(s,Expense,bid)]),request,u,'expenses')
@app.post('/admin/expenses')
def add_expense(request:Request,category:str=Form(...),amount:Decimal=Form(...),note:str=Form(''),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token); u=require(request,s,'expenses'); bid=branch_id(request,u)
    if amount<=0: raise HTTPException(400,'Số tiền phải lớn hơn 0')
    e=Expense(branch_id=bid,category=category,amount=amount,note=note); s.add(e); s.flush(); audit(s,u,'create','expense',e.id,bid); s.commit(); return redirect('/admin/expenses')

@app.get('/admin/reminders')
def reminders(request:Request,s:Session=Depends(db)):
    u=require(request,s,'reminders'); bid=branch_id(request,u); f=select_field('Bệnh nhân','patient_id',patient_options(s,bid))+field('Ngày nhắc','due_date','date')+field('Nội dung','content')
    return page('Nhắc lịch tái khám',card_form(request,'/admin/reminders',f)+table(['Bệnh nhân','Ngày','Nội dung','Trạng thái'],[(esc(s.get(Patient,r.patient_id).full_name),esc(r.due_date),esc(r.content),esc(r.status)) for r in scoped(s,Reminder,bid)]),request,u,'reminders')
@app.post('/admin/reminders')
def add_reminder(request:Request,patient_id:int=Form(...),due_date:str=Form(...),content:str=Form(...),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token); u=require(request,s,'reminders'); bid=branch_id(request,u); validate_patient(s,patient_id,bid)
    r=Reminder(branch_id=bid,patient_id=patient_id,due_date=due_date,content=content); s.add(r); s.flush(); audit(s,u,'create','reminder',r.id,bid); s.commit(); return redirect('/admin/reminders')

@app.get('/admin/pages')
def pages(request:Request,s:Session=Depends(db)):
    u=require(request,s,'pages'); f=field('Slug','slug')+field('Tiêu đề','title')+field('Mô tả SEO','seo_description',required=False)+field('Nội dung','body',required=False)
    return page('Quản lý nội dung web',card_form(request,'/admin/pages',f)+table(['Slug','Tiêu đề','Xuất bản'],[(esc(p.slug),esc(p.title),'Có' if p.published else 'Chưa') for p in s.scalars(select(ContentPage)).all()]),request,u,'pages')
@app.post('/admin/pages')
def add_page(request:Request,slug:str=Form(...),title:str=Form(...),seo_description:str=Form(''),body:str=Form(''),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token); u=require(request,s,'pages')
    if not slug.replace('-','').isalnum(): raise HTTPException(400,'Slug chỉ gồm chữ, số và dấu gạch ngang')
    if s.scalar(select(ContentPage).where(ContentPage.slug==slug)): raise HTTPException(409,'Slug đã tồn tại')
    p=ContentPage(slug=slug,title=title,seo_description=seo_description,body=body,published=False); s.add(p); s.flush(); audit(s,u,'create','page',p.id); s.commit(); return redirect('/admin/pages')
@app.get('/p/{slug}')
def public_page(slug:str,s:Session=Depends(db)):
    p=s.scalar(select(ContentPage).where(ContentPage.slug==slug,ContentPage.published==True))
    if not p: raise HTTPException(404)
    return page(p.title,f'<div class="card"><h1>{esc(p.title)}</h1><p>{esc(p.body)}</p></div>')

@app.get('/admin/branches')
def branches(request:Request,s:Session=Depends(db)):
    u=require(request,s,'branches')
    f=(field('Tên chi nhánh','name')
       +field('Địa chỉ','address',required=False)
       +field('Số điện thoại','phone',required=False))

    rows=[]
    for b in s.scalars(select(Branch).order_by(Branch.id)).all():
        edit_link=(
            f'<a href="/admin/branches/{b.id}/edit">'
            'Sửa</a>'
        )
        rows.append((
            b.id,esc(b.name),esc(b.address),
            esc(b.phone),edit_link
        ))

    return page(
        'Quản lý chi nhánh',
        card_form(request,'/admin/branches',f)
        +table(
            ['Mã','Chi nhánh','Địa chỉ','Điện thoại','Thao tác'],
            rows
        ),
        request,u,'branches'
    )

@app.post('/admin/branches')
def add_branch(request:Request,name:str=Form(...),address:str=Form(''),phone:str=Form(''),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token)
    u=require(request,s,'branches')
    b=Branch(name=name,address=address,phone=phone)
    s.add(b)
    s.flush()
    audit(s,u,'create','branch',b.id)
    s.commit()
    return redirect('/admin/branches')

@app.get('/admin/branches/{branch_id}/edit')
def edit_branch_page(branch_id:int,request:Request,s:Session=Depends(db)):
    u=require(request,s,'branches')
    b=s.get(Branch,branch_id)
    if not b:
        raise HTTPException(404,'Không tìm thấy chi nhánh')

    f=(
        '<p><strong>Chi nhánh:</strong> '+esc(b.name)+'</p>'
        +'<input type="hidden" name="branch_id" value="'+str(b.id)+'">'
        +'<label>Tên chi nhánh'
        +'<input name="name" required maxlength="150" value="'+esc(b.name)+'">'
        +'</label>'
        +'<label>Địa chỉ'
        +'<input name="address" maxlength="500" value="'+esc(b.address or '')+'">'
        +'</label>'
        +'<label>Số điện thoại'
        +'<input name="phone" maxlength="30" value="'+esc(b.phone or '')+'">'
        +'</label>'
    )

    return page(
        'Sửa chi nhánh',
        card_form(request,f'/admin/branches/{b.id}/edit',f)
        +'<p><a href="/admin/branches">← Quay lại danh sách</a></p>',
        request,u,'branches'
    )

@app.post('/admin/branches/{branch_id}/edit')
def update_branch(
    branch_id:int,
    request:Request,
    name:str=Form(...),
    address:str=Form(''),
    phone:str=Form(''),
    csrf_token:str=Form(...),
    s:Session=Depends(db)
):
    csrf(request,csrf_token)
    u=require(request,s,'branches')

    b=s.get(Branch,branch_id)
    if not b:
        raise HTTPException(404,'Không tìm thấy chi nhánh')

    name=name.strip()
    address=address.strip()
    phone=phone.strip()

    if not name or len(name)>150 or len(address)>500 or len(phone)>30:
        raise HTTPException(400,'Thông tin chi nhánh không hợp lệ')

    b.name=name
    b.address=address
    b.phone=phone

    audit(s,u,'update','branch',b.id)
    s.commit()
    return redirect('/admin/branches')

@app.get('/admin/users')
def users(request:Request,s:Session=Depends(db)):
    u=require(request,s,'users'); bid=branch_id(request,u); branches=s.scalars(select(Branch)).all()
    f=field('Tài khoản','username')+field('Họ tên','full_name')+field('Mật khẩu','password','password')+select_field('Vai trò','role',[(r,r) for r in sorted(ROLES)])+select_field('Chi nhánh','branch_id',[(b.id,b.name) for b in branches if u.role=='owner' or b.id==bid])
    staff_query = select(User)

    if u.role != 'owner':
        staff_query = staff_query.where(User.branch_id == bid)

    staff = s.scalars(
        staff_query.order_by(User.id.desc())
    ).all()

    
    branch_names = {b.id: b.name for b in branches}

    rows = [
        (
            esc(x.username),
            esc(x.full_name),
            esc(x.role),
            esc(branch_names.get(x.branch_id, "Không xác định"))
        )
        for x in staff
    ]

    return page(
        'Nhân viên và phân quyền',
        card_form(request, '/admin/users', f)
        + table(
            ['Tên đăng nhập', 'Họ tên', 'Vai trò', 'Chi nhánh'],
            rows
        ),
        request, u, 'users'
    )

@app.post('/admin/users')
def add_user(request:Request,username:str=Form(...),full_name:str=Form(...),password:str=Form(...),role:str=Form(...),branch_id_value:int=Form(...,alias='branch_id'),csrf_token:str=Form(...),s:Session=Depends(db)):
    csrf(request,csrf_token); u=require(request,s,'users')
    if role not in ROLES or (role=='owner' and u.role!='owner'): raise HTTPException(403,'Vai trò không hợp lệ')
    if u.role!='owner' and branch_id_value!=u.branch_id: raise HTTPException(403,'Không được tạo nhân viên chi nhánh khác')
    if not s.get(Branch,branch_id_value) or len(password)<10: raise HTTPException(400,'Chi nhánh không hợp lệ hoặc mật khẩu dưới 10 ký tự')
    if s.scalar(select(User).where(User.username==username)): raise HTTPException(409,'Tên đăng nhập đã tồn tại')
    x=User(username=username,full_name=full_name,password_hash=password_hash(password),role=role,branch_id=branch_id_value); s.add(x); s.flush(); audit(s,u,'create','user',x.id,branch_id_value); s.commit(); return redirect('/admin/users')
@app.get('/admin/audit')
def logs(request:Request,s:Session=Depends(db)):
    u=require(request,s,'audit'); bid=branch_id(request,u); rows=s.scalars(select(AuditLog).where(AuditLog.branch_id==bid).order_by(AuditLog.id.desc()).limit(100)).all()
    return page('Nhật ký thao tác',table(['Thời điểm','Người dùng','Thao tác','Bảng','ID'],[(esc(x.created_at),x.actor_id,esc(x.action),esc(x.entity),x.entity_id) for x in rows]),request,u,'audit')
