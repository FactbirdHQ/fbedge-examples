from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

from botocore.exceptions import ClientError

from factbird_byom._internal.boto import make_client
from factbird_byom.exceptions import wrap_s3_error

if TYPE_CHECKING:
    from boto3 import Session
    from mypy_boto3_s3 import S3Client

    from factbird_byom.config import ClientConfig


@dataclass(frozen=True, slots=True)
class DeployResult:
    bucket: str
    key: str
    etag: str
    size: int
    uploaded_at: int  # UTC epoch seconds


class ModelDeployment:
    """Deploys a compiled model artifact to the Factbird BYOM bucket.

    Dropping an object into the bucket is the public contract: the Factbird
    backend reacts to the S3 event and creates the IoT deployment job. The SDK
    does not call IoT APIs.
    """

    def __init__(self, session: Session, config: ClientConfig) -> None:
        self._session = session
        self._config = config
        self._s3: S3Client = make_client(session, "s3", config)

    def deploy(
        self,
        model_path: str | Path | BinaryIO,
        *,
        device_id: str,
        model_name: str | None = None,
    ) -> DeployResult:
        if not device_id:
            raise ValueError("device_id is required")

        uploaded_at = int(time.time())

        if isinstance(model_path, (str, Path)):
            path = Path(model_path)
            if not path.is_file():
                raise FileNotFoundError(f"Model file not found: {path}")
            name = model_name or path.name
            size = path.stat().st_size
            key = f"{device_id}/{uploaded_at}/{name}"
            with path.open("rb") as body:
                etag = self._put(key, body, size)
        else:
            if not model_name:
                raise ValueError(
                    "model_name is required when model_path is a file-like object",
                )
            size = _stream_size(model_path)
            key = f"{device_id}/{uploaded_at}/{model_name}"
            etag = self._put(key, model_path, size)

        return DeployResult(
            bucket=self._config.bucket,
            key=key,
            etag=etag,
            size=size,
            uploaded_at=uploaded_at,
        )

    def _put(self, key: str, body: BinaryIO, size: int) -> str:
        try:
            response = self._s3.put_object(
                Bucket=self._config.bucket,
                Key=key,
                Body=body,
                ContentLength=size,
                ContentType="application/octet-stream",
            )
        except ClientError as err:
            raise wrap_s3_error(err, bucket=self._config.bucket, key=key) from err
        return str(response.get("ETag", "")).strip('"')


def _stream_size(stream: BinaryIO) -> int:
    """Measure a seekable binary stream without reading it into memory."""
    if not stream.seekable():
        raise TypeError(
            "model_path file-like object must be seekable "
            "(wrap unseekable streams in io.BytesIO first)",
        )
    start = stream.tell()
    stream.seek(0, 2)  # SEEK_END
    end = stream.tell()
    stream.seek(start)
    return end - start


__all__ = ["DeployResult", "ModelDeployment"]
