from pathlib import Path
from PIL import Image
import argparse
import fitz
from PDF_image_extractor import extract_toc, get_chapter_info

def get_page_background(page, min_dimension=1200, max_width=None, max_height=None):
    """Extract largest image from page that meets dimension criteria"""
    largest_image = None
    largest_size = 0
    
    # Get all images from page
    image_list = page.get_images()
    
    for img_index, img in enumerate(image_list):
        try:
            xref = img[0]
            base_image = page.parent.extract_image(xref)
            
            if base_image:
                # Check image dimensions
                from PIL import Image
                import io
                image_bytes = base_image["image"]
                img_obj = Image.open(io.BytesIO(image_bytes))
                width, height = img_obj.size
                
                # Check minimum dimensions
                if width >= min_dimension and height >= min_dimension:
                    # Check maximum dimensions if specified
                    if (max_width is None or width <= max_width) and \
                       (max_height is None or height <= max_height):
                        size = width * height
                        if size > largest_size:
                            largest_size = size
                            largest_image = img_obj
        except Exception as e:
            print(f"Error extracting image: {e}")
            continue
    
    return largest_image

def merge_facing_pages(pdf_path, output_dir, min_dimension=1200, max_width=None, max_height=None):
    """
    Find and merge background images from facing pages
    """
    print(f"Scanning PDF for facing page backgrounds:")
    print(f"- Min dimension: {min_dimension}px")
    print(f"- Max width: {max_width if max_width else 'unlimited'}px")
    print(f"- Max height: {max_height if max_height else 'unlimited'}px")
    
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get chapter information
    chapter_info = get_chapter_info(pdf_path)
    
    # Open PDF
    pdf = fitz.open(pdf_path)
    total_pages = len(pdf)
    
    # Process facing pages (starting from page 2)
    processed_pages = set()
    merged_count = 0
    
    # Start from page 2 (index 1) to get proper facing pages
    for left_page in range(1, total_pages - 1, 2):
        right_page = left_page + 1
        
        if left_page in processed_pages or right_page >= total_pages:
            continue
            
        # Skip if right page already processed
        if right_page in processed_pages:
            continue
        
        print(f"\nChecking pages {left_page + 1} and {right_page + 1}...")
        
        # Get chapter info for these pages
        chapter_title = None
        for page_num in range(1, left_page + 2):  # Check all previous pages
            if page_num in chapter_info:
                chapter_title, _ = chapter_info[page_num]
        
        # Get largest images from both pages
        img1 = get_page_background(pdf[left_page], min_dimension, max_width, max_height)
        img2 = get_page_background(pdf[right_page], min_dimension, max_width, max_height)
        
        # Check if both pages have suitable images
        if img1 and img2:
            # Check if images are the same height
            if img1.height == img2.height:
                print(f"Found matching backgrounds:")
                print(f"Left:  {img1.width}x{img1.height}")
                print(f"Right: {img2.width}x{img2.height}")
                
                # Create new image with combined width
                new_width = img1.width + img2.width
                merged = Image.new('RGB', (new_width, img1.height))
                
                # Paste images side by side
                merged.paste(img1, (0, 0))
                merged.paste(img2, (img1.width, 0))
                
                # Create filename with chapter name if available
                if chapter_title:
                    # Clean chapter name for filename
                    safe_chapter = "".join(c for c in chapter_title if c.isalnum() or c in ('-', '_', ' '))
                    safe_chapter = safe_chapter.replace(' ', '_')
                    filename = f"{safe_chapter}_pages_{left_page + 1}_{right_page + 1}.jpg"
                else:
                    filename = f"merged_pages_{left_page + 1}_{right_page + 1}.jpg"
                
                # Save merged image
                output_path = output_dir / filename
                merged.save(output_path, 'JPEG', quality=95)
                print(f"Saved merged image: {output_path.name}")
                
                # Mark pages as processed
                processed_pages.add(left_page)
                processed_pages.add(right_page)
                merged_count += 1
            else:
                print("Images have different heights - skipping")
        else:
            if not img1 and not img2:
                print("No suitable background images found on either page")
            elif not img1:
                print("No suitable background image found on left page")
            else:
                print("No suitable background image found on right page")
    
    pdf.close()
    print("\nProcessing complete!")
    print(f"Total merged pairs: {merged_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Merge background images from facing PDF pages')
    parser.add_argument('-i', '--input', required=True, help='Input PDF file')
    parser.add_argument('-o', '--output', required=True, help='Output directory for merged images')
    parser.add_argument('-m', '--min-dimension', type=int, default=1200,
                       help='Minimum width/height for merging (default: 1200)')
    parser.add_argument('--max-width', type=int, default=None,
                       help='Maximum width for image selection (default: none)')
    parser.add_argument('--max-height', type=int, default=None,
                       help='Maximum height for image selection (default: none)')
    
    args = parser.parse_args()
    
    merge_facing_pages(args.input, args.output, args.min_dimension, args.max_width, args.max_height) 