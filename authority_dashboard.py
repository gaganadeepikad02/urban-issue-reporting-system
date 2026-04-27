from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import utils


router = APIRouter()


@router.get("/dashboard-counts")
def get_dashboard_counts(department: str, db: Session = Depends(get_db)):

    total = db.query(models.Complaint) \
        .filter(models.Complaint.department == department) \
        .count()

    high_priority = db.query(models.Complaint) \
        .filter(models.Complaint.department == department) \
        .filter(models.Complaint.priority == "High") \
        .count()

    pending = db.query(models.Complaint) \
        .filter(models.Complaint.department == department) \
        .filter(models.Complaint.status.in_(["Submitted", "Pending"])) \
        .count()

    inprogress = db.query(models.Complaint) \
        .filter(models.Complaint.department == department) \
        .filter(models.Complaint.status == "In Progress") \
        .count()

    resolved = db.query(models.Complaint) \
        .filter(models.Complaint.department == department) \
        .filter(models.Complaint.status == "Resolved") \
        .count()

    invalid = db.query(models.Complaint) \
        .filter(models.Complaint.department == department) \
        .filter(models.Complaint.status == "Invalid") \
        .count()

    return {
        "total": total,
        "high_priority": high_priority,
        "pending": pending,
        "inprogress": inprogress,
        "resolved": resolved,
        "invalid": invalid
    }


@router.get("/complaints")
def get_department_complaints(
    department: str,
    status: str | None = None,
    db: Session = Depends(get_db)
):

    query = db.query(models.Complaint).filter(
        models.Complaint.department == department
    )

    if status:
        query = query.filter(models.Complaint.status == status)

    complaints = query.order_by(models.Complaint.created_at.desc()).all()

    return complaints


@router.get("/complaint/{complaint_id}")
def get_complaint_details(complaint_id: int, db: Session = Depends(get_db)):

    complaint = db.query(models.Complaint)\
        .filter(models.Complaint.id == complaint_id)\
        .first()

    if not complaint:
        raise HTTPException(404, "Complaint not found")

    if complaint.master_id:
        linked_count = db.query(models.Complaint)\
        .filter(models.Complaint.master_id == complaint.master_id)\
        .count()
    else:
        linked_count = 1
    
    user = db.query(models.User).filter(models.User.id == complaint.user_id).first()
    result = complaint.__dict__
    result["username"] = user.username if user else "Unknown"
    result["phone"] = user.phone if user else "Unknown"
    result["linked_count"] = linked_count

    return result


@router.post("/update-status")
def update_status(
    complaint_id: int,
    status: str,
    remarks: str = None,
    db: Session = Depends(get_db)
):

    complaint = db.query(models.Complaint) \
        .filter(models.Complaint.id == complaint_id) \
        .first()

    if not complaint:
        raise HTTPException(404, "Complaint not found")

    if complaint.master_id:

        duplicate_complaints = db.query(models.Complaint).filter(
            models.Complaint.master_id == complaint.master_id
        ).all()

        for comp in duplicate_complaints:
            comp.status = status
            comp.remarks = remarks

            db.add(models.Notification(
                user_id=comp.user_id,
                title="Complaint Status Updated",
                message=f"Your complaint #{comp.id} is now {status}"
            ))

    else:
        complaint.status = status
        complaint.remarks = remarks

        db.add(models.Notification(
            user_id=complaint.user_id,
            title="Complaint Status Updated",
            message=f"Your complaint #{complaint.id} is now {status}"
        ))

    db.commit()

    return {"message": "Complaint(s) status updated successfully"}


@router.get("/notifications")
def get_notifications(department: str, db: Session = Depends(get_db)):

    complaints = db.query(models.Complaint)\
        .filter(models.Complaint.department == department)\
        .order_by(models.Complaint.created_at.desc())\
        .limit(20)\
        .all()

    notifications = []

    for c in complaints:
        notifications.append({
            "title": "New Complaint",
            "message": f"{c.category} reported at {c.locality}",
            "time": c.created_at
        })

    return notifications

@router.post("/update-profile")
def update_profile(
    email: str,
    username: str | None = None,
    password: str | None = None,
    db: Session = Depends(get_db)
):

    authority = db.query(models.Authority).filter(
        models.Authority.email == email
    ).first()

    if not authority:
        raise HTTPException(404, "Authority not found")

    if username:
        authority.username = username

    if password:
        authority.password_hash = utils.hash_password(password)

    db.commit()

    return {"message": "Profile updated successfully"}
