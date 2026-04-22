from passlib.context import CryptContext
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError
import datetime
import os


try:
    SECRET_KEY = os.getenv("SECRET_KEY")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS = 1
except Exception as e:
    raise Exception(f"Error initializing JWT configuration: {str(e)}")


try:
    pwd_context = CryptContext(
        schemes=["bcrypt"],
        deprecated="auto"
    )
except Exception as e:
    raise Exception(f"Password context initialization failed: {str(e)}")


def hash_password(password: str) -> str:
    try:
        if not password:
            raise ValueError("Password cannot be empty")

        return pwd_context.hash(password)

    except Exception as e:
        raise Exception(f"Password hashing failed: {str(e)}")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(password, hashed)

    except Exception:
        return False


def create_token(data: dict) -> str:
    try:

        to_encode = data.copy()

        expire = datetime.datetime.utcnow() + datetime.timedelta(
            days=ACCESS_TOKEN_EXPIRE_DAYS
        )

        to_encode.update({
            "exp": expire,
            "iat": datetime.datetime.utcnow(),
            "type": "access"
        })

        return jwt.encode(
            to_encode,
            SECRET_KEY,
            algorithm=ALGORITHM
        )

    except Exception as e:
        raise Exception(f"Token creation failed: {str(e)}")


def decode_token(token: str) -> dict | None:
    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except ExpiredSignatureError:
        return None

    except JWTError:
        return None

    except Exception:
        return None


def get_user_id(token: str) -> int | None:
    try:

        payload = decode_token(token)

        if payload:
            return payload.get("user_id")

        return None

    except Exception:
        return None