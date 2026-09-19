#!/usr/bin/env python3
"""
main.py — AI Video Generation Pipeline Entrypoint (v3)
=======================================================

Execution flow:

1.  Load ``.env`` (FAL_KEY, OPENROUTER_API_KEY)
2.  Validate required environment variables
3.  Auto-discover **all** image files in ``/assets`` and upload each
    to fal.ai's CDN via ``fal_client.upload_file()``
4.  Build the CrewAI sequential pipeline, passing a dictionary of
    ``{role_name: cdn_url}`` so agents can reference any uploaded image
5.  Kick off the crew and print the final MP4 video URL
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import fal_client
from dotenv import load_dotenv

# ── Logging ──────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("videogen")

# ── Paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"

# Supported image extensions (case-insensitive)
IMAGE_EXTENSIONS: set[str] = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif",
}


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────
def _validate_env() -> None:
    """Ensure required environment variables are present."""
    missing: list[str] = []

    if not os.getenv("FAL_KEY"):
        missing.append("FAL_KEY")
    if not os.getenv("OPENROUTER_API_KEY"):
        missing.append("OPENROUTER_API_KEY")

    if missing:
        logger.critical(
            "Missing required environment variables: %s\n"
            "Copy .env.example → .env and fill in your keys.",
            ", ".join(missing),
        )
        sys.exit(1)


def _upload_all_assets() -> dict[str, str]:
    """
    Discover every image file in ``/assets`` and upload each to
    fal.ai's CDN via ``fal_client.upload_file()``.

    Returns
    -------
    dict[str, str]
        Mapping of **filename stem** (e.g. ``"outfit_reference"``) to
        the publicly accessible CDN URL.  The stem is the filename
        without the extension, which doubles as the **role name** that
        agents use to pick the right reference image.

    Raises
    ------
    FileNotFoundError
        If the ``/assets`` directory does not exist or contains no
        image files.
    RuntimeError
        If any individual upload fails (the function aborts on first
        failure to avoid partial uploads with missing references).
    """
    if not ASSETS_DIR.is_dir():
        raise FileNotFoundError(
            f"Assets directory not found: {ASSETS_DIR}\n"
            f"Create it and place your reference images inside."
        )

    # Discover image files (sorted for deterministic ordering)
    image_files: list[Path] = sorted(
        p
        for p in ASSETS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not image_files:
        raise FileNotFoundError(
            f"No image files found in {ASSETS_DIR}.\n"
            f"Supported extensions: {', '.join(sorted(IMAGE_EXTENSIONS))}\n"
            f"See assets/README.md for naming conventions."
        )

    logger.info(
        "Found %d image(s) in /assets: %s",
        len(image_files),
        ", ".join(p.name for p in image_files),
    )

    uploaded: dict[str, str] = {}

    for asset_path in image_files:
        role_name = asset_path.stem  # e.g. "outfit_reference"
        logger.info("  ⬆  Uploading %s …", asset_path.name)

        try:
            cdn_url: str = fal_client.upload_file(str(asset_path))
        except Exception as exc:
            raise RuntimeError(
                f"fal_client.upload_file() failed for {asset_path}: {exc}"
            ) from exc

        uploaded[role_name] = cdn_url
        logger.info("  ✔  %s → %s", role_name, cdn_url)

    logger.info(
        "All %d asset(s) uploaded to fal CDN successfully.", len(uploaded)
    )
    return uploaded


# ─────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────
def main() -> None:
    """Load env → validate → upload assets → build crew → run pipeline."""

    # 1. Load .env from project root
    env_path = PROJECT_ROOT / ".env"
    load_dotenv(dotenv_path=env_path)
    logger.info("Environment loaded from %s", env_path)

    # 2. Validate
    _validate_env()

    # 3. Upload ALL images from /assets to fal CDN
    reference_urls = _upload_all_assets()

    # Print upload manifest
    print("\n📦  Uploaded Assets:")
    print("─" * 56)
    for role, url in reference_urls.items():
        print(f"  {role:<28s} → {url}")
    print("─" * 56)
    print()

    # 4. Import crew builder *after* env is loaded (tools read env at
    #    import time for default model endpoints).
    from crew import build_crew  # noqa: E402

    crew = build_crew(reference_urls=reference_urls)

    # 5. Kick off
    logger.info("=" * 60)
    logger.info("  🚀  KICKING OFF VIDEO GENERATION PIPELINE")
    logger.info("=" * 60)

    result = crew.kickoff()

    logger.info("=" * 60)
    logger.info("  ✅  PIPELINE COMPLETE")
    logger.info("=" * 60)

    final_output = str(result)
    print("\n🎬  Final Video URL:\n")
    print(f"    {final_output}\n")


if __name__ == "__main__":
    main()
