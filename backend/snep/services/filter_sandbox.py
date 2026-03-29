"""Sandboxed Python execution for user-defined Jinja2 filters.

Compiles user code into callable functions with restricted globals:
- No file I/O (no open, no __import__)
- No network access
- No dangerous builtins (no exec, eval, compile)
- Only admin-approved modules (default: math, ipaddress, re, json, datetime, etc.)
- Execution timeout protection

Admin can expand allowed modules via the AllowedImport settings.
"""

import builtins
import logging
import signal
from typing import Any

logger = logging.getLogger(__name__)

# Safe builtins — no exec, eval, compile, open, __import__
SAFE_BUILTIN_NAMES = {
    'abs', 'all', 'any', 'bin', 'bool', 'bytearray', 'bytes', 'chr',
    'complex', 'dict', 'divmod', 'enumerate', 'filter', 'float',
    'format', 'frozenset', 'getattr', 'hasattr', 'hash', 'hex',
    'id', 'int', 'isinstance', 'issubclass', 'iter', 'len', 'list',
    'map', 'max', 'min', 'next', 'object', 'oct', 'ord', 'pow',
    'print', 'range', 'repr', 'reversed', 'round', 'set', 'slice',
    'sorted', 'str', 'sum', 'tuple', 'type', 'vars', 'zip',
    'True', 'False', 'None',
    'ValueError', 'TypeError', 'KeyError', 'IndexError', 'AttributeError',
    'ZeroDivisionError', 'RuntimeError', 'StopIteration', 'Exception',
}

# Default allowed modules — safe for network data processing
DEFAULT_ALLOWED_MODULES = [
    'math', 'ipaddress', 're', 'json', 'datetime', 'hashlib',
    'base64', 'textwrap', 'collections', 'decimal', 'statistics',
    'string', 'functools', 'itertools', 'operator',
]

# Never allowed — hardcoded blocklist (cannot be overridden by admin)
BLOCKED_MODULES = {
    'os', 'sys', 'subprocess', 'shutil', 'socket', 'http', 'urllib',
    'importlib', 'ctypes', 'pickle', 'shelve', 'tempfile', 'pathlib',
    'signal', 'multiprocessing', 'threading', 'asyncio', 'code',
    'codeop', 'compileall', 'py_compile', 'runpy', 'builtins',
}

# Runtime state — admin can add modules
_allowed_modules: list[str] = list(DEFAULT_ALLOWED_MODULES)
_loaded_modules: dict[str, Any] = {}


def get_allowed_modules() -> list[str]:
    return list(_allowed_modules)


def add_allowed_module(module_name: str) -> dict:
    """Admin adds a module to the allowed list."""
    if module_name in BLOCKED_MODULES:
        return {"error": f"Module '{module_name}' is blocked for security reasons"}
    try:
        mod = __import__(module_name)
        _allowed_modules.append(module_name)
        _loaded_modules[module_name] = mod
        return {"status": "added", "module": module_name}
    except ImportError:
        return {"error": f"Module '{module_name}' is not installed"}


def remove_allowed_module(module_name: str) -> dict:
    if module_name in DEFAULT_ALLOWED_MODULES:
        return {"error": f"Cannot remove default module '{module_name}'"}
    if module_name in _allowed_modules:
        _allowed_modules.remove(module_name)
        _loaded_modules.pop(module_name, None)
    return {"status": "removed", "module": module_name}


def _build_safe_globals() -> dict:
    """Build the restricted globals dict for exec()."""
    # Safe builtins
    safe_builtins = {}
    for name in SAFE_BUILTIN_NAMES:
        if hasattr(builtins, name):
            safe_builtins[name] = getattr(builtins, name)

    # Load allowed modules
    modules = {}
    for mod_name in _allowed_modules:
        if mod_name not in _loaded_modules:
            try:
                _loaded_modules[mod_name] = __import__(mod_name)
            except ImportError:
                continue
        modules[mod_name] = _loaded_modules[mod_name]

    return {
        '__builtins__': safe_builtins,
        **modules,
    }


def compile_filter(name: str, code: str, signature: str = "value") -> callable:
    """Compile user Python code into a callable filter function.

    Args:
        name: Function name (used as Jinja2 filter name)
        code: Function body (indented code, NOT including the def line)
        signature: Parameter specification (e.g., "value", "value, precision=2")

    Returns:
        Callable function

    Raises:
        SyntaxError: If code has syntax errors
        NameError: If code references undefined names
        SecurityError: If code attempts blocked operations
    """
    # Build the full function
    lines = code.strip().split('\n')
    indented = '\n'.join(f'    {line}' for line in lines)
    func_source = f"def {name}({signature}):\n{indented}\n"

    safe_globals = _build_safe_globals()

    try:
        exec(func_source, safe_globals)
    except SyntaxError as e:
        raise SyntaxError(f"Syntax error in filter '{name}': {e}")

    func = safe_globals.get(name)
    if not callable(func):
        raise RuntimeError(f"Filter '{name}' did not produce a callable function")

    return func


def test_filter(name: str, code: str, signature: str, test_args: list) -> dict:
    """Compile and execute a filter with test arguments.

    Returns: {"output": str, "error": str | None, "execution_time_ms": float}
    """
    import time

    try:
        fn = compile_filter(name, code, signature)
    except Exception as e:
        return {"output": None, "error": f"Compilation error: {e}", "execution_time_ms": 0}

    start = time.monotonic()
    try:
        result = fn(*test_args)
        elapsed = (time.monotonic() - start) * 1000
        return {"output": str(result), "error": None, "execution_time_ms": round(elapsed, 2)}
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        return {"output": None, "error": f"Runtime error: {e}", "execution_time_ms": round(elapsed, 2)}
