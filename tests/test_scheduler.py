import pytest
from pydantic import ValidationError

from app.schemas import PanelConfigInput
from app.sync import SyncService


def config(interval: int) -> PanelConfigInput:
    return PanelConfigInput(
        panel_url="https://panel.example.com/base",
        api_token="token",
        subscription_template="https://subscription.example.com/sub",
        poll_interval_seconds=interval,
    )


def test_poll_interval_accepts_ten_seconds():
    assert config(10).poll_interval_seconds == 10


def test_poll_interval_rejects_less_than_ten_seconds():
    with pytest.raises(ValidationError):
        config(9)


def test_scheduler_deadline_does_not_accumulate_runtime_drift():
    assert SyncService._advance_deadline(100.0, 10, 106.0) == 110.0
    assert SyncService._advance_deadline(100.0, 10, 126.0) == 130.0
