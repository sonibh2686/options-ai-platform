from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime

from app.db.database import Base


class ScanHistory(Base):
    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    mode = Column(String, index=True)
    option_type = Column(String, index=True)
    action = Column(String, index=True)
    expiry = Column(String, index=True)
    score = Column(Float)
    recommendation = Column(String)
    payload = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)