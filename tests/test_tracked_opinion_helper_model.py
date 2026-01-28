import pathlib


def test_tracked_opinion_helper_does_not_use_sim_engine_directly() -> None:
    content = pathlib.Path("src/tracked_opinion_helper.py").read_text(encoding="utf-8")
    assert "model=sim.engine" not in content
