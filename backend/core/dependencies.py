from backend.core.database import mongodb

def get_db():
    return mongodb.db