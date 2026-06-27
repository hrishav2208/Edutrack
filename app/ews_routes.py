from flask import Blueprint, jsonify, session
from datetime import datetime
from app.models import db, EarlyWarningAlert, Student, User, Teacher

ews_bp = Blueprint('ews_bp', __name__, url_prefix='/api/ews')

@ews_bp.route('/teacher', methods=['GET'])
def get_teacher_alerts():
    if 'user_id' not in session or session.get('role') not in ['teacher', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 401
        
    alerts = EarlyWarningAlert.query.filter_by(status='Active').all()
    result = []
    for alert in alerts:
        student = Student.query.get(alert.student_id)
        if student:
            result.append({
                'id': alert.id,
                'student_name': student.name,
                'roll_no': student.roll_no,
                'risk_type': alert.risk_type,
                'risk_level': alert.risk_level,
                'trigger_reason': alert.trigger_reason,
                'created_at': alert.created_at.strftime('%Y-%m-%d')
            })
    return jsonify(result), 200

@ews_bp.route('/student', methods=['GET'])
def get_student_alerts():
    if 'user_id' not in session or session.get('role') != 'student':
        return jsonify({'error': 'Unauthorized'}), 401
        
    user = User.query.get(session['user_id'])
    if not user or not user.student_id:
        return jsonify({'error': 'Student not found'}), 404
        
    # Only return HIGH risk active alerts
    alerts = EarlyWarningAlert.query.filter_by(
        student_id=user.student_id, 
        status='Active', 
        risk_level='High'
    ).all()
    
    result = [{
        'id': a.id,
        'risk_type': a.risk_type,
        'trigger_reason': a.trigger_reason,
        'created_at': a.created_at.strftime('%Y-%m-%d')
    } for a in alerts]
    
    return jsonify(result), 200

@ews_bp.route('/resolve/<int:alert_id>', methods=['POST'])
def resolve_alert(alert_id):
    if 'user_id' not in session or session.get('role') not in ['teacher', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 401
        
    alert = EarlyWarningAlert.query.get(alert_id)
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
        
    alert.status = 'Resolved'
    alert.resolved_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Alert resolved successfully'}), 200

# Endpoint to trigger check manually
@ews_bp.route('/trigger-checks', methods=['POST'])
def trigger_checks():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
        
    from app.services.ews_engine import run_all_checks
    run_all_checks()
    return jsonify({'success': True, 'message': 'EWS checks completed'}), 200
