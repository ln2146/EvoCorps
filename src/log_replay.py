import os
import re
import time
import datetime
from typing import Iterable, Iterator


def resolve_log_path(base_dir: str, filename: str) -> str:
    """
    Resolve a user-provided log filename to an absolute path under base_dir.

    Security: blocks absolute paths and path traversal attempts.
    """
    name = (filename or "").strip()
    if not name:
        raise ValueError("empty filename")

    # Disallow absolute paths (both POSIX and Windows).
    if os.path.isabs(name):
        raise ValueError("absolute paths are not allowed")
    if os.path.splitdrive(name)[0]:
        raise ValueError("drive paths are not allowed")

    base_abs = os.path.abspath(base_dir)
    joined = os.path.abspath(os.path.join(base_abs, name))

    # Ensure resolved path stays within base_dir.
    try:
        common = os.path.commonpath([base_abs, joined])
    except ValueError:
        # Different drives, etc.
        raise ValueError("invalid path") from None
    if common != base_abs:
        raise ValueError("path traversal detected")

    return joined


def iter_log_lines(path: str, encoding: str = "utf-8") -> Iterator[str]:
    """Yield raw text lines (including trailing newline if present) from a log file."""
    with open(path, "r", encoding=encoding, errors="replace") as f:
        for line in f:
            yield line


def replay_log_lines(
    lines: Iterable[str],
    *,
    delay_sec: float,
):
    """
    Replay lines with a fixed delay between each yield.

    Note: does not sleep before the first line.
    """
    import time

    delay = max(0.0, float(delay_sec))
    first = True
    for line in lines:
        if not first and delay > 0:
            time.sleep(delay)
        first = False
        yield line


_TS_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<hms>\d{2}:\d{2}:\d{2}),(?P<ms>\d{3})\b")


def parse_log_timestamp_ms(line: str) -> int | None:
    """
    Parse a standard workflow log prefix timestamp into epoch milliseconds.

    Expected prefix format:
      YYYY-MM-DD HH:MM:SS,mmm - LEVEL - ...

    Returns None if the line doesn't start with a timestamp.
    """
    if not line:
        return None

    m = _TS_RE.match(line)
    if not m:
        return None

    try:
        dt = datetime.datetime.strptime(f"{m.group('date')} {m.group('hms')}", "%Y-%m-%d %H:%M:%S")
        # Treat as local time (the log timestamps are emitted in local time).
        sec = time.mktime(dt.timetuple())
        return int(sec * 1000) + int(m.group("ms"))
    except Exception:
        return None
