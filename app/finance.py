"""Fee structures, payments, salary disbursements."""

from datetime import date, datetime

from flask import Blueprint, jsonify, request

from app.auth import require_login
from app.models import FeePayment, FeeStructure, SalaryDisbursement, Student, Teacher, db

finance_bp = Blueprint("finance", __name__)


@finance_bp.route("/fee-structures", methods=["GET"])
def list_structures():
    u, err = require_login()
    if err:
        return err
    rows = FeeStructure.query.order_by(FeeStructure.academic_year.desc(), FeeStructure.program).all()
    return jsonify(
        [
            {
                "id": r.id,
                "program": r.program,
                "item_name": r.item_name,
                "amount": r.amount,
                "academic_year": r.academic_year,
            }
            for r in rows
        ]
    )


@finance_bp.route("/fee-structures", methods=["POST"])
def add_structure():
    u, err = require_login()
    if err:
        return err
    if u.role != "admin":
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    program = (data.get("program") or "").strip()
    item_name = (data.get("item_name") or "").strip()
    amount = float(data.get("amount") or 0)
    academic_year = (data.get("academic_year") or "2025-26").strip()
    if not program or not item_name:
        return jsonify({"error": "program and item_name required"}), 400
    r = FeeStructure(program=program, item_name=item_name, amount=amount, academic_year=academic_year)
    db.session.add(r)
    db.session.commit()
    return jsonify({"ok": True, "id": r.id})


@finance_bp.route("/fee-payments", methods=["GET"])
def list_payments():
    u, err = require_login()
    if err:
        return err
    sid = request.args.get("student_id", type=int)
    q = FeePayment.query
    if sid:
        q = q.filter_by(student_id=sid)
    elif u.role == "student" and u.student_id:
        q = q.filter_by(student_id=u.student_id)
    elif u.role == "parent" and u.parent_id:
        child_ids = [s.id for s in Student.query.filter_by(parent_id=u.parent_id).all()]
        if child_ids:
            q = q.filter(FeePayment.student_id.in_(child_ids))
        else:
            q = q.filter(FeePayment.id == -1)
    elif u.role != "admin":
        return jsonify({"error": "Forbidden"}), 403
    rows = q.order_by(FeePayment.paid_on.desc()).limit(200).all()
    out = []
    for p in rows:
        st = Student.query.get(p.student_id)
        out.append(
            {
                "id": p.id,
                "student_id": p.student_id,
                "student_name": st.name if st else "",
                "structure_id": p.structure_id,
                "amount_paid": p.amount_paid,
                "paid_on": p.paid_on.isoformat(),
                "remarks": p.remarks,
            }
        )
    return jsonify(out)


@finance_bp.route("/fee-payments", methods=["POST"])
def add_payment():
    u, err = require_login()
    if err:
        return err
    if u.role != "admin":
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    student_id = int(data.get("student_id", 0))
    structure_id = data.get("structure_id")
    structure_id = int(structure_id) if structure_id else None
    amount_paid = float(data.get("amount_paid") or 0)
    remarks = (data.get("remarks") or "").strip()
    if not student_id:
        return jsonify({"error": "student_id required"}), 400
    p = FeePayment(
        student_id=student_id,
        structure_id=structure_id,
        amount_paid=amount_paid,
        paid_on=date.today(),
        remarks=remarks,
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({"ok": True, "id": p.id})


@finance_bp.route("/salaries", methods=["GET"])
def list_salaries():
    u, err = require_login()
    if err:
        return err
    if u.role not in ("admin", "teacher"):
        return jsonify({"error": "Forbidden"}), 403
    q = SalaryDisbursement.query
    if u.role == "teacher" and u.teacher_id:
        q = q.filter_by(teacher_id=u.teacher_id)
    rows = q.order_by(SalaryDisbursement.paid_on.desc()).limit(200).all()
    out = []
    for s in rows:
        t = Teacher.query.get(s.teacher_id)
        out.append(
            {
                "id": s.id,
                "teacher_id": s.teacher_id,
                "teacher_name": t.name if t else "",
                "period_label": s.period_label,
                "gross": s.gross,
                "deductions": s.deductions,
                "net": s.net,
                "paid_on": s.paid_on.isoformat(),
                "notes": s.notes,
            }
        )
    return jsonify(out)


@finance_bp.route("/salaries", methods=["POST"])
def add_salary():
    u, err = require_login()
    if err:
        return err
    if u.role != "admin":
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    teacher_id = int(data.get("teacher_id", 0))
    period_label = (data.get("period_label") or datetime.utcnow().strftime("%Y-%m")).strip()
    gross = float(data.get("gross") or 0)
    deductions = float(data.get("deductions") or 0)
    net = float(data.get("net") or (gross - deductions))
    notes = (data.get("notes") or "").strip()
    if not teacher_id:
        return jsonify({"error": "teacher_id required"}), 400
    s = SalaryDisbursement(
        teacher_id=teacher_id,
        period_label=period_label,
        gross=gross,
        deductions=deductions,
        net=net,
        paid_on=date.today(),
        notes=notes,
    )
    db.session.add(s)
    db.session.commit()
    return jsonify({"ok": True, "id": s.id})
