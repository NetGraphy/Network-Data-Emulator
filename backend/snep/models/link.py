"""Link model — represents a connection between two interfaces."""

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snep.models.base import Base, TimestampMixin, UUIDMixin
from snep.models.enums import DiscoveryProtocol, LinkAdminState, LinkType
from snep.models.interface import Interface


class Link(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "links"
    __table_args__ = (
        UniqueConstraint("interface_a_id", "interface_b_id", name="uq_link_interface_pair"),
    )

    interface_a_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interfaces.id", ondelete="CASCADE"), index=True
    )
    interface_b_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interfaces.id", ondelete="CASCADE"), index=True
    )
    link_type: Mapped[str] = mapped_column(String(20), default=LinkType.PHYSICAL.value)
    discovery_protocol: Mapped[str] = mapped_column(String(10), default=DiscoveryProtocol.CDP.value)
    admin_state: Mapped[str] = mapped_column(String(10), default=LinkAdminState.UP.value)

    # Relationships
    interface_a: Mapped["Interface"] = relationship(foreign_keys=[interface_a_id])
    interface_b: Mapped["Interface"] = relationship(foreign_keys=[interface_b_id])
