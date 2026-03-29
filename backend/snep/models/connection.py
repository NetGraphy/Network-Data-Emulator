"""ConnectionMapping model — maps network endpoints to devices.

Separates two concerns:
- listen_address/listen_port: where the SSH/SNMP server binds (for server use)
- connect_address/connect_port: where external tools connect to (for Nornir/Ansible/UI)
"""

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
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

    # Server-side: where the emulator binds
    listen_address: Mapped[str] = mapped_column(String(255))  # 0.0.0.0, 127.0.0.2, etc.
    listen_port: Mapped[int] = mapped_column(Integer)

    # Client-side: where external tools connect to
    connect_address: Mapped[str] = mapped_column(String(255), default="127.0.0.1")  # actual reachable IP/hostname
    connect_port: Mapped[int] = mapped_column(Integer, default=0)  # usually same as listen_port

    # Relationships
    device: Mapped["Device"] = relationship(back_populates="connection_mappings")


from snep.models.device import Device  # noqa: E402, F401
