from __future__ import annotations

from typing import TYPE_CHECKING, Any

from botocore.config import Config

if TYPE_CHECKING:
    from boto3 import Session

    from factbird_byom.config import ClientConfig


def botocore_config(cfg: ClientConfig) -> Config:
    return Config(
        region_name=cfg.region,
        user_agent_extra="factbird-byom/0.1.0",
        retries={"mode": "standard"},
    )


def make_client(session: Session, service: str, cfg: ClientConfig, **kwargs: Any) -> Any:
    # boto3-stubs expresses `client()` as dozens of per-service Literal overloads,
    # so a generic str service name doesn't match any of them. We intentionally
    # keep this factory generic; callers get the right shape via service-specific
    # accessors on the returned object.
    return session.client(service, config=botocore_config(cfg), **kwargs)  # type: ignore[call-overload]
