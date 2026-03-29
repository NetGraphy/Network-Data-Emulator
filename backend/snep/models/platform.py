"""Platform model — represents a network OS family."""

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snep.models.base import Base, TimestampMixin, UUIDMixin


class Platform(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "platforms"

    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    vendor: Mapped[str] = mapped_column(String(64))
    prompt_template: Mapped[str] = mapped_column(String(256))
    error_template: Mapped[str] = mapped_column(String(512))
    cli_modes: Mapped[dict] = mapped_column(JSONB, default=dict)
    default_credentials: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    device_models: Mapped[list["DeviceModel"]] = relationship(back_populates="platform", cascade="all, delete-orphan")
    command_templates: Mapped[list] = relationship("CommandTemplate", back_populates="platform", cascade="all, delete-orphan")


# Import here to avoid circular - DeviceModel is in device.py
from snep.models.device import DeviceModel  # noqa: E402, F401
