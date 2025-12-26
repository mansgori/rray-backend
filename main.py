from fastapi import FastAPI, APIRouter
from .core.database import connect_to_mongo, close_mongo_connection
from .modules.auth.router import auth_router

app = FastAPI()

@app.get("/")
async def root():
    return {"message":"Hello World"}
    
app.include_router(auth_router, prefix="/api")

@app.on_event("startup")
async def startup():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown():
    await close_mongo_connection()

