from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database import SessionLocal
from datetime import datetime, timezone
import re
import models, utils, otp_service
import uuid
import os
from services import ai_service
from services.department_service import CATEGORY_DEPT
from services.complaint_logic import detect_duplicate, compute_priority
from services.location_service import get_exif_location, reverse_geocode
from services.department_service import get_department
from email_service import send_email_otp
from PIL import Image
from io import BytesIO
from services.cloudinary_service import upload_image


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception:
            pass


def validate_phone(phone: str):
    try:
        if not re.fullmatch(r"\d{10}", phone):
            raise HTTPException(status_code=400, detail="Invalid phone number")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Phone validation failed")


def validate_email(email: str):
    try:
        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
            raise HTTPException(status_code=400, detail="Invalid email")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Email validation failed")
    

def validate_password(password: str):
    try:
        if len(password) < 6:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 6 characters"
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Password validation failed")


def serialize(obj):
    data = obj.__dict__.copy()
    data.pop("_sa_instance_state", None)

    if "created_at" in data and data["created_at"]:
        dt = data["created_at"]

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        data["created_at"] = dt.isoformat().replace("+00:00", "Z")

    return data


@router.post("/send-otp")
def send_otp(email: str, db: Session = Depends(get_db)):

    validate_email(email)

    try:
        existing = db.query(models.OTP).filter(models.OTP.email == email).all()
        for row in existing:
            db.delete(row)

        db.commit()

        otp = otp_service.generate_otp()

        otp_record = models.OTP(
            email=email,
            otp=otp,
            expiry=otp_service.otp_expiry()
        )

        db.add(otp_record)
        db.commit()

        print("OTP:", otp) 

        send_email_otp(email, otp)

        return {"message": "OTP sent to email"}

    except Exception as e:
        db.rollback()
        print("ERROR IN SEND OTP:", str(e))  
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-otp")
def verify_otp(email: str, otp: str, db: Session = Depends(get_db)):

    validate_email(email)

    try:
        record = db.query(models.OTP).filter(
            models.OTP.email == email,
            models.OTP.otp == otp,
            models.OTP.verified == False
        ).first()

        if not record:
            raise HTTPException(400, "Invalid OTP")

        if otp_service.is_expired(record.expiry):
            raise HTTPException(400, "OTP expired")

        record.verified = True
        db.commit()

        return {"message": "OTP verified"}

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(500, "OTP verification failed")


@router.post("/signup")
def signup(username: str, phone: str, email: str, password: str, db: Session = Depends(get_db)):

    validate_phone(phone)
    validate_email(email)
    validate_password(password)

    try:

        otp_record = db.query(models.OTP).filter(
            models.OTP.email == email,
            models.OTP.verified == True
        ).first()

        if not otp_record:
            raise HTTPException(400, "OTP not verified")

        if db.query(models.User).filter(models.User.phone == phone).first():
            raise HTTPException(400, "Phone already registered")

        if db.query(models.User).filter(models.User.email == email).first():
            raise HTTPException(400, "Email already registered")

        if db.query(models.User).filter(models.User.username == username).first():
            raise HTTPException(400, "Username already taken")

        user = models.User(
            username=username,
            phone=phone,
            email=email,
            password_hash=utils.hash_password(password),
            is_verified=True
        )

        db.add(user)
        db.commit()

        return {"message": "Signup successful"}

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(500, "Signup failed")


@router.post("/login")
def login(phone: str, password: str, db: Session = Depends(get_db)):

    validate_phone(phone)

    try:
        user = db.query(models.User).filter(models.User.phone == phone).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not user.is_verified:
            raise HTTPException(status_code=403, detail="User not verified")

        if not utils.verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Incorrect password")

        token = utils.create_token({"user_id": user.id})

        return {
            "message": "Login successful",
            "token": token,
            "user_id": user.id,
            "username": user.username
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/reset-password")
def reset_password(email: str, new_password: str, db: Session = Depends(get_db)):

    validate_email(email)
    validate_password(new_password)

    try:

        otp_record = db.query(models.OTP).filter(
            models.OTP.email == email,
            models.OTP.verified == True
        ).order_by(models.OTP.created_at.desc()).first()

        if not otp_record:
            raise HTTPException(400, "OTP verification required")

        user = db.query(models.User).filter(
            models.User.email == email
        ).first()

        if not user:
            raise HTTPException(404, "User not found")

        user.password_hash = utils.hash_password(new_password)

        db.commit()

        return {"message": "Password reset successful"}

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(500, "Password reset failed")


@router.post("/analyze-image")
def analyze_image(file: UploadFile = File(...), db: Session = Depends(get_db)):

    try:

        contents = file.file.read()

        if not contents:
            raise HTTPException(400, "Empty file")

        try:
            img = Image.open(BytesIO(contents))
            img.verify()
        except Exception:
            raise HTTPException(400, "Invalid image file")

        image_url = upload_image(contents)

        temp_path = f"/tmp/{uuid.uuid4()}.jpg"

        with open(temp_path, "wb") as f:
            f.write(contents)

        category, confidence = ai_service.predict(temp_path)

        if confidence < ai_service.CONFIDENCE_THRESHOLD:
            category = "Manual Required"
            category_source = "manual"
        else:
            category = category.title()
            category_source = "ai"

        department = CATEGORY_DEPT.get(category, "Unknown")

        lat, lon = get_exif_location(temp_path)

        location_source = "image_exif"

        if lat is None or lon is None:
            location_source = "manual"

        address = {}
        if lat is not None and lon is not None:
            address = reverse_geocode(lat, lon) or {}

        duplicate_flag, master_id, dup_count = detect_duplicate(
            db, category, lat or 0, lon or 0
        )

        score, priority = compute_priority(category, dup_count)

        return {
            "category": category,
            "confidence": confidence,
            "category_source": category_source,
            "department": department,
            "latitude": lat,
            "longitude": lon,
            "priority": priority,
            "priority_score": score,
            "duplicate": duplicate_flag,
            "duplicate_count": dup_count,
            "master_id": master_id,
            "image_path": image_url,
            "location_source": location_source,
            "address": address
        }

    except HTTPException:
        raise

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit-complaint")
def submit_complaint(
    user_id: int,
    category: str,
    department: str,
    latitude: float | None = None,
    longitude: float | None = None,
    street: str = "",
    locality: str = "",
    postal_code: str = "",
    district: str = "",
    state: str = "",
    country: str = "",
    priority: str = "",
    duplicate_flag: bool = False,   
    master_id: int | None = None,   
    description: str = "",
    image_path: str = "",
    db: Session = Depends(get_db)
):

    try:

        user = db.query(models.User).filter(
            models.User.id == user_id
        ).first()

        if not user:
            raise HTTPException(404, "Invalid user")

        if not category or not department:
            raise HTTPException(400, "Invalid complaint data")

        if not image_path:
            raise HTTPException(400, "Image missing")

        is_dup, detected_master_id, dup_count = detect_duplicate(
            db, category, latitude or 0, longitude or 0
        )

        complaint = models.Complaint(
            user_id=user_id,
            category=category,
            department=department,
            latitude=str(latitude) if latitude else "",
            longitude=str(longitude) if longitude else "",
            street=street,
            locality=locality,
            postal_code=postal_code,
            district=district,
            state=state,
            country=country,
            priority=priority,
            description=description,
            image_path=image_path,
            created_at=datetime.now(timezone.utc)
        )

        notification = models.Notification(
            user_id=user_id,
            title="Complaint Submitted",
            message=f"Your complaint for {category} has been registered."
        )

        db.add(notification)
        db.add(complaint)
        db.commit()
        db.refresh(complaint)

        if is_dup:
            complaint.master_id = detected_master_id
            complaint.duplicate_flag = True
        else:
            complaint.master_id = complaint.id
            complaint.duplicate_flag = False

        db.commit()

        return {
            "message": "Complaint submitted successfully",
            "created_at": complaint.created_at.replace(tzinfo=timezone.utc)
                                     .isoformat()
                                     .replace("+00:00", "Z"),
            "status": complaint.status
        }

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@router.get("/reverse-geocode")
def reverse_geocode_api(lat: float, lon: float):

    try:
        address = reverse_geocode(lat, lon) or {}
        return address

    except Exception:
        return {}


def valid_departments():
    return list(set(CATEGORY_DEPT.values()))


@router.get("/complaint-summary")
def complaint_summary(user_id: int, db: Session = Depends(get_db)):

    try:

        total = db.query(models.Complaint)\
            .filter(models.Complaint.user_id == user_id)\
            .count()

        pending = db.query(models.Complaint)\
            .filter(
                models.Complaint.user_id == user_id,
                models.Complaint.status == "Pending"
            )\
            .count()

        inprogress = db.query(models.Complaint)\
            .filter(
                models.Complaint.user_id == user_id,
                models.Complaint.status == "In Progress"
            )\
            .count()

        resolved = db.query(models.Complaint)\
            .filter(
                models.Complaint.user_id == user_id,
                models.Complaint.status == "Resolved"
            )\
            .count()

        invalid = db.query(models.Complaint)\
            .filter(
                models.Complaint.user_id == user_id,
                models.Complaint.status == "Invalid"
            )\
            .count()

        return {
            "total": total,
            "pending": pending,
            "inprogress": inprogress,
            "resolved": resolved,
            "invalid": invalid
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch complaint summary"
        )


@router.get("/complaints")
def get_complaints(
    user_id: int,
    status: str | None = None,
    db: Session = Depends(get_db)
):

    try:

        query = db.query(models.Complaint)\
            .filter(models.Complaint.user_id == user_id)

        if status:
            query = query.filter(models.Complaint.status == status)

        complaints = query.order_by(
            models.Complaint.created_at.desc()
        ).all()

        return [serialize(c) for c in complaints]

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch complaints"
        )


@router.get("/complaint/{complaint_id}")
def get_complaint_detail(
    complaint_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):

    try:

        complaint = db.query(models.Complaint)\
            .filter(
                models.Complaint.id == complaint_id,
                models.Complaint.user_id == user_id
            )\
            .first()

        if not complaint:
            raise HTTPException(404, "Complaint not found")

        return serialize(complaint)

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch complaint detail"
        )


@router.delete("/complaint/{complaint_id}")
def delete_complaint(
    complaint_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):

    try:

        complaint = db.query(models.Complaint)\
            .filter(
                models.Complaint.id == complaint_id,
                models.Complaint.user_id == user_id
            )\
            .first()

        if not complaint:
            raise HTTPException(404, "Complaint not found")

        if complaint.status == "Resolved":
            raise HTTPException(
                400,
                "Resolved complaints cannot be deleted"
            )

        db.delete(complaint)
        db.commit()

        return {"message": "Complaint deleted successfully"}

    except HTTPException:
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to delete complaint"
        )


@router.get("/notifications")
def get_notifications(
    user_id: int,
    db: Session = Depends(get_db)
):

    try:

        notifications = db.query(models.Notification)\
            .filter(models.Notification.user_id == user_id)\
            .order_by(models.Notification.created_at.desc())\
            .all()

        return notifications

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch notifications"
        )


@router.post("/notification-read/{notification_id}")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db)
):

    try:

        notification = db.query(models.Notification)\
            .filter(models.Notification.id == notification_id)\
            .first()

        if not notification:
            raise HTTPException(404, "Notification not found")

        notification.is_read = True

        db.commit()

        return {"message": "Notification updated"}

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to update notification"
        )


@router.get("/notification-count")
def notification_count(
    user_id: int,
    db: Session = Depends(get_db)
):

    try:

        count = db.query(models.Notification)\
            .filter(
                models.Notification.user_id == user_id,
                models.Notification.is_read == False
            )\
            .count()

        return {"unread": count}

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch notification count"
        )


@router.get("/profile")
def get_profile(
    user_id: int,
    db: Session = Depends(get_db)
):

    try:

        user = db.query(models.User)\
            .filter(models.User.id == user_id)\
            .first()

        if not user:
            raise HTTPException(404, "User not found")

        return {
            "username": user.username,
            "phone": user.phone,
            "email": user.email
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch profile"
        )


@router.post("/update-profile")
def update_profile(
    user_id: int,
    username: str,
    db: Session = Depends(get_db)
):

    try:

        user = db.query(models.User)\
            .filter(models.User.id == user_id)\
            .first()

        if not user:
            raise HTTPException(404, "User not found")

        user.username = username

        db.commit()

        return {"message": "Profile updated successfully"}

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to update profile"
        )


@router.post("/update-email")
def update_email(user_id: int, email: str, db: Session = Depends(get_db)):

    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(404, "User not found")

    user.email = email
    db.commit()

    return {"message": "Email updated"}


@router.delete("/delete-account")
def delete_account(
    user_id: int,
    db: Session = Depends(get_db)
):

    try:

        user = db.query(models.User)\
            .filter(models.User.id == user_id)\
            .first()

        if not user:
            raise HTTPException(404, "User not found")

        db.delete(user)
        db.commit()

        return {"message": "Account deleted successfully"}

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete account"
        )
