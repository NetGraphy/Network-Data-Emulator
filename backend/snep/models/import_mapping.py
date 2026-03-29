"""ImportMapping model — Jinja2 templates for transforming query results into SNEP entities."""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from snep.models.base import Base, TimestampMixin, UUIDMixin


class ImportMapping(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "import_mappings"

    name: Mapped[str] = mapped_column(String(128), unique=True)
    source_type: Mapped[str] = mapped_column(String(20))  # netbox, nautobot, netgraphy, generic
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    query: Mapped[str] = mapped_column(Text, default="")  # The default GraphQL/Cypher query
    result_path: Mapped[str] = mapped_column(String(128), default="")  # JSON path to array in results, e.g. "data.device_list"

    # Jinja2 mapping templates (YAML output)
    device_template: Mapped[str] = mapped_column(Text, default="")
    interface_template: Mapped[str] = mapped_column(Text, default="")
    link_template: Mapped[str] = mapped_column(Text, default="")

    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
