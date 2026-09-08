import os
import re
import urllib.parse
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

DEFAULT_DB_PATH = Path("/tmp/fact_knowledge.db") if os.path.exists("/tmp") else Path(__file__).resolve().parent.parent.parent / "fact_knowledge.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}").strip()

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Robust URL sanitizer for Supabase / PostgreSQL credentials
if "://" in DATABASE_URL and not DATABASE_URL.startswith("sqlite"):
    DATABASE_URL = re.sub(r':\[([^\]]+)\]@', r':\1@', DATABASE_URL)
    try:
        scheme, rest = DATABASE_URL.split("://", 1)
        if "@" in rest:
            auth_part, host_part = rest.rsplit("@", 1)
            if ":" in auth_part:
                user, password = auth_part.split(":", 1)
                encoded_password = urllib.parse.quote(urllib.parse.unquote(password))
                DATABASE_URL = f"{scheme}://{user}:{encoded_password}@{host_part}"
    except Exception:
        pass

def create_db_engine(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)

try:
    engine = create_db_engine(DATABASE_URL)
    # Test connection if PostgreSQL
    if not DATABASE_URL.startswith("sqlite"):
        with engine.connect() as test_conn:
            test_conn.execute(text("SELECT 1"))
        print("[DATABASE] Successfully connected to remote PostgreSQL.")
except Exception as e:
    print(f"[DATABASE WARNING] Failed to connect to {DATABASE_URL[:25]}...: {e}")
    print(f"[DATABASE WARNING] Falling back to local SQLite at {DEFAULT_DB_PATH}")
    DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH}"
    engine = create_db_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[DATABASE] init_db error: {e}")
