# factbird-byom

Python SDK for the **Factbird Edge BYOM** (Bring Your Own Model) feature.

You've trained and compiled your own edge AI model. This SDK lets you:

1. **Deploy** the compiled artifact to a specific Factbird Edge device.
2. **View** that device's live KVS stream through a signed HLS or DASH URL.

That's the entire surface. No IoT job wrangling, no local camera capture, no
decoder shipped with the SDK — you just upload a file and get a URL.

## Install

```bash
pip install -e .
```

Requires Python 3.11+.

## Authentication

Factbird gives you long-lived access keys for the IAM user **`byom-uploader`**.
These are rotated roughly once a year and handed to you out-of-band.

Export them as standard AWS env vars (or put them in `~/.aws/credentials`),
along with the account ID Factbird gave you:

```bash
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=eu-west-1
export AWS_ACCOUNT_ID=...   # given to you by Factbird with the access keys
```

The SDK just takes a `boto3.Session`, so anything boto3's credential chain
supports (env vars, profiles, SSO) works.

### Bucket name

You never type the bucket name. The BYOM S3 bucket follows the convention
`{aws_account_id}-{region}-byom`, and the SDK builds it from `ClientConfig`'s
`account_id` and `region`. Pass the account ID and region Factbird gave you
alongside the credentials, and the rest is handled for you.

The `byom-uploader` user has exactly two policies:

- `s3:PutObject` on the BYOM bucket
- KVS read: `kinesisvideo:GetDataEndpoint`,
  `kinesisvideo:GetHLSStreamingSessionURL`,
  `kinesisvideo:GetDASHStreamingSessionURL`

Any call outside that surface will 403.

## Deploy a model

```python
import os

import boto3
from factbird_byom import ClientConfig, FactbirdByomClient

client = FactbirdByomClient(
    session=boto3.Session(),
    config=ClientConfig(
        region=os.environ["AWS_REGION"],
        account_id=os.environ["AWS_ACCOUNT_ID"],
    ),
)

result = client.deployment.deploy("./model.hef", device_id="edge-01")
print(f"s3://{result.bucket}/{result.key}")
# s3://<account-id>-<region>-byom/edge-01/1714000000/model.hef
```

The SDK uploads the file to `{device_id}/{utc_epoch}/{model_name}.hef` inside
the bucket. The Factbird backend reacts to the S3 event and creates the IoT
deployment job server-side — you don't need any IoT permissions.

`device_id` is **not verified client-side**. Pass the correct IoT thing-id;
server-side validation handles the rest.

Or from the shell:

```bash
factbird-byom deploy ./model.hef --device-id edge-01
factbird-byom deploy ./model.hef --device-id edge-01 --model-name yolov8n.hef
```

## View the live stream

```python
with client.streams.open("edge-01") as kvs:
    print(kvs.hls_url(expires_in=300))   # paste into Safari, VLC, ffplay, QuickTime
    print(kvs.dash_url(expires_in=300))  # paste into VLC, ffplay
```

Or from the shell — no Python script needed:

```bash
factbird-byom view edge-01              # prints HLS URL and launches default viewer
factbird-byom view edge-01 --dash       # DASH instead of HLS
factbird-byom view edge-01 --no-open    # just print the URL
factbird-byom view edge-01 --expires 600
```

### Players

| Player | HLS | DASH |
|---|---|---|
| Safari (macOS / iOS) | ✅ native | — |
| VLC | ✅ | ✅ |
| ffplay / ffmpeg | ✅ | ✅ |
| QuickTime | ✅ | — |
| Chrome/Firefox desktop | needs hls.js | needs dash.js |

`expires_in` is capped by AWS: min 300 s, max 43200 s (12 h).

## Examples

The `examples/` folder ships runnable scripts and a notebook:

- `examples/deploy_model.py` — single-shot deploy.
- `examples/view_stream.py` — mint an HLS/DASH URL and optionally `open` it.
- `examples/quickstart.ipynb` — both flows end-to-end.

## Troubleshooting

**`AuthError: AWS rejected ... (InvalidAccessKeyId)`**
Your `byom-uploader` keys may have been rotated. Ask Factbird for new ones.

**`StreamNotFoundError: KVS stream 'edge-01' was not found`**
The stream is only visible in KVS while the edge device is actively
streaming. Check that the device is powered on and connected.

**`ValueError: device_id is required`**
`deploy()` requires `device_id=...`; it identifies which device the backend
should target for the IoT job.

## License

MIT.
