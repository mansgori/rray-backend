from fastapi import FastAPI
from contextlib import asynccontextmanager
from backend.core.database import connect_to_mongo, close_mongo_connection
from backend.modules.auth.router import auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(auth_router, prefix="/api")