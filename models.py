from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db, login_manager

class User(UserMixin, db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(120),nullable=False); email=db.Column(db.String(150),unique=True,nullable=False); password_hash=db.Column(db.String(255),nullable=False); role=db.Column(db.String(20),default="teacher",nullable=False); active=db.Column(db.Boolean,default=True)
    def set_password(self,p): self.password_hash=generate_password_hash(p)
    def check_password(self,p): return check_password_hash(self.password_hash,p)
@login_manager.user_loader
def load_user(uid): return db.session.get(User,int(uid))

class Student(db.Model):
    id=db.Column(db.Integer,primary_key=True); student_id=db.Column(db.String(30),unique=True,nullable=False); first_name=db.Column(db.String(80),nullable=False); last_name=db.Column(db.String(80),nullable=False); email=db.Column(db.String(150)); phone=db.Column(db.String(40)); guardian=db.Column(db.String(120)); guardian_phone=db.Column(db.String(40)); class_name=db.Column(db.String(80),nullable=False); section=db.Column(db.String(30)); admission_date=db.Column(db.Date,default=date.today); dob=db.Column(db.Date); gender=db.Column(db.String(20)); address=db.Column(db.String(255)); status=db.Column(db.String(20),default="Active"); created_at=db.Column(db.DateTime,default=datetime.utcnow)
    @property
    def full_name(self): return f"{self.first_name} {self.last_name}"
class Teacher(db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(120),nullable=False); email=db.Column(db.String(150),unique=True,nullable=False); phone=db.Column(db.String(40)); subject=db.Column(db.String(100)); qualification=db.Column(db.String(150)); salary=db.Column(db.Float,default=0); status=db.Column(db.String(20),default="Active")
class Attendance(db.Model):
    id=db.Column(db.Integer,primary_key=True); student_id=db.Column(db.Integer,db.ForeignKey("student.id"),nullable=False); day=db.Column(db.Date,default=date.today,nullable=False); status=db.Column(db.String(20),nullable=False); subject=db.Column(db.String(100)); student=db.relationship("Student",backref="attendance"); __table_args__=(db.UniqueConstraint("student_id","day","subject"),)
class Fee(db.Model):
    id=db.Column(db.Integer,primary_key=True); student_id=db.Column(db.Integer,db.ForeignKey("student.id"),nullable=False); title=db.Column(db.String(100),nullable=False); amount=db.Column(db.Float,nullable=False); paid=db.Column(db.Float,default=0); due_date=db.Column(db.Date); created_at=db.Column(db.DateTime,default=datetime.utcnow); student=db.relationship("Student",backref="fees")
    invoice_no=db.Column(db.String(40),unique=True); discount=db.Column(db.Float,default=0); late_fine=db.Column(db.Float,default=0); session_label=db.Column(db.String(40)); notes=db.Column(db.Text)
    @property
    def net_total(self): return max(0, float(self.amount or 0)-float(self.discount or 0)+float(self.late_fine or 0))
    @property
    def balance(self): return max(0, self.net_total-float(self.paid or 0))
    @property
    def status(self): return "Paid" if self.balance<=0 else ("Partial" if self.paid>0 else "Unpaid")

class FeePayment(db.Model):
    id=db.Column(db.Integer,primary_key=True); fee_id=db.Column(db.Integer,db.ForeignKey("fee.id"),nullable=False); receipt_no=db.Column(db.String(40),unique=True,nullable=False); amount=db.Column(db.Float,nullable=False); method=db.Column(db.String(30),default="Cash"); reference=db.Column(db.String(100)); paid_on=db.Column(db.Date,default=date.today); note=db.Column(db.String(255)); fee=db.relationship("Fee",backref=db.backref("payments",lazy=True,cascade="all, delete-orphan"))

class AcademicSession(db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(60),unique=True,nullable=False); start_date=db.Column(db.Date); end_date=db.Column(db.Date); is_current=db.Column(db.Boolean,default=False); active=db.Column(db.Boolean,default=True)
class SchoolClass(db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(80),unique=True,nullable=False); sort_order=db.Column(db.Integer,default=0); active=db.Column(db.Boolean,default=True)
class Section(db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(40),nullable=False); class_id=db.Column(db.Integer,db.ForeignKey("school_class.id"),nullable=False); capacity=db.Column(db.Integer,default=40); room=db.Column(db.String(30)); class_group=db.relationship("SchoolClass",backref=db.backref("sections",cascade="all, delete-orphan")); __table_args__=(db.UniqueConstraint("name","class_id"),)
class Subject(db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(100),nullable=False); code=db.Column(db.String(30),unique=True); class_id=db.Column(db.Integer,db.ForeignKey("school_class.id"),nullable=False); teacher_id=db.Column(db.Integer,db.ForeignKey("teacher.id")); class_group=db.relationship("SchoolClass",backref="subjects"); teacher=db.relationship("Teacher"); active=db.Column(db.Boolean,default=True)
class Enrollment(db.Model):
    id=db.Column(db.Integer,primary_key=True); student_id=db.Column(db.Integer,db.ForeignKey("student.id"),nullable=False); class_id=db.Column(db.Integer,db.ForeignKey("school_class.id"),nullable=False); section_id=db.Column(db.Integer,db.ForeignKey("section.id")); session_id=db.Column(db.Integer,db.ForeignKey("academic_session.id"),nullable=False); enrolled_on=db.Column(db.Date,default=date.today); status=db.Column(db.String(20),default="Active"); student=db.relationship("Student"); class_group=db.relationship("SchoolClass"); section_group=db.relationship("Section"); session=db.relationship("AcademicSession"); __table_args__=(db.UniqueConstraint("student_id","session_id"),)
class Exam(db.Model):
    id=db.Column(db.Integer,primary_key=True); title=db.Column(db.String(120),nullable=False); subject=db.Column(db.String(100),nullable=False); class_name=db.Column(db.String(80),nullable=False); exam_date=db.Column(db.Date); total_marks=db.Column(db.Float,default=100); section_id=db.Column(db.Integer,db.ForeignKey("section.id")); section_group=db.relationship("Section")
class Result(db.Model):
    id=db.Column(db.Integer,primary_key=True); exam_id=db.Column(db.Integer,db.ForeignKey("exam.id"),nullable=False); student_id=db.Column(db.Integer,db.ForeignKey("student.id"),nullable=False); marks=db.Column(db.Float,nullable=False); exam=db.relationship("Exam",backref="results"); student=db.relationship("Student",backref="results"); __table_args__=(db.UniqueConstraint("exam_id","student_id"),)
class Announcement(db.Model):
    id=db.Column(db.Integer,primary_key=True); title=db.Column(db.String(160),nullable=False); body=db.Column(db.Text,nullable=False); created_at=db.Column(db.DateTime,default=datetime.utcnow)
class Timetable(db.Model):
    id=db.Column(db.Integer,primary_key=True); class_name=db.Column(db.String(80),nullable=False); weekday=db.Column(db.String(20),nullable=False); start=db.Column(db.String(10),nullable=False); end=db.Column(db.String(10),nullable=False); subject=db.Column(db.String(100),nullable=False); teacher=db.Column(db.String(120))
class LibraryBook(db.Model):
    id=db.Column(db.Integer,primary_key=True); isbn=db.Column(db.String(40)); title=db.Column(db.String(180),nullable=False); author=db.Column(db.String(120)); copies=db.Column(db.Integer,default=1); available=db.Column(db.Integer,default=1)
class BookIssue(db.Model):
    id=db.Column(db.Integer,primary_key=True); book_id=db.Column(db.Integer,db.ForeignKey("library_book.id"),nullable=False); student_id=db.Column(db.Integer,db.ForeignKey("student.id"),nullable=False); issue_date=db.Column(db.Date,default=date.today); due_date=db.Column(db.Date); returned=db.Column(db.Boolean,default=False); book=db.relationship("LibraryBook"); student=db.relationship("Student")
class Transport(db.Model):
    id=db.Column(db.Integer,primary_key=True); route_name=db.Column(db.String(100),nullable=False); vehicle_number=db.Column(db.String(40)); driver_name=db.Column(db.String(120)); driver_phone=db.Column(db.String(40)); monthly_fee=db.Column(db.Float,default=0)
class TransportStudent(db.Model):
    id=db.Column(db.Integer,primary_key=True); transport_id=db.Column(db.Integer,db.ForeignKey("transport.id"),nullable=False); student_id=db.Column(db.Integer,db.ForeignKey("student.id"),nullable=False); pickup_point=db.Column(db.String(160)); monthly_fee=db.Column(db.Float,default=0); active=db.Column(db.Boolean,default=True); transport=db.relationship("Transport",backref=db.backref("assignments",cascade="all, delete-orphan")); student=db.relationship("Student"); __table_args__=(db.UniqueConstraint("transport_id","student_id"),)
class Payroll(db.Model):
    id=db.Column(db.Integer,primary_key=True); teacher_id=db.Column(db.Integer,db.ForeignKey("teacher.id"),nullable=False); month=db.Column(db.String(20),nullable=False); amount=db.Column(db.Float,nullable=False); paid_on=db.Column(db.Date); teacher=db.relationship("Teacher"); bonus=db.Column(db.Float,default=0); deductions=db.Column(db.Float,default=0); payment_method=db.Column(db.String(30),default="Cash"); reference=db.Column(db.String(100)); status=db.Column(db.String(20),default="Paid")
    @property
    def net_amount(self): return float(self.amount or 0)+float(self.bonus or 0)-float(self.deductions or 0)
class ActivityLog(db.Model):
    id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey("user.id")); action=db.Column(db.String(200),nullable=False); created_at=db.Column(db.DateTime,default=datetime.utcnow); user=db.relationship("User")
