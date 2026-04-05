# Etsy Assistant

A CLI tool for pen & ink sketch artists that turns sketch photos into print-ready digital downloads and generates optimized Etsy listings using Claude Vision.

Built for [Carrot Sketches](https://www.etsy.com/shop/CarrotSketches).

## Features

- **Image cleanup pipeline** — autocrop, perspective correction, background cleanup, contrast enhancement
- **Multi-size output** — resize to standard print sizes (5x7, 8x10, 11x14, 16x20, A4) at 300 DPI
- **AI listing generation** — Claude Vision analyzes your sketch and generates SEO-optimized titles, tags, and descriptions
- **Frame mockups** — composite your sketch into real photo templates for listing previews
- **Etsy integration** — OAuth 2.0 auth, draft listing creation, image & file upload via Etsy v3 API
- **Batch processing** — process entire directories of sketches at once

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --group dev
```

For AI listing generation, set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY=your-key
```

## Usage

```bash
# Process a single sketch
uv run etsy-assistant process sketch.jpg -s 8x10 -s 5x7

# Process all sketches in a directory
uv run etsy-assistant batch sketches/ -s 8x10

# Generate an Etsy listing (title, tags, description)
uv run etsy-assistant generate-listing sketch.jpg

# Full pipeline: process + listing + publish as Etsy draft
uv run etsy-assistant publish sketch.jpg -p 4.99

# View image info
uv run etsy-assistant info sketch.jpg
```

### Mockups

Generate frame mockup images for your Etsy listing photos:

```python
from etsy_assistant.steps.mockup import generate_all_mockups
generate_all_mockups("sketches/flower_clean.png")
```

Templates support orientation matching — vertical sketches use vertical frame templates automatically.

## Pipeline Steps

| Step | Description |
|------|-------------|
| autocrop | Detect and crop to the paper region |
| perspective | Straighten using Hough line detection |
| background | Clean paper to pure white via adaptive thresholding |
| contrast | Enhance ink lines with CLAHE + levels normalization |

Skip any step with `--skip <step>` or `--no-perspective`.

## Testing

```bash
uv run pytest              # Run all tests
uv run pytest -v -k test_name  # Run a specific test
```

## License

All rights reserved.
