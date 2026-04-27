from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from datetime import datetime, timezone, timedelta


router = APIRouter()


def serialize(obj):
    data = obj.__dict__.copy()
    data.pop("_sa_instance_state", None)

    if "created_at" in data and data["created_at"]:
        dt = data["created_at"]

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        data["created_at"] = dt.isoformat().replace("+00:00", "Z")

    return data


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

    return [serialize(c) for c in complaints]


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
    data = serialize(complaint)

    data["username"] = user.username if user else "Unknown"
    data["phone"] = user.phone if user else "Unknown"
    data["linked_count"] = linked_count

    return data


@router.post("/update-status")
def update_status(
    complaint_id: int,
    status: str,
    remarks: str = None,
    db: Session = Depends(get_db)
):

    complaint = db.query(models.Complaint)\
        .filter(models.Complaint.id == complaint_id)\
        .first()

    if not complaint:
        raise HTTPException(404, "Complaint not found")

    master_id = complaint.master_id if complaint.master_id else complaint.id

    linked_complaints = db.query(models.Complaint)\
        .filter(
            (models.Complaint.id == master_id) |
            (models.Complaint.master_id == master_id)
        ).all()

    for c in linked_complaints:
        c.status = status
        c.remarks = remarks

        notification = models.Notification(
            user_id=c.user_id,
            title="Complaint Status Updated",
            message=f"Your complaint #{c.id} is now {status}"
        )
        db.add(notification)

    db.commit()

    return {"message": "All linked complaints updated"}


@router.get("/notifications")
def get_notifications(department: str, db: Session = Depends(get_db)):

    complaints = db.query(models.Complaint)\
        .filter(models.Complaint.department == department)\
        .order_by(models.Complaint.created_at.desc())\
        .limit(20)\
        .all()

    notifications = []

    for c in complaints:
        ist_time = c.created_at + timedelta(hours=5, minutes=30)

        notifications.append({
            "title": "New Complaint",
            "message": f"{c.category} reported at {c.locality}",
            "time": ist_time.isoformat()
        })

    return notifications
