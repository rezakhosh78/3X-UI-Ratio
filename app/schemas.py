from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class PanelConfigInput(BaseModel):
    panel_url: str = Field(min_length=8, max_length=1024)
    api_token: str = Field(default="", max_length=4096)
    subscription_template: str = Field(min_length=8, max_length=2048)
    verify_tls: bool = True
    auto_disable: bool = True
    poll_interval_seconds: int = Field(default=60, ge=10, le=86400)
    request_timeout_seconds: int = Field(default=15, ge=5, le=120)

    @field_validator("panel_url")
    @classmethod
    def valid_panel_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("panel_url must start with http:// or https://")
        return value

    @field_validator("subscription_template")
    @classmethod
    def valid_subscription_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("subscription URL must start with http:// or https://")
        return value


class QuotaInput(BaseModel):
    quota_gb: float = Field(ge=0, le=1_000_000)
    enforcement_enabled: bool = True
    reset_cycle: bool = True


class BulkQuotaInput(BaseModel):
    user_ids: list[int] = Field(min_length=1, max_length=10_000)
    quota_gb: float = Field(ge=0, le=1_000_000)
    enforcement_enabled: bool = True
    reset_cycle: bool = True

    @field_validator("user_ids")
    @classmethod
    def unique_positive_user_ids(cls, value: list[int]) -> list[int]:
        unique: list[int] = []
        seen: set[int] = set()
        for user_id in value:
            if user_id <= 0:
                raise ValueError("user_ids must contain positive integers")
            if user_id not in seen:
                seen.add(user_id)
                unique.append(user_id)
        if not unique:
            raise ValueError("At least one user must be selected")
        return unique


class BulkEnforcementInput(BaseModel):
    user_ids: list[int] = Field(min_length=1, max_length=10_000)

    @field_validator("user_ids")
    @classmethod
    def unique_positive_user_ids(cls, value: list[int]) -> list[int]:
        unique: list[int] = []
        seen: set[int] = set()
        for user_id in value:
            if user_id <= 0:
                raise ValueError("user_ids must contain positive integers")
            if user_id not in seen:
                seen.add(user_id)
                unique.append(user_id)
        if not unique:
            raise ValueError("At least one user must be selected")
        return unique


class EnforcementInput(BaseModel):
    enabled: bool


class EngineInput(BaseModel):
    enabled: bool
