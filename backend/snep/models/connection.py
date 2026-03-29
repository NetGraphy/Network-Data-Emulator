"""ConnectionMapping model — maps network endpoints to devices."""

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snep.models.base import Base, TimestampMixin, UUIDMixin


class ConnectionMapping(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "connection_mappings"
    __table_args__ = (
        UniqueConstraint("protocol", "listen_address", "listen_port", name="uq_connection_mapping_endpoint"),
    )

    device_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), index=True
    )
    protocol: Mapped[str] = mapped_column(String(10))  # ssh or snmp
    listen_address: Mapped[str] = mapped_column(String(45))  # IP address as string for flexibility
    listen_port: Mapped[int] = mapped_column(Integer)

    # Relationships
    device: Mapped["Device"] = relationship(back_populates="connection_mappings")


from snep.models.device import Device  # noqa: E402, F401
