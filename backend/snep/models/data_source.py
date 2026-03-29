"""DataSource model — configured external data connections."""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from snep.models.base import Base, TimestampMixin, UUIDMixin


class DataSource(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "data_sources"

    name: Mapped[str] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(20))  # netbox, nautobot, netgraphy, local
    url: Mapped[str] = mapped_column(String(512), default="")
    auth_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_type: Mapped[str] = mapped_column(String(20), default="token")  # token, basic, jwt
    query_language: Mapped[str] = mapped_column(String(20), default="graphql")  # graphql, cypher, sql
    graphql_path: Mapped[str] = mapped_column(String(128), default="/graphql/")  # path to GraphQL endpoint
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
