import os
import re
import urllib.parse
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "fact_knowledge.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}").strip()

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Robust URL sanitizer for Supabase / PostgreSQL credentials
if "://" in DATABASE_URL and not DATABASE_URL.startswith("sqlite"):
    # Strip accidental brackets around password if provided: :[password]@ -> :password@
    DATABASE_URL = re.sub(r':\[([^\]]+)\]@', r':\1@', DATABASE_URL)
    
    # Properly URL-encode special characters (like @, #, $, %) in the password
    try:
        scheme, rest = DATABASE_URL.split("://", 1)
        if "@" in rest:
            auth_part, host_part = rest.rsplit("@", 1)
            if ":" in auth_part:
                user, password = auth_part.split(":", 1)
                # Unquote first in case partially encoded, then quote fully
                encoded_password = urllib.parse.quote(urllib.parse.unquote(password))
                DATABASE_URL = f"{scheme}://{user}:{encoded_password}@{host_part}"
    except Exception:
        pass

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
