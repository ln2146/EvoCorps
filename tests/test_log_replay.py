import os
import tempfile

import pytest

import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


def test_resolve_log_path_allows_normal_filenames():
    from log_replay import resolve_log_path

    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "workflow_20260130.log")
        with open(p, "w", encoding="utf-8") as f:
            f.write("hello\n")

        resolved = resolve_log_path(d, "workflow_20260130.log")
        assert os.path.abspath(resolved) == os.path.abspath(p)


@pytest.mark.parametrize(
    "bad",
    [
        "../secrets.txt",
        "..\\secrets.txt",
        "/etc/passwd",
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
    ],
)
def test_resolve_log_path_blocks_path_traversal(bad):
    from log_replay import resolve_log_path

    with tempfile.TemporaryDirectory() as d:
        with pytest.raises(ValueError):
            resolve_log_path(d, bad)


def test_iter_log_lines_yields_file_lines_in_order():
    from log_replay import iter_log_lines

    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "a.log")
        with open(p, "w", encoding="utf-8") as f:
            f.write("l1\nl2\nl3\n")

        assert list(iter_log_lines(p)) == ["l1\n", "l2\n", "l3\n"]
