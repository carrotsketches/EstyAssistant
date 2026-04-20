"""Cover the AI-grouping and AI-description paths in bundles.py with mocks."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from etsy_assistant.bundles import (
    generate_bundle_description,
    generate_bundles,
    group_from_config,
    group_with_ai,
)


def _mock_anthropic(text: str):
    """Build a MagicMock Anthropic client whose messages.create() returns `text`."""
    client = MagicMock()
    message = MagicMock()
    content = MagicMock()
    content.text = text
    message.content = [content]
    client.messages.create.return_value = message
    return client


class TestGroupWithAI:
    def test_parses_ai_response(self):
        listings = [
            (Path("a.json"), {"title": "Tram Sketch", "tags": ["tram", "urban"]}),
            (Path("b.json"), {"title": "Bridge Sketch", "tags": ["bridge", "urban"]}),
            (Path("c.json"), {"title": "Park Sketch", "tags": ["park", "urban"]}),
        ]
        client = _mock_anthropic(json.dumps({
            "groups": [{"theme": "Urban Scenes", "indices": [0, 1, 2]}]
        }))
        groups = group_with_ai(listings, client=client)
        assert groups == [{"theme": "Urban Scenes", "indices": [0, 1, 2]}]
        client.messages.create.assert_called_once()

    def test_handles_fenced_json_response(self):
        listings = [(Path("a.json"), {"title": "T", "tags": ["x"]})]
        client = _mock_anthropic(
            "```json\n" + json.dumps({"groups": [{"theme": "X", "indices": [0]}]}) + "\n```"
        )
        groups = group_with_ai(listings, client=client)
        assert groups[0]["theme"] == "X"

    def test_uses_csv_hints_when_provided(self):
        listings = [(Path("a.json"), {"title": "T", "tags": ["x"]})]
        csv_data = [{"title": "Existing Shop Listing"}]
        client = _mock_anthropic(json.dumps({"groups": []}))
        group_with_ai(listings, client=client, csv_data=csv_data)
        # The prompt payload should reference the existing shop listing.
        sent = client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "Existing Shop Listing" in sent


class TestGenerateBundleDescription:
    def test_returns_mocked_description(self):
        client = _mock_anthropic("  A lovely gallery bundle of three sketches.  ")
        text = generate_bundle_description(
            theme="Urban", pack_size=3,
            listings_data=[{"title": "A", "description": "desc"}],
            client=client,
        )
        assert text == "A lovely gallery bundle of three sketches."


class TestGroupFromConfig:
    def test_loads_groups_from_json(self, tmp_path):
        path = tmp_path / "groups.json"
        path.write_text(json.dumps({
            "groups": [{"theme": "Theme A", "files": ["a.json", "b.json", "c.json"]}]
        }))
        groups = group_from_config(path)
        assert groups[0]["theme"] == "Theme A"


class TestGenerateBundlesEndToEnd:
    def _write_listing(self, d: Path, stem: str, tags: list[str], price: float = 4.99):
        payload = {
            "title": f"{stem} Ink Sketch",
            "tags": tags,
            "description": f"A sketch of {stem}.",
            "price": price,
        }
        (d / f"{stem}.json").write_text(json.dumps(payload))

    def test_empty_dir_returns_empty(self, tmp_path):
        assert generate_bundles(tmp_path) == []

    def test_config_path_drives_grouping(self, tmp_path):
        for stem, tags in [("a", ["urban"]), ("b", ["urban"]), ("c", ["urban"])]:
            self._write_listing(tmp_path, stem, tags)
        config = tmp_path / "groups.json"
        config.write_text(json.dumps({
            "groups": [{"theme": "Urban", "files": ["a.json", "b.json", "c.json"]}]
        }))
        paths = generate_bundles(tmp_path, config_path=config)
        assert len(paths) >= 1
        assert all(p.exists() for p in paths)

    def test_ai_grouping_uses_client(self, tmp_path):
        for stem in ["a", "b", "c"]:
            self._write_listing(tmp_path, stem, ["theme"])
        client = _mock_anthropic(json.dumps({
            "groups": [{"theme": "AI Theme", "indices": [0, 1, 2]}]
        }))
        paths = generate_bundles(tmp_path, use_ai_grouping=True, client=client)
        assert len(paths) >= 1
        assert client.messages.create.called

    def test_ai_description_path(self, tmp_path):
        for stem in ["a", "b", "c"]:
            self._write_listing(tmp_path, stem, ["theme"])
        config = tmp_path / "groups.json"
        config.write_text(json.dumps({
            "groups": [{"theme": "X", "files": ["a.json", "b.json", "c.json"]}]
        }))
        client = _mock_anthropic("AI-written description.")
        paths = generate_bundles(
            tmp_path, config_path=config,
            use_ai_description=True, client=client,
        )
        assert paths
        data = json.loads(paths[0].read_text())
        assert data["description"] == "AI-written description."

    def test_pre_computed_groups_override_everything(self, tmp_path):
        for stem in ["a", "b", "c"]:
            self._write_listing(tmp_path, stem, ["tag"])
        groups = [{"theme": "Pre-set", "indices": [0, 1, 2]}]
        paths = generate_bundles(tmp_path, groups=groups)
        assert paths
