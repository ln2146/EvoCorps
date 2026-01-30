import glob
import os
from typing import List, Optional


def find_latest_file(directory: str, pattern: str = "*.log") -> Optional[str]:
    """Return the newest file path in `directory` matching `pattern` by mtime."""
    candidates = glob.glob(os.path.join(directory, pattern))
    if not candidates:
        return None
    return max(candidates, key=lambda p: os.path.getmtime(p))


def tail_lines(path: str, n: int = 200, encoding: str = "utf-8") -> List[str]:
    """Return the last `n` text lines (without newlines) from a file."""
    if n <= 0:
        return []

    block_size = 8192
    data = b""

    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        end = f.tell()
        pos = end

        # Read blocks from end until we have enough newlines or reach beginning.
        while pos > 0 and data.count(b"\n") <= n:
            read_size = block_size if pos >= block_size else pos
            pos -= read_size
            f.seek(pos, os.SEEK_SET)
            chunk = f.read(read_size)
            data = chunk + data

    text = data.decode(encoding, errors="replace")
    lines = text.splitlines()
    return lines[-n:]

