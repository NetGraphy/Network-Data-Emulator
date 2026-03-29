"""Application configuration via environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings


class NetworkingSettings(BaseSettings):
    mode: str = Field("auto", alias="SNEP_NETWORK_MODE")
    bind_address: str = Field("0.0.0.0", alias="SNEP_BIND_ADDRESS")
    loopback_range: str = Field("127.0.0.0/8", alias="SNEP_LOOPBACK_RANGE")
    ssh_base_port: int = Field(10000, alias="SNEP_SSH_BASE_PORT")
    snmp_base_port: int = Field(20000, alias="SNEP_SNMP_BASE_PORT")
    prefer_standard_ports: bool = Field(True, alias="SNEP_PREFER_STANDARD_PORTS")


class Settings(BaseSettings):
    # Database
    database_url: str = Field(
        "postgresql+asyncpg://snep:snep@postgres:5432/snep",
        alias="SNEP_DATABASE_URL",
    )

    # API
    api_host: str = Field("0.0.0.0", alias="SNEP_API_HOST")
    api_port: int = Field(8000, alias="SNEP_API_PORT")
    secret_key: str = Field("change-me-in-production", alias="SNEP_SECRET_KEY")
    debug: bool = Field(False, alias="SNEP_DEBUG")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        alias="SNEP_CORS_ORIGINS",
    )

    # Networking
    networking: NetworkingSettings = NetworkingSettings()

    # SSH
    ssh_host_key_path: str = Field("/app/data/host_key", alias="SNEP_SSH_HOST_KEY_PATH")

    # Import: NetBox
    netbox_url: str = Field("", alias="SNEP_NETBOX_URL")
    netbox_token: str = Field("", alias="SNEP_NETBOX_TOKEN")

    # Import: Nautobot
    nautobot_url: str = Field("", alias="SNEP_NAUTOBOT_URL")
    nautobot_token: str = Field("", alias="SNEP_NAUTOBOT_TOKEN")

    # Import: NetGraphy
    netgraphy_neo4j_uri: str = Field("bolt://localhost:7687", alias="SNEP_NETGRAPHY_NEO4J_URI")
    netgraphy_neo4j_user: str = Field("neo4j", alias="SNEP_NETGRAPHY_NEO4J_USER")
    netgraphy_neo4j_password: str = Field("netgraphy", alias="SNEP_NETGRAPHY_NEO4J_PASSWORD")

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
