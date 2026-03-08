def get_session_tick_number(start_tick: int, absolute_tick: int) -> int:
    """Keep absolute tick numbering so child sessions continue parent's sequence."""
    return absolute_tick
