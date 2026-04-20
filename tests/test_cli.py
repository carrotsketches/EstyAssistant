"""Tests for the Click CLI commands."""

import json
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import pytest
from click.testing import CliRunner

from etsy_assistant.cli import main
from etsy_assistant.steps.keywords import ListingMetadata


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def image_file(tmp_path, sketch_on_desk):
    """Write a synthetic sketch image to disk."""
    path = tmp_path / "sketch.jpg"
    cv2.imwrite(str(path), sketch_on_desk)
    return path


@pytest.fixture
def image_dir(tmp_path, sketch_on_desk):
    """Dir with a couple of sketches."""
    d = tmp_path / "inputs"
    d.mkdir()
    for i in range(2):
        cv2.imwrite(str(d / f"sketch_{i}.jpg"), sketch_on_desk)
    return d


@pytest.fixture
def fake_listing():
    return ListingMetadata(
        title="Ink Sketch",
        tags=["pen", "ink"],
        description="A sketch.",
    )


class TestMainGroup:
    def test_help_lists_commands(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        for cmd in ("process", "batch", "info", "generate-listing",
                    "batch-listing", "publish", "auth", "generate-bundles"):
            assert cmd in result.output

    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestInfoCommand:
    def test_info_prints_metadata(self, runner, image_file):
        result = runner.invoke(main, ["info", str(image_file)])
        assert result.exit_code == 0
        assert "File:" in result.output
        assert "Size:" in result.output
        assert "DPI:" in result.output


class TestProcessCommand:
    def test_process_single_output(self, runner, image_file):
        out = image_file.parent / "out.png"
        result = runner.invoke(
            main, ["process", str(image_file), "-o", str(out), "--skip", "perspective"]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_process_with_sizes_creates_directory_of_outputs(self, runner, image_file):
        result = runner.invoke(
            main, ["process", str(image_file), "-s", "8x10", "--no-perspective"]
        )
        assert result.exit_code == 0, result.output
        outputs = list((image_file.parent / "output").glob("*_8x10.png"))
        assert len(outputs) >= 1

    def test_process_with_debug_dumps_intermediates(self, runner, image_file):
        out = image_file.parent / "out.png"
        result = runner.invoke(
            main,
            ["process", str(image_file), "-o", str(out), "--skip", "perspective", "--debug"],
        )
        assert result.exit_code == 0, result.output
        assert (image_file.parent / "debug").is_dir()

    def test_process_verbose_and_quiet_flags(self, runner, image_file):
        out = image_file.parent / "out.png"
        result = runner.invoke(
            main, ["process", str(image_file), "-o", str(out), "--no-perspective", "-v"]
        )
        assert result.exit_code == 0, result.output


class TestBatchCommand:
    def test_batch_processes_multiple(self, runner, image_dir):
        out_dir = image_dir.parent / "batch_out"
        result = runner.invoke(
            main, ["batch", str(image_dir), "-o", str(out_dir), "--no-perspective"]
        )
        assert result.exit_code == 0, result.output
        assert list(out_dir.glob("*.png"))

    def test_batch_empty_dir(self, runner, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        result = runner.invoke(main, ["batch", str(d)])
        assert result.exit_code == 0
        assert "No images" in result.output


class TestGenerateListingCommand:
    def test_skip_processing_uses_input_directly(self, runner, image_file, fake_listing):
        with patch("etsy_assistant.cli.generate_listing", return_value=fake_listing):
            result = runner.invoke(
                main,
                ["generate-listing", str(image_file), "--skip-processing"],
            )
        assert result.exit_code == 0, result.output
        assert "Ink Sketch" in result.output

    def test_json_output(self, runner, image_file, fake_listing):
        with patch("etsy_assistant.cli.generate_listing", return_value=fake_listing):
            result = runner.invoke(
                main,
                ["generate-listing", str(image_file), "--skip-processing", "--json-output"],
            )
        assert result.exit_code == 0, result.output
        start = result.output.index("{")
        end = result.output.rindex("}") + 1
        parsed = json.loads(result.output[start:end])
        assert parsed["title"] == "Ink Sketch"
        assert parsed["tags"] == ["pen", "ink"]

    def test_save_json_writes_sidecar(self, runner, image_file, fake_listing, tmp_path):
        with patch("etsy_assistant.cli.generate_listing", return_value=fake_listing):
            result = runner.invoke(
                main,
                ["generate-listing", str(image_file), "--skip-processing", "--save"],
            )
        assert result.exit_code == 0, result.output
        sidecar = image_file.with_suffix(".json")
        assert sidecar.exists()


class TestBatchListingCommand:
    def test_processes_all_images_with_mocked_listing(self, runner, image_dir, fake_listing):
        out_dir = image_dir.parent / "listings_out"
        with patch("etsy_assistant.cli.generate_listing", return_value=fake_listing):
            result = runner.invoke(
                main,
                ["batch-listing", str(image_dir), "-o", str(out_dir),
                 "--skip-processing"],
            )
        assert result.exit_code == 0, result.output
        assert "2/2" in result.output or "listings generated" in result.output
        assert any(out_dir.glob("*_listing.json"))

    def test_empty_dir_short_circuits(self, runner, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        result = runner.invoke(main, ["batch-listing", str(d)])
        assert result.exit_code == 0
        assert "No images" in result.output


class TestGenerateBundlesCommand:
    def test_no_bundles_exits_nonzero(self, runner, tmp_path):
        d = tmp_path / "listings"
        d.mkdir()
        with patch("etsy_assistant.bundles.generate_bundles", return_value=[]):
            result = runner.invoke(main, ["generate-bundles", str(d)])
        assert result.exit_code != 0
        assert "No bundles" in result.output

    def test_reports_generated_bundles(self, runner, tmp_path):
        d = tmp_path / "listings"
        d.mkdir()
        fake_path = d / "bundle_1.json"
        fake_path.write_text("{}")
        with patch("etsy_assistant.bundles.generate_bundles", return_value=[fake_path]):
            result = runner.invoke(main, ["generate-bundles", str(d)])
        assert result.exit_code == 0
        assert "bundle_1.json" in result.output


class TestPublishCommand:
    def test_dry_run_skips_upload(self, runner, image_file, fake_listing):
        with patch("etsy_assistant.cli.generate_listing", return_value=fake_listing):
            result = runner.invoke(
                main,
                ["publish", str(image_file), "-p", "4.99",
                 "--skip-processing", "--dry-run"],
            )
        assert result.exit_code == 0, result.output
        assert "dry-run" in result.output.lower()
