"""CommandOutputLibrary — versioned CLI output samples organized by platform/version/model/command.

This replaces device-specific CLI mappings as the primary way to manage CLI outputs.
Outputs are keyed by (platform, software_version, device_model, command) and can be
tested against parsers (TextFSM/NTC-Templates, Genie) to validate compatibility.
"""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snep.models.base import Base, TimestampMixin, UUIDMixin


class CommandOutputLibrary(Base, UUIDMixin, TimestampMixin):
    """A versioned CLI output sample for a specific platform/version/model/command combination."""

    __tablename__ = "command_output_library"
    __table_args__ = (
        UniqueConstraint(
            "platform_id", "software_version_id", "device_model_id", "command",
            name="uq_cli_library_entry",
        ),
    )

    platform_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platforms.id", ondelete="CASCADE"), index=True
    )
    device_model_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("device_models.id", ondelete="SET NULL"), nullable=True
    )
    software_version_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("software_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    software_version: Mapped[str] = mapped_column(String(64), index=True)  # denormalized for display
    command: Mapped[str] = mapped_column(String(256), index=True)
    raw_output: Mapped[str] = mapped_column(Text)

    # Parser validation results
    parser_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Structure: {
    #   "textfsm": {"status": "pass"|"fail"|"no_template", "template": "cisco_ios_show_version.textfsm", "parsed_fields": [...], "error": null},
    #   "genie": {"status": "pass"|"fail"|"no_parser", "parsed_fields": [...], "error": null},
    # }

    # Version lineage
    parent_version_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("command_output_library.id", ondelete="SET NULL"), nullable=True
    )
    diff_from_parent: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Structure: {
    #   "structural_change": true|false,
    #   "field_changes": [{"field": "uptime", "old_format": "...", "new_format": "..."}],
    #   "parser_compatibility": "compatible"|"new_parser_needed"|"minor_change",
    #   "diff_summary": "New field 'Smart Licensing' added in section 3"
    # }

    is_reference: Mapped[bool] = mapped_column(Boolean, default=False)
    # If true, this is the canonical reference output for this platform/version/model/command

    source_description: Mapped[str | None] = mapped_column(String(256), nullable=True)
    field_annotations: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    platform: Mapped["Platform"] = relationship()
    device_model: Mapped["DeviceModel"] = relationship()
    software_version_rel: Mapped["SoftwareVersion"] = relationship()
    parent_version: Mapped["CommandOutputLibrary"] = relationship(remote_side="CommandOutputLibrary.id")


class ParserTemplate(Base, UUIDMixin, TimestampMixin):
    """Tracks known parser templates and their version compatibility."""

    __tablename__ = "parser_templates"
    __table_args__ = (
        UniqueConstraint("parser_type", "platform_name", "command", name="uq_parser_template"),
    )

    parser_type: Mapped[str] = mapped_column(String(20))  # textfsm, genie, ttp
    platform_name: Mapped[str] = mapped_column(String(64))  # cisco_ios, arista_eos
    command: Mapped[str] = mapped_column(String(256))
    template_name: Mapped[str] = mapped_column(String(256))  # e.g., "cisco_ios_show_version.textfsm"
    expected_fields: Mapped[list] = mapped_column(JSONB, default=list)
    # e.g., ["hostname", "version", "uptime", "serial", "hardware"]

    # Version compatibility tracking
    validated_versions: Mapped[list] = mapped_column(JSONB, default=list)
    # e.g., ["15.4.23", "16.09.08", "17.06.05"]

    incompatible_versions: Mapped[list] = mapped_column(JSONB, default=list)
    # e.g., ["12.2.55"]

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


from snep.models.device import DeviceModel  # noqa: E402, F401
from snep.models.platform import Platform  # noqa: E402, F401
from snep.models.software_version import SoftwareVersion  # noqa: E402, F401
