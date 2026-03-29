"""Scenario and ScenarioEvent models."""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snep.models.base import Base, TimestampMixin, UUIDMixin


class Scenario(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "scenarios"

    name: Mapped[str] = mapped_column(String(128), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    is_repeatable: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    events: Mapped[list["ScenarioEvent"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan", order_by="ScenarioEvent.sequence_order"
    )


class ScenarioEvent(Base, UUIDMixin):
    __tablename__ = "scenario_events"

    scenario_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), index=True
    )
    sequence_order: Mapped[int] = mapped_column(Integer)
    trigger_type: Mapped[str] = mapped_column(String(20))
    trigger_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    action_type: Mapped[str] = mapped_column(String(30))
    action_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    rollback_action: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at = TimestampMixin.created_at

    # Relationships
    scenario: Mapped["Scenario"] = relationship(back_populates="events")
