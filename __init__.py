"""
FBEdge Examples - Edge AI with Local Storage

This package provides comprehensive tools and examples for working with Hailo8 edge devices,
including video streaming, dataset capture, model training, and local deployment.

Main modules:
- aws_video_stream: Video streaming and dataset capture (supports both local and AWS)
- hailo_inference: Hailo AI inference with local storage

Quick start:
    from aws_video_stream import AWSVideoStreamCapture, AWSConfiguration
    from hailo_inference import HailoAWSInference

    # Setup configuration
    AWSConfiguration.setup_video_streaming_config()

    # Initialize video streaming (local storage)
    capture = AWSVideoStreamCapture(stream_id="your_stream")

    # Initialize inference (local storage)
    inference = HailoAWSInference("models/model.hef", "stream_id")
"""

__version__ = "1.0.0"
__author__ = "Gustav Toft"
__license__ = "MIT"

# Import main classes for easy access
try:
    from .aws_video_stream import AWSVideoStreamCapture, AWSConfiguration, get_video_sources
    from .hailo_inference import HailoAWSInference, monitor_inference_performance

    __all__ = [
        "AWSVideoStreamCapture",
        "AWSConfiguration",
        "get_video_sources",
        "HailoAWSInference",
        "monitor_inference_performance",
    ]

except ImportError as e:
    # Handle cases where dependencies aren't installed yet
    import warnings
    warnings.warn(f"Some modules could not be imported: {e}. Install requirements with 'pip install -e .'")
    __all__ = []