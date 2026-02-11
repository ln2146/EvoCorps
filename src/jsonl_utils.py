from __future__ import annotations

import json
import os
from typing import Iterable, Set


def strip_fields_from_jsonl_file(path: str, fields: Iterable[str], *, encoding: str = "utf-8") -> None:
    """
    Remove the given top-level keys from every JSON object line in a JSONL file.

    Writes in-place via a temp file + atomic replace. Fails fast on invalid JSON.
    """
    fields_set: Set[str] = set(fields)
    if not fields_set:
        return

    tmp_path = f"{path}.tmp"
    try:
        with open(path, "r", encoding=encoding) as fin, open(tmp_path, "w", encoding=encoding, newline="\n") as fout:
            for line_no, raw in enumerate(fin, start=1):
                if not raw.strip():
                    fout.write(raw)
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON at {path}:{line_no}: {e.msg}") from e
                if not isinstance(obj, dict):
                    raise ValueError(f"Expected JSON object at {path}:{line_no}, got {type(obj).__name__}")
                for f in fields_set:
                    obj.pop(f, None)
                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")

        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

