from pathlib import Path
import fitz
import argparse
from PIL import Image
import io
from PDF_image_extractor import get_chapter_info

def get_page_without_text(page, zoom=2):
    """
    Render page without text at specified zoom level
    Returns a PIL Image
    """
    try:
        # Create a new PDF with just this page
        doc = fitz.open()
        doc.insert_pdf(page.parent, from_page=page.number, to_page=page.number)
        temp_page = doc[0]
        
        # Set resolution
        matrix = fitz.Matrix(zoom, zoom)
        
        # First render: Get background images
        # Extract all images from the page
        image_list = temp_page.get_images()
        background = None
        
        for img in image_list:
            try:
                xref = img[0]
                base_image = temp_page.parent.extract_image(xref)
                
                if base_image:
                    pil_img = Image.open(io.BytesIO(base_image["image"]))
                    
                    # If this is larger than current background, use it
                    if background is None or (pil_img.width * pil_img.height) > (background.width * background.height):
                        background = pil_img
            except Exception as e:
                print(f"Warning: Could not extract image: {e}")
                continue
        
        # Second render: Get graphics without text
        graphics_doc = fitz.open()
        graphics_doc.insert_pdf(page.parent, from_page=page.number, to_page=page.number)
        graphics_page = graphics_doc[0]
        
        # Get text blocks for removal
        text_blocks = graphics_page.get_text("dict")["blocks"]
        
        # Create a new content stream without text operations
        content = graphics_page.get_contents()
        if content:
            xref = graphics_page.get_contents()[0]
            cont_str = graphics_doc.xref_stream(xref)
            
            # Remove text operators
            text_operators = [
                b'BT', b'ET',  # begin/end text
                b'Tf', b'Tj', b'TJ', b'"', b"'",  # text showing
                b'Tc', b'Tw', b'Tz', b'TL', b'Tr', b'Ts',  # text parameters
                b'Td', b'TD', b'Tm', b'T*',  # text positioning
            ]
            
            new_stream = cont_str
            for op in text_operators:
                new_stream = new_stream.replace(op + b' ', b'')
                new_stream = new_stream.replace(op + b'\n', b'')
            
            # Update the page's content
            graphics_doc.update_stream(xref, new_stream)
        
        # Remove any remaining text-related content
        graphics_page.clean_contents()
        
        # Render graphics with transparency
        pix_graphics = graphics_page.get_pixmap(matrix=matrix, alpha=True)
        graphics = Image.open(io.BytesIO(pix_graphics.tobytes("png")))
        
        # Create final image
        page_width = int(temp_page.rect.width * zoom)
        page_height = int(temp_page.rect.height * zoom)
        
        if background:
            # Resize background to match page dimensions
            background = background.resize((page_width, page_height), Image.Resampling.LANCZOS)
            
            # Create new image with background
            result = Image.new('RGBA', (page_width, page_height), (255, 255, 255, 0))
            result.paste(background, (0, 0))
            
            # Convert graphics to RGBA if needed
            if graphics.mode != 'RGBA':
                graphics = graphics.convert('RGBA')
            
            # Create mask from graphics alpha channel
            mask = graphics.split()[3]
            
            # Paste graphics using mask
            result.paste(graphics, (0, 0), mask)
        else:
            result = graphics
        
        # Close temporary documents
        doc.close()
        graphics_doc.close()
        
        return result
        
    except Exception as e:
        print(f"Warning: {str(e)}")
        # Fallback method: simple render without text
        try:
            doc = fitz.open()
            doc.insert_pdf(page.parent, from_page=page.number, to_page=page.number)
            temp_page = doc[0]
            temp_page.clean_contents()
            
            matrix = fitz.Matrix(zoom, zoom)
            pix = temp_page.get_pixmap(matrix=matrix, alpha=True)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            
            doc.close()
            return img
            
        except Exception as e2:
            print(f"Error in fallback rendering: {str(e2)}")
            raise

def merge_page_images(pdf_path, output_dir, zoom=2):
    """
    Capture each PDF page as rendered, but without text
    """
    print(f"[*] Using PyMuPDF version: {fitz.__version__}")
    print(f"Processing PDF pages (zoom: {zoom}x)")
    
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get chapter information
    chapter_info = get_chapter_info(pdf_path)
    
    # Open PDF
    pdf = fitz.open(pdf_path)
    total_pages = len(pdf)
    processed_count = 0
    
    # Process each page
    for page_num in range(total_pages):
        print(f"\nProcessing page {page_num + 1}...")
        
        # Get chapter info for this page
        chapter_title = None
        for p in range(1, page_num + 2):
            if p in chapter_info:
                chapter_title, _ = chapter_info[p]
        
        try:
            # Get page render without text
            img = get_page_without_text(pdf[page_num], zoom)
            
            # Skip if image is completely empty
            if img.getbbox() is None:
                print(f"Page {page_num + 1} is empty after text removal")
                continue
            
            # Create filename with chapter name if available
            if chapter_title:
                # Clean chapter name for filename
                safe_chapter = "".join(c for c in chapter_title if c.isalnum() or c in ('-', '_', ' '))
                safe_chapter = safe_chapter.replace(' ', '_')
                filename = f"{safe_chapter}_page_{page_num + 1}.png"
            else:
                filename = f"page_{page_num + 1}.png"
            
            # Save image
            output_path = output_dir / filename
            img.save(output_path, 'PNG')
            print(f"Saved page image: {output_path.name}")
            processed_count += 1
            
        except Exception as e:
            print(f"Error processing page {page_num + 1}: {e}")
            continue
    
    pdf.close()
    print("\nProcessing complete!")
    print(f"Total pages processed: {processed_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Capture PDF pages without text')
    parser.add_argument('-i', '--input', required=True, help='Input PDF file')
    parser.add_argument('-o', '--output', required=True, help='Output directory for images')
    parser.add_argument('-z', '--zoom', type=float, default=2.0,
                       help='Zoom factor for resolution (default: 2.0)')
    
    args = parser.parse_args()
    
    merge_page_images(args.input, args.output, args.zoom) 