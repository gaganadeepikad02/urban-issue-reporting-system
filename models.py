from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index, ForeignKey
from sqlalchemy.sql import func
from datetime import datetime, timezone


try:
    from database import Base
except Exception as e:
    raise Exception(f"Failed to import Base from database module: {str(e)}")


class User(Base):
    __tablename__ = "users"

    try:
        id = Column(Integer, primary_key=True, index=True)

        username = Column(String(100), unique=True, nullable=False)
        phone = Column(String(20), unique=True, nullable=False, index=True)
        email = Column(String(100), unique=True, nullable=False, index=True)

        password_hash = Column(String(255), nullable=False)

        is_verified = Column(Boolean, default=False, nullable=False)

        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    except Exception as e:
        raise Exception(f"Error defining User model: {str(e)}")


class OTP(Base):
    __tablename__ = "otp_codes"

    try:
        id = Column(Integer, primary_key=True)

        email = Column(String(100), nullable=False, index=True)  
        otp = Column(String(6), nullable=False)

        expiry = Column(DateTime, nullable=False)

        verified = Column(Boolean, default=False, nullable=False)

        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    except Exception as e:
        raise Exception(f"Error defining OTP model: {str(e)}")


class Complaint(Base):
    __tablename__ = "complaints"

    try:
        id = Column(Integer, primary_key=True, index=True)

        user_id = Column(Integer, ForeignKey("users.id"))

        category = Column(String(100))
        category_source = Column(String(20), default="ai")

        department = Column(String(100))

        latitude = Column(String(50))
        longitude = Column(String(50))

        street = Column(String(255))
        locality = Column(String(255))
        postal_code = Column(String(20))
        district = Column(String(100))
        state = Column(String(100))
        country = Column(String(100))

        location_source = Column(String(20), default="manual")

        description = Column(String(500))

        priority = Column(String(50))
        priority_score = Column(Integer)

        duplicate_flag = Column(Boolean, default=False)
        master_id = Column(Integer, nullable=True)
        duplicate_count = Column(Integer, default=0)

        image_path = Column(String(255))

        status = Column(String(50), default="Pending")

        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    except Exception as e:
        raise Exception(f"Error defining Complaint model: {str(e)}")


class Notification(Base):
    __tablename__ = "notifications"

    try:
        id = Column(Integer, primary_key=True, index=True)

        user_id = Column(Integer, index=True)

        title = Column(String(200))
        message = Column(String(500))

        is_read = Column(Boolean, default=False)

        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    except Exception as e:
        raise Exception(f"Error defining Notification model: {str(e)}")
    

class Authority(Base):
    __tablename__ = "authorities"

    try:
        
        id = Column(Integer, primary_key=True, index=True)

        username = Column(String(100), nullable=False)

        phone = Column(String(20), unique=True, nullable=False)

        email = Column(String(100), unique=True, nullable=False)

        department = Column(String(50), nullable=False)

        password_hash = Column(String(255), nullable=False)

        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    except Exception as e:
        raise Exception(f"Error defining Authority model: {str(e)}")
