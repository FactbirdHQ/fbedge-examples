from __future__ import annotations

from botocore.exceptions import ClientError

_AUTH_CODES = frozenset(
    {
        "AccessDenied",
        "AccessDeniedException",
        "UnauthorizedException",
        "NotAuthorizedException",
        "InvalidClientTokenId",
        "SignatureDoesNotMatch",
        "ExpiredToken",
        "InvalidAccessKeyId",
    }
)

_THROTTLE_CODES = frozenset(
    {
        "ThrottlingException",
        "Throttling",
        "TooManyRequestsException",
        "RequestLimitExceeded",
        "ClientLimitExceededException",  # KVS
        "ProvisionedThroughputExceededException",
    }
)

_KVS_NOT_FOUND_CODES = frozenset({"ResourceNotFoundException"})


class FactbirdByomError(Exception):
    """Base class for all factbird-byom SDK errors."""


class AuthError(FactbirdByomError):
    """AWS rejected the caller's credentials or the operation is not permitted."""


class ModelUploadError(FactbirdByomError):
    """Uploading the model artifact to S3 failed."""


class BucketNotFoundError(ModelUploadError):
    """The BYOM S3 bucket does not exist for the configured account + region.

    The bucket name is derived as `{account_id}-{region}-byom`; the most
    likely cause of this error is a wrong `account_id` or `region`.
    """


class StreamNotFoundError(FactbirdByomError):
    """The requested KVS stream does not exist or is not currently streaming."""


class ThrottledError(FactbirdByomError):
    """AWS throttled the request. Callers may retry with backoff."""


def wrap_s3_error(err: ClientError, *, bucket: str, key: str) -> FactbirdByomError:
    code = err.response.get("Error", {}).get("Code", "")
    if code in _AUTH_CODES:
        return AuthError(
            f"AWS rejected s3:PutObject on {bucket}/{key} ({code}). "
            "Check the `byom-uploader` access keys — they rotate roughly yearly."
        )
    if code == "NoSuchBucket":
        return BucketNotFoundError(
            f"BYOM bucket '{bucket}' does not exist. "
            "Double-check `account_id` and `region` — the bucket name is "
            "derived as `{account_id}-{region}-byom`."
        )
    if code in _THROTTLE_CODES:
        return ThrottledError(
            f"AWS throttled the upload to {bucket}/{key} ({code}). Retry with backoff."
        )
    return ModelUploadError(f"Failed to upload to s3://{bucket}/{key}: {code or err}")


def wrap_kvs_error(err: ClientError, *, stream_id: str) -> FactbirdByomError:
    code = err.response.get("Error", {}).get("Code", "")
    if code in _AUTH_CODES:
        return AuthError(
            f"AWS rejected the KVS request for stream '{stream_id}' ({code}). "
            "Check the `byom-uploader` access keys — they rotate roughly yearly."
        )
    if code in _KVS_NOT_FOUND_CODES:
        return StreamNotFoundError(
            f"KVS stream '{stream_id}' was not found. "
            "Make sure the edge device is currently streaming and the name matches."
        )
    if code in _THROTTLE_CODES:
        return ThrottledError(
            f"AWS throttled the KVS request for stream '{stream_id}' ({code}). "
            "Retry with backoff."
        )
    return FactbirdByomError(f"KVS call failed for stream '{stream_id}': {code or err}")
