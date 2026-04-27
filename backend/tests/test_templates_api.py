"""Tests for the /templates endpoints (custom frame template upload + CRUD)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestListTemplates:
    @patch("api.routes.templates.list_custom_templates")
    @patch("api.routes.templates.list_bundled_templates")
    def test_lists_bundled_only_when_no_customs(self, mock_bundled, mock_custom):
        mock_bundled.return_value = ["blank_frame_1", "wood_frame"]
        mock_custom.return_value = []

        resp = client.get("/templates")
        assert resp.status_code == 200
        templates = resp.json()["templates"]
        assert len(templates) == 2
        assert {t["id"] for t in templates} == {"blank_frame_1", "wood_frame"}
        assert all(not t["is_custom"] for t in templates)
        # Names are humanized (underscores -> spaces)
        assert {t["name"] for t in templates} == {"blank frame 1", "wood frame"}

    @patch("api.routes.templates.list_custom_templates")
    @patch("api.routes.templates.list_bundled_templates")
    def test_merges_bundled_and_custom(self, mock_bundled, mock_custom):
        mock_bundled.return_value = ["blank_frame_1"]
        mock_custom.return_value = [
            {
                "id": "abc123",
                "name": "My Walnut Frame",
                "orientation": "horizontal",
                "is_custom": True,
                "s3_key": "templates/abc123",
                "frame_bbox": [10, 10, 200, 300],
            },
        ]

        resp = client.get("/templates")
        assert resp.status_code == 200
        templates = resp.json()["templates"]
        assert len(templates) == 2
        custom = next(t for t in templates if t["is_custom"])
        assert custom["id"] == "abc123"
        assert custom["name"] == "My Walnut Frame"
        assert custom["orientation"] == "horizontal"
        assert custom["s3_key"] == "templates/abc123"
        assert custom["frame_bbox"] == [10, 10, 200, 300]

    @patch("api.routes.templates.list_custom_templates")
    @patch("api.routes.templates.list_bundled_templates")
    def test_handles_empty_bundle_list(self, mock_bundled, mock_custom):
        mock_bundled.return_value = []
        mock_custom.return_value = []
        resp = client.get("/templates")
        assert resp.status_code == 200
        assert resp.json() == {"templates": []}


class TestUploadTemplate:
    @patch("api.routes.templates.generate_upload_url")
    def test_returns_presigned_url_and_template_stub(self, mock_gen):
        mock_gen.return_value = ("https://s3.example.com/put", "ignored-key")

        resp = client.post("/templates/upload?content_type=image/jpeg")
        assert resp.status_code == 200
        body = resp.json()
        assert body["upload_url"] == "https://s3.example.com/put"
        assert body["template"]["is_custom"] is True
        # s3_key uses generated UUID under templates/, not the helper-returned key
        assert body["template"]["s3_key"].startswith("templates/")
        assert len(body["template"]["id"]) == 12

    @patch("api.routes.templates.generate_upload_url")
    def test_default_content_type_is_jpeg(self, mock_gen):
        mock_gen.return_value = ("https://s3.example.com/put", "ignored-key")
        resp = client.post("/templates/upload")
        assert resp.status_code == 200
        mock_gen.assert_called_once_with("image/jpeg")

    @patch("api.routes.templates.generate_upload_url")
    def test_custom_content_type_passes_through(self, mock_gen):
        mock_gen.return_value = ("https://s3.example.com/put", "ignored-key")
        client.post("/templates/upload?content_type=image/png")
        mock_gen.assert_called_once_with("image/png")

    @patch("api.routes.templates.generate_upload_url")
    def test_each_call_returns_unique_id(self, mock_gen):
        mock_gen.return_value = ("https://s3.example.com/put", "k")
        first = client.post("/templates/upload").json()
        second = client.post("/templates/upload").json()
        assert first["template"]["id"] != second["template"]["id"]


class TestSaveTemplate:
    @patch("api.routes.templates.save_custom_template")
    def test_saves_metadata(self, mock_save):
        mock_save.return_value = {
            "id": "tmpl-001",
            "name": "Walnut Frame",
            "orientation": "vertical",
            "is_custom": True,
            "s3_key": "templates/tmpl-001",
            "frame_bbox": None,
        }

        resp = client.post(
            "/templates",
            json={
                "name": "Walnut Frame",
                "s3_key": "templates/tmpl-001",
                "orientation": "vertical",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "tmpl-001"
        assert body["name"] == "Walnut Frame"
        assert body["is_custom"] is True

        save_kwargs = mock_save.call_args.kwargs
        assert save_kwargs["name"] == "Walnut Frame"
        assert save_kwargs["s3_key"] == "templates/tmpl-001"
        assert save_kwargs["orientation"] == "vertical"
        # template_id is generated server-side
        assert "template_id" in save_kwargs
        assert len(save_kwargs["template_id"]) == 12

    @patch("api.routes.templates.save_custom_template")
    def test_orientation_defaults_to_vertical(self, mock_save):
        mock_save.return_value = {
            "id": "tmpl-002",
            "name": "X",
            "orientation": "vertical",
            "is_custom": True,
            "s3_key": "templates/tmpl-002",
            "frame_bbox": None,
        }
        resp = client.post(
            "/templates",
            json={"name": "X", "s3_key": "templates/tmpl-002"},
        )
        assert resp.status_code == 200
        assert mock_save.call_args.kwargs["orientation"] == "vertical"

    def test_rejects_missing_required_fields(self):
        # Missing s3_key
        resp = client.post("/templates", json={"name": "Only Name"})
        assert resp.status_code == 422


class TestRemoveTemplate:
    @patch("api.routes.templates.delete_custom_template")
    def test_deletes_existing(self, mock_delete):
        mock_delete.return_value = True
        resp = client.delete("/templates/tmpl-001")
        assert resp.status_code == 200
        assert resp.json() == {"success": True}
        mock_delete.assert_called_once_with("tmpl-001")

    @patch("api.routes.templates.delete_custom_template")
    def test_404_when_not_found(self, mock_delete):
        mock_delete.return_value = False
        resp = client.delete("/templates/nonexistent")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
