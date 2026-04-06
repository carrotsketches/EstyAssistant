"""Tests for analytics endpoint."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestAnalytics:
    @patch("api.routes.analytics.httpx.Client")
    @patch("api.routes.analytics.load_credentials")
    def test_returns_stats(self, mock_creds, mock_http_cls):
        mock_creds.return_value = {
            "api_key": "key", "access_token": "tok",
            "refresh_token": "ref", "user_id": "123", "shop_id": "456",
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "results": [
                {
                    "listing_id": 111,
                    "title": "Sketch A",
                    "views": 50,
                    "num_favorers": 5,
                    "url": "https://etsy.com/listing/111",
                },
                {
                    "listing_id": 222,
                    "title": "Sketch B",
                    "views": 30,
                    "num_favorers": 2,
                    "url": "https://etsy.com/listing/222",
                },
            ]
        }
        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.get.return_value = mock_resp
        mock_http_cls.return_value = mock_http

        resp = client.get("/analytics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_views"] == 80
        assert data["total_favorites"] == 7
        assert len(data["listings"]) == 2
        # Sorted by views descending
        assert data["listings"][0]["views"] == 50

    @patch("api.routes.analytics.load_credentials")
    def test_not_connected(self, mock_creds):
        mock_creds.return_value = None
        resp = client.get("/analytics")
        assert resp.status_code == 401

    @patch("api.routes.analytics.load_credentials")
    def test_no_shop_id(self, mock_creds):
        mock_creds.return_value = {
            "api_key": "key", "access_token": "tok",
            "refresh_token": "ref", "user_id": "123", "shop_id": None,
        }
        resp = client.get("/analytics")
        assert resp.status_code == 400
