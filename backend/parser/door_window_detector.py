import cv2
import numpy as np
import math


def detect_arcs(gray):
    """
    Detect door arcs (quarter circles) using HoughCircles.
    In floor plans, doors are shown as arcs + straight line.
    """
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.5,
        minDist=30,
        param1=50,
        param2=25,
        minRadius=15,
        maxRadius=80
    )
    doors = []
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        for (cx, cy, r) in circles:
            doors.append({
                "x": int(cx - r),
                "y": int(cy - r),
                "width": int(r * 2),
                "height": int(r * 2),
                "center_x": int(cx),
                "center_y": int(cy),
                "radius": int(r),
                "type": "arc_door"
            })
    return doors


def detect_wall_gaps(gray, walls):
    """
    Detect openings in walls as potential doors/windows.
    Gaps are short dark regions perpendicular to wall direction.
    """
    openings = []
    _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

    for wall_idx, wall in enumerate(walls):
        x1, y1 = wall["start"]
        x2, y2 = wall["end"]
        length = wall["length"]

        if length < 60:
            continue

        is_h = wall["orientation"] == "horizontal"
        steps = int(length / 10)

        gap_start = None
        for i in range(steps):
            t = i / steps
            cx = int(x1 + t * (x2 - x1))
            cy = int(y1 + t * (y2 - y1))

            # Sample along wall
            h_img, w_img = binary.shape
            if 0 <= cx < w_img and 0 <= cy < h_img:
                val = binary[cy, cx]
                if val == 0 and gap_start is None:
                    gap_start = (cx, cy)
                elif val > 0 and gap_start is not None:
                    gap_len = math.sqrt(
                        (cx - gap_start[0])**2 + (cy - gap_start[1])**2
                    )
                    if 20 < gap_len < 150:
                        gx = min(gap_start[0], cx)
                        gy = min(gap_start[1], cy)
                        openings.append({
                            "x": int(gx),
                            "y": int(gy),
                            "width": int(abs(cx - gap_start[0]) + 20),
                            "height": int(abs(cy - gap_start[1]) + 20),
                            "gap_length": float(gap_len),
                            "type": "gap_opening",
                            "source_wall_index": int(wall_idx),
                            "source_wall_start": [int(x1), int(y1)],
                            "source_wall_end": [int(x2), int(y2)],
                            "source_wall_orientation": wall.get("orientation", "unknown")
                        })
                    gap_start = None

    return openings


def classify_openings(openings):
    """Classify gap openings as doors or windows based on size."""
    doors, windows = [], []
    for o in openings:
        gap = o.get("gap_length", max(o["width"], o["height"]))
        if gap >= 60:
            doors.append({**o, "opening_type": "door"})
        else:
            windows.append({**o, "opening_type": "window"})
    return doors, windows


def detect_triple_lines(gray):
    """
    Windows in floor plans often appear as 3 parallel lines.
    Detect using morphological analysis.
    """
    # Detect thin parallel line clusters
    windows = []
    edges = cv2.Canny(gray, 40, 120)
    kernel_h = np.ones((1, 20), np.uint8)
    kernel_v = np.ones((20, 1), np.uint8)

    h_lines = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_h)
    v_lines = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_v)

    for lines_img in [h_lines, v_lines]:
        contours, _ = cv2.findContours(lines_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 300 < area < 4000:
                x, y, w, h = cv2.boundingRect(cnt)
                ar = w / max(h, 1)
                if ar > 3 or ar < 0.33:
                    windows.append({
                        "x": int(x), "y": int(y),
                        "width": int(w), "height": int(h),
                        "opening_type": "window"
                    })
    return windows


def detect_doors_windows(image, walls=None):
    """
    Multi-method door & window detection:
    1. Arc detection (HoughCircles) → doors
    2. Wall gap detection → doors/windows
    3. Triple-line detection → windows
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Method 1: Arc-based door detection
    arc_doors = detect_arcs(gray)

    # Method 2: Wall gap detection
    gap_doors, gap_windows = [], []
    if walls:
        openings = detect_wall_gaps(gray, walls)
        gap_doors, gap_windows = classify_openings(openings)

    # Method 3: Triple line windows
    triple_windows = detect_triple_lines(gray)

    # Combine
    all_doors = arc_doors + gap_doors
    all_windows = gap_windows + triple_windows

    # Deduplicate by proximity
    def dedup(items, dist=40):
        out = []
        for item in items:
            cx = item["x"] + item["width"] / 2
            cy = item["y"] + item["height"] / 2
            dup = False
            for kept in out:
                kx = kept["x"] + kept["width"] / 2
                ky = kept["y"] + kept["height"] / 2
                if math.sqrt((cx-kx)**2 + (cy-ky)**2) < dist:
                    dup = True
                    break
            if not dup:
                out.append(item)
        return out

    all_doors = dedup(all_doors)
    all_windows = dedup(all_windows)

    return all_doors, all_windows
