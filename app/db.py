from sqlmodel import SQLModel, create_engine, Session
import os


# Use SQLite for development, but allow override for production
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./appointments.db")
engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    return Session(engine)