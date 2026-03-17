"""
Render the first page of a PDF as a full-page image (e.g. cover).
Extract all images from the cover and/or render the cover without text.
"""
import argparse
import io
from pathlib import Path

import fitz
from PIL import Image


def _rect_sort_key(page, xref):
    """Return (y0, x0) for sorting images top-to-bottom, left-to-right. Uses 0,0 if rect unavailable."""
    try:
        rects = page.get_image_rects(xref, transform=True)
        if rects:
            r = rects[0]
            for attempt in [(getattr(r, "x0", None), getattr(r, "y0", None)), (r[0], r[1]) if hasattr(r, "__getitem__") else (None, None)]:
                if attempt[0] is not None and attempt[1] is not None:
                    try:
                        return (float(attempt[1]), float(attempt[0]))
                    except (TypeError, ValueError):
                        continue
    except Exception:
        pass
    return (0.0, 0.0)


def extract_cover_images(pdf_path: str, output_dir: str, page_index: int = 0) -> int:
    """Extract every image from the given page (e.g. cover) into output_dir with traceable names.
    Names: cover_NN_WxH_xX_yY.ext — index (reading order), dimensions, position when available.
    Example: cover_01_2520x1620_x72_y72.jpeg
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with fitz.open(pdf_path) as doc:
        if page_index >= len(doc):
            raise ValueError(f"Page {page_index + 1} does not exist (PDF has {len(doc)} pages)")
        page = doc[page_index]
        image_list = page.get_images(full=True)
        items = []
        for img in image_list:
            try:
                xref = img[0]
                base = doc.extract_image(xref)
                image_bytes = base["image"]
                ext = base.get("ext", "png").lower()
                if ext == "jpg":
                    ext = "jpeg"
                pil = Image.open(io.BytesIO(image_bytes))
                if pil.mode == "CMYK":
                    pil = pil.convert("RGB")
                y0, x0 = _rect_sort_key(page, xref)
                items.append((xref, int(round(x0)), int(round(y0)), base, pil, ext))
            except Exception as e:
                print(f"[!] Skipping image xref {img[0]}: {e}")
        items.sort(key=lambda t: (t[2], t[1]))  # (y0, x0) reading order
        count = 0
        for i, (_xref, x0, y0, base, pil, ext) in enumerate(items, start=1):
            try:
                w, h = pil.width, pil.height
                name = f"cover_{i:02d}_{w}x{h}_x{x0}_y{y0}.{ext}"
                out_path = output_dir / name
                if ext == "jpeg":
                    pil.save(out_path, "JPEG", quality=95)
                else:
                    pil.save(out_path, "PNG")
                print(f"[+] {out_path.name}")
                count += 1
            except Exception as e:
                print(f"[!] Failed to save image {i}: {e}")
    return count


def render_cover_no_text(pdf_path: str, output_path: str, page_index: int = 0, zoom: float = 2.0) -> None:
    """Render the page without the text layer (graphics and images only)."""
    from merge_page_images import get_page_without_text

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(pdf_path) as doc:
        if page_index >= len(doc):
            raise ValueError(f"Page {page_index + 1} does not exist (PDF has {len(doc)} pages)")
        page = doc[page_index]
        img = get_page_without_text(page, zoom=zoom)
        img.save(output_path, "PNG")
    print(f"[+] Saved cover (no text): {output_path}")


def render_cover(pdf_path: str, output_path: str, zoom: float = 2.0, page_index: int = 0) -> None:
    """Render a single PDF page to an image file."""
    pdf_path = Path(pdf_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(pdf_path) as doc:
        if page_index >= len(doc):
            raise ValueError(f"Page {page_index + 1} does not exist (PDF has {len(doc)} pages)")
        page = doc[page_index]
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        ext = output_path.suffix.lower() or ".png"
        if ext == ".jpg" or ext == ".jpeg":
            pix.save(str(output_path), "jpeg", quality=95)
        else:
            pix.save(str(output_path), "png")
    print(f"[+] Saved cover: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Render PDF cover (first page), extract cover images, and/or render cover without text."
    )
    parser.add_argument("-i", "--input", required=True, help="Input PDF file")
    parser.add_argument("-o", "--output", help="Full cover image path (e.g. folder/Cover.png)")
    parser.add_argument(
        "--extract-images-to",
        metavar="DIR",
        help="Extract all images from the cover page into this directory (e.g. sweetness/cover_images)",
    )
    parser.add_argument(
        "--no-text",
        metavar="PATH",
        help="Render cover without text layer (graphics only) to this path (e.g. sweetness/Sweetness_cover_no_text.png)",
    )
    parser.add_argument("-z", "--zoom", type=float, default=2.0, help="Resolution zoom (default: 2.0)")
    parser.add_argument("-p", "--page", type=int, default=1, help="Page number (default: 1)")
    args = parser.parse_args()
    page_index = args.page - 1

    if args.extract_images_to:
        n = extract_cover_images(args.input, args.extract_images_to, page_index=page_index)
        print(f"[+] Extracted {n} images from cover to {args.extract_images_to}")
    if args.no_text:
        render_cover_no_text(args.input, args.no_text, page_index=page_index, zoom=args.zoom)
    if args.output:
        render_cover(args.input, args.output, args.zoom, page_index=page_index)
