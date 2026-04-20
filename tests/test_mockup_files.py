"""Tests for file-based mockup generation and frame detection."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from etsy_assistant.steps.mockup import (
    _art_orientation,
    _detect_frame_interior,
    generate_all_mockups,
    generate_mockup,
    list_templates,
)


@pytest.fixture
def portrait_art(tmp_path):
    image = np.full((800, 600, 3), 240, dtype=np.uint8)
    cv2.rectangle(image, (100, 100), (500, 700), (30, 30, 30), 2)
    path = tmp_path / "art.png"
    cv2.imwrite(str(path), image)
    return path


@pytest.fixture
def landscape_art(tmp_path):
    image = np.full((400, 800, 3), 240, dtype=np.uint8)
    cv2.line(image, (50, 50), (750, 50), (20, 20, 20), 2)
    path = tmp_path / "landscape_art.png"
    cv2.imwrite(str(path), image)
    return path


@pytest.fixture
def synthetic_frame(tmp_path):
    """Create a synthetic frame image: dark border, bright interior."""
    image = np.full((600, 400, 3), 30, dtype=np.uint8)
    # Bright rectangular interior
    image[80:520, 60:340] = 250
    path = tmp_path / "frame.jpg"
    cv2.imwrite(str(path), image)
    return path


class TestArtOrientation:
    def test_portrait(self, portrait_art):
        assert _art_orientation(portrait_art) == "vertical"

    def test_landscape(self, landscape_art):
        assert _art_orientation(landscape_art) == "horizontal"


class TestDetectFrameInterior:
    def test_finds_bright_rectangle(self, synthetic_frame):
        x1, y1, x2, y2 = _detect_frame_interior(synthetic_frame)
        # Inset of 3% from the synthetic frame's (60, 80, 340, 520) region
        assert 60 < x1 < 100
        assert 80 < y1 < 120
        assert 300 < x2 < 340
        assert 500 < y2 < 520

    def test_raises_when_no_bright_region(self, tmp_path):
        dark = np.full((200, 200, 3), 20, dtype=np.uint8)
        path = tmp_path / "dark.jpg"
        cv2.imwrite(str(path), dark)
        with pytest.raises(ValueError, match="Could not detect"):
            _detect_frame_interior(path)


class TestGenerateMockup:
    def test_creates_jpeg_file(self, portrait_art, tmp_path):
        templates = list_templates()
        if not templates:
            pytest.skip("No templates available")
        out = tmp_path / "mockup.jpg"
        result = generate_mockup(portrait_art, templates[0], out)
        assert result == out
        assert out.exists()
        assert out.read_bytes()[:2] == b"\xff\xd8"

    def test_default_template(self, portrait_art, tmp_path):
        result = generate_mockup(portrait_art, output_path=tmp_path / "mockup.jpg")
        assert result.exists()

    def test_unknown_template_raises(self, portrait_art):
        with pytest.raises(ValueError, match="Unknown template"):
            generate_mockup(portrait_art, template_name="nope")

    def test_orientation_mismatch_raises(self, landscape_art):
        templates = list_templates()
        if not templates:
            pytest.skip("No templates available")
        with pytest.raises(ValueError, match="only"):
            generate_mockup(landscape_art, templates[0])

    def test_default_output_path_next_to_art(self, portrait_art):
        templates = list_templates()
        if not templates:
            pytest.skip("No templates available")
        result = generate_mockup(portrait_art, templates[0])
        assert result.parent == portrait_art.parent
        assert templates[0] in result.name


class TestGenerateAllMockups:
    def test_portrait_produces_at_least_one(self, portrait_art, tmp_path):
        out = tmp_path / "outputs"
        paths = generate_all_mockups(portrait_art, out)
        assert len(paths) >= 1
        for p in paths:
            assert p.exists()

    def test_landscape_skips_vertical_templates(self, landscape_art, tmp_path):
        paths = generate_all_mockups(landscape_art, tmp_path / "outputs")
        # All bundled templates are vertical; landscape art should skip them all.
        assert paths == []

    def test_default_output_dir(self, portrait_art):
        paths = generate_all_mockups(portrait_art)
        assert all(p.parent == portrait_art.parent for p in paths)
