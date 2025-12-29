from motor.motor_asyncio import AsyncIOMotorClient
from backend.core.config import MONGODB_URL, DATABASE_NAME

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

mongodb = MongoDB()

async def connect_to_mongo():
    mongodb.client = AsyncIOMotorClient(MONGODB_URL)
    mongodb.db = mongodb.client[DATABASE_NAME]

    # Test connection
    await mongodb.client.admin.command("ping")
    print("✅ MongoDB connected")

async def close_mongo_connection():
    mongodb.client.close()
    print("🔌 MongoDB disconnected")

# Test connection
async def test_connection():
    try:
        await mongodb.client.admin.command('ping')
        print("✅ MongoDB connected successfully")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")