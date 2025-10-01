"""
IoT Deployment Module

This module provides functions for deploying models to edge devices via AWS IoT jobs.
Supports creating deployment jobs that instruct devices to download models from URLs.

Author: Claude Code Assistant
License: MIT
"""

import json
import logging
from datetime import datetime
from botocore.exceptions import ClientError

# Setup logging
logger = logging.getLogger(__name__)


def check_iot_thing_exists(aws_session, thing_id):
    """
    Check if an IoT thing exists in AWS IoT Core

    Args:
        aws_session: Boto3 session with AWS credentials
        thing_id (str): IoT thing identifier

    Returns:
        tuple: (bool, dict) - exists status and thing info
    """
    logger.info(f"Checking if IoT thing exists: {thing_id}")

    try:
        iot_client = aws_session.client('iot')

        # Try to describe the thing
        response = iot_client.describe_thing(thingName=thing_id)
        thing_info = response

        logger.info(f"IoT thing found: {thing_id}")
        print(f"✅ IoT Thing found: {thing_id}")
        print(f"   Thing Name: {thing_info['thingName']}")
        print(f"   Thing ARN: {thing_info['thingArn']}")

        if 'attributes' in thing_info and thing_info['attributes']:
            print(f"   Attributes: {thing_info['attributes']}")

        # Check if thing is connected (optional)
        try:
            shadow_client = aws_session.client('iot-data')
            shadow_response = shadow_client.get_thing_shadow(thingName=thing_id)
            logger.debug("Thing shadow available - device may be connected")
            print(f"   📡 Shadow available (device may be connected)")
        except Exception:
            logger.debug("No shadow found - device may be offline")
            print(f"   📡 No shadow found (device may be offline)")

        return True, thing_info

    except iot_client.exceptions.ResourceNotFoundException:
        logger.error(f"IoT thing not found: {thing_id}")
        print(f"❌ IoT Thing not found: {thing_id}")
        print("   The thing must be registered in AWS IoT Core first.")
        print("   Check your device provisioning and registration.")
        return False, None

    except ClientError as e:
        logger.error(f"ClientError checking IoT thing: {e}")
        print(f"❌ Error checking IoT thing: {str(e)}")
        return False, None

    except Exception as e:
        logger.error(f"Unexpected error checking IoT thing: {e}")
        print(f"❌ Error checking IoT thing: {str(e)}")
        return False, None


def create_deployment_job(aws_session, thing_arn, deployment_url):
    """
    Create an IoT job to download a file to the edge device

    Args:
        aws_session: Boto3 session with AWS credentials
        thing_arn (str): IoT thing ARN
        deployment_url (str): URL where device can download the file

    Returns:
        tuple: (bool, str, str) - success status, job_id, job_arn
    """
    logger.info(f"Creating deployment job for thing ARN: {thing_arn}")
    logger.debug(f"Deployment URL: {deployment_url}")

    try:
        iot_client = aws_session.client('iot')

        # Generate unique job ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_id = f"deploy_download_{timestamp}"

        # Create job document with deployment instructions
        job_document = {
            "download": {
                "url": deployment_url,
                "destination": "/data/download-tests/test.txt"
            }
        }

        logger.debug(f"Job document: {job_document}")

        # Convert to JSON string
        document_source = json.dumps(job_document)
        logger.debug(f"Document source JSON: {document_source}")

        # Create the IoT job
        response = iot_client.create_job(
            jobId=job_id,
            targets=[thing_arn],
            document=document_source,  # Use 'document' instead of 'documentSource'
            description=f"Download file to edge device {thing_arn.split('/')[-1]}",
            targetSelection='SNAPSHOT',  # Required parameter
            jobExecutionsRolloutConfig={
                'maximumPerMinute': 10
            },
            timeoutConfig={
                'inProgressTimeoutInMinutes': 10
            }
        )

        job_arn = response['jobArn']

        logger.info(f"IoT job created successfully: {job_id}")
        print(f"✅ IoT Job created successfully!")
        print(f"   Job ID: {job_id}")
        print(f"   Job ARN: {job_arn}")
        print(f"   Target Thing: {thing_arn.split('/')[-1]}")
        print(f"   Download URL: {deployment_url}")
        print(f"   Created: {datetime.now()}")

        return True, job_id, job_arn

    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"ClientError creating IoT job: {error_code}")
        print(f"❌ Failed to create IoT job: {error_code}")

        if error_code == 'UnauthorizedException':
            print("   Missing IoT permissions. Ensure your credentials have:")
            print("   - iot:CreateJob")
            print("   - iot:DescribeJob")
        elif error_code == 'ResourceAlreadyExistsException':
            print("   Job with this ID already exists")
        else:
            print(f"   Error: {e.response['Error']['Message']}")

        return False, None, None

    except Exception as e:
        logger.error(f"Unexpected error creating IoT job: {e}")
        print(f"❌ Failed to create IoT job: {str(e)}")
        return False, None, None


def check_job_status(aws_session, job_id):
    """
    Check the status of an IoT job

    Args:
        aws_session: Boto3 session with AWS credentials
        job_id (str): IoT job identifier

    Returns:
        str: Job status or None if failed
    """
    logger.debug(f"Checking status of job: {job_id}")

    try:
        iot_client = aws_session.client('iot')

        response = iot_client.describe_job(jobId=job_id)
        job_status = response['job']['status']

        logger.info(f"Job {job_id} status: {job_status}")
        print(f"📊 Job Status: {job_status}")

        # Get job executions
        try:
            executions = iot_client.list_job_executions_for_job(jobId=job_id)

            for execution in executions['executionSummaries']:
                thing_name = execution['thingArn'].split('/')[-1]
                status = execution['status']
                logger.debug(f"Execution for {thing_name}: {status}")
                print(f"   📱 {thing_name}: {status}")

        except Exception as e:
            logger.warning(f"Could not get job executions: {e}")

        return job_status

    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"ClientError checking job status: {error_code}")

        if error_code == 'ResourceNotFoundException':
            print(f"❌ Job not found: {job_id}")
        else:
            print(f"❌ Failed to check job status: {error_code}")

        return None

    except Exception as e:
        logger.error(f"Unexpected error checking job status: {e}")
        print(f"❌ Failed to check job status: {str(e)}")
        return None


def list_deployment_jobs(aws_session, thing_id=None, limit=10):
    """
    List recent deployment jobs

    Args:
        aws_session: Boto3 session with AWS credentials
        thing_id (str, optional): Filter by thing ID
        limit (int): Maximum number of jobs to return

    Returns:
        list: List of job summaries
    """
    logger.debug(f"Listing deployment jobs, thing_id: {thing_id}, limit: {limit}")

    try:
        iot_client = aws_session.client('iot')

        params = {
            'status': 'IN_PROGRESS',
            'maxResults': limit
        }

        if thing_id:
            params['thingGroupName'] = thing_id

        response = iot_client.list_jobs(**params)
        jobs = response['jobs']

        # Also get completed jobs
        params['status'] = 'COMPLETED'
        completed_response = iot_client.list_jobs(**params)
        jobs.extend(completed_response['jobs'])

        # Sort by creation date
        jobs.sort(key=lambda x: x['createdAt'], reverse=True)

        logger.info(f"Found {len(jobs)} deployment jobs")

        if jobs:
            print(f"📋 Recent deployment jobs:")
            for job in jobs[:limit]:
                print(f"   {job['jobId']} - {job['status']} - {job['createdAt']}")
        else:
            print(f"📋 No deployment jobs found")

        return jobs

    except Exception as e:
        logger.error(f"Error listing deployment jobs: {e}")
        print(f"❌ Failed to list deployment jobs: {str(e)}")
        return []


def cancel_deployment_job(aws_session, job_id, reason="Manual cancellation"):
    """
    Cancel a deployment job

    Args:
        aws_session: Boto3 session with AWS credentials
        job_id (str): IoT job identifier
        reason (str): Reason for cancellation

    Returns:
        bool: Success status
    """
    logger.info(f"Cancelling deployment job: {job_id}")

    try:
        iot_client = aws_session.client('iot')

        response = iot_client.cancel_job(
            jobId=job_id,
            reasonCode="USER_INITIATED",
            comment=reason
        )

        logger.info(f"Job cancelled successfully: {job_id}")
        print(f"✅ Job cancelled: {job_id}")
        print(f"   Reason: {reason}")

        return True

    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        print(f"❌ Failed to cancel job: {str(e)}")
        return False