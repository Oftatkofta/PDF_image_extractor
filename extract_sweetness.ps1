# Extract images from Delta Green Sweetness PDF into ./sweetness
# Uses conda base environment.

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$PdfPath = "C:\Users\oftak\iCloudDrive\Family\Rollspel\Delta Green\Delta-Dreen_Sweetness.pdf"
$OutputDir = "sweetness"

Set-Location $ProjectRoot
conda run -n base python PDF_image_extractor.py --input $PdfPath --output $OutputDir -v
