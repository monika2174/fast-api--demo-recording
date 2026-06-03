from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

# Database URL for SQLAlchemy (Postgres)
db_url = "postgresql://postgres:1234567890@localhost:5432/new"

# Try to create an engine for Postgres; if connection fails, fall back to SQLite
try:
	engine = create_engine(db_url)
	# test connection
	with engine.connect() as conn:
		pass
except OperationalError:
	print("Warning: cannot connect to Postgres 'telusko'; falling back to SQLite ./fallback.db")
	engine = create_engine("sqlite:///./fallback.db", connect_args={"check_same_thread": False})

# Session factory bound to the active engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Convenience callable to get a session: use `session()` in code
session = SessionLocal