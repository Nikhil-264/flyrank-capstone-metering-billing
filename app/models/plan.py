from datetime import datetime
from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g. 'free', 'pro'
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    max_api_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
