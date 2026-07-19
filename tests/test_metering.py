from app.metering import update_cycle_meter


def test_first_read_establishes_baseline():
    result = update_cycle_meter(None, 0, 100)
    assert result.delta == 0
    assert result.new_cycle_used == 0
    assert result.new_last_raw == 100


def test_positive_delta_accumulates():
    result = update_cycle_meter(100, 50, 140)
    assert result.delta == 40
    assert result.new_cycle_used == 90
    assert result.reset_detected is False


def test_remote_reset_preserves_ratio_cycle():
    result = update_cycle_meter(1000, 500, 25)
    assert result.delta == 25
    assert result.new_cycle_used == 525
    assert result.reset_detected is True
