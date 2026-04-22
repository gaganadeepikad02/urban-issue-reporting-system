from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
import os


try:
    DATABASE_URL = os.getenv("DATABASE_URL")
except Exception as e:
    raise Exception(f"Error loading DATABASE_URL: {str(e)}")


try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=20,
        echo=False,
        connect_args={"connect_timeout": 10}
    )
except SQLAlchemyError as e:
    raise Exception(f"Database engine creation failed: {str(e)}")
except Exception as e:
    raise Exception(f"Unexpected error while creating database engine: {str(e)}")


try:
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
except Exception as e:
    raise Exception(f"SessionLocal creation failed: {str(e)}")


try:
    Base = declarative_base()
except Exception as e:
    raise Exception(f"Declarative base initialization failed: {str(e)}")


def get_db():
    try:
        db = SessionLocal()
    except SQLAlchemyError as e:
        raise Exception(f"Failed to create database session: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error creating DB session: {str(e)}")

    try:
        yield db

    except SQLAlchemyError:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

    finally:
        try:
            db.close()
        except Exception as e:
            raise Exception(f"Error closing DB session: {str(e)}")


def init_db():
    try:
        import models
    except Exception as e:
        raise Exception(f"Failed to import models during DB initialization: {str(e)}")

    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as e:
        raise Exception(f"Error creating database tables: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error during table creation: {str(e)}")