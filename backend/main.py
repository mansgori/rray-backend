from fastapi import FastAPI
from contextlib import asynccontextmanager
from backend.core.database import connect_to_mongo, close_mongo_connection
from backend.modules.auth.router import auth_router
from backend.modules.users.router import user_router
from backend.core.email_service.email_instance import email_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    if email_service.client:
        print("📧 Email service initialized (SendGrid)")
    else:
        print("📧 Email service running in MOCK mode")
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/api")