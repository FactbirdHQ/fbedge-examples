from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

import boto3

from factbird_byom.client import FactbirdByomClient
from factbird_byom.config import ClientConfig
from factbird_byom.exceptions import FactbirdByomError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="factbird-byom",
        description="Factbird BYOM CLI — deploy a model or view a device's KVS stream.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    deploy = subparsers.add_parser(
        "deploy",
        help="Upload a compiled model to a device (triggers the server-side IoT job).",
    )
    deploy.add_argument("model_path", help="Path to the compiled model (e.g. a .hef file).")
    deploy.add_argument(
        "--device-id",
        dest="device_id",
        required=True,
        help="Target device (IoT thing-id).",
    )
    deploy.add_argument(
        "--model-name",
        dest="model_name",
        default=None,
        help="Override the uploaded file name (default: the source file's name).",
    )
    _add_aws_args(deploy)

    view = subparsers.add_parser("view", help="Print (and open) a signed streaming URL.")
    view.add_argument("stream_id", help="KVS stream name (same as the device stream-id).")
    view.add_argument(
        "--dash",
        action="store_true",
        help="Emit a DASH URL instead of HLS (HLS is the default — plays in Safari natively).",
    )
    view.add_argument(
        "--expires",
        type=int,
        default=300,
        help="Session URL validity in seconds (min 300, max 43200). Default: 300.",
    )
    view.add_argument(
        "--no-open",
        action="store_true",
        help="Just print the URL; don't try to launch a viewer.",
    )
    _add_aws_args(view)

    args = parser.parse_args(argv)

    if args.command == "deploy":
        return _cmd_deploy(args)
    if args.command == "view":
        return _cmd_view(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _add_aws_args(sub: argparse.ArgumentParser) -> None:
    sub.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION"),
        help="AWS region. Defaults to AWS_REGION / AWS_DEFAULT_REGION env var.",
    )
    sub.add_argument(
        "--account-id",
        dest="account_id",
        default=os.environ.get("AWS_ACCOUNT_ID", ""),
        help="AWS account ID. Defaults to the AWS_ACCOUNT_ID env var.",
    )


def _build_client(args: argparse.Namespace) -> FactbirdByomClient | None:
    """Build a client or print an error and return None."""
    if not args.region:
        print(
            "error: --region not set and no AWS_REGION / AWS_DEFAULT_REGION env var.",
            file=sys.stderr,
        )
        return None
    if not args.account_id:
        print(
            "error: --account-id not set and no AWS_ACCOUNT_ID env var.",
            file=sys.stderr,
        )
        return None
    return FactbirdByomClient(
        session=boto3.Session(),
        config=ClientConfig(region=args.region, account_id=args.account_id),
    )


def _cmd_deploy(args: argparse.Namespace) -> int:
    client = _build_client(args)
    if client is None:
        return 2
    try:
        result = client.deployment.deploy(
            args.model_path,
            device_id=args.device_id,
            model_name=args.model_name,
        )
    except FactbirdByomError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    print(f"uploaded: s3://{result.bucket}/{result.key}")
    print(f"  size:  {result.size} bytes")
    print(f"  etag:  {result.etag}")
    return 0


def _cmd_view(args: argparse.Namespace) -> int:
    client = _build_client(args)
    if client is None:
        return 2

    try:
        with client.streams.open(args.stream_id) as kvs:
            if args.dash:
                url = kvs.dash_url(expires_in=args.expires)
            else:
                url = kvs.hls_url(expires_in=args.expires)
    except FactbirdByomError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    print(url)

    if args.no_open:
        return 0

    opener = _find_opener()
    if opener is None:
        print(
            "(no viewer opener found — paste the URL into VLC, Safari, or ffplay)",
            file=sys.stderr,
        )
        return 0

    try:
        subprocess.Popen([opener, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as err:
        print(f"(failed to launch {opener}: {err})", file=sys.stderr)
    return 0


def _find_opener() -> str | None:
    if sys.platform == "darwin":
        return "open"
    if sys.platform.startswith("linux"):
        return shutil.which("xdg-open")
    if sys.platform == "win32":
        return "start"
    return None


if __name__ == "__main__":
    raise SystemExit(main())
