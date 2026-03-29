"""Application configuration via environment variables."""

import json
import os


class NetworkingSettings:
    def __init__(self):
        self.mode = os.environ.get("SNEP_NETWORK_MODE", "auto")
        self.bind_address = os.environ.get("SNEP_BIND_ADDRESS", "0.0.0.0")
        self.loopback_range = os.environ.get("SNEP_LOOPBACK_RANGE", "127.0.0.0/8")
        self.ssh_base_port = int(os.environ.get("SNEP_SSH_BASE_PORT", "10000"))
        self.snmp_base_port = int(os.environ.get("SNEP_SNMP_BASE_PORT", "20000"))
        self.prefer_standard_ports = os.environ.get("SNEP_PREFER_STANDARD_PORTS", "true").lower() == "true"


class Settings:
    def __init__(self):
        self.database_url = os.environ.get("SNEP_DATABASE_URL", "postgresql+asyncpg://snep:snep@postgres:5432/snep")
        self.api_host = os.environ.get("SNEP_API_HOST", "0.0.0.0")
        self.api_port = int(os.environ.get("SNEP_API_PORT", os.environ.get("PORT", "8000")))
        self.secret_key = os.environ.get("SNEP_SECRET_KEY", "change-me-in-production")
        self.debug = os.environ.get("SNEP_DEBUG", "false").lower() == "true"

        cors_raw = os.environ.get("SNEP_CORS_ORIGINS", '["http://localhost:3000","http://localhost:5173"]')
        try:
            self.cors_origins = json.loads(cors_raw)
        except (json.JSONDecodeError, TypeError):
            self.cors_origins = [s.strip() for s in cors_raw.split(",")]

        self.networking = NetworkingSettings()
        self.ssh_host_key_path = os.environ.get("SNEP_SSH_HOST_KEY_PATH", "/app/data/host_key")
        self.netbox_url = os.environ.get("SNEP_NETBOX_URL", "")
        self.netbox_token = os.environ.get("SNEP_NETBOX_TOKEN", "")
        self.nautobot_url = os.environ.get("SNEP_NAUTOBOT_URL", "")
        self.nautobot_token = os.environ.get("SNEP_NAUTOBOT_TOKEN", "")
        self.netgraphy_neo4j_uri = os.environ.get("SNEP_NETGRAPHY_NEO4J_URI", "bolt://localhost:7687")
        self.netgraphy_neo4j_user = os.environ.get("SNEP_NETGRAPHY_NEO4J_USER", "neo4j")
        self.netgraphy_neo4j_password = os.environ.get("SNEP_NETGRAPHY_NEO4J_PASSWORD", "netgraphy")


settings = Settings()
