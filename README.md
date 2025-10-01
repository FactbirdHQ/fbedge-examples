# Edge AI Examples with Local Storage

This repository provides comprehensive examples for getting started with Hailo8 edge devices, including video streaming, model training, compilation, and local deployment. AWS integration is available as an optional feature.

## 📁 Project Structure

```
fbedge-examples/
├── examples.ipynb              # Main Jupyter notebook with complete workflow
├── video_capture.py            # KVS stream consumption and data capture
├── iot_deployment.py           # AWS IoT job creation for edge deployment
├── __init__.py                 # Package initialization
├── setup.py                    # Package setup (setuptools)
├── pyproject.toml             # Modern Python packaging configuration
├── requirements.txt            # Python package dependencies
├── MANIFEST.in                 # Package manifest for distribution
├── .env.example               # Example environment configuration
├── CLAUDE.md                   # Claude Code assistant instructions
├── README.md                   # This file
└── .env                        # AWS configuration (created by setup)
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd fbedge-examples

# Option A: Install as editable package (recommended)
pip install -e .

# Option B: Install with extras
pip install -e .[ml]         # Machine learning dependencies
pip install -e .[dev]        # Development tools (pytest, black)
pip install -e .[jupyter]    # Jupyter notebook support
pip install -e .[aws]        # AWS integration (optional)

# Option C: Traditional requirements file
pip install -r requirements.txt

# Optional: Install Hailo Platform SDK (from Hailo)
# pip install hailo-platform-sdk
```

### 2. Quick Setup

After installation, you can use the command-line tool:

```bash
# Run the setup wizard
fbedge-setup

# Or copy the example environment file
cp .env.example .env
# Then edit .env with your settings
```

### 3. Data Storage Setup

Data is organized in structured directories:
- Raw frames: `data/raw/{stream_id}/{timestamp}/`
- Processed data: `data/processed/calibration-set/`
- Models: `models/onnx/`, `models/hef/`, `models/checkpoints/`

### 4. KVS Stream Data Capture

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

### 5. IoT Deployment

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

**AWS Kinesis Video Streams integration and data capture**

- `test_aws_connection()`: Test AWS credentials and connectivity
- `setup_data_directories()`: Create organized data storage structure
- `setup_kvs_stream()`: Configure KVS stream connections
- `KVSStreamConsumer`: Consume video streams from edge devices
- Stream identification with Stream ID
- Backward consumption from KVS streams
- Frame extraction and local storage

### `iot_deployment.py`

**AWS IoT Core integration for edge device deployment**

- `check_iot_thing_exists()`: Verify IoT thing registration
- `create_deployment_job()`: Create download jobs for edge devices
- `check_job_status()`: Monitor deployment job progress
- `list_deployment_jobs()`: List recent deployment jobs
- `cancel_deployment_job()`: Cancel active jobs
- Download job document creation for edge device communication

## 💾 Local Storage Organization

### Data Directory Structure
```
data/
├── raw/
│   └── {stream_id}/
│       └── {YYYYMMDD_HHMMSS}/
│           ├── frame_001.jpg
│           ├── frame_002.jpg
│           └── session_metadata.json
└── processed/
    └── calibration-set/
        ├── image_001.jpg
        └── image_002.jpg
```

### Models Directory Structure
```
models/
├── onnx/
│   └── model.onnx
├── hef/
│   └── model.hef
└── checkpoints/
    └── best.pt
```

## 🌐 Optional AWS Integration Features

When using the `[aws]` extra, you can enable:
- S3 uploads for data storage
- IoT Core messaging for real-time updates
- Cloud-based monitoring and analytics

## 📊 Environment Configuration

Create a `.env` file with:

```bash
# Stream Configuration
STREAM_ID=video_stream_001

# Video Capture Settings
DEFAULT_VIDEO_SOURCE=0
TARGET_FPS=5
CAPTURE_DURATION=60
CONFIDENCE_THRESHOLD=0.7

# Data Storage Paths
DATA_DIR=./data
MODELS_DIR=./models

# Optional: AWS Integration (if using [aws] extra)
# AWS_ACCESS_KEY_ID=your_aws_access_key
# AWS_SECRET_ACCESS_KEY=your_aws_secret_key
# AWS_REGION=us-west-2
# S3_BUCKET=video-streaming-datasets
# IOT_ENDPOINT=your-iot-endpoint.iot.us-west-2.amazonaws.com
```

## ⚙️ Model Compilation Prerequisites

**IMPORTANT**: Model compilation to HEF format requires specific environment setup:

### Requirements
- **Operating System**: Linux x86_64 only
- **Hailo Dataflow Compiler (DFC)**: Must be installed and available
- **Python Environment**: Same virtual environment used for training

### Setup Instructions
1. **Linux x86 Environment**: Compilation only works on Linux x86_64 systems
2. **Install Hailo DFC**: Follow Hailo's official installation guide for the Dataflow Compiler
3. **Virtual Environment**: Use the same Python virtual environment that was used for model training:
   ```bash
   # Activate the training environment
   source your-training-venv/bin/activate

   # Verify Hailo DFC installation
   hailo -h
   ```
4. **Prerequisites**: Ensure all training dependencies are available in the same environment

### Note
If you don't have access to a Linux x86 system with Hailo DFC, you can:
- Use Hailo's cloud compilation services
- Contact Hailo support for compilation assistance
- Use pre-compiled HEF models for testing

## 🎯 Complete Workflow

1. **Setup**: Configure Stream ID and AWS credentials for KVS integration
2. **Data Capture**: Consume video streams from edge devices via AWS Kinesis Video Streams
3. **Data Annotation**: Annotate captured frames using Roboflow, CVAT, or other tools
4. **Training**: Train models using Hailo Model Zoo Docker environment
5. **Compilation**: Convert ONNX → HAR → optimized HAR → HEF (requires Hailo DFC on Linux x86)
6. **Deployment**: Create AWS IoT jobs to deploy models to edge devices

## 📝 Example Notebooks

The main `examples.ipynb` notebook includes:
- AWS configuration and credential setup
- KVS stream setup and video data consumption
- Data annotation guidelines and tool recommendations
- Hailo Model Zoo training workflow
- Complete compilation pipeline (ONNX → HAR → optimized HAR → HEF)
- AWS IoT job creation for edge device deployment
- Deployment monitoring and status checking

## 🆘 Troubleshooting

### Common Issues

1. **AWS Connection Issues**
   - Check your AWS credentials are current (short-lived tokens expire)
   - Verify IAM permissions for KVS, IoT Core, and STS
   - Test with `test_aws_connection()` function

2. **KVS Stream Issues**
   - Ensure your edge device is actively streaming to KVS
   - Check stream exists with correct Stream ID
   - Verify stream is in ACTIVE status

3. **IoT Deployment Issues**
   - Verify IoT thing is registered in AWS IoT Core
   - Check thing ARN matches your device
   - Ensure deployment URL is publicly accessible

4. **Compilation Issues**
   - Requires Linux x86_64 system with Hailo DFC
   - Use same virtual environment as training
   - Verify all training dependencies are available

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with both real and mock Hailo implementations
5. Submit a pull request

## 📞 Support

- Check the Hailo Developer Zone for SDK documentation
- AWS documentation for IoT Core and S3 setup
- Create issues for bugs or feature requests