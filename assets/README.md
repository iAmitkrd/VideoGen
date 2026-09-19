# Assets — Reference Image Guide

This folder holds **local reference images** that the pipeline uploads to
[fal.ai's CDN](https://fal.ai) at runtime via `fal_client.upload_file()`.
Every image file found here is automatically discovered, uploaded, and made
available to the AI agents as a hosted URL.

---

## Quick Start

```bash
# Drop your images here
cp ~/photos/my_dress.jpg      assets/outfit_reference.jpg
cp ~/photos/model_pose.jpg    assets/pose_reference.jpg

# Run the pipeline — all images are auto-uploaded
python main.py
```

---

## How It Works

1. `main.py` scans this folder for **all** image files on startup.
2. Each file is uploaded to fal.ai's temporary CDN.
3. The **filename stem** (filename without extension) becomes the
   **role name** that agents see in their task description.
4. Agent 1 (Visual Concept Director) receives a manifest of every
   uploaded image and selects the most appropriate one for the scene.

### Example Manifest (what the agent sees)

```
AVAILABLE REFERENCE IMAGES (3 total):
  1. outfit_reference          → https://fal.media/files/abc123...
  2. pose_reference            → https://fal.media/files/def456...
  3. background_reference      → https://fal.media/files/ghi789...
```

---

## Naming Conventions

The filename (without extension) is the **role name**. Use descriptive,
underscore-separated names so the AI agent understands each image's purpose.

### Recommended Names

| Filename                        | Role Name              | Purpose                                        |
|---------------------------------|------------------------|-------------------------------------------------|
| `outfit_reference.jpg`          | `outfit_reference`     | The primary garment / outfit to preserve        |
| `pose_reference.jpg`            | `pose_reference`       | A body pose the model should approximate        |
| `background_reference.jpg`      | `background_reference` | A scene / environment to use as backdrop        |
| `style_reference.png`           | `style_reference`      | An artistic style or mood board image           |
| `face_reference.jpg`            | `face_reference`       | A face / identity to maintain likeness          |
| `color_palette_reference.png`   | `color_palette_reference` | A colour palette swatch to match             |
| `texture_reference.jpg`         | `texture_reference`    | A fabric or material texture to replicate       |
| `accessory_reference.jpg`       | `accessory_reference`  | A specific accessory (bag, shoes, jewellery)    |

### Naming Rules

- **Use underscores** `_` to separate words (not hyphens or spaces).
- **End with `_reference`** so the agent clearly knows it's a conditioning input.
- **Be specific** — `evening_dress_reference.jpg` is better than `image1.jpg`.
- **Avoid generic names** like `test.jpg`, `photo.png`, `IMG_0001.jpg`.

---

## Supported File Formats

| Extension       | Format           |
|-----------------|------------------|
| `.jpg` `.jpeg`  | JPEG             |
| `.png`          | PNG              |
| `.webp`         | WebP             |
| `.bmp`          | Bitmap           |
| `.tiff` `.tif`  | TIFF             |

> **Tip:** JPEG and PNG are recommended for best compatibility with fal.ai
> models. Keep images under 10 MB for fastest upload.

---

## Single vs. Multiple Images

### Single Image (simplest)

```
assets/
└── outfit_reference.jpg
```

The agent receives one reference and uses it directly — no selection needed.

### Multiple Images (recommended for complex scenes)

```
assets/
├── outfit_reference.jpg
├── pose_reference.jpg
├── background_reference.jpg
└── style_reference.png
```

The agent receives a manifest of all four images and intelligently selects
the most relevant one for the `fal_conditioned_image` tool call. To influence
which image gets used, be specific in `prompts/image_generation.txt` — for
example, mentioning "the reference outfit" will bias the agent toward
`outfit_reference`.

---

## Image Quality Tips

- **Resolution:** At least 1024×1024 for best conditioning results.
- **Clarity:** Use sharp, well-lit photos — avoid blurry or noisy images.
- **Background:** Plain backgrounds work best for outfit / accessory references.
- **Cropping:** Crop to the subject — remove unnecessary whitespace or clutter.
- **Consistency:** If using multiple references, keep lighting and colour
  temperature consistent for a more cohesive output.

---

## Files to Ignore

The pipeline skips non-image files automatically. These are safe to keep here:

- `README.md` (this file)
- `.gitkeep`
- `.DS_Store`
- Any file without a supported image extension
