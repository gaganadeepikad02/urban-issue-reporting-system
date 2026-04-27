from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, utils, otp_service
from database import get_db
from email_service import send_email_otp
import re
from datetime import datetime, timezone


router = APIRouter()


def validate_phone(phone: str):
    if not re.fullmatch(r"\d{10}", phone):
        raise HTTPException(status_code=400, detail="Invalid phone number")


def validate_email(email: str):
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")


def get_department_from_email(email: str):
    email = email.lower()

    if "roads" in email:
        return "Roads"
    elif "sanitation" in email:
        return "Sanitation"
    elif "disaster" in email:
        return "Disaster"
    else:
        raise HTTPException(status_code=400, detail="Invalid authority email")
    

def validate_password(password: str):
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")


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

        db.query(models.OTP).filter(models.OTP.email == email).delete()

        otp = otp_service.generate_otp()

        otp_record = models.OTP(
            email=email,
            otp=otp,
            expiry=otp_service.otp_expiry()
        )

        db.add(otp_record)
        db.commit()

        send_email_otp(email, otp)

        return {"message": "OTP sent to email"}

    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to send OTP")


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

    except Exception:
        db.rollback()
        raise HTTPException(500, "OTP verification failed")


@router.post("/signup")
def signup(username: str, phone: str, email: str, password: str, db: Session = Depends(get_db)):

    validate_phone(phone)
    validate_email(email)
    validate_password(password)

    department = get_department_from_email(email)

    try:

        otp_record = db.query(models.OTP).filter(
            models.OTP.email == email,
            models.OTP.verified == True
        ).first()

        if not otp_record:
            raise HTTPException(status_code=400, detail="OTP not verified")

        if db.query(models.Authority).filter(models.Authority.phone == phone).first():
            raise HTTPException(400, "Phone already registered")

        if db.query(models.Authority).filter(models.Authority.email == email).first():
            raise HTTPException(400, "Email already registered")

        authority = models.Authority(
            username=username,
            phone=phone,
            email=email,
            department=department,
            password_hash=utils.hash_password(password)
        )

        db.add(authority)
        db.commit()

        return {"message": "Signup successful"}

    except Exception:
        db.rollback()
        raise HTTPException(500, "Signup failed")


@router.post("/login")
def login(email: str, password: str, db: Session = Depends(get_db)):

    validate_email(email)

    try:

        authority = db.query(models.Authority).filter(
            models.Authority.email == email
        ).first()

        if not authority:
            raise HTTPException(status_code=404, detail="Authority not found")

        if not utils.verify_password(password, authority.password_hash):
            raise HTTPException(status_code=401, detail="Incorrect password")

        token = utils.create_token({"authority_id": authority.id})

        return {
            "message": "Login successful",
            "token": token,
            "username": authority.username,
            "department": authority.department,
            "phone": authority.phone,
            "email": authority.email
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/forgot-password")
def forgot_password(email: str, db: Session = Depends(get_db)):

    validate_email(email)

    try:

        authority = db.query(models.Authority).filter(
            models.Authority.email == email
        ).first()

        if not authority:
            raise HTTPException(404, "Authority not found")

        otp = otp_service.generate_otp()

        otp_record = models.OTP(
            email=email,
            otp=otp,
            expiry=otp_service.otp_expiry()
        )

        db.add(otp_record)
        db.commit()

        send_email_otp(email, otp)

        return {"message": "OTP sent to email"}

    except Exception:
        db.rollback()
        raise HTTPException(500, "Failed to send reset OTP")


@router.post("/reset-password")
def reset_password(email: str, new_password: str, db: Session = Depends(get_db)):

    validate_email(email)
    validate_password(new_password)

    try:

        otp_record = db.query(models.OTP).filter(
            models.OTP.email == email,
            models.OTP.verified == True
        ).first()

        if not otp_record:
            raise HTTPException(400, "OTP verification required")

        authority = db.query(models.Authority).filter(
            models.Authority.email == email
        ).first()

        if not authority:
            raise HTTPException(404, "Authority not found")

        authority.password_hash = utils.hash_password(new_password)
        db.commit()

        return {"message": "Password reset successful"}

    except Exception:
        db.rollback()
        raise HTTPException(500, "Password reset failed")


@router.get("/department-complaints")
def department_complaints(
    department: str,
    priority: str | None = None,
    db: Session = Depends(get_db)
):

    allowed = ["Roads", "Sanitation", "Disaster"]

    if department not in allowed:
        raise HTTPException(status_code=400, detail="Invalid department")

    try:
        query = db.query(models.Complaint).filter(
            models.Complaint.department == department
        )

        if priority:
            query = query.filter(models.Complaint.priority == priority)

        complaints = query.order_by(models.Complaint.created_at.desc()).all()

        return [serialize(c) for c in complaints]

    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch complaints")
