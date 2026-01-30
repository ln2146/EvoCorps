import os
import time

import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from log_tail import find_latest_file, tail_lines


def test_find_latest_file_picks_newest_mtime(tmp_path):
    d = tmp_path / "logs"
    d.mkdir()

    p1 = d / "a.log"
    p2 = d / "b.log"

    p1.write_text("a\n", encoding="utf-8")
    time.sleep(0.01)
    p2.write_text("b\n", encoding="utf-8")

    latest = find_latest_file(str(d), pattern="*.log")
    assert latest == str(p2)


def test_tail_lines_returns_last_n_lines(tmp_path):
    p = tmp_path / "x.log"
    p.write_text("1\n2\n3\n4\n", encoding="utf-8")

    assert tail_lines(str(p), n=2) == ["3", "4"]


def test_tail_lines_handles_small_files(tmp_path):
    p = tmp_path / "x.log"
    p.write_text("only\n", encoding="utf-8")

    assert tail_lines(str(p), n=50) == ["only"]


def test_tail_lines_handles_no_newline_at_end(tmp_path):
    p = tmp_path / "x.log"
    p.write_text("1\n2\n3", encoding="utf-8")

    assert tail_lines(str(p), n=2) == ["2", "3"]
