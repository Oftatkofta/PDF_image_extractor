import os
import re
import sys
import svgwrite
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

class SVGPathPen(BasePen):
    def __init__(self, glyphSet):
        super().__init__(glyphSet)
        self.path_commands = []

    def _moveTo(self, p):
        # Move current point
        self.path_commands.append(f"M {p[0]} {-p[1]}")

    def _lineTo(self, p):
        # Draw a line to point
        self.path_commands.append(f"L {p[0]} {-p[1]}")

    def _curveToOne(self, p1, p2, p3):
        # Draw a cubic Bézier curve
        self.path_commands.append(
            f"C {p1[0]} {-p1[1]}, {p2[0]} {-p2[1]}, {p3[0]} {-p3[1]}"
        )

    def _closePath(self):
        self.path_commands.append("Z")


def glyph_to_svg_path(glyph, glyphSet):
    pen = SVGPathPen(glyphSet)
    glyph.draw(pen)
    # Combine all commands into an SVG path string
    return " ".join(pen.path_commands)


def save_glyph_as_svg(char, path_data, out_dir):
    # Replace illegal filename characters
    safe_char = re.sub(r"[\\/*?:\"<>|]", "_", char)
    if not safe_char.strip():
        # Fallback if char is empty or invalid
        safe_char = f"u{ord(char):04X}"

    filename = f"{safe_char}.svg"
    file_path = os.path.join(out_dir, filename)

    dwg = svgwrite.Drawing(file_path, profile='tiny')

    # Typically, TTF coordinates have y increasing upwards, while SVG has y increasing downwards.
    # Above, we negated y-coordinates in _moveTo/_lineTo/etc. so that glyphs render in positive SVG space.
    dwg.add(dwg.path(d=path_data, fill="black", stroke="none"))
    dwg.save()
    print(f"Saved glyph '{char}' to {file_path}")


def main(ttf_path, out_dir="svgs"):
    # Create output directory if needed
    os.makedirs(out_dir, exist_ok=True)

    # Load the font
    font = TTFont(ttf_path)
    glyphSet = font.getGlyphSet()

    # Use the best cmap to get a mapping of Unicode codepoints -> glyph names
    cmap = font['cmap'].getBestCmap()

    # Invert the mapping to easily find codepoints by glyph name
    glyph_to_codepoint = {}
    for codepoint, gname in cmap.items():
        glyph_to_codepoint[gname] = codepoint

    # Iterate over all glyphs in the font
    for glyph_name in glyphSet.keys():
        if glyph_name in glyph_to_codepoint:
            codepoint = glyph_to_codepoint[glyph_name]
            char = chr(codepoint)
            glyph = glyphSet[glyph_name]

            # Skip empty or composite glyphs
            if glyph.numberOfContours <= 0:
                continue

            path_data = glyph_to_svg_path(glyph, glyphSet)
            if not path_data.strip():
                continue

            save_glyph_as_svg(char, path_data, out_dir)


    print("\nExtraction complete.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_glyphs.py /path/to/font.ttf [output_folder]")
        sys.exit(1)

    ttf_file = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else "svgs"
    main(ttf_file, output_folder)