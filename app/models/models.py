from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True)
    password_hash = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(String)

    profile = relationship("UserProfile", back_populates="user", uselist=False)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    age = Column(Integer)
    roles = Column(JSON)
    company_structure = Column(String)
    income = Column(Float)
    tax_paid = Column(Float)
    investments = Column(JSON)
    debts = Column(Float)
    pension = Column(JSON)
    risk_tolerance = Column(String)
    files_uploaded = Column(JSON)
    personal = Column(JSON)
    income_streams = Column(JSON)
    tax_status = Column(JSON)
    pensions = Column(JSON)
    companies = Column(JSON)
    investment_wrappers = Column(JSON)
    debt_breakdown = Column(JSON)

    user = relationship("User", back_populates="profile")

class FIC(Base):
    __tablename__ = "fics"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    fic_name = Column(String)
    capital = Column(Float, default=0)
    corporation_tax = Column(Float, default=0.19)
    dividend_strategy = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Investment(Base):
    __tablename__ = "investments"
    id = Column(Integer, primary_key=True)
    fic_id = Column(Integer, ForeignKey("fics.id"))
    type = Column(String)
    amount = Column(Float)
    start_date = Column(DateTime)
    projected_return = Column(Float)
    fic = relationship("FIC", backref="investments")

class Advisor(Base):
    __tablename__ = "advisors"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    expertise = Column(String)
    verified = Column(Integer, default=0)
    contact_info = Column(String)
