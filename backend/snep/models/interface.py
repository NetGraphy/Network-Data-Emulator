"""Interface and InterfaceCounter models."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snep.models.base import Base, TimestampMixin, UUIDMixin
from snep.models.enums import Duplex, InterfaceAdminStatus, InterfaceOperStatus, InterfaceType


class Interface(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interfaces"
    __table_args__ = (
        UniqueConstraint("device_id", "name", name="uq_interface_device_name"),
        UniqueConstraint("device_id", "if_index", name="uq_interface_device_ifindex"),
    )

    device_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    short_name: Mapped[str] = mapped_column(String(64))
    if_index: Mapped[int] = mapped_column(Integer)
    interface_type: Mapped[str] = mapped_column(String(20), default=InterfaceType.ETHERNET.value)
    admin_status: Mapped[str] = mapped_column(String(10), default=InterfaceAdminStatus.UP.value)
    oper_status: Mapped[str] = mapped_column(String(20), default=InterfaceOperStatus.UP.value)
    speed_mbps: Mapped[int] = mapped_column(Integer, default=1000)
    duplex: Mapped[str | None] = mapped_column(String(10), nullable=True)
    mtu: Mapped[int] = mapped_column(Integer, default=1500)
    mac_address: Mapped[str] = mapped_column(String(17))
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    ipv6_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)
    vlan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_trunk: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    allowed_vlans: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_input: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_output: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_state_change: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    device: Mapped["Device"] = relationship(back_populates="interfaces")
    counter: Mapped["InterfaceCounter"] = relationship(back_populates="interface", uselist=False, cascade="all, delete-orphan")


class InterfaceCounter(Base, UUIDMixin):
    __tablename__ = "interface_counters"

    interface_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interfaces.id", ondelete="CASCADE"), unique=True
    )
    in_octets: Mapped[int] = mapped_column(BigInteger, default=0)
    out_octets: Mapped[int] = mapped_column(BigInteger, default=0)
    in_unicast_pkts: Mapped[int] = mapped_column(BigInteger, default=0)
    out_unicast_pkts: Mapped[int] = mapped_column(BigInteger, default=0)
    in_multicast_pkts: Mapped[int] = mapped_column(BigInteger, default=0)
    out_multicast_pkts: Mapped[int] = mapped_column(BigInteger, default=0)
    in_broadcast_pkts: Mapped[int] = mapped_column(BigInteger, default=0)
    out_broadcast_pkts: Mapped[int] = mapped_column(BigInteger, default=0)
    in_errors: Mapped[int] = mapped_column(BigInteger, default=0)
    out_errors: Mapped[int] = mapped_column(BigInteger, default=0)
    in_discards: Mapped[int] = mapped_column(BigInteger, default=0)
    out_discards: Mapped[int] = mapped_column(BigInteger, default=0)
    crc_errors: Mapped[int] = mapped_column(BigInteger, default=0)
    collisions: Mapped[int] = mapped_column(BigInteger, default=0)
    rate_in_bps: Mapped[int] = mapped_column(BigInteger, default=300_000_000)
    rate_out_bps: Mapped[int] = mapped_column(BigInteger, default=150_000_000)
    rate_reference: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Relationships
    interface: Mapped["Interface"] = relationship(back_populates="counter")


from snep.models.device import Device  # noqa: E402, F401
