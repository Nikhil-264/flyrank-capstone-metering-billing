import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, BigInteger, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'api_call' or 'ai_token'
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    token_input: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_cached_input: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_output: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_reasoning: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_microcents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_tenant_idempotency_key"),
    )
