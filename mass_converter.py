import os
from pathlib import Path
from PIL import Image
import shutil
import hashlib

def get_image_hash(filepath):
    """Calculate SHA-256 hash of image file"""
    with open(filepath, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def convert_images(input_dir, output_dir, jpeg_quality=95):
    """
    Recursively process images from input_dir:
    - Copy jpg/jpeg files directly
    - Convert png files to high-quality jpg
    """
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Track processed files by their hash
    processed_files = {}  # hash -> output_path
    
    # First, scan output directory for existing files
    print("\nScanning existing output directory...")
    for existing_file in output_dir.glob('*.jpg'):
        file_hash = get_image_hash(existing_file)
        processed_files[file_hash] = existing_file
        print(f"Found existing: {existing_file.name} (hash: {file_hash[:8]})")
    
    # Walk through directory tree
    print("\nProcessing input files...")
    for root, _, files in os.walk(input_dir):
        for filename in files:
            filepath = Path(root) / filename
            
            # Get lowercase extension
            ext = filepath.suffix.lower()
            
            # Skip non-image files
            if ext not in ['.jpg', '.jpeg', '.png']:
                continue
            
            print(f"\nProcessing: {filepath}")
            
            # Get file hash
            file_hash = get_image_hash(filepath)
            print(f"File hash: {file_hash[:8]}")
            
            # Skip if we've already processed this image
            if file_hash in processed_files:
                print(f"Skipping duplicate: {filepath} (already exists as {processed_files[file_hash].name})")
                continue
            
            # Generate base output filename (without extension)
            base_name = filepath.stem
            output_path = output_dir / f"{base_name}.jpg"
            
            # If a file with this name exists but has a different hash,
            # find a unique name
            counter = 0
            while output_path.exists() and get_image_hash(output_path) != file_hash:
                counter += 1
                output_path = output_dir / f"{base_name}_{counter}.jpg"
            
            # If the file exists and has the same hash, skip it
            if output_path.exists():
                print(f"Skipping duplicate: {filepath} (already exists as {output_path.name})")
                processed_files[file_hash] = output_path
                continue
            
            try:
                if ext in ['.jpg', '.jpeg']:
                    # Copy jpg files directly
                    shutil.copy2(filepath, output_path)
                    print(f"Copied: {filepath} -> {output_path}")
                
                elif ext == '.png':
                    # Convert png to jpg
                    with Image.open(filepath) as img:
                        # Convert to RGB if necessary
                        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            background.paste(img, mask=img.split()[-1])
                            img = background
                        elif img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # Save as high-quality JPEG
                        img.save(output_path, 'JPEG', quality=jpeg_quality)
                    print(f"Converted: {filepath} -> {output_path}")
                
                # Add to processed files
                processed_files[file_hash] = output_path
                
            except Exception as e:
                print(f"Error processing {filepath}: {e}")

    print("\nProcessing complete!")
    print(f"Total unique files processed: {len(processed_files)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert/copy images to jpg format')
    parser.add_argument('-i', '--input', required=True, help='Input directory to process recursively')
    parser.add_argument('-o', '--output', required=True, help='Output directory for all images')
    parser.add_argument('-q', '--quality', type=int, default=95,
                       help='JPEG quality (1-100, default: 95)')
    
    args = parser.parse_args()
    
    convert_images(args.input, args.output, args.quality)
