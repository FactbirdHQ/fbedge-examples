#!/usr/bin/env python3
"""
Setup script for Edge AI Examples with AWS Integration
"""

from setuptools import setup, find_packages

# Minimal dependencies for core functionality
CORE_DEPS = [
    "opencv-python>=4.8.0",
    "numpy>=1.24.0",
    "python-dotenv>=1.0.0",
]

setup(
    name="fbedge-examples",
    version="1.0.0",
    author="Claude Code Assistant",
    description="Edge AI Examples with AWS Integration",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=CORE_DEPS,
    extras_require={
        "ml": [
            "torch>=2.0.0",
            "ultralytics>=8.0.0",
            "onnx>=1.14.0",
        ],
        "jupyter": [
            "jupyter>=1.0.0",
            "notebook>=7.0.0",
        ],
        "dev": [
            "pytest>=7.4.0",
            "black>=23.0.0",
        ],
        "aws": [
            "boto3>=1.28.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "fbedge-setup=aws_video_stream:quick_start_video_capture",
        ],
    },
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)