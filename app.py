from datetime import date, datetime
from functools import wraps
from io import StringIO, BytesIO
import csv, os
from dotenv import load_dotenv

load_dotenv()
from flask import Flask, render_template, request, redirect, url_for, flash, make_response, abort, send_file
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_, func, inspect, text, extract
from config import Config
from extensions import db, login_manager, csrf
from models import *

app=Flask(__name__); app.config.from_object(Config); db.init_app(app); login_manager.init_app(app); login_manager.login_view="login"; csrf.init_app(app)
ROLES={"admin","teacher","student","parent"}
def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapped(*a,**kw):
            if current_user.role not in roles: abort(403)
            return fn(*a,**kw)
        return wrapped
    return deco
def log(action):
    db.session.add(ActivityLog(user_id=current_user.id,action=action)); db.session.commit()
def as_date(value):
    try:return datetime.strptime(value,"%Y-%m-%d").date() if value else None
    except ValueError:return None
@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=User.query.filter_by(email=request.form.get("email","").strip().lower(),active=True).first()
        if u and u.check_password(request.form.get("password","")):
            login_user(u); log("Signed in"); return redirect(url_for("dashboard"))
        flash("Invalid email or password","danger")
    return render_template("login.html")
@app.post("/logout")
@login_required
def logout(): logout_user(); return redirect(url_for("login"))
@app.route("/")
@roles_required("admin","teacher")
def dashboard():
    stats={"students":Student.query.count(),"teachers":Teacher.query.count(),"present":Attendance.query.filter_by(day=date.today(),status="Present").count(),"fees":sum(float(x.paid or 0) for x in Fee.query.all()),"books":LibraryBook.query.count(),"unpaid":sum(1 for x in Fee.query.all() if x.balance>0)}
    recent=Student.query.order_by(Student.created_at.desc()).limit(6).all(); return render_template("dashboard.html",stats=stats,recent=recent)
@app.route("/students")
@roles_required("admin","teacher")
def students():
    q=request.args.get("q","").strip(); query=Student.query
    if q: query=query.filter(or_(Student.first_name.ilike(f"%{q}%"),Student.last_name.ilike(f"%{q}%"),Student.student_id.ilike(f"%{q}%")))
    page=query.order_by(Student.created_at.desc()).paginate(page=request.args.get("page",1,type=int),per_page=12,error_out=False); return render_template("students.html",page=page,q=q)
@app.route("/students/new",methods=["GET","POST"])
@roles_required("admin")
def student_new():
    if request.method=="POST":
        code=request.form.get("student_id","").strip()
        if not code or Student.query.filter_by(student_id=code).first(): flash("Student ID is required and must be unique","danger")
        else:
            s=Student(student_id=code,first_name=request.form["first_name"].strip(),last_name=request.form["last_name"].strip(),email=request.form.get("email"),phone=request.form.get("phone"),guardian=request.form.get("guardian"),guardian_phone=request.form.get("guardian_phone"),class_name=request.form["class_name"].strip(),section=request.form.get("section"),gender=request.form.get("gender"),dob=as_date(request.form.get("dob")),address=request.form.get("address"),admission_date=as_date(request.form.get("admission_date")) or date.today())
            db.session.add(s); db.session.commit(); log(f"Added student {code}"); flash("Student admitted","success"); return redirect(url_for("students"))
    return render_template("student_form.html",s=None)
@app.route("/students/<int:id>/edit",methods=["GET","POST"])
@roles_required("admin")
def student_edit(id):
    s=Student.query.get_or_404(id)
    if request.method=="POST":
        for k in ["student_id","first_name","last_name","email","phone","guardian","guardian_phone","class_name","section","status","gender","address"]: setattr(s,k,request.form.get(k))
        s.dob=as_date(request.form.get("dob")); s.admission_date=as_date(request.form.get("admission_date")) or s.admission_date; db.session.commit(); log(f"Updated student {s.student_id}"); flash("Student updated","success"); return redirect(url_for("students"))
    return render_template("student_form.html",s=s)
@app.post("/students/<int:id>/delete")
@roles_required("admin")
def student_delete(id):
    s=Student.query.get_or_404(id); db.session.delete(s); db.session.commit(); log(f"Deleted student {s.student_id}"); flash("Student deleted","success"); return redirect(url_for("students"))
@app.route("/teachers",methods=["GET","POST"])
@roles_required("admin")
def teachers():
    if request.method=="POST":
        email=request.form["email"].lower().strip()
        if Teacher.query.filter_by(email=email).first(): flash("Teacher email already exists","danger")
        else: db.session.add(Teacher(name=request.form["name"],email=email,phone=request.form.get("phone"),subject=request.form.get("subject"),qualification=request.form.get("qualification"),salary=float(request.form.get("salary") or 0))); db.session.commit(); log("Added teacher"); flash("Teacher added","success")
        return redirect(url_for("teachers"))
    return render_template("teachers.html",teachers=Teacher.query.order_by(Teacher.name).all())
@app.route("/attendance",methods=["GET","POST"])
@roles_required("admin","teacher")
def attendance():
    day=as_date(request.values.get("day")) or date.today()
    class_name=request.values.get("class_name","").strip(); section=request.values.get("section","").strip(); subject=request.values.get("subject","").strip()
    query=Student.query.filter_by(status="Active")
    if class_name: query=query.filter(Student.class_name==class_name)
    if section: query=query.filter(Student.section==section)
    active=query.order_by(Student.class_name,Student.section,Student.student_id,Student.first_name).all()
    if request.method=="POST":
        for st in active:
            status=request.form.get(f"s{st.id}")
            if status not in ["Present","Absent","Late","Excused"]: continue
            record=Attendance.query.filter_by(student_id=st.id,day=day,subject=subject or "General").first()
            if record: record.status=status; record.subject=subject or "General"
            else: db.session.add(Attendance(student_id=st.id,day=day,status=status,subject=subject or "General"))
        db.session.commit(); log(f"Saved attendance for {day} / {class_name or 'all classes'} / {section or 'all sections'}")
        flash("Section-wise attendance saved","success")
        return redirect(url_for("attendance",day=day.isoformat(),class_name=class_name,section=section,subject=subject))
    records={r.student_id:r.status for r in Attendance.query.filter_by(day=day,subject=subject or "General").all()}
    class_options=sorted({x.class_name for x in Student.query.filter_by(status="Active").all()})
    section_options=sorted({x.section for x in Student.query.filter_by(status="Active").all() if x.section})
    subjects=Subject.query.filter_by(active=True).order_by(Subject.name).all()
    return render_template("attendance.html",students=active,records=records,day=day,class_options=class_options,section_options=section_options,class_name=class_name,section=section,subject=subject,subjects=subjects)
@app.route("/fees",methods=["GET","POST"])
@roles_required("admin")
def fees():
    if request.method=="POST":
        try:
            amount=float(request.form["amount"]); discount=float(request.form.get("discount") or 0); fine=float(request.form.get("late_fine") or 0); student_id=int(request.form["student_id"])
            if amount<=0 or discount<0 or fine<0 or discount>amount: raise ValueError
            invoice=Fee(student_id=student_id,title=request.form["title"].strip(),amount=amount,paid=0,due_date=as_date(request.form.get("due_date")),discount=discount,late_fine=fine,session_label=request.form.get("session_label"),notes=request.form.get("notes"),invoice_no=f"INV-{datetime.utcnow():%y%m%d}-{os.urandom(3).hex().upper()}")
            db.session.add(invoice); db.session.flush()
            initial=float(request.form.get("initial_payment") or 0)
            if initial<0 or initial>invoice.net_total: raise ValueError
            if initial:
                invoice.paid=initial; db.session.add(FeePayment(fee_id=invoice.id,receipt_no=f"RCP-{datetime.utcnow():%y%m%d}-{os.urandom(3).hex().upper()}",amount=initial,method=request.form.get("payment_method") or "Cash",paid_on=date.today()))
            db.session.commit(); log(f"Created invoice {invoice.invoice_no}"); flash("Fee invoice created successfully","success")
        except (ValueError,KeyError,TypeError):
            db.session.rollback(); flash("Please enter valid fee and payment amounts","danger")
        return redirect(url_for("fees"))
    return render_template("fees.html",fees=Fee.query.order_by(Fee.id.desc()).all(),students=Student.query.filter_by(status="Active").all())
@app.post("/fees/<int:id>/payment")
@roles_required("admin")
def fee_payment(id):
    f=Fee.query.get_or_404(id)
    try:
        amount=float(request.form.get("amount") or 0)
        if amount<=0 or amount>f.balance: raise ValueError
        payment=FeePayment(fee_id=f.id,receipt_no=f"RCP-{datetime.utcnow():%y%m%d}-{os.urandom(3).hex().upper()}",amount=amount,method=request.form.get("method") or "Cash",reference=request.form.get("reference"),paid_on=as_date(request.form.get("paid_on")) or date.today(),note=request.form.get("note"))
        f.paid+=amount; db.session.add(payment); db.session.commit(); log(f"Recorded payment for invoice {f.invoice_no or f.id}"); flash("Payment recorded. Receipt is ready to print.","success")
        return redirect(url_for("fee_receipt",payment_id=payment.id))
    except (ValueError,TypeError): db.session.rollback(); flash("Payment amount is invalid","danger"); return redirect(url_for("fees"))
@app.get("/fees/receipt/<int:payment_id>")
@roles_required("admin")
def fee_receipt(payment_id):
    payment=FeePayment.query.get_or_404(payment_id); return render_template("fee_receipt.html",payment=payment,fee=payment.fee)
@app.get("/fees/invoice/<int:id>")
@roles_required("admin")
def fee_invoice(id):
    fee=Fee.query.get_or_404(id); return render_template("fee_invoice.html",fee=fee)
@app.route("/classes",methods=["GET","POST"])
@roles_required("admin")
def classes():
    if request.method=="POST":
        action=request.form.get("action")
        try:
            if action=="session":
                name=request.form["name"].strip()
                if not name or AcademicSession.query.filter_by(name=name).first(): raise ValueError
                if request.form.get("is_current"): AcademicSession.query.update({AcademicSession.is_current:False})
                db.session.add(AcademicSession(name=name,start_date=as_date(request.form.get("start_date")),end_date=as_date(request.form.get("end_date")),is_current=bool(request.form.get("is_current"))))
            elif action=="class":
                name=request.form["name"].strip()
                if not name or SchoolClass.query.filter_by(name=name).first(): raise ValueError
                db.session.add(SchoolClass(name=name,sort_order=int(request.form.get("sort_order") or 0)))
            elif action=="section":
                db.session.add(Section(name=request.form["name"].strip(),class_id=int(request.form["class_id"]),capacity=int(request.form.get("capacity") or 40),room=request.form.get("room")))
            elif action=="subject":
                db.session.add(Subject(name=request.form["name"].strip(),code=request.form.get("code") or None,class_id=int(request.form["class_id"]),teacher_id=int(request.form["teacher_id"]) if request.form.get("teacher_id") else None))
            elif action=="enrollment":
                student=Student.query.get_or_404(int(request.form["student_id"])); class_item=SchoolClass.query.get_or_404(int(request.form["class_id"])); session=AcademicSession.query.get_or_404(int(request.form["session_id"]))
                section_id=int(request.form["section_id"]) if request.form.get("section_id") else None
                if section_id and Section.query.filter_by(id=section_id,class_id=class_item.id).first() is None: raise ValueError
                existing=Enrollment.query.filter_by(student_id=student.id,session_id=session.id).first()
                if existing: raise ValueError
                db.session.add(Enrollment(student_id=student.id,class_id=class_item.id,section_id=section_id,session_id=session.id))
                student.class_name=class_item.name; student.section=Section.query.get(section_id).name if section_id else None
            db.session.commit(); log(f"Added {action} in Classes Management"); flash("Record saved successfully","success")
        except Exception:
            db.session.rollback(); flash("Could not save. Check required fields and avoid duplicate names/codes.","danger")
        return redirect(url_for("classes"))
    return render_template("classes.html",sessions=AcademicSession.query.order_by(AcademicSession.id.desc()).all(),classes=SchoolClass.query.order_by(SchoolClass.sort_order,SchoolClass.name).all(),teachers=Teacher.query.filter_by(status="Active").all(),subjects=Subject.query.order_by(Subject.name).all(),students=Student.query.filter_by(status="Active").order_by(Student.first_name).all(),enrollments=Enrollment.query.order_by(Enrollment.id.desc()).limit(30).all())
@app.post("/classes/section/<int:id>/delete")
@roles_required("admin")
def section_delete(id):
    item=Section.query.get_or_404(id)
    if Enrollment.query.filter_by(section_id=id).first(): flash("Section has student enrollments and cannot be deleted","danger")
    else: db.session.delete(item); db.session.commit(); flash("Section deleted","success")
    return redirect(url_for("classes"))
@app.route("/exams",methods=["GET","POST"])
@roles_required("admin","teacher")
def exams():
    if request.method=="POST":
        class_name=request.form["class_name"].strip(); section_id=int(request.form["section_id"]) if request.form.get("section_id") else None
        section_item=Section.query.get(section_id) if section_id else None
        if section_item and section_item.class_group.name!=class_name:
            flash("Selected section does not belong to this class","danger"); return redirect(url_for("exams"))
        db.session.add(Exam(title=request.form["title"].strip(),subject=request.form["subject"].strip(),class_name=class_name,section_id=section_id,total_marks=float(request.form["total_marks"]),exam_date=as_date(request.form.get("exam_date"))))
        db.session.commit(); log("Created class and section exam"); flash("Exam created","success"); return redirect(url_for("exams"))
    return render_template("exams.html",exams=Exam.query.order_by(Exam.id.desc()).all(),sections=Section.query.order_by(Section.class_id,Section.name).all())
@app.route("/exams/<int:id>/results",methods=["GET","POST"])
@roles_required("admin","teacher")
def results(id):
    e=Exam.query.get_or_404(id); query=Student.query.filter_by(class_name=e.class_name,status="Active")
    if e.section_id: query=query.filter_by(section= e.section_group.name)
    students=query.order_by(Student.student_id).all()
    if request.method=="POST":
        for st in students:
            raw=request.form.get(f"m{st.id}","").strip()
            if not raw: continue
            try: marks=float(raw)
            except ValueError: flash("Marks must be numeric","danger"); return redirect(url_for("results",id=id))
            if marks<0 or marks>e.total_marks: flash("Marks outside allowed range","danger"); return redirect(url_for("results",id=id))
            result=Result.query.filter_by(exam_id=id,student_id=st.id).first()
            if result: result.marks=marks
            else: db.session.add(Result(exam_id=id,student_id=st.id,marks=marks))
        db.session.commit(); log(f"Saved results for exam {id}"); flash("Section-wise results saved","success"); return redirect(url_for("results",id=id))
    current={r.student_id:r.marks for r in Result.query.filter_by(exam_id=id).all()}
    return render_template("results.html",e=e,students=students,current=current)
@app.route("/announcements",methods=["GET","POST"])
@roles_required("admin","teacher")
def announcements():
    if request.method=="POST": db.session.add(Announcement(title=request.form["title"],body=request.form["body"])); db.session.commit(); log("Published announcement"); flash("Announcement published","success"); return redirect(url_for("announcements"))
    return render_template("announcements.html",items=Announcement.query.order_by(Announcement.created_at.desc()).all())
@app.route("/timetable",methods=["GET","POST"])
@roles_required("admin","teacher")
def timetable():
    if request.method=="POST": db.session.add(Timetable(class_name=request.form["class_name"],weekday=request.form["weekday"],start=request.form["start"],end=request.form["end"],subject=request.form["subject"],teacher=request.form.get("teacher"))); db.session.commit(); log("Added timetable entry"); flash("Timetable saved","success"); return redirect(url_for("timetable"))
    return render_template("timetable.html",items=Timetable.query.order_by(Timetable.weekday,Timetable.start).all())
@app.route("/library",methods=["GET","POST"])
@roles_required("admin","teacher")
def library():
    if request.method=="POST": db.session.add(LibraryBook(isbn=request.form.get("isbn"),title=request.form["title"],author=request.form.get("author"),copies=int(request.form.get("copies") or 1),available=int(request.form.get("copies") or 1))); db.session.commit(); log("Added library book"); flash("Book added","success"); return redirect(url_for("library"))
    return render_template("library.html",books=LibraryBook.query.order_by(LibraryBook.title).all(),students=Student.query.filter_by(status="Active").all(),issues=BookIssue.query.order_by(BookIssue.id.desc()).all())
@app.post("/library/issue")
@roles_required("admin","teacher")
def issue_book():
    b=LibraryBook.query.get_or_404(int(request.form["book_id"]))
    if b.available<1: flash("No copies available","danger")
    else:b.available-=1; db.session.add(BookIssue(book_id=b.id,student_id=int(request.form["student_id"]),due_date=as_date(request.form.get("due_date")))); db.session.commit(); log(f"Issued book {b.title}"); flash("Book issued","success")
    return redirect(url_for("library"))
@app.post("/library/return/<int:id>")
@roles_required("admin","teacher")
def return_book(id):
    issue=BookIssue.query.get_or_404(id)
    if not issue.returned: issue.returned=True; issue.book.available+=1; db.session.commit(); log("Returned library book")
    return redirect(url_for("library"))
@app.route("/transport",methods=["GET","POST"])
@roles_required("admin")
def transport():
    if request.method=="POST":
        db.session.add(Transport(route_name=request.form["route_name"].strip(),vehicle_number=request.form.get("vehicle_number"),driver_name=request.form.get("driver_name"),driver_phone=request.form.get("driver_phone"),monthly_fee=float(request.form.get("monthly_fee") or 0)))
        db.session.commit(); log("Added transport route"); flash("Transport route saved","success"); return redirect(url_for("transport"))
    return render_template("transport.html",items=Transport.query.order_by(Transport.route_name).all(),students=Student.query.filter_by(status="Active").order_by(Student.first_name).all(),assignments=TransportStudent.query.filter_by(active=True).order_by(TransportStudent.id.desc()).all())
@app.post("/transport/assign")
@roles_required("admin")
def transport_assign():
    try:
        tid=int(request.form["transport_id"]); sid=int(request.form["student_id"])
        if TransportStudent.query.filter_by(transport_id=tid,student_id=sid).first(): raise ValueError
        db.session.add(TransportStudent(transport_id=tid,student_id=sid,pickup_point=request.form.get("pickup_point"),monthly_fee=float(request.form.get("monthly_fee") or 0)))
        db.session.commit(); log("Assigned student to transport route"); flash("Student assigned to route","success")
    except (ValueError,KeyError,TypeError): db.session.rollback(); flash("Invalid or duplicate student route assignment","danger")
    return redirect(url_for("transport"))
@app.post("/transport/assignment/<int:id>/remove")
@roles_required("admin")
def transport_remove(id):
    item=TransportStudent.query.get_or_404(id); item.active=False; db.session.commit(); log("Removed student from transport route"); return redirect(url_for("transport"))
@app.route("/payroll",methods=["GET","POST"])
@roles_required("admin")
def payroll():
    if request.method=="POST":
        try:
            basic=float(request.form["amount"]); bonus=float(request.form.get("bonus") or 0); deductions=float(request.form.get("deductions") or 0)
            if basic<0 or bonus<0 or deductions<0 or deductions>basic+bonus: raise ValueError
            db.session.add(Payroll(teacher_id=int(request.form["teacher_id"]),month=request.form["month"],amount=basic,bonus=bonus,deductions=deductions,paid_on=as_date(request.form.get("paid_on")),payment_method=request.form.get("payment_method") or "Cash",reference=request.form.get("reference"),status=request.form.get("status") or "Paid"))
            db.session.commit(); log("Recorded staff payroll"); flash("Payroll record saved","success")
        except (ValueError,KeyError,TypeError): db.session.rollback(); flash("Check payroll values","danger")
        return redirect(url_for("payroll",month=request.form.get("month","")))
    month=request.args.get("month",""); query=Payroll.query
    if month: query=query.filter_by(month=month)
    items=query.order_by(Payroll.id.desc()).all(); gross=sum(x.amount+x.bonus for x in items); deductions=sum(x.deductions for x in items); net=sum(x.net_amount for x in items)
    return render_template("payroll.html",items=items,teachers=Teacher.query.order_by(Teacher.name).all(),month=month,gross=gross,deductions=deductions,net=net)
@app.route("/reports")
@roles_required("admin","teacher")
def reports():
    month=request.args.get("month",date.today().strftime("%Y-%m")); class_name=request.args.get("class_name",""); section=request.args.get("section","")
    year, month_number = [int(part) for part in month.split("-")]
    attendance_query=Attendance.query.filter(extract("year",Attendance.day)==year, extract("month",Attendance.day)==month_number)
    attendance_rows=attendance_query.join(Student).all()
    if class_name: attendance_rows=[r for r in attendance_rows if r.student.class_name==class_name]
    if section: attendance_rows=[r for r in attendance_rows if r.student.section==section]
    attendance_summary={}
    for r in attendance_rows:
        key=(r.student.class_name,r.student.section or "—",r.subject or "General")
        attendance_summary.setdefault(key,{"Present":0,"Absent":0,"Late":0,"Excused":0,"Total":0})
        attendance_summary[key][r.status]=attendance_summary[key].get(r.status,0)+1; attendance_summary[key]["Total"]+=1
    exam_rows=Result.query.join(Exam).join(Student).filter(extract("year",Exam.exam_date)==year, extract("month",Exam.exam_date)==month_number).all(); exam_summary={}
    for r in exam_rows:
        key=(r.exam.class_name,r.exam.section_group.name if r.exam.section_group else "All sections",r.exam.subject)
        exam_summary.setdefault(key,[]).append((r.marks,r.exam.total_marks))
    exam_summary={k:{"count":len(v),"average":round(sum(a/b*100 for a,b in v if b)/len(v),1) if v else 0} for k,v in exam_summary.items()}
    billed=float(db.session.query(func.coalesce(func.sum(Fee.amount),0)).scalar() or 0); paid=float(db.session.query(func.coalesce(func.sum(Fee.paid),0)).scalar() or 0)
    classes=sorted({x.class_name for x in Student.query.all()}); sections=sorted({x.section for x in Student.query.all() if x.section})
    return render_template("reports.html",month=month,class_name=class_name,section=section,attendance_summary=attendance_summary,exam_summary=exam_summary,billed=billed,paid=paid,classes=classes,sections=sections)
@app.route("/activity")
@roles_required("admin")
def activity(): return render_template("activity.html",items=ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(100).all())
@app.route("/export/students.csv")
@roles_required("admin","teacher")
def export_students():
    out=StringIO(); w=csv.writer(out); w.writerow(["Student ID","Name","Class","Section","Email","Phone","Status"])
    for s in Student.query.order_by(Student.student_id).all():w.writerow([s.student_id,s.full_name,s.class_name,s.section,s.email,s.phone,s.status])
    res=make_response(out.getvalue()); res.headers["Content-Disposition"]="attachment; filename=students.csv"; res.headers["Content-Type"]="text/csv"; return res
@app.route("/health")
def health(): return {"status":"ok","database":"connected"}
with app.app_context():
    db.create_all()
    # Safe additive migration for the earlier SQLite version supplied by the user.
    if db.engine.dialect.name == "sqlite":
        # Upgrade legacy attendance uniqueness (student + day) to allow one record
        # per student, date and subject. Existing records are retained as General.
        unique_sets = [tuple(item.get("column_names") or []) for item in inspect(db.engine).get_unique_constraints("attendance")]
        if ("student_id", "day") in unique_sets:
            raw = db.engine.raw_connection()
            try:
                cur = raw.cursor(); cur.execute("PRAGMA foreign_keys=OFF")
                cur.execute("BEGIN")
                has_subject = "subject" in {c[1] for c in cur.execute("PRAGMA table_info(attendance)").fetchall()}
                subject_expr = "COALESCE(subject, 'General')" if has_subject else "'General'"
                cur.execute("CREATE TABLE attendance_new (id INTEGER NOT NULL PRIMARY KEY, student_id INTEGER NOT NULL, day DATE NOT NULL, status VARCHAR(20) NOT NULL, subject VARCHAR(100) NOT NULL DEFAULT 'General', FOREIGN KEY(student_id) REFERENCES student (id), CONSTRAINT uq_attendance_student_day_subject UNIQUE (student_id, day, subject))")
                cur.execute(f"INSERT INTO attendance_new (id, student_id, day, status, subject) SELECT id, student_id, day, status, {subject_expr} FROM attendance")
                cur.execute("DROP TABLE attendance")
                cur.execute("ALTER TABLE attendance_new RENAME TO attendance")
                raw.commit()
            except Exception:
                raw.rollback(); raise
            finally:
                raw.close()
        additions = {
            "student": {"dob": "DATE", "gender": "VARCHAR(20)", "address": "VARCHAR(255)"},
            "teacher": {"salary": "FLOAT DEFAULT 0", "status": "VARCHAR(20) DEFAULT 'Active'"},
            "fee": {"invoice_no": "VARCHAR(40)", "discount": "FLOAT DEFAULT 0", "late_fine": "FLOAT DEFAULT 0", "session_label": "VARCHAR(40)", "notes": "TEXT"},
            "attendance": {"subject": "VARCHAR(100)"},
            "exam": {"section_id": "INTEGER"},
            "payroll": {"bonus": "FLOAT DEFAULT 0", "deductions": "FLOAT DEFAULT 0", "payment_method": "VARCHAR(30) DEFAULT 'Cash'", "reference": "VARCHAR(100)", "status": "VARCHAR(20) DEFAULT 'Paid'"},
        }
        inspector = inspect(db.engine)
        for table, columns in additions.items():
            existing = {c["name"] for c in inspector.get_columns(table)}
            for column, sql_type in columns.items():
                if column not in existing:
                    with db.engine.begin() as conn:
                        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {sql_type}'))
    # Create the first administrator only when credentials are explicitly
    # provided in the local .env file. Never ship a shared default password.
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    admin_name = os.getenv("ADMIN_NAME", "System Administrator").strip() or "System Administrator"
    if admin_email and admin_password and not User.query.filter_by(role="admin").first():
        if len(admin_password) < 12:
            raise RuntimeError("ADMIN_PASSWORD must be at least 12 characters long.")
        if "@" not in admin_email:
            raise RuntimeError("ADMIN_EMAIL must be a valid email address.")
        u = User(name=admin_name, email=admin_email, role="admin")
        u.set_password(admin_password)
        db.session.add(u)
        db.session.commit()
if __name__=="__main__": app.run(debug=os.getenv("FLASK_DEBUG","0")=="1")
