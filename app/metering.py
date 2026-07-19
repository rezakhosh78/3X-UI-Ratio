from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MeterUpdate:
    new_last_raw: int
    new_cycle_used: int
    delta: int
    reset_detected: bool


def update_cycle_meter(last_raw: int | None, cycle_used: int, current_raw: int) -> MeterUpdate:
    current = max(0, int(current_raw))
    cycle = max(0, int(cycle_used))
    if last_raw is None:
        return MeterUpdate(current, cycle, 0, False)

    previous = max(0, int(last_raw))
    if current >= previous:
        delta = current - previous
        reset_detected = False
    else:
        # The remote 3X-UI counter was reset. Count the new post-reset value,
        # preserving Ratio's independent quota cycle.
        delta = current
        reset_detected = True
    return MeterUpdate(current, cycle + delta, delta, reset_detected)
