# VideoGen

AI-powered video generation pipeline that uses reference images, CrewAI agents, OpenRouter LLMs, and fal.ai to create cinematic video clips from a prompt.

## Overview

This project automates a two-step creative workflow:

1. Uploads all image assets from the `assets/` directory to fal.ai CDN.
2. Uses a sequential CrewAI pipeline to:
   - select the most relevant reference image,
   - generate a stylized image based on the prompt,
   - create a motion video from that image.

## Features

- Uploads all supported image files in `assets/`
- Maps each uploaded image to a role name based on its filename
- Uses multiple AI agents for image generation and motion design
- Reads prompt text from files in the `prompts/` directory
- Generates a final hosted MP4 video URL

## Project Structure

```text
VideoGen/
├── assets/                  # Reference images for generation
├── prompts/                 # Prompt files for image and motion generation
│   ├── image_generation.txt
│   └── video_motion.txt
├── tools/                   # fal.ai generation tools
│   ├── __init__.py
│   └── fal_tools.py
├── crew.py                  # CrewAI agent and task setup
├── main.py                  # Entry point for the pipeline
├── requirements.txt         # Python dependencies
├── .env                     # Local environment variables (not committed)
└── README.md                # Project documentation
```

## Requirements

- Python 3.10+
- API keys for:
  - `FAL_KEY`
  - `OPENROUTER_API_KEY`

## Setup

1. Create and activate a virtual environment (optional but recommended):

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root:

```env
FAL_KEY=your_fal_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

4. Add your reference images in the `assets/` folder.

5. Run the project:

```bash
python main.py
```

## How It Works

- `main.py` loads environment variables and validates them.
- It scans `assets/` for supported image files and uploads each one to fal.ai.
- `crew.py` builds a CrewAI workflow with:
  - a visual concept director,
  - a motion choreographer.
- The pipeline produces a final video URL from the generated result.

## Notes

- Supported image formats include JPG, JPEG, PNG, WEBP, BMP, TIFF, and TIF.
- The project expects the reference images to be placed directly under `assets/`.
- Prompt content is stored in `prompts/` and loaded at runtime.

## License

This project is for educational and personal use.
