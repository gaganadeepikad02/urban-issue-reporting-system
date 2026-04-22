from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
load_dotenv()
from database import Base, engine
import auth
import os
import authority_auth
import authority_dashboard


try:
    app = FastAPI(
        title="UrbanEye API",
        description="Smart City Complaint Management System",
        version="1.0.0"
    )
except Exception as e:
    raise Exception(f"Failed to initialize FastAPI application: {str(e)}")


@app.on_event("startup")
def startup():

    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        raise Exception(f"Database initialization failed: {str(e)}")

    try:
        os.makedirs("uploads", exist_ok=True)
    except Exception as e:
        raise Exception(f"Failed to create uploads directory: {str(e)}")


try:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
except Exception as e:
    raise Exception(f"Failed to configure CORS middleware: {str(e)}")


try:
    app.include_router(auth.router, prefix="/auth")
except Exception as e:
    raise Exception(f"Failed to include auth router: {str(e)}")


try:
    app.include_router(authority_auth.router, prefix="/authority")
except Exception as e:
    raise Exception(f"Failed to include auth router: {str(e)}")


try:
    app.include_router(authority_dashboard.router, prefix="/authority")
except Exception as e:
    raise Exception(f"Failed to include auth router: {str(e)}")


try:
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
except Exception as e:
    raise Exception(f"Failed to mount uploads directory: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):

    try:
        import traceback
        traceback.print_exc()
    except Exception:
        pass

    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )


@app.get("/")
def root():

    try:
        return {"message": "UrbanEye API running"}
    except Exception:
        return {"message": "UrbanEye API running"}