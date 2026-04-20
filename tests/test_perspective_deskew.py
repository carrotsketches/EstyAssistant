"""Coverage for the rotation-deskew fallback path in perspective.py."""

import cv2
import numpy as np

from etsy_assistant.config import PipelineConfig
from etsy_assistant.steps.perspective import (
    _rotation_deskew,
    correct_perspective,
)


def _rotated_line_image(angle_deg: float, size: int = 500) -> np.ndarray:
    """Make an image with a single long line rotated `angle_deg` from horizontal."""
    image = np.full((size, size, 3), 255, dtype=np.uint8)
    cx, cy = size // 2, size // 2
    length = size // 2 - 20
    rad = np.deg2rad(angle_deg)
    dx = int(np.cos(rad) * length)
    dy = int(np.sin(rad) * length)
    cv2.line(image, (cx - dx, cy - dy), (cx + dx, cy + dy), (0, 0, 0), 3)
    return image


class TestRotationDeskew:
    def test_no_lines_returns_image_unchanged(self):
        image = np.full((200, 200, 3), 255, dtype=np.uint8)
        config = PipelineConfig()
        result = _rotation_deskew(image, config)
        np.testing.assert_array_equal(result, image)

    def test_small_angle_short_circuits(self):
        """Near-horizontal line (<0.5°) should skip rotation."""
        image = _rotated_line_image(0.0)
        config = PipelineConfig()
        result = _rotation_deskew(image, config)
        # Returned unchanged when angle is below threshold
        np.testing.assert_array_equal(result, image)

    def test_skewed_image_gets_rotated(self):
        """A clearly-rotated line should trigger the rotation branch."""
        image = _rotated_line_image(10.0)
        config = PipelineConfig()
        result = _rotation_deskew(image, config)
        # Rotated output has different shape than the input (bounding box grows).
        assert result.shape != image.shape or not np.array_equal(result, image)

    def test_grayscale_input_is_handled(self):
        image = _rotated_line_image(7.0)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        config = PipelineConfig()
        result = _rotation_deskew(gray, config)
        assert result.ndim == 2


class TestCorrectPerspectiveFallback:
    def test_falls_back_to_deskew_when_no_quad(self):
        """No quadrilateral in the image → rotation path is taken."""
        image = _rotated_line_image(12.0)
        config = PipelineConfig()
        result = correct_perspective(image, config)
        assert result is not None
        assert result.ndim == 3
