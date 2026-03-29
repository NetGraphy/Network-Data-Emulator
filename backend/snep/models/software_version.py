"""SoftwareVersion model — tracks OS versions per platform."""

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snep.models.base import Base, TimestampMixin, UUIDMixin


class SoftwareVersion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "software_versions"

    platform_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platforms.id", ondelete="CASCADE"), index=True
    )
    version_string: Mapped[str] = mapped_column(String(64), index=True)
    major: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    patch: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="current")
    # current, deprecated, end_of_support, end_of_life
    release_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    end_of_support: Mapped[str | None] = mapped_column(Date, nullable=True)
    end_of_life: Mapped[str | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    platform: Mapped["Platform"] = relationship()


from snep.models.platform import Platform  # noqa: E402, F401
