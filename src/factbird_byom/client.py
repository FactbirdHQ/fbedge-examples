from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from factbird_byom.deployment import ModelDeployment
from factbird_byom.streams import StreamService

if TYPE_CHECKING:
    from boto3 import Session

    from factbird_byom.config import ClientConfig


class FactbirdByomClient:
    """Top-level SDK entry point.

    Wraps a boto3 Session and a ClientConfig, exposing the two BYOM operations
    as sub-services:

        client.deployment.deploy(...)   # S3 PutObject triggers the server-side IoT job
        client.streams.open(stream_id)  # signed HLS/DASH URL for viewing

    Credentials come from the supplied boto3 Session (env vars, profile, etc.).
    The SDK does not rotate, refresh, or assume roles — the `byom-uploader`
    IAM user's access keys are rotated out-of-band by Factbird (~annually).
    """

    def __init__(self, session: Session, config: ClientConfig) -> None:
        self._session = session
        self._config = config

    @property
    def config(self) -> ClientConfig:
        return self._config

    @cached_property
    def deployment(self) -> ModelDeployment:
        return ModelDeployment(self._session, self._config)

    @cached_property
    def streams(self) -> StreamService:
        return StreamService(self._session, self._config)


__all__ = ["FactbirdByomClient"]
