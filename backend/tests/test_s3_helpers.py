"""Direct tests for the S3 helper module via moto."""

import importlib
import os

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def s3_bucket():
    """Provision a mock S3 bucket and reload the s3 module against it."""
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_ACCESS_KEY_ID"] = "test"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
    os.environ["S3_BUCKET"] = "test-bucket"

    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")

        from api import s3
        s3._client = None
        importlib.reload(s3)
        yield s3
        s3._client = None


class TestS3Helpers:
    def test_generate_upload_url_returns_key_and_url(self, s3_bucket):
        url, key = s3_bucket.generate_upload_url("image/png")
        assert key.startswith("uploads/")
        assert "test-bucket" in url
        # presigned URL for PUT
        assert "X-Amz-Signature" in url or "Signature" in url

    def test_write_and_read_roundtrip(self, s3_bucket):
        data = b"hello-world-payload"
        download_url = s3_bucket.write_image("processed/x.png", data)
        assert "test-bucket" in download_url

        fetched = s3_bucket.read_image("processed/x.png")
        assert fetched == data

    def test_write_uses_provided_content_type(self, s3_bucket):
        s3_bucket.write_image("outputs/y.jpg", b"jpg-bytes", content_type="image/jpeg")
        boto_client = boto3.client("s3", region_name="us-east-1")
        head = boto_client.head_object(Bucket="test-bucket", Key="outputs/y.jpg")
        assert head["ContentType"] == "image/jpeg"

    def test_upload_url_default_content_type(self, s3_bucket):
        url, key = s3_bucket.generate_upload_url()
        assert key.startswith("uploads/")
        assert url.startswith("https://")
