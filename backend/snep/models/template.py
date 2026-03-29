"""CommandTemplate model."""

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snep.models.base import Base, TimestampMixin, UUIDMixin


class CommandTemplate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "command_templates"
    __table_args__ = (
        UniqueConstraint("platform_id", "device_model_id", "command_canonical", name="uq_template_platform_model_cmd"),
    )

    platform_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platforms.id", ondelete="CASCADE"), index=True
    )
    device_model_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("device_models.id", ondelete="CASCADE"), nullable=True
    )
    command_pattern: Mapped[str] = mapped_column(String(256))
    command_canonical: Mapped[str] = mapped_column(String(256))
    template_body: Mapped[str] = mapped_column(Text)
    required_state: Mapped[list] = mapped_column(JSONB, default=list)
    output_type: Mapped[str] = mapped_column(String(20), default="freeform")
    platform_version_min: Mapped[str | None] = mapped_column(String(32), nullable=True)
    platform_version_max: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Relationships
    platform: Mapped["Platform"] = relationship(back_populates="command_templates")


from snep.models.platform import Platform  # noqa: E402, F401
