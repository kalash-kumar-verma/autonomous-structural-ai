import cv2
import numpy as np
from .text_filter import detect_text_regions, create_text_filtered_image, extract_text_regions_for_annotation


def parse_floor_plan(image_path, debug=False):
    """
    Enhanced floor plan parsing with text filtering:
    - Detect and mask text regions to avoid spurious wall detection
    - Adaptive thresholding for better wall extraction
    - Morphological cleanup to remove noise
    - Probabilistic Hough with tuned params
    - Extract text annotations for 3D model labeling
    
    Args:
        image_path: Path to floor plan image
        debug: If True, save intermediate processing images for diagnostic
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")

    h, w = img.shape[:2]
    
    if debug:
        import os
        debug_dir = os.path.join(os.path.dirname(image_path), "debug_output")
        os.makedirs(debug_dir, exist_ok=True)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Adaptive denoising
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # Enhance contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    if debug:
        cv2.imwrite(os.path.join(debug_dir, "01_enhanced.png"), enhanced)

    # ── TEXT FILTERING: Detect and mask text regions before wall detection ──
    text_mask = None
    text_regions = []
    try:
        text_mask, text_regions = detect_text_regions(gray, enhanced)
    except Exception as e:
        # If text detection fails, continue without it
        # This ensures robustness - text filtering is optional improvement
        print(f"[WARNING] Text filtering failed: {str(e)}. Continuing without text filtering.")
        text_mask = np.zeros((h, w), dtype=np.uint8)
        text_regions = []
    
    if debug:
        cv2.imwrite(os.path.join(debug_dir, "02_text_mask.png"), text_mask)

    # Adaptive threshold to handle varying background
    adaptive = cv2.adaptiveThreshold(
        enhanced, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=15,
        C=4
    )

    # Also use Otsu for a second mask
    _, otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Combine both masks
    combined = cv2.bitwise_or(adaptive, otsu)
    
    if debug:
        cv2.imwrite(os.path.join(debug_dir, "03_combined_before_filter.png"), combined)

    # REMOVE TEXT REGIONS from the combined mask
    combined = create_text_filtered_image(combined, text_mask)
    
    if debug:
        cv2.imwrite(os.path.join(debug_dir, "04_combined_after_text_filter.png"), combined)

    # Morphological cleanup: remove thin noise, keep thick walls
    kernel_clean = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel_clean, iterations=1)
    
    if debug:
        cv2.imwrite(os.path.join(debug_dir, "05_cleaned.png"), cleaned)

    # Strengthen wall lines
    kernel_dilate = np.ones((2, 2), np.uint8)
    strengthened = cv2.dilate(cleaned, kernel_dilate, iterations=1)
    
    if debug:
        cv2.imwrite(os.path.join(debug_dir, "06_strengthened.png"), strengthened)

    # Scale-adaptive Hough parameters
    scale = max(w, h) / 800.0
    min_line_len = int(60 * scale)
    max_gap = int(20 * scale)
    threshold = int(80 * scale)

    lines = cv2.HoughLinesP(
        strengthened,
        rho=1,
        theta=np.pi / 180,
        threshold=threshold,
        minLineLength=min_line_len,
        maxLineGap=max_gap
    )

    # Return image, detected lines, grayscale, text mask, and text regions
    return img, lines, gray, text_mask, text_regions
