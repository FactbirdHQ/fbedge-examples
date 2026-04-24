from __future__ import annotations

from enum import StrEnum
from types import TracebackType
from typing import TYPE_CHECKING, Literal

from botocore.exceptions import ClientError

from factbird_byom._internal.boto import make_client
from factbird_byom.exceptions import wrap_kvs_error

if TYPE_CHECKING:
    from boto3 import Session
    from mypy_boto3_kinesis_video_archived_media import KinesisVideoArchivedMediaClient
    from mypy_boto3_kinesisvideo import KinesisVideoClient

    from factbird_byom.config import ClientConfig

# AWS GetHLSStreamingSessionURL / GetDASHStreamingSessionURL accept Expires
# between 300 (5 min) and 43200 (12 h). Default is 300.
_MIN_EXPIRES_IN = 300
_MAX_EXPIRES_IN = 43200

_StreamingApi = Literal[
    "GET_HLS_STREAMING_SESSION_URL",
    "GET_DASH_STREAMING_SESSION_URL",
]


class PlaybackMode(StrEnum):
    LIVE = "LIVE"
    LIVE_REPLAY = "LIVE_REPLAY"
    ON_DEMAND = "ON_DEMAND"


class StreamService:
    """Factory for KvsStream consumers, scoped to a session + config."""

    def __init__(self, session: Session, config: ClientConfig) -> None:
        self._session = session
        self._config = config

    def open(self, stream_id: str) -> KvsStream:
        if not stream_id:
            raise ValueError("stream_id is required")
        return KvsStream(self._session, self._config, stream_id)


class KvsStream:
    """One KVS stream, exposed as signed HLS and DASH URLs.

    Use as a context manager; the underlying boto clients are closed on exit.
    v0.1 does not offer raw-bytes or decoded-frame access — open the URL in
    any HLS/DASH-capable player (Safari, VLC, ffplay, QuickTime).
    """

    def __init__(self, session: Session, config: ClientConfig, stream_id: str) -> None:
        self._session = session
        self._config = config
        self._stream_id = stream_id
        self._kv: KinesisVideoClient = make_client(session, "kinesisvideo", config)
        # Archived-media client is lazy; it needs the stream's data endpoint.
        self._archived: KinesisVideoArchivedMediaClient | None = None
        self._closed = False

    @property
    def stream_id(self) -> str:
        return self._stream_id

    def hls_url(
        self,
        *,
        expires_in: int = 300,
        playback_mode: PlaybackMode = PlaybackMode.LIVE,
    ) -> str:
        client = self._archived_media_client("GET_HLS_STREAMING_SESSION_URL")
        try:
            response = client.get_hls_streaming_session_url(
                StreamName=self._stream_id,
                PlaybackMode=playback_mode.value,
                Expires=_bounded_expires(expires_in),
            )
        except ClientError as err:
            raise wrap_kvs_error(err, stream_id=self._stream_id) from err
        return str(response["HLSStreamingSessionURL"])

    def dash_url(
        self,
        *,
        expires_in: int = 300,
        playback_mode: PlaybackMode = PlaybackMode.LIVE,
    ) -> str:
        client = self._archived_media_client("GET_DASH_STREAMING_SESSION_URL")
        try:
            response = client.get_dash_streaming_session_url(
                StreamName=self._stream_id,
                PlaybackMode=playback_mode.value,
                Expires=_bounded_expires(expires_in),
            )
        except ClientError as err:
            raise wrap_kvs_error(err, stream_id=self._stream_id) from err
        return str(response["DASHStreamingSessionURL"])

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for client in (self._archived, self._kv):
            if client is None:
                continue
            closer = getattr(client, "close", None)
            if callable(closer):
                closer()

    def __enter__(self) -> KvsStream:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _archived_media_client(self, api_name: _StreamingApi) -> KinesisVideoArchivedMediaClient:
        if self._archived is not None:
            return self._archived
        try:
            endpoint = self._kv.get_data_endpoint(
                StreamName=self._stream_id,
                APIName=api_name,
            )["DataEndpoint"]
        except ClientError as err:
            raise wrap_kvs_error(err, stream_id=self._stream_id) from err
        self._archived = make_client(
            self._session,
            "kinesis-video-archived-media",
            self._config,
            endpoint_url=endpoint,
        )
        return self._archived


def _bounded_expires(expires_in: int) -> int:
    if expires_in < _MIN_EXPIRES_IN:
        return _MIN_EXPIRES_IN
    if expires_in > _MAX_EXPIRES_IN:
        return _MAX_EXPIRES_IN
    return expires_in


__all__ = ["KvsStream", "PlaybackMode", "StreamService"]
