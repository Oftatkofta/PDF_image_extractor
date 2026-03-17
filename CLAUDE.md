# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A PDF extraction and processing toolkit focused on extracting images, text, fonts, and vectors from PDFs. It also includes tools for building Foundry VTT game modules from extracted content.

## Running the Tools

All scripts are standalone Python files — no build step required.

```bash
# Primary extractor — images, text, fonts, vectors
python PDF_image_extractor.py --input <file.pdf> --output <dir> [options]

# Extract everything with chapter organization
python PDF_image_extractor.py --input ac_goetia.pdf --output ars_goetia -t --extract-fonts --organize-by-chapter

# Extract specific pages
python PDF_image_extractor.py --input file.pdf --pages "1,3-5,7" --output out/

# Show table of contents
python PDF_image_extractor.py --input file.pdf --show-toc

# Build Foundry VTT module from extracted content
python build_foundry_module.py

# Merge facing page backgrounds
python merge_facing_pages.py

# Render pages without text layer
python merge_page_images.py

# Convert images to JPEG
python mass_converter.py

# Extract font glyphs to SVG
python glyph_extractor.py
```

## Key CLI Options for PDF_image_extractor.py

| Flag | Description |
|---|---|
| `-i`/`--input` | PDF file (required) |
| `-o`/`--output` | Output directory |
| `-f`/`--format` | Image format (png/jpeg) |
| `-t`/`--extract-text` | Extract text to Markdown |
| `--extract-fonts` | Extract embedded fonts |
| `--extract-vectors` | Extract vector graphics as SVG |
| `--no-images` | Skip image extraction |
| `--organize-by-chapter` | Group output by chapter |
| `--hash-mode` | Duplicate detection: `exact` (MD5) or `perceptual` |
| `--hash-threshold` | Perceptual hash threshold 0–64 (default: 5) |
| `-s`/`-e` | Start/end page (1-based) |
| `-p`/`--pages` | Page ranges, e.g. `"1,3-5,7"` |

## Dependencies

```bash
pip install pymupdf pillow svgwrite imagehash fonttools
```

- `fitz` (PyMuPDF) — core PDF processing
- `PIL` (Pillow) — image manipulation and CMYK→RGB conversion
- `imagehash` — perceptual duplicate detection (optional)
- `svgwrite` — SVG vector output
- `fontTools` — font glyph extraction (`glyph_extractor.py` only)

## Architecture

### Extraction Pipeline (`PDF_image_extractor.py`)

**Images:** `page.get_images()` → hash dedup (MD5 or perceptual) → dimension filter → CMYK→RGB conversion → save

**Text:** `pdf_file.get_toc()` builds page→chapter map → `page.get_text("dict")` with font flags → Markdown with bold/italic → numbered `NN_ChapterName_text.md` files

**Fonts:** `page.get_fonts()` → raw PDF xref → FontDescriptor → `/FontFile`, `/FontFile2`, `/FontFile3` → `.pfb`/`.ttf`/`.otf`

**Vectors:** `page.get_svg_image(text_as_path=True)` with fallback to manual SVG path construction

### Foundry VTT Module Builder (`build_foundry_module.py`)

Reads from `sweetness/` directory, produces `foundry-module/delta-green-sweetness/`:
1. Scans images → copies to `assets/` → generates `scene-list.json`
2. Parses `actors.txt` (NPC stat blocks) → `sweetness-npcs.json`
3. Emits `module.json`, `init.js` (with scene/NPC data embedded for offline use)
4. Creates `delta-green-sweetness-forge.zip` for Forge platform deployment

### NPC stat block format (`actors.txt`)

```
Name
STR 12 CON 7 DEX 14 INT 11 POW 10 CHA 8
HP 10 WP 9 SAN 0

SKILLS: ...
ATTACKS: ...
```
