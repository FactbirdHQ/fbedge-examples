"""Deploy a compiled model to a Factbird Edge device.

Dropping the file into the BYOM bucket is the public contract — the Factbird
backend reacts to the S3 event and creates the IoT deployment job server-side.

Usage:
    python examples/deploy_model.py ./model.hef --device-id edge-01
"""

from __future__ import annotations

import argparse
import os
import sys

import boto3

from factbird_byom import ClientConfig, FactbirdByomClient


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model_path", help="Path to the compiled model (e.g. .hef file).")
    parser.add_argument("--device-id", required=True, help="Target device (IoT thing-id).")
    parser.add_argument(
        "--model-name",
        default=None,
        help="Override the model file name (default: the source file's name).",
    )
    parser.add_argument(
        "--account-id",
        dest="account_id",
        default=os.environ.get("AWS_ACCOUNT_ID"),
        help="AWS account ID. Defaults to the AWS_ACCOUNT_ID env var.",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION"),
        help="AWS region. Defaults to AWS_REGION / AWS_DEFAULT_REGION env var.",
    )
    args = parser.parse_args()

    if not args.account_id:
        print("error: --account-id not set and no AWS_ACCOUNT_ID env var.", file=sys.stderr)
        return 2
    if not args.region:
        print("error: --region not set and no AWS_REGION env var.", file=sys.stderr)
        return 2

    client = FactbirdByomClient(
        session=boto3.Session(),
        config=ClientConfig(region=args.region, account_id=args.account_id),
    )
    result = client.deployment.deploy(
        args.model_path,
        device_id=args.device_id,
        model_name=args.model_name,
    )
    print(f"uploaded: s3://{result.bucket}/{result.key}")
    print(f"  size:   {result.size} bytes")
    print(f"  etag:   {result.etag}")
    print(f"  epoch:  {result.uploaded_at}")
    print("the Factbird backend will pick this up and create the IoT deployment job.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
