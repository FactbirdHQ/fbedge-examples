from __future__ import annotations

import boto3
import pytest
from botocore.stub import Stubber

from factbird_byom import (
    AuthError,
    ClientConfig,
    FactbirdByomClient,
    PlaybackMode,
    StreamNotFoundError,
    ThrottledError,
)

REGION = "eu-west-1"
STREAM = "edge-01"
DATA_ENDPOINT = "https://kvs-archived-media.eu-west-1.amazonaws.com"
HLS_URL = "https://example.com/hls/session?token=abc"
DASH_URL = "https://example.com/dash/session?token=xyz"


def _client() -> FactbirdByomClient:
    return FactbirdByomClient(
        session=boto3.Session(region_name=REGION),
        config=ClientConfig(region=REGION, account_id="123456789012"),
    )


def _stub_endpoint(kvs: object, api_name: str) -> None:
    """Resolve the data endpoint via a stubbed kinesisvideo client.

    After this runs the archived-media client on `kvs` is live and can be stubbed.
    """
    stub = Stubber(kvs._kv)  # type: ignore[attr-defined]
    stub.add_response(
        "get_data_endpoint",
        {"DataEndpoint": DATA_ENDPOINT},
        {"StreamName": STREAM, "APIName": api_name},
    )
    stub.activate()
    try:
        kvs._archived_media_client(api_name)  # type: ignore[attr-defined]
    finally:
        stub.deactivate()


def test_hls_url_resolves_endpoint_and_returns_signed_url() -> None:
    client = _client()
    with client.streams.open(STREAM) as kvs:
        _stub_endpoint(kvs, "GET_HLS_STREAMING_SESSION_URL")
        with Stubber(kvs._archived) as arch:
            arch.add_response(
                "get_hls_streaming_session_url",
                {"HLSStreamingSessionURL": HLS_URL},
                {"StreamName": STREAM, "PlaybackMode": "LIVE", "Expires": 300},
            )
            url = kvs.hls_url(expires_in=300)

    assert url == HLS_URL


def test_dash_url_uses_archived_media() -> None:
    client = _client()
    with client.streams.open(STREAM) as kvs:
        _stub_endpoint(kvs, "GET_DASH_STREAMING_SESSION_URL")
        with Stubber(kvs._archived) as arch:
            arch.add_response(
                "get_dash_streaming_session_url",
                {"DASHStreamingSessionURL": DASH_URL},
                {"StreamName": STREAM, "PlaybackMode": "LIVE", "Expires": 600},
            )
            url = kvs.dash_url(expires_in=600, playback_mode=PlaybackMode.LIVE)

    assert url == DASH_URL


def test_stream_not_found_raises_typed_error() -> None:
    client = _client()
    with client.streams.open(STREAM) as kvs, Stubber(kvs._kv) as kv_stub:
        kv_stub.add_client_error(
            "get_data_endpoint",
            service_error_code="ResourceNotFoundException",
            service_message="stream missing",
            expected_params={
                "StreamName": STREAM,
                "APIName": "GET_HLS_STREAMING_SESSION_URL",
            },
        )
        with pytest.raises(StreamNotFoundError):
            kvs.hls_url()


def test_throttled_on_endpoint_raises_throttled_error() -> None:
    client = _client()
    with client.streams.open(STREAM) as kvs, Stubber(kvs._kv) as kv_stub:
        kv_stub.add_client_error(
            "get_data_endpoint",
            service_error_code="ClientLimitExceededException",
            service_message="slow down",
            expected_params={
                "StreamName": STREAM,
                "APIName": "GET_HLS_STREAMING_SESSION_URL",
            },
        )
        with pytest.raises(ThrottledError):
            kvs.hls_url()


def test_access_denied_on_endpoint_raises_auth_error() -> None:
    client = _client()
    with client.streams.open(STREAM) as kvs, Stubber(kvs._kv) as kv_stub:
        kv_stub.add_client_error(
            "get_data_endpoint",
            service_error_code="AccessDeniedException",
            service_message="denied",
            expected_params={
                "StreamName": STREAM,
                "APIName": "GET_HLS_STREAMING_SESSION_URL",
            },
        )
        with pytest.raises(AuthError) as excinfo:
            kvs.hls_url()
    assert "byom-uploader" in str(excinfo.value)


def test_expires_is_clamped_to_min() -> None:
    client = _client()
    with client.streams.open(STREAM) as kvs:
        _stub_endpoint(kvs, "GET_HLS_STREAMING_SESSION_URL")
        with Stubber(kvs._archived) as arch:
            arch.add_response(
                "get_hls_streaming_session_url",
                {"HLSStreamingSessionURL": HLS_URL},
                {"StreamName": STREAM, "PlaybackMode": "LIVE", "Expires": 300},
            )
            kvs.hls_url(expires_in=10)


def test_expires_is_clamped_to_max() -> None:
    client = _client()
    with client.streams.open(STREAM) as kvs:
        _stub_endpoint(kvs, "GET_HLS_STREAMING_SESSION_URL")
        with Stubber(kvs._archived) as arch:
            arch.add_response(
                "get_hls_streaming_session_url",
                {"HLSStreamingSessionURL": HLS_URL},
                {"StreamName": STREAM, "PlaybackMode": "LIVE", "Expires": 43200},
            )
            kvs.hls_url(expires_in=999999)


def test_stream_id_required() -> None:
    with pytest.raises(ValueError):
        _client().streams.open("")


def test_context_manager_closes_clients() -> None:
    client = _client()
    kvs = client.streams.open(STREAM)
    with kvs:
        pass
    assert kvs._closed is True
