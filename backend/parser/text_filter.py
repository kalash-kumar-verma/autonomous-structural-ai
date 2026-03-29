"""
Text Detection and Filtering for Floor Plans

Identifies text regions in floor plan images and masks them out before wall detection.
Also extracts text labels for use in 3D model annotations.
"""

import cv2
import numpy as np
from typing import Tuple, List, Dict

def detect_text_regions(gray_image: np.ndarray, enhanced_image: np.ndarray) -> Tuple[np.ndarray, List[Dict]]:
    """
    Detect text regions in floor plan using morphological operations.
    
    Args:
        gray_image: Original grayscale image
        enhanced_image: CLAHE-enhanced image
    
    Returns:
        mask: Binary mask where text regions are white (255)
        regions: List of detected text region bounding boxes
    """
    h, w = gray_image.shape[:2]
    
    # Threshold to get binary image for text detection
    _, binary = cv2.threshold(enhanced_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Invert: text is darker on light background
    binary_inv = cv2.bitwise_not(binary)
    
    # Morphological operations to enhance text regions
    # Text has characteristic thin lines and small components
    kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    
    # Erode to separate touching characters
    eroded = cv2.erode(binary_inv, kernel_erode, iterations=1)
    
    # Find contours (potential text regions)
    contours, _ = cv2.findContours(eroded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Analyze contours to identify text-like shapes
    text_mask = np.zeros((h, w), dtype=np.uint8)
    text_regions = []
    
    for contour in contours:
        area = cv2.contourArea(contour)
        
        # Text characteristics:
        # - Small to medium area (typical character/number size)
        # - Medium-to-high aspect ratio
        # - High solidity (filled characters)
        
        # VERY CONSERVATIVE: Only filter absolutely clear text
        if area < 200:  # Significantly increased minimum area (was 100)
            continue
        
        if area > h * w * 0.08:  # Reduced threshold (was 0.10)
            continue
        
        x, y, tw, th = cv2.boundingRect(contour)
        min_dim = min(tw, th)
        max_dim = max(tw, th)
        
        # Aspect ratio check
        aspect_ratio = max_dim / (min_dim + 1e-6)
        
        # Solidity check: how filled
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        solidity = float(area) / (hull_area + 1e-6)
        
        # VERY STRICT: Only filter high-confidence text
        # Text: very high solidity (0.7-1.0), moderate to high aspect ratio
        # Walls: low to medium solidity, extreme aspect ratios
        is_text_like = (
            0.7 < solidity < 1.0 and  # Very high solidity (definitely filled, not structural)
            (1.2 < aspect_ratio < 4.0) and  # Moderate elongation
            (tw >= 15 and th >= 15)  # Larger minimum dimensions (eliminate tiny noise)
        )
        
        if is_text_like:
            # Expand region slightly to catch nearby text
            expand = 3
            x1 = max(0, x - expand)
            y1 = max(0, y - expand)
            x2 = min(w, x + tw + expand)
            y2 = min(h, y + th + expand)
            
            cv2.rectangle(text_mask, (x1, y1), (x2, y2), 255, -1)
            text_regions.append({
                'x': x,
                'y': y,
                'width': tw,
                'height': th,
                'area': area,
                'solidity': solidity,
                'aspect_ratio': aspect_ratio
            })
    
    # Dilate text mask slightly to ensure we catch all text-adjacent pixels
    # REDUCED KERNEL: from 5x5 to 3x3 to avoid eroding important structural info
    kernel_dilate_text = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    text_mask = cv2.dilate(text_mask, kernel_dilate_text, iterations=1)
    
    return text_mask, text_regions


def create_text_filtered_image(binary_image: np.ndarray, text_mask: np.ndarray) -> np.ndarray:
    """
    Remove text regions from binary wall image.
    
    Args:
        binary_image: Binary image with walls and text
        text_mask: Mask where text regions are white
    
    Returns:
        Filtered binary image with text removed
    """
    # Invert text mask (white becomes black, black stays black)
    text_mask_inv = cv2.bitwise_not(text_mask)
    
    # Apply mask: keep only non-text regions
    filtered = cv2.bitwise_and(binary_image, binary_image, mask=text_mask_inv)
    
    return filtered


def extract_text_regions_for_annotation(
    gray_image: np.ndarray,
    enhanced_image: np.ndarray,
    text_mask: np.ndarray,
    rooms: List[Dict] = None
) -> List[Dict]:
    """
    Extract text regions and attempt to associate them with rooms.
    
    Args:
        gray_image: Original grayscale image
        enhanced_image: Enhanced image
        text_mask: Text region mask from detect_text_regions
        rooms: Optional list of detected rooms for text association
    
    Returns:
        List of text annotations with positions and associated room IDs
    """
    h, w = gray_image.shape[:2]
    annotations = []
    
    # Find connected components in text mask
    _, labels, stats, centroids = cv2.connectedComponentsWithStats(text_mask, connectivity=8)
    
    for label_id in range(1, len(stats)):  # Skip background (0)
        x, y, width, height, area = stats[label_id]
        cx, cy = int(centroids[label_id][0]), int(centroids[label_id][1])
        
        if area < 10:  # Skip very small regions
            continue
        
        # Try to associate with a room
        associated_room = None
        if rooms:
            # Find room containing this text center
            for room_id, room in enumerate(rooms):
                room_x = room.get('x', 0)
                room_y = room.get('y', 0)
                room_w = room.get('width', 0)
                room_h = room.get('height', 0)
                
                if (room_x <= cx <= room_x + room_w and
                    room_y <= cy <= room_y + room_h):
                    associated_room = room_id
                    break
        
        annotation = {
            'type': 'text_region',
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'center_x': cx,
            'center_y': cy,
            'area': area,
            'associated_room': associated_room
        }
        annotations.append(annotation)
    
    return annotations


def should_keep_line(line_coords: Tuple[int, int, int, int], text_mask: np.ndarray, 
                     min_overlap_ratio: float = 0.3) -> bool:
    """
    Determine if a detected line should be kept based on overlap with text regions.
    
    Args:
        line_coords: (x1, y1, x2, y2) line coordinates
        text_mask: Text region mask
        min_overlap_ratio: Maximum allowed overlap ratio (0-1) with text
    
    Returns:
        True if line should be kept (not text), False if likely part of text
    """
    x1, y1, x2, y2 = line_coords
    
    # Create a line mask
    line_mask = np.zeros_like(text_mask)
    cv2.line(line_mask, (x1, y1), (x2, y2), 255, 2)
    
    # Calculate overlap
    overlap = cv2.bitwise_and(line_mask, text_mask)
    overlap_pixels = cv2.countNonZero(overlap)
    line_pixels = cv2.countNonZero(line_mask)
    
    if line_pixels == 0:
        return True
    
    overlap_ratio = overlap_pixels / line_pixels
    
    # Keep line if overlap is below threshold
    return overlap_ratio < min_overlap_ratio
