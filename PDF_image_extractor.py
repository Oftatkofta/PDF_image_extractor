import os
import fitz  # PyMuPDF
import io
from PIL import Image
import argparse
from pathlib import Path
import hashlib
import svgwrite
import json
from datetime import datetime
import unicodedata

print(f"[*] Using PyMuPDF version: {fitz.__version__}")

def get_image_hash(image_bytes, mode='exact', threshold=5):
    """
    Generate a hash of the image data
    
    Args:
        image_bytes: Raw image data
        mode: 'exact' for MD5 hash or 'perceptual' for similarity-based hash
        threshold: Difference threshold for perceptual hashing (0-64)
    
    Returns:
        For exact mode: hash string
        For perceptual mode: (hash object, threshold)
    """
    if mode == 'exact':
        return hashlib.md5(image_bytes).hexdigest()
    else:
        # Try to import imagehash only when perceptual mode is requested
        try:
            import imagehash
        except ImportError:
            print("[!] Perceptual hashing requires additional packages. Install with:")
            print("    pip install imagehash")
            print("[!] Falling back to exact hashing")
            return hashlib.md5(image_bytes).hexdigest()
        
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Calculate perceptual hash
            return (imagehash.average_hash(image), threshold)
        except Exception as e:
            print(f"[!] Error calculating perceptual hash: {e}")
            print("[!] Falling back to exact hashing")
            return hashlib.md5(image_bytes).hexdigest()

def is_duplicate(hash_value, seen_hashes, mode='exact'):
    """
    Check if an image hash indicates a duplicate
    
    Args:
        hash_value: Hash from get_image_hash
        seen_hashes: Set of previously seen hashes
        mode: 'exact' or 'perceptual'
    
    Returns:
        bool: True if duplicate detected
    """
    if mode == 'exact':
        return hash_value in seen_hashes
    else:
        img_hash, threshold = hash_value
        # For perceptual hashing, check if any existing hash is similar enough
        for seen_hash in seen_hashes:
            if (img_hash - seen_hash[0]) <= threshold:
                return True
        return False

def add_to_seen(hash_value, seen_hashes):
    """Add hash to seen set, handling both exact and perceptual modes"""
    if isinstance(hash_value, str):  # exact mode
        seen_hashes.add(hash_value)
    else:  # perceptual mode
        seen_hashes.add(hash_value)

def main():
    parser = argparse.ArgumentParser(description='Extract images and vector graphics from PDF files')
    parser.add_argument('--input', '-i', required=True, help='Input PDF file path')
    parser.add_argument('--output', '-o', default='extracted_content', help='Output directory for extracted content')
    parser.add_argument('--format', '-f', default='png', help='Output image format (e.g., png, jpg)')
    parser.add_argument('--min-width', '-w', type=int, default=100, help='Minimum image width')
    parser.add_argument('--min-height', '-mh', type=int, default=100, help='Minimum image height')
    parser.add_argument('--extract-text', '-t', action='store_true', help='Extract formatted text to HTML')
    parser.add_argument('--extract-vectors', '-ev', action='store_true', help='Extract vector graphics')
    parser.add_argument('--extract-fonts', '-ef', action='store_true', help='Extract embedded fonts')
    parser.add_argument('--no-images', action='store_true', help='Skip image extraction')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug output')
    parser.add_argument('--start-page', '-s', type=int, help='Starting page number (1-based)')
    parser.add_argument('--end-page', '-e', type=int, help='Ending page number (1-based)')
    parser.add_argument('--pages', '-p', help='Comma-separated list of page numbers or ranges (e.g., "1,3-5,7")')
    parser.add_argument('--show-toc', action='store_true', help='Display the table of contents')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output about saved files')
    parser.add_argument('--organize-by-chapter', '-c', action='store_true', 
                       help='Organize extracted content into chapter-based subfolders')
    parser.add_argument('--hash-mode', choices=['exact', 'perceptual'], default='exact',
                       help='Image duplicate detection mode: exact (default) or perceptual')
    parser.add_argument('--hash-threshold', type=int, default=5,
                       help='Threshold for perceptual hash difference (0-64, default: 5, only used with perceptual mode)')
    
    args = parser.parse_args()

    # Add TOC display before processing
    if args.show_toc:
        try:
            toc = extract_toc(args.input)
            if isinstance(toc, str):
                print(toc)
            else:
                print("\nTable of Contents:")
                print("=================")
                for item in toc:
                    indent = "  " * item['depth']
                    print(f"{indent}{item['title']} - Page {item['page']}")
                print("\n")
        except Exception as e:
            print(f"[!] Error extracting table of contents: {e}")
    
    # Create base output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with fitz.open(args.input) as pdf_file:
            total_pages = len(pdf_file)
            
            # Calculate page range
            pages_to_process = None
            
            if args.pages:
                # Parse comma-separated list of pages and ranges
                pages_to_process = set()
                for part in args.pages.split(','):
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        pages_to_process.update(range(start - 1, min(end, total_pages)))
                    else:
                        page_num = int(part) - 1
                        if 0 <= page_num < total_pages:
                            pages_to_process.add(page_num)
                pages_to_process = sorted(pages_to_process)
            elif args.start_page or args.end_page:
                # Use start_page and end_page if provided
                start = (args.start_page - 1) if args.start_page else 0
                end = min(args.end_page or total_pages, total_pages)
                pages_to_process = list(range(max(0, start), end))
            else:
                # Process all pages if no range specified
                pages_to_process = list(range(total_pages))
            
            print(f"[*] Processing {len(pages_to_process)} pages from PDF")
            
            # Get chapter information once
            chapter_info = get_chapter_info(args.input) if args.extract_text or not args.no_images else {}
            
            # Extract text if requested
            if args.extract_text:
                extract_formatted_text(pdf_file, output_dir, pages_to_process, args.debug, 
                                    chapter_info, args.organize_by_chapter)
            
            # Extract fonts if requested
            if args.extract_fonts:
                fonts_dir = output_dir / "fonts"
                fonts_dir.mkdir(exist_ok=True)
                extract_fonts(pdf_file, fonts_dir, args.debug, pages_to_process)
            
            # Process pages for images and vectors
            if not args.no_images or args.extract_vectors:
                process_pages(pdf_file, output_dir, args, pages_to_process)
            
    except Exception as e:
        print(f"[!] Error processing PDF: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()

def process_page(pdf_file, page_index, output_dir, output_format, min_width, min_height, seen_images, hash_mode='exact', hash_threshold=5):
    page = pdf_file[page_index]
    image_list = page.get_images(full=True)
    
    if image_list:
        print(f"[*] Found {len(image_list)} images in page {page_index + 1}")
        # Create images directory only when we have images to save
        output_dir.mkdir(exist_ok=True)
    
    for image_index, img in enumerate(image_list, start=1):
        try:
            save_image(pdf_file, img, page_index, image_index, output_dir, output_format, 
                      min_width, min_height, seen_images, hash_mode, hash_threshold)
        except Exception as e:
            print(f"[!] Error processing image {image_index} on page {page_index + 1}: {e}")

def save_image(pdf_file, img, page_index, image_index, output_dir, output_format, 
               min_width, min_height, seen_images, hash_mode='exact', hash_threshold=5):
    xref = img[0]
    base_image = pdf_file.extract_image(xref)
    image_bytes = base_image["image"]
    
    # Generate hash of image data
    image_hash = get_image_hash(image_bytes, hash_mode, hash_threshold)
    
    # Skip if we've seen this image before
    if is_duplicate(image_hash, seen_images, hash_mode):
        print(f"[-] Skipping duplicate image {image_index} on page {page_index + 1}")
        return
    
    image = Image.open(io.BytesIO(image_bytes))
    
    # Convert CMYK to RGB if necessary
    if image.mode == 'CMYK':
        print(f"[*] Converting CMYK image to RGB on page {page_index + 1}, image {image_index}")
        image = image.convert('RGB')
    
    if image.width >= min_width and image.height >= min_height:
        # Use page_index + 1 for 1-based page numbers
        output_path = output_dir / f"page{page_index + 1}_image{image_index}.{output_format}"
        image.save(output_path, format=output_format.upper())
        add_to_seen(image_hash, seen_images)
    else:
        print(f"[-] Skipping image {image_index} on page {page_index + 1} "
              f"(size: {image.width}x{image.height}) - below minimum dimensions")

def clean_text(text):
    """Clean text by removing special characters and normalizing spaces"""
    # Remove soft hyphens and other special characters
    special_chars = {
        '\u00AD': '',  # soft hyphen (SHY)
        '\u200B': '',  # zero-width space
        '\u200C': '',  # zero-width non-joiner
        '\u200D': '',  # zero-width joiner
        '\u2060': '',  # word joiner
    }
    
    # Normalize unicode and replace special characters
    text = unicodedata.normalize('NFKC', text)
    for char, replacement in special_chars.items():
        text = text.replace(char, replacement)
    
    return text.strip()

def extract_formatted_text(pdf_file, output_dir, pages_to_process=None, debug=False, chapter_info=None, organize_by_chapter=False):
    """Extract formatted text from PDF pages into chapter-based Markdown documents"""
    try:
        if debug:
            print("[DEBUG] Starting text extraction...")
        
        if pages_to_process is None:
            pages_to_process = range(len(pdf_file))
        
        # Track current chapter content and info
        current_chapter = None
        current_chapter_num = None
        chapter_content = []
        
        # Process each page
        for page_num in pages_to_process:
            try:
                if debug:
                    print(f"[DEBUG] Extracting text from page {page_num + 1}")
                
                # Get chapter information for this page
                chapter_info_tuple = chapter_info.get(page_num + 1, ("Uncategorized", 0))
                chapter_title, chapter_num = chapter_info_tuple
                
                # If we've moved to a new chapter, save the previous chapter's content
                if current_chapter and (current_chapter != chapter_title or current_chapter_num != chapter_num):
                    save_chapter_text(current_chapter, chapter_content, output_dir, debug, organize_by_chapter, current_chapter_num)
                    chapter_content = []
                
                current_chapter = chapter_title
                current_chapter_num = chapter_num
                
                page = pdf_file[page_num]
                
                # Add page marker as a comment
                chapter_content.append(f"\n<!-- Page {page_num + 1} -->\n")
                
                # Extract text blocks with style information
                blocks = page.get_text("dict")["blocks"]
                
                for block in blocks:
                    if "lines" not in block:
                        continue
                    
                    for line in block["lines"]:
                        line_text = []
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if not text:
                                continue
                            
                            # Clean and normalize text
                            text = clean_text(text)
                            if not text:  # Skip if text becomes empty after cleaning
                                continue
                            
                            # Normalize text encoding
                            text = unicodedata.normalize('NFKC', text)
                            
                            # Check font flags for formatting
                            flags = span.get("flags", 0)
                            font_name = span.get("font", "").lower()
                            
                            # Apply formatting
                            if flags & 2**3:  # Bold
                                text = f"**{text}**"
                            elif flags & 2**0:  # Italic
                                text = f"*{text}*"
                            elif "bold" in font_name:
                                text = f"**{text}**"
                            elif "italic" in font_name:
                                text = f"*{text}*"
                            
                            line_text.append(text)
                        
                        if line_text:
                            chapter_content.append(" ".join(line_text))
                    
                    chapter_content.append("\n")
                
            except Exception as e:
                print(f"[!] Error extracting text from page {page_num + 1}: {e}")
                if debug:
                    import traceback
                    traceback.print_exc()
                continue
        
        # Save the last chapter's content
        if current_chapter and chapter_content:
            save_chapter_text(current_chapter, chapter_content, output_dir, debug, organize_by_chapter, current_chapter_num)
        
    except Exception as e:
        print(f"[!] Error during text extraction: {e}")
        if debug:
            import traceback
            traceback.print_exc()

def sanitize_chapter_path(chapter_title, chapter_num):
    """Create a sanitized path with chapter number prefix"""
    prefix = "00" if chapter_num == 0 else f"{chapter_num:02d}"
    return f"{prefix}_{sanitize_filename(chapter_title)}"

def save_chapter_text(chapter_title, content, output_dir, debug=False, organize_by_chapter=False, chapter_num=0):
    """Save chapter text content to a file"""
    try:
        if organize_by_chapter:
            # Create chapter directory with number prefix
            chapter_path = sanitize_chapter_path(chapter_title, chapter_num)
            chapter_dir = output_dir / chapter_path
            chapter_dir.mkdir(exist_ok=True)
            output_file = chapter_dir / f"{sanitize_filename(chapter_title)}_text.md"
        else:
            # Format filename with chapter number prefix
            prefix = "00" if chapter_num == 0 else f"{chapter_num:02d}"
            output_file = output_dir / f"{prefix}_{sanitize_filename(chapter_title)}_text.md"
            
        if debug:
            print(f"[DEBUG] Saving text to {output_file}")
            
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))
            
        print(f"[+] Saved text for chapter '{chapter_title}'")
        
    except Exception as e:
        print(f"[!] Error saving text for chapter '{chapter_title}': {e}")
        if debug:
            import traceback
            traceback.print_exc()

def extract_vectors(page, page_index, output_dir, seen_vectors=None):
    """Extract ALL vector graphics from the page"""
    if seen_vectors is None:
        seen_vectors = set()
        
    try:
        # Get both drawings and form XObjects (might contain additional vectors)
        paths = page.get_drawings()
        xobjects = page.get_xobjects()
        
        # Combine all vector content for hashing
        vector_content = str(paths) + str(xobjects)
        vector_hash = get_image_hash(vector_content.encode())
        
        if is_duplicate(vector_hash, seen_vectors):
            print(f"[*] Skipping duplicate vector content on page {page_index + 1}")
            return
            
        # First try to get complete SVG representation
        try:
            svg_data = page.get_svg_image(text_as_path=True)
            output_path = output_dir / f"page{page_index + 1}_vectors_full.svg"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(svg_data)
            print(f"[+] Saved complete vector graphics from page {page_index + 1}")
        except Exception as e:
            print(f"[*] Falling back to manual vector extraction for page {page_index + 1}")
            
            # Fallback to manual extraction
            drawing = svgwrite.Drawing(
                filename=str(output_dir / f"page{page_index + 1}_vectors.svg"),
                size=(page.rect.width, page.rect.height)
            )
            
            # Process all paths
            for path in paths:
                try:
                    if path["type"] == "path":
                        d = " ".join([f"{cmd} {' '.join(map(str, args))}" 
                                    for cmd, args in path["items"]])
                        path_element = drawing.path(d=d)
                        
                        if path.get("stroke"):
                            path_element.stroke(path["stroke"], width=path.get("width", 1))
                        if path.get("fill"):
                            path_element.fill(path["fill"])
                        else:
                            path_element.fill("none")
                            
                        drawing.add(path_element)
                    elif path["type"] == "rect":
                        rect = drawing.rect(
                            insert=(path["rect"][0], path["rect"][1]),
                            size=(path["rect"][2] - path["rect"][0], 
                                  path["rect"][3] - path["rect"][1])
                        )
                        if path.get("stroke"):
                            rect.stroke(path["stroke"], width=path.get("width", 1))
                            rect.stroke(path["stroke"], width=path.get("width", 1))
                        if path.get("fill"):
                            rect.fill(path["fill"])
                        else:
                            rect.fill("none")
                        drawing.add(rect)
                except Exception as e:
                    continue  # Skip problematic paths
            
            drawing.save()
        
        add_to_seen(vector_hash, seen_vectors)
            
    except Exception as e:
        print(f"[!] Error extracting vectors from page {page_index + 1}: {e}")

def extract_fonts(pdf_file, fonts_dir, debug=False, pages_to_process=None):
    """Extract ALL fonts from specified PDF pages"""
    print("[*] Starting font extraction...")
    if debug:
        print(f"[DEBUG] PDF has {len(pdf_file)} total pages")
    
    # Initialize pages_to_process if None
    if pages_to_process is None:
        pages_to_process = range(len(pdf_file))
    
    if debug:
        print(f"[DEBUG] Processing pages: {list(pages_to_process)}")
        print(f"[DEBUG] Output directory: {fonts_dir}")
    
    extracted_fonts = {}
    font_data_hashes = set()
    
    # Process each specified page
    for page_num in pages_to_process:
        if debug:
            print(f"\n[DEBUG] ===== Processing page {page_num + 1}/{len(pdf_file)} =====")
        
        try:
            page = pdf_file[page_num]
            
            # Get fonts from the page
            fonts = page.get_fonts()
            if fonts:
                if debug:
                    print(f"[DEBUG] Found {len(fonts)} fonts:")
                    for i, f in enumerate(fonts, 1):
                        print(f"[DEBUG]   {i}. xref={f[0]}, type={f[2]}, name={f[3]}, base={f[4]}, enc={f[5]}")
                
                print(f"[+] Found {len(fonts)} fonts on page {page_num + 1}")
                
                for font in fonts:
                    try:
                        xref = font[0]
                        font_type = font[2]
                        font_name = font[3]
                        base_font = font[4]
                        encoding = font[5]
                        
                        if debug:
                            print(f"\n[DEBUG] Processing font:")
                            print(f"[DEBUG]   xref: {xref}")
                            print(f"[DEBUG]   type: {font_type}")
                            print(f"[DEBUG]   name: {font_name}")
                            print(f"[DEBUG]   base: {base_font}")
                            print(f"[DEBUG]   encoding: {encoding}")
                        
                        print(f"[*] Attempting to extract font: {font_name}")
                        
                        # Get the raw PDF object for this font
                        raw_obj = pdf_file.xref_object(xref)
                        if debug:
                            print(f"[DEBUG] Raw font object: {raw_obj}")
                            print("[DEBUG] Searching for FontDescriptor...")
                        
                        if raw_obj:
                            # Parse the font descriptor reference from the raw object
                            desc_ref = None
                            if '/FontDescriptor' in raw_obj:
                                # Extract the reference number from the raw object string
                                import re
                                match = re.search(r'/FontDescriptor\s+(\d+)\s+0\s+R', raw_obj)
                                if match:
                                    desc_ref = int(match.group(1))
                                    if debug:
                                        print(f"[DEBUG] Found font descriptor reference: {desc_ref}")
                                    
                                    # Get the font descriptor object
                                    desc_obj = pdf_file.xref_object(desc_ref)
                                    if debug:
                                        print(f"[DEBUG] Font descriptor object: {desc_obj}")
                                        print("[DEBUG] Searching for font file references...")
                                    
                                    # Try different font file types
                                    for key in ['/FontFile3', '/FontFile2', '/FontFile']:
                                        if key in desc_obj:
                                            if debug:
                                                print(f"[DEBUG] Found {key} entry")
                                            
                                            # Extract the font file reference number
                                            font_ref_match = re.search(rf'{key}\s+(\d+)\s+0\s+R', desc_obj)
                                            if font_ref_match:
                                                font_ref = int(font_ref_match.group(1))
                                                if debug:
                                                    print(f"[DEBUG] Found {key} reference: {font_ref}")
                                                    print("[DEBUG] Attempting to extract font data...")
                                                
                                                try:
                                                    # Get the actual font data
                                                    font_buffer = pdf_file.xref_stream(font_ref)
                                                    if font_buffer and len(font_buffer) > 4:
                                                        if debug:
                                                            print(f"[DEBUG] Got font data from {key}, size: {len(font_buffer)} bytes")
                                                            print("[DEBUG] Computing font data hash...")
                                                        
                                                        # Hash the font data
                                                        font_hash = get_image_hash(font_buffer)
                                                        
                                                        if font_hash not in font_data_hashes:
                                                            if debug:
                                                                print(f"[DEBUG] New font hash: {font_hash}")
                                                            
                                                            # Determine font file extension
                                                            if key == '/FontFile':
                                                                ext = '.pfb'
                                                            elif key == '/FontFile2':
                                                                ext = '.ttf'
                                                            elif key == '/FontFile3':
                                                                ext = '.otf'
                                                            else:
                                                                ext = '.font'
                                                            
                                                            if debug:
                                                                print(f"[DEBUG] Using extension: {ext}")
                                                            
                                                            # Clean font name for file system
                                                            safe_font_name = "".join(c for c in font_name if c.isalnum() or c in ('-', '_'))
                                                            if not safe_font_name:
                                                                safe_font_name = f"Font_{xref}"
                                                            
                                                            if debug:
                                                                print(f"[DEBUG] Safe font name: {safe_font_name}")
                                                            
                                                            # Ensure unique filename
                                                            font_path = fonts_dir / f"{safe_font_name}{ext}"
                                                            counter = 1
                                                            while font_path.exists():
                                                                font_path = fonts_dir / f"{safe_font_name}_{counter}{ext}"
                                                                counter += 1
                                                            
                                                            if debug:
                                                                print(f"[DEBUG] Final font path: {font_path}")
                                                                print("[DEBUG] Saving font file...")
                                                            
                                                            # Save the font file
                                                            with open(font_path, 'wb') as f:
                                                                f.write(font_buffer)
                                                            
                                                            extracted_fonts[font_name] = font_path.name
                                                            font_data_hashes.add(font_hash)
                                                            print(f"[+] Saved font: {font_name} ({font_type}) -> {font_path.name}")
                                                            break  # Successfully saved this font
                                                        else:
                                                            if debug:
                                                                print(f"[DEBUG] Duplicate font hash: {font_hash}")
                                                            print(f"[*] Skipping duplicate font: {font_name}")
                                                            break
                                                    else:
                                                        if debug:
                                                            print("[DEBUG] Font buffer is empty or too small")
                                                except Exception as e:
                                                    if debug:
                                                        print(f"[DEBUG] Error extracting font data: {str(e)}")
                                    
                                    if font_name not in extracted_fonts:
                                        if debug:
                                            print("[DEBUG] No valid font data found in any font file reference")
                                        print(f"[*] No font data available for: {font_name}")
                            else:
                                if debug:
                                    print("[DEBUG] No font descriptor found in font object")
                                print(f"[*] No font data available for: {font_name}")
                        else:
                            if debug:
                                print("[DEBUG] Could not get raw font object")
                            print(f"[*] No font data available for: {font_name}")
                    
                    except Exception as e:
                        print(f"[!] Error processing font {font_name}: {str(e)}")
                        if debug:
                            print("[DEBUG] Exception details:")
                            import traceback
                            traceback.print_exc()
                        continue
            else:
                if debug:
                    print("[DEBUG] No fonts found on this page")
                print(f"[*] No fonts found on page {page_num + 1}")
                
        except Exception as e:
            print(f"[!] Error processing page {page_num + 1}: {str(e)}")
            if debug:
                print("[DEBUG] Exception details:")
                import traceback
                traceback.print_exc()
            continue
    
    if extracted_fonts:
        print(f"\n[+] Successfully extracted {len(extracted_fonts)} unique fonts to {fonts_dir}")
        print("[+] Extracted fonts:")
        for font_name, file_name in extracted_fonts.items():
            print(f"    - {font_name} -> {file_name}")
    else:
        print("\n[!] No fonts were extracted. The PDF might not contain extractable fonts.")

def get_chapter_info(pdf_path):
    """
    Create a mapping of page numbers to chapter information
    
    Returns:
        dict: Mapping of page numbers to (chapter_title, chapter_number) tuples
    """
    toc = extract_toc(pdf_path)
    if isinstance(toc, str):  # No TOC found
        return {}
        
    # Filter for top-level entries (depth = 0) which we consider chapters
    chapters = [entry for entry in toc if entry['depth'] == 0]
    
    # Create page to chapter mapping
    page_to_chapter = {}
    for i, chapter in enumerate(chapters):
        start_page = chapter['page']
        # End page is the start of next chapter - 1, or None for last chapter
        end_page = chapters[i + 1]['page'] - 1 if i < len(chapters) - 1 else None
        
        # Map each page in the chapter range to this chapter
        if end_page:
            for page in range(start_page, end_page + 1):
                page_to_chapter[page] = (chapter['title'], i + 1)
        else:
            # For the last chapter, map all remaining pages
            page_to_chapter[start_page] = (chapter['title'], i + 1)
            
    return page_to_chapter

def sanitize_filename(filename):
    """Convert string to valid filename"""
    # Replace invalid characters with underscore
    invalid_chars = '<>:"/\\|?*'
    
    # Normalize unicode characters (e.g., combining characters)
    filename = unicodedata.normalize('NFKD', filename)
    
    # Remove non-ASCII characters and replace invalid chars
    filename = ''.join(c for c in filename if c.isascii() and c not in invalid_chars)
    
    # Replace spaces with underscores and remove multiple underscores
    filename = '_'.join(filter(None, filename.split()))
    
    return filename.strip('_')

def process_pages(pdf_file, output_dir, args, pages_to_process=None):
    """Process pages for images and vector graphics"""
    if pages_to_process is None:
        pages_to_process = range(len(pdf_file))
        
    if args.debug:
        print(f"[DEBUG] Processing {len(pages_to_process)} pages for images/vectors")
    
    # Get chapter information
    chapter_info = get_chapter_info(args.input)
    
    # Track image counts per chapter and unique images
    chapter_image_counts = {}
    seen_images = set()  # Track unique images across all chapters
    total_images = 0
    
    # Create directory for vector graphics only
    if args.extract_vectors:
        vectors_dir = output_dir / "vectors"
        vectors_dir.mkdir(exist_ok=True)
        if args.debug:
            print(f"[DEBUG] Created vectors directory: {vectors_dir}")
    
    # Process each page
    for page_num in pages_to_process:
        try:
            if args.debug:
                print(f"\n[DEBUG] Processing page {page_num + 1} for images/vectors")
            
            page = pdf_file[page_num]
            
            # Get chapter information for this page
            chapter_info_tuple = chapter_info.get(page_num + 1, ("Uncategorized", 0))
            chapter_title, chapter_num = chapter_info_tuple
            
            try:
                # Ensure chapter title is properly decoded
                if isinstance(chapter_title, bytes):
                    chapter_title = chapter_title.decode('utf-8', errors='replace')
            except Exception:
                chapter_title = f"Chapter_{chapter_num}"
            
            # Determine output directory based on organization preference
            if args.organize_by_chapter:
                # Create chapter directory with number prefix
                chapter_path = sanitize_chapter_path(chapter_title, chapter_num)
                save_dir = output_dir / chapter_path
                save_dir.mkdir(exist_ok=True)
            else:
                save_dir = output_dir
            
            # Initialize chapter image count if needed
            if chapter_num not in chapter_image_counts:
                chapter_image_counts[chapter_num] = 1
                        
            # Extract images if not disabled
            if not args.no_images:
                image_list = page.get_images()
                if image_list:
                    page_images = len(image_list)
                    if args.verbose:
                        print(f"[+] Found {page_images} images on page {page_num + 1}")
                    
                    # Track actual image index for this page
                    page_image_index = 1
                    
                    for img_index, img in enumerate(image_list):
                        try:
                            xref = img[0]
                            if args.debug:
                                print(f"[DEBUG] Processing image {img_index + 1}, xref: {xref}")
                            
                            base_image = pdf_file.extract_image(xref)
                            if base_image:
                                image_bytes = base_image["image"]
                                
                                # Check for duplicate images
                                image_hash = get_image_hash(image_bytes, args.hash_mode, args.hash_threshold)
                                if is_duplicate(image_hash, seen_images, args.hash_mode):
                                    if args.verbose:
                                        print(f"[-] Skipping duplicate image on page {page_num + 1}")
                                    continue
                                
                                image_ext = base_image["ext"]
                                
                                # Check image dimensions if specified
                                if args.min_width or args.min_height:
                                    from PIL import Image
                                    import io
                                    img_obj = Image.open(io.BytesIO(image_bytes))
                                    width, height = img_obj.size
                                    
                                    if (args.min_width and width < args.min_width) or \
                                       (args.min_height and height < args.min_height):
                                        if args.debug:
                                            print(f"[DEBUG] Image too small ({width}x{height}), skipping")
                                        continue
                                
                                # Create filename with chapter number and sequential counter
                                if args.organize_by_chapter:
                                    image_filename = f"{sanitize_filename(chapter_title)}_{chapter_image_counts[chapter_num]}_page_{page_num + 1}.{image_ext}"
                                else:
                                    prefix = "00" if chapter_num == 0 else f"{chapter_num:02d}"
                                    image_filename = f"{prefix}_{sanitize_filename(chapter_title)}_{chapter_image_counts[chapter_num]}_page_{page_num + 1}.{image_ext}"
                                
                                image_path = save_dir / image_filename
                                
                                with open(image_path, 'wb') as img_file:
                                    img_file.write(image_bytes)
                                if args.verbose:
                                    print(f"[+] Saved image: {image_path.name}")
                                
                                add_to_seen(image_hash, seen_images)
                                chapter_image_counts[chapter_num] += 1
                                total_images += 1
                                page_image_index += 1  # Only increment for successfully saved images
                            
                        except Exception as e:
                            print(f"[!] Error extracting image {img_index + 1} from page {page_num + 1}: {e}")
                            if args.debug:
                                import traceback
                                traceback.print_exc()
                elif args.verbose:
                    print(f"[*] No images found on page {page_num + 1}")
            
            # Extract vector graphics if requested
            if args.extract_vectors:
                # TODO: Implement vector graphics extraction
                pass
                
        except Exception as e:
            print(f"[!] Error processing page {page_num + 1}: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            continue
    
    # Print summary at the end
    if total_images > 0:
        print(f"\n[+] Total images extracted: {total_images}")
        if args.verbose:
            for chapter_num in sorted(chapter_image_counts.keys()):
                if chapter_num == 0:
                    chapter_name = "Uncategorized"
                else:
                    chapter_name = next((title for title, num in chapter_info.values() if num == chapter_num), "Unknown")
                print(f"  Chapter '{chapter_name}': {chapter_image_counts[chapter_num] - 1} images")

def extract_toc(pdf_path):
    """
    Extract the table of contents from a PDF file using PyMuPDF
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        list: List of dictionaries containing title, page number, and depth
    """
    with fitz.open(pdf_path) as pdf_file:
        toc = pdf_file.get_toc()
        
        if not toc:
            return "No table of contents found in the PDF"
            
        result = []
        for level, title, page in toc:
            result.append({
                'title': title,
                'page': page,
                'depth': level - 1  # PyMuPDF uses 1-based levels
            })
            
        return result

if __name__ == "__main__":
    main()
