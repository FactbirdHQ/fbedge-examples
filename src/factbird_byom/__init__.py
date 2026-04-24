"""Factbird BYOM SDK — deploy compiled models and view live edge streams."""

from factbird_byom.client import FactbirdByomClient
from factbird_byom.config import ClientConfig
from factbird_byom.deployment import DeployResult
from factbird_byom.exceptions import (
    AuthError,
    BucketNotFoundError,
    FactbirdByomError,
    ModelUploadError,
    StreamNotFoundError,
    ThrottledError,
)
from factbird_byom.streams import KvsStream, PlaybackMode

__version__ = "0.1.0"

__all__ = [
    "AuthError",
    "BucketNotFoundError",
    "ClientConfig",
    "DeployResult",
    "FactbirdByomClient",
    "FactbirdByomError",
    "KvsStream",
    "ModelUploadError",
    "PlaybackMode",
    "StreamNotFoundError",
    "ThrottledError",
    "__version__",
]
