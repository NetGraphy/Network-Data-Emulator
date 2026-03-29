"""Tests for SSH command parser."""

from snep.ssh.parser import classify_command, get_prompt_char


def test_classify_empty():
    result = classify_command("", "privileged_exec")
    assert result["type"] == "empty"


def test_classify_show_command():
    result = classify_command("show version", "privileged_exec")
    assert result["type"] == "show"
    assert result["command"] == "show version"


def test_classify_abbreviated_show():
    result = classify_command("sh ip int br", "privileged_exec")
    assert result["type"] == "show"


def test_classify_enable():
    result = classify_command("enable", "user_exec")
    assert result["type"] == "mode_transition"
    assert result["target_mode"] == "privileged_exec"


def test_classify_config_terminal():
    result = classify_command("configure terminal", "privileged_exec")
    assert result["type"] == "mode_transition"
    assert result["target_mode"] == "global_config"


def test_classify_exit_from_config():
    result = classify_command("exit", "global_config")
    assert result["type"] == "mode_transition"
    assert result["target_mode"] == "privileged_exec"


def test_classify_end():
    result = classify_command("end", "interface_config")
    assert result["type"] == "mode_transition"
    assert result["target_mode"] == "privileged_exec"


def test_classify_terminal_length():
    result = classify_command("terminal length 0", "privileged_exec")
    assert result["type"] == "session_control"
    assert result["command"] == "set_terminal_length"
    assert result["args"] == "0"


def test_classify_unknown():
    result = classify_command("foobar", "privileged_exec")
    assert result["type"] == "unknown"


def test_classify_config_command():
    result = classify_command("interface GigabitEthernet1/0/1", "global_config")
    assert result["type"] == "config"


def test_prompt_chars():
    assert get_prompt_char("user_exec") == ">"
    assert get_prompt_char("privileged_exec") == "#"
    assert get_prompt_char("global_config") == "(config)#"
