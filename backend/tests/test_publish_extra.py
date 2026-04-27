"""Additional coverage for routes/publish.py:

- `_on_token_refresh` callback (saves refreshed tokens to DynamoDB).
- Publish error path (job marked "failed" + 500 returned).
- Bulk-publish error path (per-item failure recorded but loop continues).
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes.publish import _on_token_refresh

client = TestClient(app)


@pytest.fixture
def fake_creds_dict():
    return {
        "api_key": "key", "access_token": "tok",
        "refresh_token": "ref", "user_id": "u1", "shop_id": "s1",
    }


class TestOnTokenRefresh:
    @patch("api.routes.publish.save_credentials")
    def test_persists_refreshed_creds(self, mock_save):
        creds = MagicMock(
            api_key="new-key", access_token="new-tok",
            refresh_token="new-ref", user_id="u1", shop_id="s1",
        )
        _on_token_refresh(creds)
        mock_save.assert_called_once_with(
            api_key="new-key",
            access_token="new-tok",
            refresh_token="new-ref",
            user_id="u1",
            shop_id="s1",
        )


class TestPublishErrorPath:
    @patch("api.routes.publish.update_job")
    @patch("api.routes.publish.create_job")
    @patch("api.routes.publish.process_image_bytes")
    @patch("api.routes.publish.read_image")
    @patch("api.routes.publish.load_credentials")
    def test_failure_marks_job_failed_and_returns_500(
        self, mock_creds, mock_read, mock_process, mock_create_job, mock_update_job,
        fake_creds_dict,
    ):
        mock_creds.return_value = fake_creds_dict
        mock_read.return_value = b"png-bytes"
        mock_process.side_effect = RuntimeError("boom")

        resp = client.post("/publish", json={
            "s3_key": "uploads/x", "sizes": ["8x10"],
            "title": "T", "description": "D", "tags": ["t"], "price": 4.99,
        })
        assert resp.status_code == 500
        assert "boom" in resp.json()["detail"]

        # Job lifecycle: created → processing → failed (with error)
        statuses = [c.args[1] for c in mock_update_job.call_args_list]
        assert "processing" in statuses
        assert "failed" in statuses
        # Failed call carried the error string
        failed_call = next(
            c for c in mock_update_job.call_args_list if c.args[1] == "failed"
        )
        assert "boom" in failed_call.kwargs["error"]


class TestBulkPublishErrorPath:
    @patch("api.routes.publish.update_job")
    @patch("api.routes.publish.create_job")
    @patch("api.routes.publish.upload_listing_file_bytes")
    @patch("api.routes.publish.upload_listing_image_bytes")
    @patch("api.routes.publish.create_draft_listing")
    @patch("api.routes.publish.process_image_bytes")
    @patch("api.routes.publish.read_image")
    @patch("api.routes.publish.load_credentials")
    def test_one_item_fails_others_succeed(
        self, mock_creds, mock_read, mock_process, mock_draft,
        mock_upload_img, mock_upload_file, mock_create_job, mock_update_job,
        fake_creds_dict,
    ):
        mock_creds.return_value = fake_creds_dict
        mock_read.return_value = b"png"
        mock_process.return_value = [("8x10", b"\x89PNG")]
        good_draft = MagicMock(listing_id="111", url="https://x", title="OK")
        # first item succeeds, second item raises during draft creation
        mock_draft.side_effect = [good_draft, RuntimeError("draft fail")]

        resp = client.post("/publish/bulk", json={
            "items": [
                {"s3_key": "k1", "sizes": ["8x10"], "title": "A",
                 "description": "d", "tags": ["t"], "price": 1.0},
                {"s3_key": "k2", "sizes": ["8x10"], "title": "B",
                 "description": "d", "tags": ["t"], "price": 2.0},
            ],
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["job_ids"]) == 2

        # One job is "completed", one is "failed"
        statuses = [c.args[1] for c in mock_update_job.call_args_list]
        assert "completed" in statuses
        assert "failed" in statuses
        failed_call = next(
            c for c in mock_update_job.call_args_list if c.args[1] == "failed"
        )
        assert "draft fail" in failed_call.kwargs["error"]


class TestAuthCallbackErrorPath:
    """Token-exchange failure is the missing branch in routes/auth.py."""

    @patch("api.routes.auth.exchange_code")
    @patch("api.routes.auth.load_oauth_state")
    @patch("api.routes.auth.ETSY_API_KEY", "test-key")
    def test_exchange_failure_returns_400(self, mock_state, mock_exchange):
        mock_state.return_value = {"verifier": "v", "redirect_uri": "http://cb"}
        mock_exchange.side_effect = RuntimeError("etsy rejected")

        resp = client.post("/auth/etsy/callback?code=c&state=s")
        assert resp.status_code == 400
        assert "etsy rejected" in resp.json()["detail"]

    @patch("api.routes.auth.ETSY_API_KEY", "")
    def test_callback_missing_api_key(self):
        resp = client.post("/auth/etsy/callback?code=c&state=s")
        assert resp.status_code == 500
