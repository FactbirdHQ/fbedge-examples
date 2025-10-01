# Factbird Edge AI Examples

This repository provides guidance for working with custom AI models on the Factbird EDGE, including AWS Kinesis Video Streams consumption and IoT Core deployment workflows.

## 📁 Project Structure

```
fbedge-examples/
├── examples.ipynb              # Main Jupyter notebook with complete workflow
├── video_capture.py            # KVS stream consumption and data capture
├── iot_deployment.py           # AWS IoT job creation for edge deployment
├── requirements.txt            # Python package dependencies
├── pyproject.toml             # Python packaging configuration
├── setup.py                    # Package setup
└── README.md                   # This file
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/FactbirdHQ/fbedge-examples.git
cd fbedge-examples

# Install dependencies
pip install -r requirements.txt

# Or install as package with optional extras
pip install -e .              # Core dependencies
pip install -e .[jupyter]     # Jupyter notebook support
pip install -e .[dev]         # Development tools
```

### 2. AWS Configuration

Configure your AWS credentials for Kinesis Video Streams and IoT Core access. Use temporary credentials from AWS SSO or STS:

```bash
# Get temporary credentials
aws sts get-session-token --duration-seconds 3600
```

Add credentials to your notebook or script as shown in `examples.ipynb`.

### 3. Run the Notebook

```bash
jupyter notebook examples.ipynb
```

The notebook walks through:

1. AWS credential setup and testing
2. Kinesis Video Streams consumption
3. Data capture and organization
4. IoT deployment job creation

## 📺 KVS Stream Data Capture

```python
from video_capture import test_aws_connection, setup_kvs_stream, KVSStreamConsumer

# Test AWS connection
aws_connected, aws_session = test_aws_connection(AWS_CONFIG)

# Setup KVS stream
kvs_config = setup_kvs_stream(aws_session, "your_stream_id", AWS_CONFIG)

# Consume video data from edge device
consumer = KVSStreamConsumer(aws_session, kvs_config)
success = consumer.consume_stream(session_dir, stream_config)
```

## 🚀 IoT Deployment

```python
from iot_deployment import check_iot_thing_exists, create_deployment_job

# Check if IoT thing exists
thing_exists, thing_info = check_iot_thing_exists(aws_session, "thing_id")

# Create download job for edge device
job_created, job_id, job_arn = create_deployment_job(
    aws_session,
    thing_info['thingArn'],
    "https://your-download-url.com/model.hef"
)
```

## 🔧 Core Modules

### `video_capture.py`

AWS Kinesis Video Streams integration for consuming video data from Factbird EDGE devices.

**Key Functions:**

- `test_aws_connection()` - Test AWS credentials and connectivity
- `setup_kvs_stream()` - Configure KVS stream connections
- `KVSStreamConsumer` - Consume video streams and extract frames

### `iot_deployment.py`

AWS IoT Core integration for deploying files to Factbird EDGE devices.

**Key Functions:**

- `check_iot_thing_exists()` - Verify IoT thing registration
- `create_deployment_job()` - Create download jobs for edge devices
- `check_job_status()` - Monitor deployment job progress

## 💾 Local Storage Organization

```
data/
└── raw/
    └── {stream_id}/
        └── {YYYYMMDD_HHMMSS}/
            ├── frame_001.jpg
            ├── frame_002.jpg
            └── session_metadata.json
```

## 🎯 Workflow

1. **Setup** - Configure AWS credentials (temporary credentials recommended)
2. **Data Capture** - Consume video streams from Factbird EDGE via Kinesis Video Streams
3. **Data Annotation** - Annotate captured frames using your preferred tool
4. **Model Training** - Train custom models (outside scope of this repo)
5. **Deployment** - Use IoT jobs to deploy models to Factbird EDGE devices

## 🆘 Troubleshooting

### AWS Connection Issues

- Check your AWS credentials are current (temporary tokens expire)
- Verify IAM permissions for KVS, IoT Core, and STS
- Test with `test_aws_connection()` function

### KVS Stream Issues

- Ensure Factbird EDGE device is actively streaming to KVS
- Check stream exists with correct Stream ID
- Verify stream is in ACTIVE status

### IoT Deployment Issues

- Verify IoT thing is registered in AWS IoT Core
- Check thing ARN matches your device
- Ensure deployment URL is publicly accessible

## 📞 Support

For questions or issues, please create an issue in this repository.
