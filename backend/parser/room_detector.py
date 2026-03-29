import cv2
import numpy as np
import os


def detect_rooms(image):
    """
    Detect rooms using connected components analysis.
    
    Args:
        image: Floor plan image
    
    Returns:
        List of detected room regions with bounding boxes and statistics
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Binary threshold - threshold value adjusted for typical floor plans
    _, thresh = cv2.threshold(
        gray,
        200,
        255,
        cv2.THRESH_BINARY_INV
    )

    # Strengthen walls with dilation
    kernel = np.ones((7, 7), np.uint8)
    walls = cv2.dilate(thresh, kernel, iterations=2)

    # Invert to get free space (rooms)
    free_space = cv2.bitwise_not(walls)

    # Connected components analysis
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        free_space,
        connectivity=8
    )

    rooms = []

    for i in range(1, num_labels):  # skip background (i=0)

        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        area = stats[i, cv2.CC_STAT_AREA]

        # Filter out small regions (noise) and very large regions (likely exterior)
        # Minimum room area: ~3000 pixels (roughly 5x5 units)
        # Maximum room area: 50% of image (would mean only 2 rooms)
        if area > 3000 and area < gray.shape[0] * gray.shape[1] * 0.5:

            rooms.append({
                "label": f"Room {len(rooms) + 1}",
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
                "area": int(area),
                "area_sqm": round(area * 0.025 * 0.025, 2),
                "aspect_ratio": round((w / h) if h != 0 else 1.0, 2)
            })

    return rooms