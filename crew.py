"""
Crew Definition — AI Video Generation Pipeline (v2)
Crew Definition — AI Video Generation Pipeline (v3)
=====================================================

Wires Agents, Tasks, and Crew using ``Process.sequential``.

LLM: meta-llama/llama-3.3-70b-instruct:free via OpenRouter.

Agent 1 (Visual Concept Director)
  → receives uploaded reference-image URL + external image prompt
  → receives a manifest of ALL uploaded reference-image URLs
  → selects the most relevant reference for the scene
  → invokes FalConditionedImageTool (image-to-image)
  → outputs stylised image URL

Agent 2 (Motion Choreographer)
  → receives image URL from Agent 1 via task context
  → reads external motion prompt
  → invokes FalImageToVideoTool
  → outputs MP4 video URL
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from crewai import Agent, Crew, LLM, Process, Task

from tools.fal_tools import FalConditionedImageTool, FalImageToVideoTool

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"


# ── Prompt loader ────────────────────────────────────────────────────
def _load_prompt(filename: str) -> str:
    """Read and return the contents of a prompt file from ``/prompts``."""
    path = PROMPTS_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(
            f"Prompt file not found: {path}. "
            f"Create it or check the /prompts directory."
        )
    text = path.read_text(encoding="utf-8").strip()
    logger.info("Loaded prompt from %s (%d chars)", path.name, len(text))
    return text


# ── LLM configuration (OpenRouter free tier) ─────────────────────────
def _build_llm() -> LLM:
    """
    Construct a CrewAI ``LLM`` instance configured for the OpenRouter
    free tier.  All values can be overridden via environment variables.
    """
    model = os.getenv(
        "OPENROUTER_MODEL",
        "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    )
    base_url = os.getenv(
        "OPENROUTER_BASE_URL",
        "https://openrouter.ai/api/v1",
    )
    api_key = os.getenv("OPENROUTER_API_KEY", "")

    llm = LLM(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=0.4,
    )
    logger.info(
        "LLM configured: model=%s  base_url=%s",
        model,
        base_url,
    )
    return llm


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────
def build_crew(reference_image_url: str) -> Crew:
def _format_reference_manifest(reference_urls: dict[str, str]) -> str:
    """
    Build a human-readable manifest block listing every uploaded
    reference image so the LLM agent can pick the right one.

    Example output::

        AVAILABLE REFERENCE IMAGES (3 total):
          1. outfit_reference      → https://fal.media/files/abc123
          2. pose_reference         → https://fal.media/files/def456
          3. background_reference   → https://fal.media/files/ghi789
    """
    lines = [f"AVAILABLE REFERENCE IMAGES ({len(reference_urls)} total):"]
    for idx, (role, url) in enumerate(reference_urls.items(), start=1):
        lines.append(f"  {idx}. {role:<26s} → {url}")
    return "\n".join(lines)


def build_crew(reference_urls: dict[str, str]) -> Crew:
    """
    Construct and return the ready-to-kickoff Crew.

    Parameters
    ----------
    reference_image_url:
        Publicly accessible (fal CDN) URL of the reference image that
        was uploaded from ``/assets`` by ``main.py``.
    reference_urls:
        Mapping of ``{role_name: cdn_url}`` for every image that was
        uploaded from ``/assets`` by ``main.py``.  Role names are the
        filename stems (e.g. ``"outfit_reference"``).
    """

    # Load external prompts
    image_prompt = _load_prompt("image_generation.txt")
    motion_prompt = _load_prompt("video_motion.txt")

    # Format the reference-image manifest for agents
    ref_manifest = _format_reference_manifest(reference_urls)

    # Instantiate tools
    conditioned_tool = FalConditionedImageTool()
    i2v_tool = FalImageToVideoTool()

    # Build LLM
    llm = _build_llm()

    # ── Agent 1: Visual Concept Director ─────────────────────────────
    visual_director = Agent(
        role="Visual Concept Director",
        goal=(
            "Generate a single high-resolution image that stylises the "
            "reference outfit into the scene described by the image prompt, "
            "preserving the outfit's design fidelity."
            "Generate a single high-resolution image that incorporates "
            "the provided reference images into the scene described by "
            "the image prompt, preserving the reference subjects' fidelity."
        ),
        backstory=(
            "You are an elite fashion photographer and creative director "
            "with 20 years of experience in editorial concept art.  "
            "You translate written scene descriptions into photorealistic "
            "imagery while faithfully preserving a reference garment's "
            "imagery while faithfully preserving reference subjects' "
            "style, colour palette, and silhouette using AI image-"
            "conditioning tools."
            "conditioning tools.  When multiple reference images are "
            "available you select the most relevant one for the scene."
        ),
        tools=[conditioned_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    # ── Agent 2: Motion Choreographer ────────────────────────────────
    motion_choreographer = Agent(
        role="Motion Choreographer",
        goal=(
            "Transform the generated image into a cinematic video clip "
            "with compelling camera movement and natural animation."
        ),
        backstory=(
            "You are a motion-design specialist and cinematographer who "
            "breathes life into still images.  You craft smooth camera "
            "moves, realistic fabric flow, and dramatic pacing using "
            "AI video generation tools."
        ),
        tools=[i2v_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    # ── Task 1: Generate conditioned image ───────────────────────────
    task_generate_image = Task(
        description=(
            "Using the fal_conditioned_image tool, generate an image that "
            "places the reference outfit into the scene described below.\n\n"
            f"REFERENCE IMAGE URL:\n{reference_image_url}\n\n"
            "places the reference subject into the scene described below.\n\n"
            f"{ref_manifest}\n\n"
            "Choose the most appropriate reference image for the scene "
            "and pass its URL as the 'reference_image_url' argument.\n\n"
            f"--- IMAGE PROMPT START ---\n{image_prompt}\n--- IMAGE PROMPT END ---\n\n"
            "Pass the reference image URL as the 'reference_image_url' "
            "Pass the chosen reference image URL as the 'reference_image_url' "
            "argument and the image prompt text as the 'prompt' argument.\n\n"
            "Return ONLY the resulting hosted image URL, nothing else."
        ),
        expected_output=(
            "A single HTTPS URL pointing to the generated image "
            "(e.g. https://fal.media/files/...)."
        ),
        agent=visual_director,
    )

    # ── Task 2: Generate video ───────────────────────────────────────
    task_generate_video = Task(
        description=(
            "Using the fal_image_to_video tool, convert the image from the "
            "previous task into a cinematic video clip.\n\n"
            "Use the image URL from the prior task's output as the "
            "'image_url' argument and the motion prompt below as the "
            "'prompt' argument.\n\n"
            f"--- MOTION PROMPT START ---\n{motion_prompt}\n--- MOTION PROMPT END ---\n\n"
            "Return ONLY the resulting hosted MP4 video URL, nothing else."
        ),
        expected_output=(
            "A single HTTPS URL pointing to the generated MP4 video "
            "(e.g. https://fal.media/files/...)."
        ),
        agent=motion_choreographer,
        context=[task_generate_image],
    )

    # ── Crew ─────────────────────────────────────────────────────────
    crew = Crew(
        agents=[visual_director, motion_choreographer],
        tasks=[task_generate_image, task_generate_video],
        process=Process.sequential,
        verbose=True,
    )

    logger.info(
        "Crew built: 2 agents, 2 tasks, Process.sequential  "
        "ref_image=%s",
        reference_image_url[:80],
        "reference_images=%d",
        len(reference_urls),
    )
    return crew
