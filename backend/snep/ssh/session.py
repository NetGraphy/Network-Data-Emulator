"""SSH session handler — manages a single interactive CLI session."""

import asyncio
import logging

import asyncssh

from snep.ssh.parser import classify_command, get_prompt_char

logger = logging.getLogger(__name__)


class CLISession(asyncssh.SSHServerProcess):
    """Handles an interactive SSH session for an emulated device."""

    def __init__(self, device_info: dict, db_session_factory):
        self._device_info = device_info
        self._db_session_factory = db_session_factory
        self._mode = "user_exec"
        self._terminal_length = 24
        self._terminal_width = 80
        self._hostname = device_info["hostname"]
        self._platform_name = device_info.get("platform_name", "cisco_ios")
        self._enable_password = device_info.get("enable_password")
        self._device_id = device_info["device_id"]

        if device_info.get("privilege_level", 1) >= 15:
            self._mode = "privileged_exec"

    def _prompt(self) -> str:
        return f"{self._hostname}{get_prompt_char(self._mode)}"

    async def handle_session(self, process: asyncssh.SSHServerProcess) -> None:
        """Main session loop — read commands, dispatch, return output."""
        try:
            process.stdout.write(f"\n{self._prompt()}")

            async for line in process.stdin:
                line = line.rstrip("\n\r")
                result = classify_command(line, self._mode)

                if result["type"] == "empty":
                    process.stdout.write(f"{self._prompt()}")
                    continue

                if result["type"] == "mode_transition":
                    await self._handle_mode_transition(process, result)
                elif result["type"] == "session_control":
                    self._handle_session_control(result)
                elif result["type"] == "show":
                    await self._handle_show(process, result)
                elif result["type"] == "config":
                    # Accept config commands silently in MVP
                    pass
                elif result["type"] == "unknown":
                    self._write_error(process, line)

                process.stdout.write(f"{self._prompt()}")

        except (asyncssh.BreakReceived, asyncssh.TerminalSizeChanged):
            pass
        except asyncssh.ConnectionLost:
            logger.debug(f"Connection lost for {self._hostname}")
        finally:
            process.exit(0)

    async def _handle_mode_transition(self, process, result):
        target = result["target_mode"]

        if target == "privileged_exec" and self._mode == "user_exec":
            # Enable — may require password
            if self._enable_password:
                process.stdout.write("Password: ")
                try:
                    password = await asyncio.wait_for(process.stdin.readline(), timeout=30)
                    password = password.strip()
                    if password != self._enable_password:
                        process.stdout.write("% Access denied\n\n")
                        return
                except asyncio.TimeoutError:
                    process.stdout.write("\n% Timeout\n\n")
                    return

        if target == "user_exec" and self._mode == "user_exec":
            # Exit from user exec = disconnect
            process.stdout.write("\n")
            process.exit(0)
            return

        self._mode = target

    def _handle_session_control(self, result):
        if result["command"] == "set_terminal_length":
            try:
                self._terminal_length = int(result["args"])
            except (ValueError, TypeError):
                pass
        elif result["command"] == "set_terminal_width":
            try:
                self._terminal_width = int(result["args"])
            except (ValueError, TypeError):
                pass

    async def _handle_show(self, process, result):
        """Execute a show command via the rendering engine."""
        from snep.services.rendering import render_command
        from snep.services.state import get_device_full

        async with self._db_session_factory() as session:
            device = await get_device_full(session, self._device_id)
            if not device:
                process.stdout.write("% Device state unavailable\n\n")
                return

            rendered = await render_command(session, device, result["command"])
            output = rendered["output"]

            # Apply paging if terminal length > 0
            if self._terminal_length > 0:
                lines = output.split("\n")
                page_size = self._terminal_length - 1
                for i in range(0, len(lines), page_size):
                    chunk = "\n".join(lines[i:i + page_size])
                    process.stdout.write(chunk + "\n")
                    if i + page_size < len(lines):
                        process.stdout.write(" --More-- ")
                        try:
                            key = await asyncio.wait_for(process.stdin.read(1), timeout=300)
                            process.stdout.write("\r          \r")  # clear --More--
                            if key == "q":
                                break
                        except asyncio.TimeoutError:
                            break
            else:
                process.stdout.write(output + "\n")

    def _write_error(self, process, command: str):
        process.stdout.write(f"\n% Invalid input detected at '^' marker.\n\n")
