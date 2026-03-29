"""LogEntry model — persistent device syslog buffer.

Stores formatted syslog messages per device. Supports:
- `show logging` CLI rendering
- Log viewer in the UI
- Scenario audit trail (which scenario/event generated the log)
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snep.models.base import Base, UUIDMixin


class LogEntry(Base, UUIDMixin):
    __tablename__ = "log_entries"

    device_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    severity: Mapped[int] = mapped_column(Integer)  # 0-7
    facility: Mapped[str] = mapped_column(String(32))  # LINK, LINEPROTO, BGP, SYS, etc.
    mnemonic: Mapped[str] = mapped_column(String(64))  # UPDOWN, ADJCHANGE, RELOAD, etc.
    message: Mapped[str] = mapped_column(Text)  # Full formatted syslog line
    raw_message: Mapped[str] = mapped_column(Text)  # Unformatted message text
    event_type: Mapped[str] = mapped_column(String(64))  # Template key: interface_down, bgp_down, etc.

    # Scenario audit trail
    scenario_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="SET NULL"), nullable=True
    )
    scenario_event_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenario_events.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    device: Mapped["Device"] = relationship()


from snep.models.device import Device  # noqa: E402, F401
