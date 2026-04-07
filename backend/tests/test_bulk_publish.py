"""Tests for bulk publish endpoint."""

from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


@pytest.fixture
def sketch_png_bytes():
    image = np.full((400, 600, 3), 240, dtype=np.uint8)
    cv2.rectangle(image, (100, 100), (500, 350), (30, 30, 30), 2)
    _, buf = cv2.imencode(".png", image)
    return buf.tobytes()


class TestBulkPublish:
    @patch("api.routes.publish.update_job")
    @patch("api.routes.publish.create_job")
    @patch("api.routes.publish.upload_listing_file_bytes")
    @patch("api.routes.publish.upload_listing_image_bytes")
    @patch("api.routes.publish.create_draft_listing")
    @patch("api.routes.publish.process_image_bytes")
    @patch("api.routes.publish.read_image")
    @patch("api.routes.publish.load_credentials")
    def test_bulk_publish_success(self, mock_creds, mock_read, mock_process,
                                   mock_create, mock_img, mock_file,
                                   mock_create_job, mock_update_job, sketch_png_bytes):
        mock_creds.return_value = {
            "api_key": "key", "access_token": "tok",
            "refresh_token": "ref", "user_id": "123", "shop_id": "456",
        }
        mock_read.return_value = sketch_png_bytes
        mock_process.return_value = [("8x10", b"\x89PNGfake")]
        mock_draft = MagicMock()
        mock_draft.listing_id = "999"
        mock_draft.url = "https://etsy.com/listing/999"
        mock_draft.title = "Test"
        mock_create.return_value = mock_draft

        resp = client.post("/publish/bulk", json={
            "items": [
                {
                    "s3_key": "uploads/a",
                    "sizes": ["8x10"],
                    "title": "Listing A",
                    "description": "Desc A",
                    "tags": ["art"],
                    "price": 4.99,
                },
                {
                    "s3_key": "uploads/b",
                    "sizes": ["8x10"],
                    "title": "Listing B",
                    "description": "Desc B",
                    "tags": ["art"],
                    "price": 4.99,
                },
            ]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["job_ids"]) == 2

    @patch("api.routes.publish.load_credentials")
    def test_bulk_publish_not_connected(self, mock_creds):
        mock_creds.return_value = None
        resp = client.post("/publish/bulk", json={
            "items": [{
                "s3_key": "uploads/a",
                "sizes": ["8x10"],
                "title": "Test",
                "description": "Test",
                "tags": ["art"],
                "price": 4.99,
            }]
        })
        assert resp.status_code == 401
