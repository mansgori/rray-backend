from pathlib import Path
from dotenv import load_dotenv
import os


ROOT_DIR= Path(__file__).resolve().parent.parent

load_dotenv(ROOT_DIR / ".env")

MONGODB_URL = os.getenv("MONGODB_URL","mongodb://localhost:27017")
DATABASE_NAME=os.getenv("DATABASE_NAME","rayy_db")