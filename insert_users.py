from app import create_app
from app.models import db, Teacher, Parent, Student, User
from werkzeug.security import generate_password_hash

app = create_app('dev')

with app.app_context():
    ph = generate_password_hash("Welcome@123")

    # Teachers
    t1 = Teacher.query.filter_by(email="andrew33@gmail.com").first()
    if not t1:
        t1 = Teacher(name="Andrew Tate", email="andrew33@gmail.com", department="AIML", monthly_salary=40000.0)
        db.session.add(t1)
    
    t2 = Teacher.query.filter_by(email="hrishav888@gmail.com").first()
    if not t2:
        t2 = Teacher(name="Hrishav Bisht", email="hrishav888@gmail.com", department="AIML", monthly_salary=90000.0)
        db.session.add(t2)

    t3 = Teacher.query.filter_by(email="bishthrishav@gmail.com").first()
    if not t3:
        t3 = Teacher(name="Hrishav Hrishav Hrishav", email="bishthrishav@gmail.com", department="CSE", monthly_salary=100000.0)
        db.session.add(t3)
    
    db.session.flush()

    if not User.query.filter_by(email=t1.email).first():
        u_t1 = User(email=t1.email, uid="EMP-AI26AND001", password_hash=ph, role="teacher", display_name=t1.name, teacher_id=t1.id)
        db.session.add(u_t1)
    
    if not User.query.filter_by(email=t2.email).first():
        u_t2 = User(email=t2.email, uid="EMP-AI26HRI001", password_hash=ph, role="teacher", display_name=t2.name, teacher_id=t2.id)
        db.session.add(u_t2)

    if not User.query.filter_by(email=t3.email).first():
        u_t3 = User(email=t3.email, uid="EMP-CSE26HRI001", password_hash=ph, role="teacher", display_name=t3.name, teacher_id=t3.id)
        db.session.add(u_t3)

    # Parents
    p1 = Parent.query.filter_by(email="sanjay@gmail.com").first()
    if not p1:
        p1 = Parent(name="SANJAY GAIKWAD", email="sanjay@gmail.com", phone="+91 8373711116")
        db.session.add(p1)
        db.session.flush()

    if not User.query.filter_by(email=p1.email).first():
        u_p1 = User(email=p1.email, uid="PAR-26SAN001", password_hash=ph, role="parent", display_name=p1.name, parent_id=p1.id)
        db.session.add(u_p1)

    # Students
    s1 = Student.query.filter_by(email="wilsongaikwad@gmail.com").first()
    if not s1:
        s1 = Student(roll_no="CS21554", name="WILSON GAIKWAD", email="wilsongaikwad@gmail.com", department="AIML")
        db.session.add(s1)
        db.session.flush()

    if not User.query.filter_by(email=s1.email).first():
        u_s1 = User(email=s1.email, uid="STU-AIM26WIL001", password_hash=ph, role="student", display_name=s1.name, student_id=s1.id)
        db.session.add(u_s1)

    db.session.commit()
    print("Users added successfully.")
