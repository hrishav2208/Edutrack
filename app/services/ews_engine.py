import os
import urllib.request
import urllib.parse
import json
from datetime import datetime
from app.models import db, Student, AttendanceRecord, Mark, EarlyWarningAlert, Notification, User

def send_ews_email(student, alert):
    user = User.query.filter_by(student_id=student.id).first()
    recipient_email = student.email
    if not recipient_email and user:
        recipient_email = user.email

    emailjs_service_id = os.environ.get('EMAILJS_SERVICE_ID')
    emailjs_template_id = os.environ.get('EMAILJS_TEMPLATE_ID')
    emailjs_public_key = os.environ.get('EMAILJS_PUBLIC_KEY')

    if emailjs_service_id and emailjs_template_id and emailjs_public_key and recipient_email:
        try:
            data = {
                "service_id": emailjs_service_id,
                "template_id": emailjs_template_id,
                "user_id": emailjs_public_key,
                "template_params": {
                    "to_email": recipient_email,
                    "subject": f"Early Warning Alert: {alert.risk_type}",
                    "message": alert.trigger_reason,
                    "student_name": student.name
                }
            }
            req = urllib.request.Request(
                'https://api.emailjs.com/api/v1.0/email/send',
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req) as response:
                print(f"EWS EmailJS Response: {response.status}")
        except Exception as e:
            print(f"Failed to send EWS email via EmailJS: {e}")
    else:
        print(f"[WARNING] EmailJS keys missing or student has no email. Alert not emailed.")

def run_attendance_check():
    students = Student.query.all()
    for student in students:
        # Check active alert
        active_alert = EarlyWarningAlert.query.filter_by(student_id=student.id, risk_type='Attendance', status='Active').first()
        if active_alert:
            continue
            
        records = AttendanceRecord.query.filter_by(student_id=student.id).all()
        if not records:
            continue
            
        total = len(records)
        present = sum(1 for r in records if r.present)
        attendance_percentage = (present / total) * 100
        
        if attendance_percentage < 75.0:
            alert = EarlyWarningAlert(
                student_id=student.id,
                risk_type='Attendance',
                risk_level='High',
                trigger_reason=f"Attendance dropped to {attendance_percentage:.1f}% ({present}/{total} classes)."
            )
            db.session.add(alert)
            db.session.commit()
            
            # Send notification
            user = User.query.filter_by(student_id=student.id).first()
            if user:
                notif = Notification(
                    user_id=user.id,
                    title="Attendance Warning",
                    message=alert.trigger_reason,
                    type="danger"
                )
                db.session.add(notif)
                db.session.commit()
            
            send_ews_email(student, alert)

def run_academic_check():
    students = Student.query.all()
    for student in students:
        # Check active alert
        active_alert = EarlyWarningAlert.query.filter_by(student_id=student.id, risk_type='Academics', status='Active').first()
        if active_alert:
            continue
            
        marks = Mark.query.filter_by(student_id=student.id).order_by(Mark.graded_at.asc()).all()
        if not marks:
            continue
            
        total_score = sum(m.score for m in marks)
        total_max = sum(m.max_score for m in marks)
        avg_percentage = (total_score / total_max) * 100 if total_max > 0 else 0
        
        trigger_reason = ""
        if avg_percentage < 40.0:
            trigger_reason = f"Overall academic average is below passing criteria ({avg_percentage:.1f}%)."
        elif len(marks) >= 2:
            # Check for 15% drop in last two
            last_mark = marks[-1]
            prev_mark = marks[-2]
            last_perc = (last_mark.score / last_mark.max_score) * 100 if last_mark.max_score > 0 else 0
            prev_perc = (prev_mark.score / prev_mark.max_score) * 100 if prev_mark.max_score > 0 else 0
            
            if prev_perc - last_perc > 15.0:
                trigger_reason = f"Academic score dropped by {prev_perc - last_perc:.1f}% in recent assessment ({last_mark.exam_title})."
                
        if trigger_reason:
            alert = EarlyWarningAlert(
                student_id=student.id,
                risk_type='Academics',
                risk_level='Medium' if 'dropped' in trigger_reason else 'High',
                trigger_reason=trigger_reason
            )
            db.session.add(alert)
            db.session.commit()
            
            # Send notification
            user = User.query.filter_by(student_id=student.id).first()
            if user:
                notif = Notification(
                    user_id=user.id,
                    title="Academic Warning",
                    message=alert.trigger_reason,
                    type="warning" if alert.risk_level == 'Medium' else "danger"
                )
                db.session.add(notif)
                db.session.commit()
                
            if alert.risk_level == 'High':
                send_ews_email(student, alert)

def run_all_checks():
    run_attendance_check()
    run_academic_check()
