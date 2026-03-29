"""TrapDestination model — SNMP trap and syslog receiver targets.

Configures where SNEP sends generated traps and syslog messages.
Supports both SNMP trap receivers and syslog servers.
"""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from snep.models.base import Base, TimestampMixin, UUIDMixin


class TrapDestination(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "trap_destinations"

    name: Mapped[str] = mapped_column(String(128))
    destination_type: Mapped[str] = mapped_column(String(20))  # snmp_trap, syslog
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer)  # 162 for SNMP traps, 514 for syslog
    protocol: Mapped[str] = mapped_column(String(10), default="udp")  # udp, tcp
    community: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SNMPv2c community
    snmp_version: Mapped[str] = mapped_column(String(5), default="v2c")  # v1, v2c, v3
    syslog_facility: Mapped[str | None] = mapped_column(String(20), nullable=True)  # local0-local7
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
