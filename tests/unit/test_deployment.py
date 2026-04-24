from __future__ import annotations

import io
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

from factbird_byom import (
    AuthError,
    BucketNotFoundError,
    ClientConfig,
    FactbirdByomClient,
    ModelUploadError,
    ThrottledError,
)

REGION = "eu-west-1"
ACCOUNT_ID = "123456789012"
BUCKET = f"{ACCOUNT_ID}-{REGION}-byom"


def _client(account_id: str = ACCOUNT_ID) -> FactbirdByomClient:
    return FactbirdByomClient(
        session=boto3.Session(region_name=REGION),
        config=ClientConfig(region=REGION, account_id=account_id),
    )


@mock_aws
def test_deploy_puts_object_at_device_epoch_modelname_key(tmp_path: Path) -> None:
    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(
        Bucket=BUCKET,
        CreateBucketConfiguration={"LocationConstraint": REGION},
    )

    model = tmp_path / "model.hef"
    model.write_bytes(b"hailo-compiled-bytes")

    result = _client().deployment.deploy(model, device_id="edge-01")

    assert result.bucket == BUCKET
    assert result.key.startswith("edge-01/")
    assert result.key.endswith("/model.hef")
    assert result.size == len(b"hailo-compiled-bytes")
    assert result.etag
    assert result.uploaded_at > 0

    # Key structure: edge-01/<epoch>/model.hef
    parts = result.key.split("/")
    assert parts[0] == "edge-01"
    assert parts[1].isdigit()
    assert parts[2] == "model.hef"

    body = s3.get_object(Bucket=BUCKET, Key=result.key)["Body"].read()
    assert body == b"hailo-compiled-bytes"


@mock_aws
def test_deploy_accepts_model_name_override(tmp_path: Path) -> None:
    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})

    model = tmp_path / "model.hef"
    model.write_bytes(b"x")

    result = _client().deployment.deploy(
        model,
        device_id="edge-42",
        model_name="custom.hef",
    )
    assert result.key.endswith("/custom.hef")
    assert result.key.startswith("edge-42/")


@mock_aws
def test_deploy_accepts_bytesio(tmp_path: Path) -> None:
    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})

    buf = io.BytesIO(b"inline-bytes")

    result = _client().deployment.deploy(
        buf,
        device_id="edge-99",
        model_name="buf.hef",
    )
    assert result.size == len(b"inline-bytes")
    assert result.key.endswith("/buf.hef")


@mock_aws
def test_deploy_missing_bucket_raises_bucket_not_found(tmp_path: Path) -> None:
    # Bucket deliberately not created — the derived name won't exist in moto.
    model = tmp_path / "model.hef"
    model.write_bytes(b"x")

    with pytest.raises(BucketNotFoundError) as excinfo:
        _client(account_id="999999999999").deployment.deploy(model, device_id="edge-01")

    # BucketNotFoundError is still a ModelUploadError for broad catchers.
    assert isinstance(excinfo.value, ModelUploadError)
    assert "account_id" in str(excinfo.value)


@mock_aws
def test_deploy_throttled_raises_throttled_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from botocore.exceptions import ClientError

    model = tmp_path / "model.hef"
    model.write_bytes(b"x")

    client = _client()

    def throttle(**kwargs: object) -> None:
        raise ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "slow down"}},
            "PutObject",
        )

    monkeypatch.setattr(client.deployment._s3, "put_object", throttle)

    with pytest.raises(ThrottledError) as excinfo:
        client.deployment.deploy(model, device_id="edge-01")
    assert "backoff" in str(excinfo.value).lower()


@mock_aws
def test_deploy_access_denied_raises_auth_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from botocore.exceptions import ClientError

    model = tmp_path / "model.hef"
    model.write_bytes(b"x")

    client = _client()

    def fail(**kwargs: object) -> None:
        raise ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "no"}},
            "PutObject",
        )

    monkeypatch.setattr(client.deployment._s3, "put_object", fail)

    with pytest.raises(AuthError) as excinfo:
        client.deployment.deploy(model, device_id="edge-01")
    assert "byom-uploader" in str(excinfo.value)


def test_deploy_requires_device_id(tmp_path: Path) -> None:
    model = tmp_path / "model.hef"
    model.write_bytes(b"x")
    with pytest.raises(ValueError):
        _client().deployment.deploy(model, device_id="")


def test_deploy_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _client().deployment.deploy(tmp_path / "nope.hef", device_id="edge-01")


def test_deploy_bytesio_requires_model_name() -> None:
    buf = io.BytesIO(b"x")
    with pytest.raises(ValueError):
        _client().deployment.deploy(buf, device_id="edge-01")
