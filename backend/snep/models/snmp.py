"""SNMP Profile model."""

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snep.models.base import Base, TimestampMixin, UUIDMixin


class SNMPProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "snmp_profiles"

    device_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), unique=True
    )
    v2_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    v2_community: Mapped[str | None] = mapped_column(String(64), nullable=True)
    v3_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    v3_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    v3_auth_protocol: Mapped[str | None] = mapped_column(String(10), nullable=True)
    v3_auth_password: Mapped[str | None] = mapped_column(String(128), nullable=True)
    v3_priv_protocol: Mapped[str | None] = mapped_column(String(10), nullable=True)
    v3_priv_password: Mapped[str | None] = mapped_column(String(128), nullable=True)
    v3_context: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sys_descr: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sys_contact: Mapped[str | None] = mapped_column(String(256), nullable=True)
    sys_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    sys_location: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Relationships
    device: Mapped["Device"] = relationship(back_populates="snmp_profile")


from snep.models.device import Device  # noqa: E402, F401
