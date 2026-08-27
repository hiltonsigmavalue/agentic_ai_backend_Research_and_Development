from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    txnid: Mapped[str] = mapped_column(String(25), unique=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    payment_category: Mapped[str] = mapped_column(String(20), default="domestic")
    productinfo: Mapped[str] = mapped_column(String(255))
    firstname: Mapped[str] = mapped_column(String(100))
    lastname: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="created", index=True)
    unmappedstatus: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mihpayid: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    bank_ref_num: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_hash_verified: Mapped[str] = mapped_column(String(10), default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
