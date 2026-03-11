from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class RiskClassificationDB(Base):
    __tablename__ = "risk_classifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ai_system_id: Mapped[str] = mapped_column(String(255), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)
    classification_path: Mapped[str] = mapped_column(String(50), nullable=False)
    annex_i_legislation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_safety_component: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    requires_third_party_assessment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    annex_iii_category: Mapped[int | None] = mapped_column(nullable=True)
    profiles_natural_persons: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    exception_applies: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    exception_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(nullable=False, default=1.0)
    classified_by: Mapped[str] = mapped_column(String(50), default="auto")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )
