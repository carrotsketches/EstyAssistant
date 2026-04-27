"""Tests for AI-driven bundle paths and manual config grouping.

These complement test_bundles.py — they cover the Claude-API-backed code paths
(`group_with_ai`, `generate_bundle_description`) and the JSON-config grouping
path (`group_from_config`), all of which were untested before.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from etsy_assistant.bundles import (
    generate_bundle_description,
    generate_bundles,
    group_from_config,
    group_with_ai,
    load_listing_jsons,
)


def _fake_message(text: str) -> MagicMock:
    """Build a Claude-shaped response object: message.content[0].text."""
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


@pytest.fixture
def listing_jsons(tmp_path):
    """A handful of listings with overlapping tags (mirrors test_bundles.py)."""
    listings = [
        {"title": "Trolley Sketch", "tags": ["urban", "ink", "sketch"], "description": "T"},
        {"title": "City Bridge", "tags": ["urban", "ink", "sketch"], "description": "C"},
        {"title": "Skyline", "tags": ["urban", "ink", "sketch"], "description": "S"},
        {"title": "Dahlia", "tags": ["floral", "ink"], "description": "D"},
        {"title": "Rose", "tags": ["floral", "ink"], "description": "R"},
    ]
    for i, data in enumerate(listings):
        (tmp_path / f"listing_{i}.json").write_text(json.dumps(data))
    return tmp_path


class TestGroupWithAi:
    def test_parses_plain_json(self, listing_jsons):
        listings = load_listing_jsons(listing_jsons)
        client = MagicMock()
        client.messages.create.return_value = _fake_message(
            json.dumps({"groups": [
                {"theme": "Urban Scenes", "indices": [0, 1, 2]},
                {"theme": "Florals", "indices": [3, 4]},
            ]})
        )

        groups = group_with_ai(listings, client=client)
        assert len(groups) == 2
        assert groups[0]["theme"] == "Urban Scenes"
        assert groups[0]["indices"] == [0, 1, 2]
        # Prompt should mention every listing
        called_prompt = client.messages.create.call_args.kwargs["messages"][0]["content"]
        for n in ("Trolley Sketch", "City Bridge", "Skyline", "Dahlia", "Rose"):
            assert n in called_prompt

    def test_strips_markdown_fences(self, listing_jsons):
        listings = load_listing_jsons(listing_jsons)
        client = MagicMock()
        fenced = "```json\n" + json.dumps({"groups": [
            {"theme": "Urban", "indices": [0, 1, 2]}
        ]}) + "\n```"
        client.messages.create.return_value = _fake_message(fenced)

        groups = group_with_ai(listings, client=client)
        assert groups == [{"theme": "Urban", "indices": [0, 1, 2]}]

    def test_includes_csv_titles_in_prompt_when_provided(self, listing_jsons):
        listings = load_listing_jsons(listing_jsons)
        client = MagicMock()
        client.messages.create.return_value = _fake_message('{"groups": []}')

        csv_data = [{"title": "Existing Etsy Listing A"},
                    {"title": "Existing Etsy Listing B"}]
        group_with_ai(listings, client=client, csv_data=csv_data)

        prompt = client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "Existing Etsy shop listings for reference" in prompt
        assert "Existing Etsy Listing A" in prompt
        assert "Existing Etsy Listing B" in prompt

    def test_returns_empty_when_no_groups_in_response(self, listing_jsons):
        listings = load_listing_jsons(listing_jsons)
        client = MagicMock()
        client.messages.create.return_value = _fake_message('{"groups": []}')
        assert group_with_ai(listings, client=client) == []

    def test_invalid_json_raises(self, listing_jsons):
        listings = load_listing_jsons(listing_jsons)
        client = MagicMock()
        client.messages.create.return_value = _fake_message("this is not json")
        with pytest.raises(json.JSONDecodeError):
            group_with_ai(listings, client=client)

    def test_constructs_default_client_when_none_passed(self, listing_jsons):
        listings = load_listing_jsons(listing_jsons)
        with patch("etsy_assistant.bundles.anthropic.Anthropic") as cls:
            instance = MagicMock()
            instance.messages.create.return_value = _fake_message('{"groups": []}')
            cls.return_value = instance

            group_with_ai(listings)
            cls.assert_called_once_with()


class TestGroupFromConfig:
    def test_loads_groups_from_json(self, tmp_path):
        cfg = tmp_path / "groups.json"
        cfg.write_text(json.dumps({
            "groups": [
                {"theme": "Urban", "files": ["a.json", "b.json", "c.json"]},
                {"theme": "Floral", "files": ["d.json", "e.json"]},
            ]
        }))
        groups = group_from_config(cfg)
        assert len(groups) == 2
        assert groups[0]["theme"] == "Urban"
        assert groups[0]["files"] == ["a.json", "b.json", "c.json"]

    def test_returns_empty_when_no_groups_key(self, tmp_path):
        cfg = tmp_path / "empty.json"
        cfg.write_text(json.dumps({"unrelated": 1}))
        assert group_from_config(cfg) == []

    def test_invalid_json_raises(self, tmp_path):
        cfg = tmp_path / "broken.json"
        cfg.write_text("not json at all")
        with pytest.raises(json.JSONDecodeError):
            group_from_config(cfg)


class TestGenerateBundleDescriptionAi:
    def test_returns_claude_text(self):
        client = MagicMock()
        client.messages.create.return_value = _fake_message(
            "  This is the AI-generated bundle description.  "
        )
        data = [{"title": "T1", "description": "d1"},
                {"title": "T2", "description": "d2"},
                {"title": "T3", "description": "d3"}]

        desc = generate_bundle_description("Urban", 3, data, client=client)
        # Strips whitespace
        assert desc == "This is the AI-generated bundle description."

        # Theme + pack_size are interpolated into the prompt
        prompt = client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "Urban" in prompt
        assert "3-pack" in prompt or "3" in prompt
        # Each individual title shows up
        for title in ("T1", "T2", "T3"):
            assert title in prompt

    def test_constructs_default_client_when_none_passed(self):
        with patch("etsy_assistant.bundles.anthropic.Anthropic") as cls:
            instance = MagicMock()
            instance.messages.create.return_value = _fake_message("desc")
            cls.return_value = instance

            generate_bundle_description("X", 3, [{"title": "T", "description": "d"}])
            cls.assert_called_once_with()


class TestGenerateBundlesIntegration:
    """End-to-end tests for generate_bundles paths that weren't covered."""

    def test_uses_config_path_grouping(self, listing_jsons):
        cfg = listing_jsons / "groups.json"
        cfg.write_text(json.dumps({
            "groups": [{
                "theme": "From Config",
                "files": ["listing_0.json", "listing_1.json", "listing_2.json"],
            }],
        }))

        paths = generate_bundles(listing_jsons, config_path=cfg)
        assert len(paths) == 1
        data = json.loads(paths[0].read_text())
        assert data["theme"] == "From Config"
        assert data["pack_size"] == 3

    def test_config_path_skips_groups_with_too_few_files(self, listing_jsons):
        cfg = listing_jsons / "groups.json"
        cfg.write_text(json.dumps({
            "groups": [
                {"theme": "Too Small", "files": ["listing_0.json", "listing_1.json"]},
                {"theme": "Big Enough", "files": [
                    "listing_0.json", "listing_1.json", "listing_2.json"
                ]},
            ],
        }))
        paths = generate_bundles(listing_jsons, config_path=cfg)
        # Only the 3+ group should produce a bundle file
        assert len(paths) == 1
        assert json.loads(paths[0].read_text())["theme"] == "Big Enough"

    def test_use_ai_grouping_invokes_claude(self, listing_jsons):
        with patch("etsy_assistant.bundles.group_with_ai") as mock_ai:
            mock_ai.return_value = [{"theme": "AI Theme", "indices": [0, 1, 2]}]
            paths = generate_bundles(listing_jsons, use_ai_grouping=True)

        mock_ai.assert_called_once()
        assert len(paths) == 1
        assert json.loads(paths[0].read_text())["theme"] == "AI Theme"

    def test_use_ai_description_invokes_claude(self, listing_jsons):
        groups = [{"theme": "Manual", "indices": [0, 1, 2]}]
        with patch("etsy_assistant.bundles.generate_bundle_description") as mock_desc:
            mock_desc.return_value = "AI-WRITTEN BODY"
            paths = generate_bundles(
                listing_jsons, groups=groups, use_ai_description=True
            )

        mock_desc.assert_called_once()
        assert json.loads(paths[0].read_text())["description"] == "AI-WRITTEN BODY"

    def test_falls_back_to_tag_grouping_when_ai_returns_nothing(self, listing_jsons):
        """If AI grouping yields no groups, code falls back to tag-overlap."""
        with patch("etsy_assistant.bundles.group_with_ai") as mock_ai:
            mock_ai.return_value = []
            paths = generate_bundles(listing_jsons, use_ai_grouping=True)
        # Tag-overlap fallback should still produce at least one bundle
        # (listings 0/1/2 share tags "urban", "ink", "sketch")
        assert len(paths) >= 1
