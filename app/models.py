from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()
def now(): return datetime.now(timezone.utc)
class Branch(Base):
    __tablename__='branches'
    id=Column(Integer,primary_key=True); name=Column(String(150),nullable=False); address=Column(String(250),default=''); phone=Column(String(30),default=''); active=Column(Boolean,default=True)
class User(Base):
    __tablename__='users'
    id=Column(Integer,primary_key=True); username=Column(String(80),unique=True,nullable=False); password_hash=Column(String(300),nullable=False); full_name=Column(String(150),nullable=False); role=Column(String(30),nullable=False); branch_id=Column(Integer,ForeignKey('branches.id')); active=Column(Boolean,default=True)
class Patient(Base):
    __tablename__='patients'
    id=Column(Integer,primary_key=True); branch_id=Column(Integer,ForeignKey('branches.id'),nullable=False); full_name=Column(String(150),nullable=False); phone=Column(String(30),default=''); birth_date=Column(String(10),default=''); gender=Column(String(20),default=''); address=Column(String(250),default=''); medical_note=Column(Text,default=''); created_at=Column(DateTime(timezone=True),default=now)
class Chair(Base):
    __tablename__='chairs'; id=Column(Integer,primary_key=True); branch_id=Column(Integer,ForeignKey('branches.id'),nullable=False); name=Column(String(100),nullable=False)
class Appointment(Base):
    __tablename__='appointments'; id=Column(Integer,primary_key=True); branch_id=Column(Integer,ForeignKey('branches.id'),nullable=False); patient_id=Column(Integer,ForeignKey('patients.id'),nullable=False); chair_id=Column(Integer,ForeignKey('chairs.id')); doctor_id=Column(Integer,ForeignKey('users.id')); starts_at=Column(DateTime,nullable=False); ends_at=Column(DateTime,nullable=False); status=Column(String(30),default='scheduled'); note=Column(Text,default='')
class Service(Base):
    __tablename__='services'; id=Column(Integer,primary_key=True); name=Column(String(150),nullable=False); price=Column(Numeric(14,2),nullable=False); duration_minutes=Column(Integer,default=30); active=Column(Boolean,default=True)
class Treatment(Base):
    __tablename__='treatments'; id=Column(Integer,primary_key=True); branch_id=Column(Integer,ForeignKey('branches.id'),nullable=False); patient_id=Column(Integer,ForeignKey('patients.id'),nullable=False); doctor_id=Column(Integer,ForeignKey('users.id')); tooth_number=Column(String(10),default=''); diagnosis=Column(Text,default=''); plan=Column(Text,default=''); status=Column(String(30),default='planned'); created_at=Column(DateTime(timezone=True),default=now)
class Invoice(Base):
    __tablename__='invoices'; id=Column(Integer,primary_key=True); branch_id=Column(Integer,ForeignKey('branches.id'),nullable=False); patient_id=Column(Integer,ForeignKey('patients.id'),nullable=False); total=Column(Numeric(14,2),nullable=False); paid=Column(Numeric(14,2),default=0); note=Column(Text,default=''); created_at=Column(DateTime(timezone=True),default=now)
class Payment(Base):
    __tablename__='payments'; id=Column(Integer,primary_key=True); invoice_id=Column(Integer,ForeignKey('invoices.id'),nullable=False); amount=Column(Numeric(14,2),nullable=False); method=Column(String(30),default='cash'); created_at=Column(DateTime(timezone=True),default=now)
class InventoryItem(Base):
    __tablename__='inventory_items'; id=Column(Integer,primary_key=True); branch_id=Column(Integer,ForeignKey('branches.id'),nullable=False); name=Column(String(150),nullable=False); sku=Column(String(70),nullable=False); quantity=Column(Integer,default=0); minimum_quantity=Column(Integer,default=0); unit=Column(String(30),default='cái'); __table_args__=(UniqueConstraint('branch_id','sku'),)
class StockMovement(Base):
    __tablename__='stock_movements'; id=Column(Integer,primary_key=True); branch_id=Column(Integer,ForeignKey('branches.id'),nullable=False); item_id=Column(Integer,ForeignKey('inventory_items.id'),nullable=False); delta=Column(Integer,nullable=False); reason=Column(String(150),default=''); created_at=Column(DateTime(timezone=True),default=now)
class Expense(Base):
    __tablename__='expenses'; id=Column(Integer,primary_key=True); branch_id=Column(Integer,ForeignKey('branches.id'),nullable=False); category=Column(String(100),nullable=False); amount=Column(Numeric(14,2),nullable=False); note=Column(Text,default=''); created_at=Column(DateTime(timezone=True),default=now)
class Reminder(Base):
    __tablename__='reminders'; id=Column(Integer,primary_key=True); branch_id=Column(Integer,ForeignKey('branches.id'),nullable=False); patient_id=Column(Integer,ForeignKey('patients.id'),nullable=False); due_date=Column(String(10),nullable=False); content=Column(Text,nullable=False); status=Column(String(20),default='pending')
class ContentPage(Base):
    __tablename__='content_pages'; id=Column(Integer,primary_key=True); slug=Column(String(120),unique=True,nullable=False); title=Column(String(200),nullable=False); body=Column(Text,default=''); seo_description=Column(String(300),default=''); published=Column(Boolean,default=False)
class AuditLog(Base):
    __tablename__='audit_logs'; id=Column(Integer,primary_key=True); actor_id=Column(Integer,ForeignKey('users.id')); branch_id=Column(Integer,ForeignKey('branches.id')); action=Column(String(100),nullable=False); entity=Column(String(100),nullable=False); entity_id=Column(Integer); created_at=Column(DateTime(timezone=True),default=now)
class AppointmentRequest(Base):
    __tablename__ = 'appointment_requests'

    id = Column(Integer, primary_key=True)

    branch_id = Column(
        Integer,
        ForeignKey('branches.id'),
        nullable=False
    )

    full_name = Column(String(150), nullable=False)
    phone = Column(String(30), nullable=False)

    preferred_at = Column(
        DateTime,
        nullable=False
    )

    status = Column(
        String(30),
        nullable=False,
        default='pending'
    )

    created_at = Column(
        DateTime(timezone=True),
        default=now,
        nullable=False
    )


class CustomerReview(Base):
    __tablename__ = 'customer_reviews'

    id = Column(Integer, primary_key=True)
    customer_name = Column(String(150), nullable=False)
    avatar_url = Column(String(500), default='')
    avatar_public_id = Column(String(255), default='')
    content = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False, default=5)
    sort_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=now)
