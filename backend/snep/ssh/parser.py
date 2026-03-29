"""CLI command parser — abbreviation expansion, mode transitions, argument extraction."""

import re

# Mode transition commands
MODE_TRANSITIONS = {
    "enable": "privileged_exec",
    "disable": "user_exec",
    "configure terminal": "global_config",
    "conf t": "global_config",
    "exit": "_parent",  # go to parent mode
    "end": "privileged_exec",
}

# Session-control commands (handled by session, not rendering)
SESSION_COMMANDS = {
    "terminal length": "set_terminal_length",
    "terminal width": "set_terminal_width",
    "term len": "set_terminal_length",
    "term wid": "set_terminal_width",
}


def classify_command(raw: str, current_mode: str) -> dict:
    """Classify a command and determine how to handle it.

    Returns: {
        "type": "show" | "mode_transition" | "session_control" | "config" | "empty" | "unknown",
        "command": <normalized command string>,
        "args": <additional arguments>,
        "target_mode": <for mode transitions>,
    }
    """
    line = raw.strip()

    if not line:
        return {"type": "empty", "command": "", "args": None, "target_mode": None}

    lower = line.lower()

    # Mode transitions
    for cmd, target in MODE_TRANSITIONS.items():
        if lower == cmd or lower.startswith(cmd + " "):
            actual_target = target
            if target == "_parent":
                actual_target = _parent_mode(current_mode)
            return {"type": "mode_transition", "command": cmd, "args": None, "target_mode": actual_target}

    # Session control
    for prefix, action in SESSION_COMMANDS.items():
        if lower.startswith(prefix):
            rest = lower[len(prefix):].strip()
            return {"type": "session_control", "command": action, "args": rest, "target_mode": None}

    # Show commands
    if lower.startswith("sh"):
        return {"type": "show", "command": line, "args": None, "target_mode": None}

    # Config mode commands
    if current_mode in ("global_config", "interface_config", "router_config"):
        return {"type": "config", "command": line, "args": None, "target_mode": None}

    # Unknown
    return {"type": "unknown", "command": line, "args": None, "target_mode": None}


def _parent_mode(current: str) -> str:
    """Get parent mode for 'exit' command."""
    parents = {
        "user_exec": "user_exec",  # exit from user exec disconnects
        "privileged_exec": "user_exec",
        "global_config": "privileged_exec",
        "interface_config": "global_config",
        "router_config": "global_config",
    }
    return parents.get(current, "privileged_exec")


def get_prompt_char(mode: str) -> str:
    """Get the prompt suffix character for a CLI mode."""
    chars = {
        "user_exec": ">",
        "privileged_exec": "#",
        "global_config": "(config)#",
        "interface_config": "(config-if)#",
        "router_config": "(config-router)#",
    }
    return chars.get(mode, "#")
