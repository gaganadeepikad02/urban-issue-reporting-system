import secrets
from datetime import datetime, timedelta


try:
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 5
    RESEND_COOLDOWN_SECONDS = 30
    MAX_OTP_ATTEMPTS = 5
except Exception as e:
    raise Exception(f"Error initializing OTP configuration: {str(e)}")


def now() -> datetime:
    try:
        return datetime.utcnow()
    except Exception as e:
        raise Exception(f"Failed to get current UTC time: {str(e)}")


def generate_otp() -> str:
    try:
        digits = "0123456789"
        return ''.join(secrets.choice(digits) for _ in range(OTP_LENGTH))
    except Exception as e:
        raise Exception(f"OTP generation failed: {str(e)}")


def otp_expiry() -> datetime:
    try:
        return now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    except Exception as e:
        raise Exception(f"Failed to calculate OTP expiry: {str(e)}")


def is_expired(expiry_time: datetime) -> bool:
    try:
        return now() > expiry_time
    except Exception as e:
        raise Exception(f"Error checking OTP expiry: {str(e)}")


def can_resend(last_created: datetime | None) -> bool:
    try:
        if not last_created:
            return True

        diff = now() - last_created
        return diff.total_seconds() >= RESEND_COOLDOWN_SECONDS

    except Exception as e:
        raise Exception(f"Error checking OTP resend cooldown: {str(e)}")