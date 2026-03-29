"""Enum types for the data model."""

import enum


class AdminState(str, enum.Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class InterfaceAdminStatus(str, enum.Enum):
    UP = "up"
    DOWN = "down"


class InterfaceOperStatus(str, enum.Enum):
    UP = "up"
    DOWN = "down"
    DORMANT = "dormant"
    NOT_PRESENT = "notPresent"
    LOWER_LAYER_DOWN = "lowerLayerDown"


class InterfaceType(str, enum.Enum):
    ETHERNET = "ethernet"
    LOOPBACK = "loopback"
    VLAN = "vlan"
    PORT_CHANNEL = "port_channel"
    TUNNEL = "tunnel"
    MANAGEMENT = "management"


class LinkType(str, enum.Enum):
    PHYSICAL = "physical"
    LOGICAL = "logical"
    VIRTUAL = "virtual"


class DiscoveryProtocol(str, enum.Enum):
    CDP = "cdp"
    LLDP = "lldp"
    BOTH = "both"
    NONE = "none"


class LinkAdminState(str, enum.Enum):
    UP = "up"
    DOWN = "down"


class CLIMappingMode(str, enum.Enum):
    STATIC = "static"
    MAPPED = "mapped"


class TemplateOutputType(str, enum.Enum):
    TABULAR = "tabular"
    FREEFORM = "freeform"
    STRUCTURED = "structured"


class ScenarioStatus(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class TriggerType(str, enum.Enum):
    IMMEDIATE = "immediate"
    DELAY = "delay"
    MANUAL = "manual"
    CONDITIONAL = "conditional"


class ActionType(str, enum.Enum):
    INTERFACE_STATE_CHANGE = "interface_state_change"
    INTERFACE_ADMIN_CHANGE = "interface_admin_change"
    COUNTER_SET = "counter_set"
    COUNTER_RATE_CHANGE = "counter_rate_change"
    LINK_STATE_CHANGE = "link_state_change"
    DEVICE_STATE_CHANGE = "device_state_change"
    LOG_EVENT = "log_event"
    BULK_UPDATE = "bulk_update"


class ConnectionProtocol(str, enum.Enum):
    SSH = "ssh"
    SNMP = "snmp"


class SNMPAuthProtocol(str, enum.Enum):
    MD5 = "md5"
    SHA = "sha"
    SHA256 = "sha256"
    SHA512 = "sha512"


class SNMPPrivProtocol(str, enum.Enum):
    DES = "des"
    AES128 = "aes128"
    AES256 = "aes256"


class Duplex(str, enum.Enum):
    FULL = "full"
    HALF = "half"
    AUTO = "auto"
