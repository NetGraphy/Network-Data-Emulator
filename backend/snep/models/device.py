"""Device, DeviceModel, and DeviceCredential models."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snep.models.base import Base, TimestampMixin, UUIDMixin
from snep.models.enums import AdminState


class DeviceModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "device_models"
    __table_args__ = (UniqueConstraint("platform_id", "name", name="uq_device_model_platform_name"),)

    platform_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("platforms.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(128))
    display_name: Mapped[str] = mapped_column(String(256))
    software_version: Mapped[str] = mapped_column(String(64))
    default_interface_pattern: Mapped[list] = mapped_column(JSONB, default=list)
    hardware_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    platform: Mapped["Platform"] = relationship(back_populates="device_models")
    devices: Mapped[list["Device"]] = relationship(back_populates="device_model", cascade="all, delete-orphan")


class Device(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "devices"

    device_model_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("device_models.id", ondelete="CASCADE"))
    hostname: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    management_ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    serial_number: Mapped[str] = mapped_column(String(32), unique=True)
    software_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    uptime_seconds: Mapped[int] = mapped_column(BigInteger, default=7776000)
    uptime_reference: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    admin_state: Mapped[str] = mapped_column(String(20), default=AdminState.ACTIVE.value)
    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    emulation_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    device_model: Mapped["DeviceModel"] = relationship(back_populates="devices")
    interfaces: Mapped[list["Interface"]] = relationship(
        back_populates="device", cascade="all, delete-orphan", order_by="Interface.sort_order"
    )
    credentials: Mapped[list["DeviceCredential"]] = relationship(back_populates="device", cascade="all, delete-orphan")
    snmp_profile: Mapped["SNMPProfile"] = relationship(back_populates="device", uselist=False, cascade="all, delete-orphan")
    cli_mappings: Mapped[list["CLIOutputMapping"]] = relationship(back_populates="device", cascade="all, delete-orphan")
    connection_mappings: Mapped[list["ConnectionMapping"]] = relationship(back_populates="device", cascade="all, delete-orphan")


class DeviceCredential(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "device_credentials"
    __table_args__ = (UniqueConstraint("device_id", "username", name="uq_credential_device_username"),)

    device_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"))
    username: Mapped[str] = mapped_column(String(64))
    password: Mapped[str] = mapped_column(String(128))
    enable_password: Mapped[str | None] = mapped_column(String(128), nullable=True)
    privilege_level: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    device: Mapped["Device"] = relationship(back_populates="credentials")


# Avoid circular imports
from snep.models.cli_mapping import CLIOutputMapping  # noqa: E402, F401
from snep.models.connection import ConnectionMapping  # noqa: E402, F401
from snep.models.interface import Interface  # noqa: E402, F401
from snep.models.platform import Platform  # noqa: E402, F401
from snep.models.snmp import SNMPProfile  # noqa: E402, F401
