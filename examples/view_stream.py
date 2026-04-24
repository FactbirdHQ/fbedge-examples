"""Mint a signed HLS (or DASH) URL for a Factbird Edge KVS stream.

Paste the printed URL into Safari (macOS/iOS), VLC, QuickTime, or ffplay.
On macOS / Linux, pass --open to launch the default viewer automatically.

Usage:
    python examples/view_stream.py edge-01
    python examples/view_stream.py edge-01 --dash --expires 600 --open
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

import boto3

from factbird_byom import ClientConfig, FactbirdByomClient


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("stream_id", help="KVS stream name (same as the device stream-id).")
    parser.add_argument("--dash", action="store_true", help="Emit a DASH URL instead of HLS.")
    parser.add_argument(
        "--expires",
        type=int,
        default=300,
        help="URL validity in seconds (min 300, max 43200). Default: 300.",
    )
    parser.add_argument(
        "--open",
        dest="auto_open",
        action="store_true",
        help="Also launch the default viewer (macOS: `open`; Linux: `xdg-open`).",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION"),
        help="AWS region. Defaults to AWS_REGION / AWS_DEFAULT_REGION env var.",
    )
    parser.add_argument(
        "--account-id",
        dest="account_id",
        default=os.environ.get("AWS_ACCOUNT_ID"),
        help="AWS account ID. Defaults to the AWS_ACCOUNT_ID env var.",
    )
    args = parser.parse_args()

    if not args.region:
        print("error: --region not set and no AWS_REGION env var.", file=sys.stderr)
        return 2
    if not args.account_id:
        print("error: --account-id not set and no AWS_ACCOUNT_ID env var.", file=sys.stderr)
        return 2

    client = FactbirdByomClient(
        session=boto3.Session(),
        config=ClientConfig(region=args.region, account_id=args.account_id),
    )
    with client.streams.open(args.stream_id) as kvs:
        url = kvs.dash_url(expires_in=args.expires) if args.dash else kvs.hls_url(expires_in=args.expires)

    print(url)
    if args.auto_open:
        _launch(url)
    return 0


def _launch(url: str) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["open", url])
    elif sys.platform.startswith("linux") and (opener := shutil.which("xdg-open")):
        subprocess.Popen([opener, url])
    else:
        print("(no viewer opener available on this platform)", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
