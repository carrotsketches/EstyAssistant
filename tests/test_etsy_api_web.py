"""Tests for the web-flow Etsy API helpers (bytes-based, no filesystem)."""

from unittest.mock import MagicMock, patch

import pytest

from etsy_assistant.etsy_api import (
    EtsyCredentials,
    _api_headers,
    _get_shop_id,
    _request_with_refresh,
    build_auth_url,
    exchange_code,
    upload_listing_file,
    upload_listing_file_bytes,
    upload_listing_image_bytes,
)


@pytest.fixture
def creds():
    return EtsyCredentials(
        api_key="api-key",
        access_token="12345.token",
        refresh_token="refresh",
        user_id="12345",
        shop_id="shop-1",
    )


@pytest.fixture
def creds_no_shop():
    return EtsyCredentials(
        api_key="api-key",
        access_token="12345.token",
        refresh_token="refresh",
        user_id="12345",
    )


class TestApiHeaders:
    def test_headers_shape(self, creds):
        headers = _api_headers(creds)
        assert headers["Authorization"] == "Bearer 12345.token"
        assert headers["x-api-key"] == "api-key"


class TestBuildAuthUrl:
    def test_returns_url_state_verifier(self):
        url, state, verifier = build_auth_url("api-key", "http://localhost:3000/cb")
        assert url.startswith("https://www.etsy.com/oauth/connect?")
        assert "client_id=api-key" in url
        assert "code_challenge_method=S256" in url
        assert state in url
        assert len(verifier) >= 43


class TestExchangeCode:
    def test_returns_creds_with_shop(self):
        token_resp = MagicMock()
        token_resp.json.return_value = {
            "access_token": "99.access",
            "refresh_token": "refresh-x",
        }
        shop_resp = MagicMock()
        shop_resp.status_code = 200
        shop_resp.json.return_value = {"results": [{"shop_id": 1234567}]}

        with patch("etsy_assistant.etsy_api.httpx.Client") as mock_cls:
            http = MagicMock()
            mock_cls.return_value.__enter__.return_value = http
            mock_cls.return_value.__exit__.return_value = False
            http.post.return_value = token_resp
            http.get.return_value = shop_resp

            creds = exchange_code("api-key", "code", "verifier", "http://cb")

        assert creds.access_token == "99.access"
        assert creds.user_id == "99"
        assert creds.shop_id == "1234567"

    def test_falls_back_to_no_shop(self):
        token_resp = MagicMock()
        token_resp.json.return_value = {
            "access_token": "99.access",
            "refresh_token": "refresh-x",
        }
        shop_resp = MagicMock()
        shop_resp.status_code = 404

        with patch("etsy_assistant.etsy_api.httpx.Client") as mock_cls:
            http = MagicMock()
            mock_cls.return_value.__enter__.return_value = http
            mock_cls.return_value.__exit__.return_value = False
            http.post.return_value = token_resp
            http.get.return_value = shop_resp

            creds = exchange_code("api-key", "code", "verifier", "http://cb")

        assert creds.shop_id is None


class TestGetShopId:
    def test_no_results_returns_none(self, creds):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"results": []}

        with patch("etsy_assistant.etsy_api.httpx.Client") as mock_cls:
            http = MagicMock()
            mock_cls.return_value.__enter__.return_value = http
            mock_cls.return_value.__exit__.return_value = False
            http.get.return_value = resp

            assert _get_shop_id(creds) is None

    def test_non_200_returns_none(self, creds):
        resp = MagicMock()
        resp.status_code = 500

        with patch("etsy_assistant.etsy_api.httpx.Client") as mock_cls:
            http = MagicMock()
            mock_cls.return_value.__enter__.return_value = http
            mock_cls.return_value.__exit__.return_value = False
            http.get.return_value = resp

            assert _get_shop_id(creds) is None


class TestRequestWithRefresh:
    def test_success_returns_response(self, creds):
        resp = MagicMock()
        resp.status_code = 200

        with patch("etsy_assistant.etsy_api.httpx.Client") as mock_cls:
            http = MagicMock()
            mock_cls.return_value.__enter__.return_value = http
            mock_cls.return_value.__exit__.return_value = False
            http.request.return_value = resp

            result = _request_with_refresh(creds, "POST", "http://x", data={"k": "v"})
            assert result is resp
            assert http.request.call_count == 1

    def test_401_triggers_refresh_and_retry(self, creds, tmp_path):
        expired = MagicMock()
        expired.status_code = 401
        retried = MagicMock()
        retried.status_code = 200

        refreshed_creds = EtsyCredentials(
            api_key=creds.api_key, access_token="99.new", refresh_token="r2",
            user_id="99", shop_id=creds.shop_id,
        )

        creds_path = tmp_path / "creds.json"

        with patch("etsy_assistant.etsy_api.httpx.Client") as mock_cls, \
             patch("etsy_assistant.etsy_api.refresh_access_token",
                   return_value=refreshed_creds) as mock_refresh:
            http = MagicMock()
            mock_cls.return_value.__enter__.return_value = http
            mock_cls.return_value.__exit__.return_value = False
            http.request.side_effect = [expired, retried]

            result = _request_with_refresh(
                creds, "POST", "http://x", creds_path=creds_path, data={"k": "v"},
            )

        assert result is retried
        mock_refresh.assert_called_once()
        assert creds_path.exists()


class TestUploadListingImageBytes:
    def test_uploads_and_returns_id(self, creds):
        resp = MagicMock()
        resp.status_code = 201
        resp.json.return_value = {"listing_image_id": 777}

        with patch("etsy_assistant.etsy_api.httpx.Client") as mock_cls:
            http = MagicMock()
            mock_cls.return_value.__enter__.return_value = http
            mock_cls.return_value.__exit__.return_value = False
            http.request.return_value = resp

            image_id = upload_listing_image_bytes(creds, "123", b"png-bytes")

        assert image_id == "777"

    def test_401_triggers_refresh_callback(self, creds):
        expired = MagicMock()
        expired.status_code = 401
        retried = MagicMock()
        retried.status_code = 200
        retried.json.return_value = {"listing_image_id": 12}

        on_refresh = MagicMock()
        with patch("etsy_assistant.etsy_api.httpx.Client") as mock_cls, \
             patch("etsy_assistant.etsy_api.refresh_access_token",
                   return_value=creds):
            http = MagicMock()
            mock_cls.return_value.__enter__.return_value = http
            mock_cls.return_value.__exit__.return_value = False
            http.request.side_effect = [expired, retried]

            image_id = upload_listing_image_bytes(
                creds, "123", b"png-bytes", on_refresh=on_refresh,
            )

        assert image_id == "12"
        on_refresh.assert_called_once()

    def test_without_shop_id_raises(self, creds_no_shop):
        with pytest.raises(ValueError, match="No shop_id"):
            upload_listing_image_bytes(creds_no_shop, "123", b"data")


class TestUploadListingFileBytes:
    def test_uploads_small_file(self, creds):
        resp = MagicMock()
        resp.status_code = 201
        resp.json.return_value = {"listing_file_id": 42}

        with patch("etsy_assistant.etsy_api.httpx.Client") as mock_cls:
            http = MagicMock()
            mock_cls.return_value.__enter__.return_value = http
            mock_cls.return_value.__exit__.return_value = False
            http.request.return_value = resp

            file_id = upload_listing_file_bytes(creds, "123", b"png-bytes")

        assert file_id == "42"

    def test_rejects_too_large(self, creds):
        payload = b"\x00" * (21 * 1024 * 1024)
        with pytest.raises(ValueError, match="too large"):
            upload_listing_file_bytes(creds, "123", payload)

    def test_401_triggers_refresh_callback(self, creds):
        expired = MagicMock()
        expired.status_code = 401
        retried = MagicMock()
        retried.status_code = 200
        retried.json.return_value = {"listing_file_id": 9}

        on_refresh = MagicMock()
        with patch("etsy_assistant.etsy_api.httpx.Client") as mock_cls, \
             patch("etsy_assistant.etsy_api.refresh_access_token",
                   return_value=creds):
            http = MagicMock()
            mock_cls.return_value.__enter__.return_value = http
            mock_cls.return_value.__exit__.return_value = False
            http.request.side_effect = [expired, retried]

            file_id = upload_listing_file_bytes(
                creds, "123", b"bytes", on_refresh=on_refresh,
            )

        assert file_id == "9"
        on_refresh.assert_called_once()

    def test_without_shop_id_raises(self, creds_no_shop):
        with pytest.raises(ValueError, match="No shop_id"):
            upload_listing_file_bytes(creds_no_shop, "123", b"data")


class TestUploadListingFile:
    def test_without_shop_id_raises(self, tmp_path, creds_no_shop):
        path = tmp_path / "a.png"
        path.write_bytes(b"\x00" * 10)
        with pytest.raises(ValueError, match="No shop_id"):
            upload_listing_file(creds_no_shop, "1", path)
