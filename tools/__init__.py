"""
fal.ai Custom Tool Definitions for CrewAI
==========================================

Implements two BaseTool subclasses wrapping fal-client SDK calls:

  • FalConditionedImageTool  – image-conditioned generation via
    fal-ai/flux/dev/image-to-image (accepts prompt + reference image URL)
  • FalImageToVideoTool      – image-to-video via fal-ai/wan-i2v

Each tool enforces a strict Pydantic ``args_schema`` so the LLM agent
always provides correctly typed parameters.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Type

import fal_client
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Default model endpoints (overridable via env) ────────────────────
DEFAULT_CONDITIONED_MODEL: str = os.getenv(
    "FAL_CONDITIONED_MODEL", "fal-ai/flux/dev/image-to-image"
)
DEFAULT_I2V_MODEL: str = os.getenv(
    "FAL_I2V_MODEL", "fal-ai/wan-i2v"
)

# ── Global timeout for fal_client.subscribe (seconds) ────────────────
FAL_TIMEOUT: int = int(os.getenv("FAL_TIMEOUT", "300"))


# =====================================================================
#  Tool 1 — Conditioned (Reference) Image Generation
# =====================================================================
class ConditionedImageInput(BaseModel):
    """Strict input schema for FalConditionedImageTool."""

    prompt: str = Field(
        ...,
        description=(
            "Detailed text description of the target image to generate. "
            "Include scene, lighting, composition, and quality directives."
        ),
    )
    reference_image_url: str = Field(
        ...,
        description=(
            "Publicly accessible URL of the reference / conditioning image "
            "(e.g. an outfit photo uploaded to fal.ai CDN)."
        ),
    )
    strength: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description=(
            "Controls how much the output diverges from the reference image. "
            "0.0 = nearly identical to reference, 1.0 = maximum creative freedom. "
            "Recommended range: 0.65 – 0.85."
        ),
    )
    image_size: str = Field(
        default="landscape_16_9",
        description=(
            "Output image dimensions. Common values: 'landscape_16_9', "
            "'portrait_9_16', 'square_hd', 'square'."
        ),
    )


class FalConditionedImageTool(BaseTool):
    """
    Generate a high-resolution image that is *conditioned* on a reference
    image (e.g. preserving an outfit or subject) using fal.ai's
    image-to-image Flux endpoint.

    Returns the hosted image URL on success, or an error message string
    on failure.
    """

    name: str = "fal_conditioned_image"
    description: str = (
        "Generate a new image conditioned on a reference image and a text "
        "prompt using fal.ai's Flux image-to-image model. The reference "
        "image guides style / subject fidelity while the prompt controls "
        "the scene. Returns the hosted image URL."
    )
    args_schema: Type[BaseModel] = ConditionedImageInput

    def _run(
        self,
        prompt: str,
        reference_image_url: str,
        strength: float = 0.75,
        image_size: str = "landscape_16_9",
    ) -> str:
        model_id = DEFAULT_CONDITIONED_MODEL
        logger.info(
            "▶ fal Conditioned-Image  model=%s  strength=%.2f  "
            "ref=%.60s…  prompt=%.80s…",
            model_id,
            strength,
            reference_image_url,
            prompt,
        )

        try:
            result: dict[str, Any] = fal_client.subscribe(
                model_id,
                arguments={
                    "prompt": prompt,
                    "image_url": reference_image_url,
                    "strength": strength,
                    "image_size": image_size,
                    "num_inference_steps": 28,
                },
                with_logs=True,
                timeout=FAL_TIMEOUT,
            )
        except Exception as exc:
            error_msg = f"fal Conditioned-Image call failed: {exc}"
            logger.exception(error_msg)
            return error_msg

        # ── Extract image URL from response ──────────────────────────
        try:
            image_url: str = result["images"][0]["url"]
        except (KeyError, IndexError, TypeError) as exc:
            error_msg = (
                f"Unexpected conditioned-image response structure: {exc}. "
                f"Raw keys: {list(result.keys()) if isinstance(result, dict) else type(result)}"
            )
            logger.error(error_msg)
            return error_msg

        logger.info("✔ Conditioned image generated: %s", image_url)
        return image_url


# =====================================================================
#  Tool 2 — Image-to-Video
# =====================================================================
class ImageToVideoInput(BaseModel):
    """Strict input schema for FalImageToVideoTool."""

    image_url: str = Field(
        ...,
        description="Publicly accessible URL of the source image to animate.",
    )
    prompt: str = Field(
        ...,
        description=(
            "Motion directive prompt describing camera movement, "
            "subject animation, particle effects, and pacing."
        ),
    )
    duration: str = Field(
        default="5",
        description="Video duration in seconds. Typical values: '5' or '10'.",
    )
    aspect_ratio: str = Field(
        default="16:9",
        description="Aspect ratio for the generated video (e.g. '16:9', '9:16').",
    )


class FalImageToVideoTool(BaseTool):
    """
    Transform a static image into a short cinematic video clip using
    fal.ai's Wan-I2V model.

    Returns the hosted MP4 URL on success, or an error message string
    on failure.
    """

    name: str = "fal_image_to_video"
    description: str = (
        "Convert a source image into a short cinematic video clip using "
        "fal.ai's image-to-video model (Wan-I2V). Requires an image URL "
        "and a motion directive prompt. Returns the hosted MP4 URL."
    )
    args_schema: Type[BaseModel] = ImageToVideoInput

    def _run(
        self,
        image_url: str,
        prompt: str,
        duration: str = "5",
        aspect_ratio: str = "16:9",
    ) -> str:
        model_id = DEFAULT_I2V_MODEL
        logger.info(
            "▶ fal I2V  model=%s  image=%.60s…  prompt=%.80s…",
            model_id,
            image_url,
            prompt,
        )

        try:
            result: dict[str, Any] = fal_client.subscribe(
                model_id,
                arguments={
                    "image_url": image_url,
                    "prompt": prompt,
                    "duration": duration,
                    "aspect_ratio": aspect_ratio,
                },
                with_logs=True,
                timeout=FAL_TIMEOUT,
            )
        except Exception as exc:
            error_msg = f"fal I2V call failed: {exc}"
            logger.exception(error_msg)
            return error_msg

        # ── Extract video URL (resilient across fal model variants) ──
        video_url: str | None = None
        try:
            if "video" in result:
                video_url = result["video"]["url"]
            elif "data" in result and "video" in result.get("data", {}):
                video_url = result["data"]["video"]["url"]
            elif "output" in result:
                video_url = result["output"]["url"]
        except (KeyError, TypeError):
            pass

        if not video_url:
            error_msg = (
                f"Could not extract video URL from I2V response. "
                f"Raw keys: {list(result.keys()) if isinstance(result, dict) else type(result)}"
            )
            logger.error(error_msg)
            return error_msg

        logger.info("✔ Video generated: %s", video_url)
        return video_url
