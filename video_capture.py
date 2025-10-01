"""
Video Capture Module

This module provides KVS stream consumption and local video capture capabilities.
Supports both AWS Kinesis Video Streams and local storage.

Author: Claude Code Assistant
License: MIT
"""

import cv2
import os
import boto3
import json
import time
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from botocore.exceptions import ClientError, NoCredentialsError
import logging

# Configure single debug log file
class ColoredFormatter(logging.Formatter):
    """Colored log formatter for console output"""

    # Color codes
    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Create logger with console and single debug file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.handlers.clear()

# Console handler with colors - only show INFO and above
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter())
console_handler.setLevel(logging.INFO)  # Only show INFO, WARNING, ERROR, CRITICAL in console

# Single debug file handler with detailed format
file_handler = logging.FileHandler('video_capture_debug.log', mode='w')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
))

logger.addHandler(console_handler)
logger.addHandler(file_handler)


class KVSStreamConsumer:
    """
    AWS Kinesis Video Streams consumer for extracting frames
    """

    def __init__(self, aws_session, kvs_config):
        """
        Initialize KVS stream consumer

        Args:
            aws_session: Boto3 session with AWS credentials
            kvs_config: Dictionary with KVS stream configuration
        """
        self.aws_session = aws_session
        self.kvs_config = kvs_config

    def consume_stream(self, session_dir, stream_config):
        """
        Consume KVS stream backwards from latest frames

        Args:
            session_dir (Path): Directory to save extracted frames
            stream_config (dict): Stream consumption configuration

        Returns:
            bool: True if frames were extracted successfully
        """
        logger.info(f"Starting KVS stream consumption for stream: {self.kvs_config['stream_name']}")
        logger.debug(f"Session directory: {session_dir}")
        logger.debug(f"Stream config: {stream_config}")

        try:
            # Initialize KVS Media client for live stream consumption
            logger.debug(f"Creating KVS media client with endpoint: {self.kvs_config['data_endpoint']}")
            kvs_media_client = self.aws_session.client(
                'kinesis-video-media',
                endpoint_url=self.kvs_config['data_endpoint']
            )
            logger.info("KVS media client created successfully")

            print(f"📡 Starting KVS live stream consumption...")
            print(f"🎯 Stream: {self.kvs_config['stream_name']}")
            print(f"📁 Saving to: {session_dir}")
            print(f"🎯 Extract rate: {stream_config['frame_extract_fps']} FPS")
            print("\n🔴 LIVE CONSUMPTION STARTING...")

            # Get live media stream starting from latest data
            print(f"📅 Consuming live stream from NOW")
            logger.info("Requesting live media stream with StartSelector=NOW")

            response = kvs_media_client.get_media(
                StreamName=self.kvs_config['stream_name'],
                StartSelector={
                    'StartSelectorType': 'NOW'  # Start from current live position
                }
            )
            logger.info("Successfully got media stream response")
            logger.debug(f"Response metadata: {response.get('ResponseMetadata', {})}")

            # Process the live stream
            logger.info("Starting to process live stream data")
            result = self._process_live_stream_data(
                response['Payload'],
                session_dir,
                stream_config
            )
            logger.info(f"Stream processing completed with result: {result}")
            return result

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"ClientError during stream consumption: {error_code}")
            logger.error(f"Full error response: {e.response}")
            print(f"❌ Live stream consumption failed: {error_code}")

            if error_code == 'ResourceNotFoundException':
                logger.warning("Stream not found - device may not be streaming")
                print("   Stream not found - check that edge device is currently streaming")
            elif error_code == 'NotAuthorizedException':
                logger.warning("Missing permissions for GetMedia")
                print("   Missing permissions for kinesis-video-media:GetMedia")
            elif error_code == 'InvalidArgumentException':
                logger.warning("Invalid parameters - stream may not be active")
                print("   Invalid parameters - check stream is currently active")
            else:
                logger.error(f"Other ClientError: {e.response['Error']['Message']}")
                print(f"   Error: {e.response['Error']['Message']}")

            return False

        except Exception as e:
            logger.critical(f"Unexpected error during stream consumption: {str(e)}")
            logger.critical(f"Exception type: {type(e).__name__}")
            print(f"❌ Unexpected error: {e}")
            import traceback
            logger.critical(f"Full traceback: {traceback.format_exc()}")
            traceback.print_exc()
            return False

    def _process_live_stream_data(self, stream_payload, session_dir, stream_config):
        """
        Process live KVS stream data and save raw chunks for analysis
        """
        logger.info("Starting live stream data processing")
        logger.debug(f"Stream payload type: {type(stream_payload)}")
        logger.debug(f"Target frames: {stream_config['max_frames']}")

        try:
            from IPython.display import clear_output
            logger.debug("IPython clear_output available")
        except ImportError:
            logger.debug("IPython not available, using dummy clear_output")
            # Define a dummy clear_output if not in Jupyter
            def clear_output(wait=True):
                pass

        process_start_time = time.time()
        saved_count = 0
        total_bytes_read = 0
        chunk_count = 0

        print(f"📡 Reading live stream data...")
        print(f"🖼️ Extracting video frames as images")
        print(f"🎯 Target: {stream_config['max_frames']} frames")

        # Create a buffer to accumulate stream data for frame extraction
        stream_buffer = b''
        temp_video_file = session_dir / 'stream_buffer.webm'
        frames_extracted = 0

        try:
            logger.info("Starting main stream reading loop with frame extraction")
            # Read stream in chunks and accumulate for frame extraction
            while frames_extracted < stream_config['max_frames']:
                current_time = time.time()
                elapsed_time = current_time - process_start_time
                logger.debug(f"Loop iteration: frames_extracted={frames_extracted}, elapsed={elapsed_time:.1f}s")

                # Stop after reasonable time if no frames found
                if elapsed_time > 60:  # 60 second timeout for frame extraction
                    logger.warning(f"Timeout reached after {elapsed_time:.1f}s")
                    print(f"\n⏰ Timeout reached after {elapsed_time:.1f}s")
                    break

                try:
                    # Read chunk from live stream
                    logger.debug(f"Attempting to read chunk {chunk_count + 1}")
                    chunk = stream_payload.read(65536)  # 64KB chunks for better frame extraction

                    if not chunk:
                        logger.info("Stream ended - no more data available")
                        print(f"\n📡 Stream ended or no more data")
                        break

                    chunk_size = len(chunk)
                    total_bytes_read += chunk_size
                    chunk_count += 1
                    stream_buffer += chunk

                    logger.debug(f"Read chunk {chunk_count}: {chunk_size} bytes")
                    logger.debug(f"Total bytes so far: {total_bytes_read}")
                    logger.debug(f"Buffer size: {len(stream_buffer)} bytes")

                    # Try to extract frames every few chunks when we have enough buffer
                    if chunk_count % 3 == 0 and len(stream_buffer) > 200000:  # 200KB buffer threshold
                        logger.info(f"Attempting frame extraction from {len(stream_buffer)} byte buffer")

                        # Extract frames from accumulated buffer
                        new_frames = self._extract_frames_from_stream_buffer(
                            stream_buffer, frames_extracted, session_dir
                        )

                        if new_frames > 0:
                            frames_extracted += new_frames
                            saved_count += new_frames  # Update saved_count for compatibility
                            logger.info(f"Extracted {new_frames} frames, total: {frames_extracted}")
                            print(f"🖼️ Extracted {new_frames} frame(s), total: {frames_extracted}")
                        else:
                            logger.debug("No frames extracted from current buffer")

                        # Keep buffer size manageable - keep last 300KB for context
                        if len(stream_buffer) > 500000:
                            logger.debug("Trimming stream buffer to prevent memory issues")
                            stream_buffer = stream_buffer[-300000:]

                    # Update progress
                    if chunk_count % 10 == 0:  # Log every 10 chunks
                        logger.info(f"Progress: {chunk_count} chunks processed, {frames_extracted} frames extracted, {total_bytes_read:,} bytes total")

                    clear_output(wait=True)
                    print(f"📡 LIVE STREAM PROCESSING:")
                    print(f"⏱️  Processing time: {elapsed_time:.1f}s")
                    print(f"🖼️ Frames extracted: {frames_extracted}")
                    print(f"📊 Total data: {total_bytes_read:,} bytes")
                    print(f"📦 Chunks processed: {chunk_count}")

                except Exception as e:
                    logger.error(f"Error reading/processing chunk: {str(e)}")
                    logger.error(f"Exception type: {type(e).__name__}")
                    print(f"\n❌ Error reading chunk: {e}")
                    break

                # Smaller delay for better real-time processing
                time.sleep(0.05)

            # Final frame extraction attempt with remaining buffer
            if len(stream_buffer) > 50000 and frames_extracted < stream_config['max_frames']:
                logger.info("Final frame extraction attempt with remaining buffer")
                final_frames = self._extract_frames_from_stream_buffer(
                    stream_buffer, frames_extracted, session_dir
                )
                if final_frames > 0:
                    frames_extracted += final_frames
                    saved_count += final_frames
                    logger.info(f"Final extraction: {final_frames} frames")
                    print(f"🖼️ Final extraction: {final_frames} frame(s)")

            logger.info(f"Stream processing loop completed. Final stats: saved={saved_count}, chunks={chunk_count}, bytes={total_bytes_read}")

        except KeyboardInterrupt:
            logger.info("Stream consumption stopped by user (KeyboardInterrupt)")
            print(f"\n⏹️  Stream consumption stopped by user")

        except Exception as e:
            logger.error(f"Unexpected error in stream processing: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

        finally:
            # Close the stream
            logger.info("Closing stream payload")
            try:
                stream_payload.close()
                logger.debug("Stream payload closed successfully")
            except Exception as close_error:
                logger.warning(f"Error closing stream payload: {close_error}")

        # Save consumption summary
        logger.info("Saving consumption summary")
        self._save_live_summary(
            saved_count, process_start_time, session_dir,
            stream_config, total_bytes_read, chunk_count
        )

        result = saved_count > 0
        logger.info(f"Stream processing completed with result: {result}")
        return result

    def _detect_stream_format(self, chunk):
        """Try to detect the format of the stream chunk"""
        if len(chunk) < 8:
            return "Too small to analyze"

        # Check common video format signatures
        signatures = {
            b'\x1A\x45\xDF\xA3': 'WebM/EBML',
            b'\x00\x00\x00\x01': 'H.264 NAL',
            b'\x00\x00\x01': 'H.264 NAL (short)',
            b'ftyp': 'MP4',
            b'moov': 'MP4 Movie',
            b'mdat': 'MP4 Media Data',
            b'\x18\x53\x80\x67': 'WebM Segment',
            b'\x1F\x43\xB6\x75': 'WebM Cluster',
        }

        # Check first few bytes
        for sig, format_name in signatures.items():
            if chunk.startswith(sig) or sig in chunk[:64]:
                return format_name

        # If no known signature, show hex preview
        return f"Unknown (starts with {chunk[:8].hex()})"

    def _extract_frames_from_stream_buffer(self, stream_buffer, frame_offset, session_dir):
        """Extract video frames from accumulated stream buffer"""
        logger.info(f"Attempting frame extraction from {len(stream_buffer)} byte buffer")
        extracted_count = 0

        try:
            # Method 1: Try saving buffer as different video formats and extract frames
            video_formats = [
                ('webm', b''),  # Raw WebM data
                ('mkv', b''),   # Matroska container
                ('mp4', b'')    # MP4 container
            ]

            for fmt, header in video_formats:
                if extracted_count > 0:
                    break  # Stop if we successfully extracted frames

                temp_video_file = session_dir / f'temp_stream_{frame_offset}.{fmt}'
                logger.debug(f"Trying format {fmt} with temp file: {temp_video_file}")

                try:
                    # Write stream buffer as video file
                    with open(temp_video_file, 'wb') as f:
                        if header:
                            f.write(header)
                        f.write(stream_buffer)

                    logger.debug(f"Saved {len(stream_buffer)} bytes to {temp_video_file}")

                    # Try to extract frames using OpenCV
                    cap = cv2.VideoCapture(str(temp_video_file))

                    if cap.isOpened():
                        logger.info(f"Successfully opened video file as {fmt}")
                        frame_count = 0
                        max_frames = min(5, 10 - frame_offset)  # Limit frames to extract

                        while frame_count < max_frames:
                            ret, frame = cap.read()
                            if not ret or frame is None:
                                logger.debug(f"No more frames available, extracted {frame_count}")
                                break

                            # Save frame as JPG
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                            frame_filename = f'frame_{frame_offset + extracted_count + 1:04d}_{timestamp}.jpg'
                            frame_path = session_dir / frame_filename

                            success = cv2.imwrite(str(frame_path), frame)
                            if success:
                                extracted_count += 1
                                frame_count += 1
                                logger.info(f"Saved frame: {frame_filename}")
                                logger.debug(f"Frame shape: {frame.shape}, size: {frame.size}")
                            else:
                                logger.warning(f"Failed to save frame {frame_filename}")

                        cap.release()

                        if extracted_count > 0:
                            logger.info(f"Successfully extracted {extracted_count} frames using {fmt} format")
                            break
                    else:
                        logger.debug(f"Could not open video file as {fmt}")

                except Exception as e:
                    logger.debug(f"Error processing {fmt} format: {str(e)}")
                    continue

                finally:
                    # Clean up temporary file
                    if temp_video_file.exists():
                        try:
                            temp_video_file.unlink()
                            logger.debug(f"Cleaned up temp file: {temp_video_file}")
                        except:
                            pass

            # Method 2: Look for embedded JPEG frames if video extraction failed
            if extracted_count == 0:
                logger.debug("Trying to extract embedded JPEG frames")
                jpeg_frames = self._extract_jpeg_from_buffer(stream_buffer, frame_offset, session_dir)
                extracted_count += jpeg_frames

            # Method 3: Try to find H.264/VP8/VP9 NAL units if still no frames
            if extracted_count == 0:
                logger.debug("Trying to extract raw video frames")
                raw_frames = self._extract_raw_video_frames(stream_buffer, frame_offset, session_dir)
                extracted_count += raw_frames

            logger.info(f"Frame extraction completed: {extracted_count} frames extracted")
            return extracted_count

        except Exception as e:
            logger.error(f"Error in frame extraction: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            return 0

    def _extract_jpeg_from_buffer(self, buffer, frame_offset, session_dir):
        """Extract JPEG images embedded in the stream buffer"""
        logger.debug("Looking for embedded JPEG frames")
        extracted_count = 0

        try:
            # JPEG markers
            jpeg_start = b'\xFF\xD8'  # SOI (Start of Image)
            jpeg_end = b'\xFF\xD9'    # EOI (End of Image)

            pos = 0
            while pos < len(buffer) - 1000 and extracted_count < 5:
                # Find JPEG start
                start_pos = buffer.find(jpeg_start, pos)
                if start_pos == -1:
                    break

                # Find JPEG end
                end_pos = buffer.find(jpeg_end, start_pos + 2)
                if end_pos == -1:
                    pos = start_pos + 2
                    continue

                # Extract JPEG data
                jpeg_data = buffer[start_pos:end_pos + 2]
                logger.debug(f"Found potential JPEG: {len(jpeg_data)} bytes")

                # Save as JPG file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                frame_filename = f'frame_{frame_offset + extracted_count + 1:04d}_{timestamp}.jpg'
                frame_path = session_dir / frame_filename

                try:
                    with open(frame_path, 'wb') as f:
                        f.write(jpeg_data)

                    # Verify it's a valid image
                    test_img = cv2.imread(str(frame_path))
                    if test_img is not None:
                        extracted_count += 1
                        logger.info(f"Saved embedded JPEG: {frame_filename}")
                        logger.debug(f"JPEG dimensions: {test_img.shape}")
                    else:
                        # Remove invalid file
                        frame_path.unlink()
                        logger.debug("Invalid JPEG removed")

                except Exception as e:
                    logger.debug(f"Error saving JPEG: {e}")
                    if frame_path.exists():
                        frame_path.unlink()

                pos = end_pos + 2

            logger.debug(f"JPEG extraction completed: {extracted_count} frames")
            return extracted_count

        except Exception as e:
            logger.error(f"Error in JPEG extraction: {str(e)}")
            return 0

    def _extract_raw_video_frames(self, buffer, frame_offset, session_dir):
        """Try to extract raw video frames (H.264 NAL units, VP8/VP9)"""
        logger.debug("Looking for raw video frame data")
        extracted_count = 0

        try:
            # Look for H.264 NAL unit start codes
            h264_start_codes = [
                b'\x00\x00\x00\x01',  # 4-byte start code
                b'\x00\x00\x01'       # 3-byte start code
            ]

            # Look for VP8/VP9 frame headers
            vp_signatures = [
                b'\x9d\x01\x2a',  # VP8 keyframe
                b'\x82'           # VP9 frame (simplified)
            ]

            all_signatures = h264_start_codes + vp_signatures

            pos = 0
            while pos < len(buffer) - 10000 and extracted_count < 3:
                # Find next potential frame
                next_frame_pos = None
                frame_type = None

                for sig in all_signatures:
                    sig_pos = buffer.find(sig, pos)
                    if sig_pos != -1:
                        if next_frame_pos is None or sig_pos < next_frame_pos:
                            next_frame_pos = sig_pos
                            frame_type = 'h264' if sig in h264_start_codes else 'vp'

                if next_frame_pos is None:
                    break

                # Extract potential frame data (next 50KB)
                frame_end = min(next_frame_pos + 51200, len(buffer))
                frame_data = buffer[next_frame_pos:frame_end]

                logger.debug(f"Found {frame_type} frame candidate at pos {next_frame_pos}, size {len(frame_data)}")

                # Try to decode as video frame
                success = self._try_decode_raw_frame(frame_data, frame_offset + extracted_count, session_dir, frame_type)

                if success:
                    extracted_count += 1

                pos = next_frame_pos + 1000  # Move forward

            logger.debug(f"Raw video extraction completed: {extracted_count} frames")
            return extracted_count

        except Exception as e:
            logger.error(f"Error in raw video extraction: {str(e)}")
            return 0

    def _try_decode_raw_frame(self, frame_data, frame_index, session_dir, frame_type):
        """Try to decode raw video frame data"""
        try:
            # Create minimal container around raw frame data
            if frame_type == 'h264':
                # Wrap H.264 data in minimal MP4 container
                container_ext = 'mp4'
                header = b''  # Simple approach, let OpenCV handle it
            else:  # VP8/VP9
                # Wrap VP data in minimal WebM container
                container_ext = 'webm'
                header = b'\x1a\x45\xdf\xa3'  # EBML header signature

            temp_file = session_dir / f'temp_raw_{frame_index}.{container_ext}'

            with open(temp_file, 'wb') as f:
                f.write(header)
                f.write(frame_data)

            # Try to extract frame with OpenCV
            cap = cv2.VideoCapture(str(temp_file))
            ret, frame = cap.read()
            cap.release()

            if ret and frame is not None:
                # Save frame as JPG
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                frame_filename = f'frame_{frame_index + 1:04d}_{timestamp}.jpg'
                frame_path = session_dir / frame_filename

                success = cv2.imwrite(str(frame_path), frame)
                if success:
                    logger.info(f"Saved raw {frame_type} frame: {frame_filename}")
                    return True

            return False

        except Exception as e:
            logger.debug(f"Error decoding raw {frame_type} frame: {e}")
            return False

        finally:
            # Clean up temp file
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass



    def _save_live_summary(self, saved_count, process_start_time, session_dir,
                         stream_config, total_bytes_read, chunk_count):
        """Save live stream consumption summary to JSON file"""
        live_summary = {
            'frames_extracted': saved_count,
            'total_chunks_processed': chunk_count,
            'processing_duration_seconds': time.time() - process_start_time,
            'total_bytes_read': total_bytes_read,
            'target_fps': stream_config['frame_extract_fps'],
            'max_frames_limit': stream_config['max_frames'],
            'kvs_stream': self.kvs_config['stream_name'],
            'consumption_method': 'Live_Stream_Frame_Extraction',
            'config': stream_config,
            'session_dir': str(session_dir),
            'completed_at': datetime.now().isoformat()
        }

        with open(session_dir / 'live_consumption_summary.json', 'w') as f:
            json.dump(live_summary, f, indent=2)

        print(f"\n📊 LIVE STREAM PROCESSING SUMMARY:")
        print(f"   Frames extracted: {saved_count}")
        print(f"   Total chunks processed: {chunk_count}")
        print(f"   Processing time: {time.time() - process_start_time:.1f} seconds")
        print(f"   Data processed: {total_bytes_read:,} bytes")
        print(f"   Stream: {self.kvs_config['stream_name']}")
        print(f"   Method: Live stream video frame extraction")
        print(f"   Storage location: {session_dir}")
        print(f"   Summary saved: live_consumption_summary.json")
        if saved_count > 0:
            print(f"\n✅ Check the frame_*.jpg files for extracted images")
        else:
            print(f"\n⚠️  No frames extracted - check stream format and connectivity")


def setup_kvs_stream(aws_session, stream_id, aws_config):
    """
    Connect to existing AWS Kinesis Video Stream

    Args:
        aws_session: Boto3 session with AWS credentials
        stream_id (str): Stream identifier
        aws_config (dict): AWS configuration

    Returns:
        dict: KVS configuration or None if failed
    """
    logger.info(f"Setting up KVS stream for stream_id: {stream_id}")
    logger.debug(f"AWS config: {aws_config}")

    try:
        # Initialize KVS client
        logger.debug("Creating KVS client")
        kvs_client = aws_session.client('kinesisvideo')
        logger.info("KVS client created successfully")

        # Connect to existing stream
        stream_name = f"{stream_id}"
        logger.info(f"Attempting to connect to stream: {stream_name}")

        try:
            # Try to describe the stream
            logger.debug("Describing stream")
            response = kvs_client.describe_stream(StreamName=stream_name)
            stream_info = response['StreamInfo']
            logger.info(f"Stream found successfully: {stream_name}")
            logger.debug(f"Stream info: {stream_info}")

            print(f"✅ Found KVS stream: {stream_name}")
            print(f"   Status: {stream_info['Status']}")
            print(f"   ARN: {stream_info['StreamARN']}")
            print(f"   Created: {stream_info['CreationTime']}")

            if stream_info['Status'] != 'ACTIVE':
                logger.warning(f"Stream status is not ACTIVE: {stream_info['Status']}")
                print(f"⚠️  Stream status is {stream_info['Status']} - may not be ready for consumption")

        except kvs_client.exceptions.ResourceNotFoundException as e:
            logger.error(f"Stream not found: {stream_name}")
            logger.debug(f"ResourceNotFoundException details: {e}")
            print(f"❌ KVS stream not found: {stream_name}")
            print("   The stream must be created by your edge device or infrastructure team.")
            print("   Common stream naming patterns:")
            print(f"     - {stream_id}_video_stream")
            print(f"     - {stream_id}_camera")
            print(f"     - edge_{stream_id}")
            print("   Check with your edge device configuration.")
            return None

        # Get stream endpoint for live media consumption
        logger.debug("Getting data endpoint for GET_MEDIA")
        response = kvs_client.get_data_endpoint(
            StreamName=stream_name,
            APIName='GET_MEDIA'  # For live media streaming
        )
        data_endpoint = response['DataEndpoint']
        logger.info(f"Got data endpoint: {data_endpoint}")

        print(f"📺 Live media endpoint: {data_endpoint}")

        # Store stream configuration
        kvs_config = {
            'stream_name': stream_name,
            'stream_arn': stream_info['StreamARN'],
            'data_endpoint': data_endpoint,
            'region': aws_config['region'],
            'status': stream_info['Status']
        }
        logger.debug(f"Created KVS config: {kvs_config}")
        logger.info("KVS stream setup completed successfully")

        return kvs_config

    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"ClientError during KVS setup: {error_code}")
        logger.error(f"Full error response: {e.response}")
        print(f"❌ KVS setup failed: {error_code}")

        if error_code == 'AccessDeniedException':
            logger.warning("Missing KVS permissions")
            print("   Missing KVS permissions. Ensure your credentials have:")
            print("   - kinesisvideo:DescribeStream")
            print("   - kinesisvideo:GetDataEndpoint")
            print("   - kinesis-video-archived-media:GetHLSStreamingSessionURL")
        else:
            logger.error(f"Other ClientError: {e.response['Error']['Message']}")
            print(f"   Error: {e.response['Error']['Message']}")

        return None

    except Exception as e:
        logger.critical(f"Unexpected error setting up KVS: {str(e)}")
        logger.critical(f"Exception type: {type(e).__name__}")
        import traceback
        logger.critical(f"Full traceback: {traceback.format_exc()}")
        print(f"❌ Unexpected error setting up KVS: {e}")
        return None


def test_aws_connection(aws_config):
    """
    Test AWS connection with short-lived credentials

    Args:
        aws_config (dict): AWS configuration with credentials

    Returns:
        tuple: (bool, boto3.Session) - success status and session
    """
    logger.info("Testing AWS connection")
    logger.debug(f"AWS config keys present: {list(aws_config.keys())}")

    try:
        # Create session with short-lived credentials
        if all([aws_config.get('access_key_id'), aws_config.get('secret_access_key'), aws_config.get('session_token')]):
            logger.info("Using configured short-lived credentials")
            session = boto3.Session(
                aws_access_key_id=aws_config['access_key_id'],
                aws_secret_access_key=aws_config['secret_access_key'],
                aws_session_token=aws_config['session_token'],
                region_name=aws_config['region']
            )
            print("🔑 Using configured short-lived credentials")
        else:
            logger.info("Using default credential provider chain")
            # Try default credentials
            session = boto3.Session(region_name=aws_config['region'])
            print("🔑 Using default credential provider chain")

        # Test STS - basic AWS API call
        logger.debug("Testing STS get_caller_identity")
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        logger.info("STS call successful")
        logger.debug(f"Caller identity: {identity}")

        print("✅ AWS Connection successful!")
        print(f"   Account ID: {identity['Account']}")
        print(f"   User ARN: {identity['Arn']}")

        # Check if using temporary credentials
        if 'assumed-role' in identity['Arn'] or aws_config.get('session_token'):
            logger.info("Using temporary/short-lived credentials")
            print("   🕐 Using temporary/short-lived credentials")

        # Test S3 access
        try:
            logger.debug("Testing S3 access")
            s3 = session.client('s3')
            buckets = s3.list_buckets()
            logger.info(f"S3 access successful - {len(buckets['Buckets'])} buckets found")
            print(f"   S3 Access: OK ({len(buckets['Buckets'])} buckets accessible)")
        except ClientError as e:
            if e.response['Error']['Code'] in ['AccessDenied', 'InvalidAccessKeyId']:
                logger.warning("S3 access denied - limited permissions")
                print("   S3 Access: Limited (no S3 permissions)")
            else:
                logger.warning(f"S3 access error: {e.response['Error']['Code']}")
                print(f"   S3 Access: Error ({e.response['Error']['Code']})")

        logger.info("AWS connection test completed successfully")
        return True, session

    except NoCredentialsError as e:
        logger.error("No AWS credentials found")
        logger.debug(f"NoCredentialsError details: {e}")
        print("❌ AWS credentials not found")
        print("   For short-lived credentials, get them with:")
        print("   aws sts get-session-token --duration-seconds 3600")
        print("   Then update AWS_CONFIG with AccessKeyId, SecretAccessKey, and SessionToken")
        return False, None

    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"ClientError during AWS connection test: {error_code}")
        logger.error(f"Full error response: {e.response}")
        print(f"❌ AWS connection failed: {error_code}")

        if error_code == 'TokenRefreshRequired':
            logger.warning("Session token expired")
            print("   Your session token has expired. Get new temporary credentials:")
            print("   aws sts get-session-token --duration-seconds 3600")
        elif error_code == 'InvalidAccessKeyId':
            logger.warning("Invalid access key ID")
            print("   Invalid credentials. Check your AccessKeyId and SecretAccessKey")
        elif error_code == 'SignatureDoesNotMatch':
            logger.warning("Invalid session token signature")
            print("   Invalid session token. Make sure SessionToken is included and correct")
        else:
            logger.error(f"Other ClientError: {e.response['Error']['Message']}")
            print("   Please check your credentials and network connection")

        return False, None

    except Exception as e:
        logger.critical(f"Unexpected error during AWS connection test: {str(e)}")
        logger.critical(f"Exception type: {type(e).__name__}")
        import traceback
        logger.critical(f"Full traceback: {traceback.format_exc()}")
        print(f"❌ Unexpected error: {e}")
        return False, None


def setup_data_directories(stream_id):
    """
    Setup data directories for the session

    Args:
        stream_id (str): Stream identifier

    Returns:
        tuple: (dict, Path) - data directories and session directory
    """
    # Create data directories
    data_dirs = {
        'raw': Path('data/raw'),
        'processed': Path('data/processed'),
        'models': Path('models')
    }

    for name, path in data_dirs.items():
        path.mkdir(parents=True, exist_ok=True)
        print(f"✅ {name} directory ready: {path}")

    # Create session-specific directory for this capture
    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = data_dirs['raw'] / stream_id / session_timestamp
    session_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 Session directory created: {session_dir}")

    return data_dirs, session_dir


def save_session_metadata(session_dir, stream_id, session_timestamp, aws_connected):
    """Save session metadata to JSON file"""
    session_metadata = {
        'stream_id': stream_id,
        'session_timestamp': session_timestamp,
        'aws_connected': aws_connected,
        'created_at': datetime.now().isoformat()
    }

    with open(session_dir / 'session_info.json', 'w') as f:
        json.dump(session_metadata, f, indent=2)

    print(f"📄 Session metadata saved")