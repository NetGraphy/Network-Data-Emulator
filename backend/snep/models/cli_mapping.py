"""CLI Output Mapping model — stores pasted CLI output and field annotations."""

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snep.models.base import Base, TimestampMixin, UUIDMixin


class CLIOutputMapping(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "cli_output_mappings"

    device_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), index=True
    )
    command: Mapped[str] = mapped_column(String(256))
    raw_output: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(10), default="static")  # static or mapped
    field_annotations: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_description: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Relationships
    device: Mapped["Device"] = relationship(back_populates="cli_mappings")


from snep.models.device import Device  # noqa: E402, F401
