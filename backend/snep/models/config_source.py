"""ConfigSource and DeviceConfig models — Git-backed device configuration management.

ConfigSource: Points to a Git repo containing device config files.
DeviceConfig: Stores the matched config per device for show running-config.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snep.models.base import Base, TimestampMixin, UUIDMixin


class ConfigSource(Base, UUIDMixin, TimestampMixin):
    """A Git repository containing device configuration backups."""
    __tablename__ = "config_sources"

    name: Mapped[str] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(20), default="git")  # git, netgraphy, s3
    repo_url: Mapped[str] = mapped_column(String(512))
    branch: Mapped[str] = mapped_column(String(128), default="main")
    auth_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Jinja2 path template: {{ device.hostname }}.cfg
    path_template: Mapped[str] = mapped_column(String(512), default="{{ device.hostname }}.cfg")
    file_extension: Mapped[str] = mapped_column(String(20), default=".cfg")

    # Sync state
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # success, failed, partial
    last_sync_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class DeviceConfig(Base, UUIDMixin, TimestampMixin):
    """A device's configuration text, imported from a ConfigSource."""
    __tablename__ = "device_configs"

    device_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), index=True
    )
    config_type: Mapped[str] = mapped_column(String(20), default="running")  # running, startup
    config_text: Mapped[str] = mapped_column(Text)
    line_count: Mapped[int | None] = mapped_column(default=0)

    # Source tracking
    source_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("config_sources.id", ondelete="SET NULL"), nullable=True
    )
    source_path: Mapped[str | None] = mapped_column(String(512), nullable=True)  # file path in repo
    source_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    device: Mapped["Device"] = relationship()
    source: Mapped["ConfigSource"] = relationship()


from snep.models.device import Device  # noqa: E402, F401
