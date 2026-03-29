"""CustomFilter model — user-defined Jinja2 filter functions stored in DB.

These are Python functions that can be used in CLI templates and syslog messages:
  {{ counter_value | bits_to_human }}
  {{ rate_bps | utilization(speed_mbps) }}
"""

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from snep.models.base import Base, TimestampMixin, UUIDMixin


class CustomFilter(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "custom_filters"

    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    code: Mapped[str] = mapped_column(Text)  # Python function body (NOT the def line)
    signature: Mapped[str] = mapped_column(String(256), default="value")  # e.g., "value, precision=2"
    test_input: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: e.g., "[450000000]"
    test_expected: Mapped[str | None] = mapped_column(String(512), nullable=True)  # e.g., "450.0 Mbps"
    category: Mapped[str] = mapped_column(String(32), default="general")
    # Categories: formatting, calculation, network, conversion, general
    platform_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platforms.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)  # Seed filters can't be deleted
