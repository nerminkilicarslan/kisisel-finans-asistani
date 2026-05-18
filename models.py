from pathlib import Path
from sqlalchemy import Column, Integer, String, Float, Date, Boolean, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import date

Base = declarative_base()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = DATA_DIR / "finans.db"
DATABASE_URL = f"sqlite:///{DB_FILE.as_posix()}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, default="")
    type = Column(String, nullable=False)       # "gelir" | "gider"
    source = Column(String, default="manual")   # "manual" | "csv" | "mock"


class BudgetPlan(Base):
    __tablename__ = "budget_plans"
    id = Column(Integer, primary_key=True, index=True)
    month = Column(Integer, nullable=False)     # 1-12
    year = Column(Integer, nullable=False)
    category = Column(String, nullable=False)
    limit_amount = Column(Float, nullable=False)


class SavingsGoal(Base):
    __tablename__ = "savings_goals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    target_date = Column(Date, nullable=True)
    is_completed = Column(Boolean, default=False)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
