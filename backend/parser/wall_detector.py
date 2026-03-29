import math
import numpy as np
from collections import defaultdict

def remove_duplicate_walls(walls, threshold=20):

    unique = []

    for w in walls:

        duplicate = False

        for u in unique:

            if (
                abs(w["start"][0] - u["start"][0]) < threshold and
                abs(w["start"][1] - u["start"][1]) < threshold and
                abs(w["end"][0] - u["end"][0]) < threshold and
                abs(w["end"][1] - u["end"][1]) < threshold
            ):
                duplicate = True
                break

        if not duplicate:
            unique.append(w)

    return unique

def line_length(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def snap_line(x1, y1, x2, y2):
    """Snap near-axis lines to perfectly horizontal or vertical."""
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    if dx > dy:
        avg_y = (y1 + y2) // 2
        return int(x1), int(avg_y), int(x2), int(avg_y)
    else:
        avg_x = (x1 + x2) // 2
        return int(avg_x), int(y1), int(avg_x), int(y2)


def line_angle(x1, y1, x2, y2):
    return math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180


def cluster_lines(lines, angle_threshold=15):
    horizontal, vertical, diagonal = [], [], []
    for x1, y1, x2, y2 in lines:
        angle = line_angle(x1, y1, x2, y2)
        if angle < angle_threshold or angle > 180 - angle_threshold:
            horizontal.append((x1, y1, x2, y2))
        elif 90 - angle_threshold < angle < 90 + angle_threshold:
            vertical.append((x1, y1, x2, y2))
        else:
            diagonal.append((x1, y1, x2, y2))
    return horizontal, vertical, diagonal


def merge_collinear(lines, axis, band=18, gap=30):
    if not lines:
        return []
    bands = defaultdict(list)
    for x1, y1, x2, y2 in lines:
        coord = ((y1 + y2) / 2) if axis == 'h' else ((x1 + x2) / 2)
        key = round(coord / band) * band
        bands[key].append((x1, y1, x2, y2))

    merged = []
    for key, grp in bands.items():
        if axis == 'h':
            avg_y = int(np.mean([(l[1] + l[3]) / 2 for l in grp]))
            segs = sorted([(min(l[0], l[2]), max(l[0], l[2])) for l in grp])
            result = [list(segs[0])]
            for s, e in segs[1:]:
                if s <= result[-1][1] + gap:
                    result[-1][1] = max(result[-1][1], e)
                else:
                    result.append([s, e])
            for s, e in result:
                merged.append((int(s), int(avg_y), int(e), int(avg_y)))
        else:
            avg_x = int(np.mean([(l[0] + l[2]) / 2 for l in grp]))
            segs = sorted([(min(l[1], l[3]), max(l[1], l[3])) for l in grp])
            result = [list(segs[0])]
            for s, e in segs[1:]:
                if s <= result[-1][1] + gap:
                    result[-1][1] = max(result[-1][1], e)
                else:
                    result.append([s, e])
            for s, e in result:
                merged.append((int(avg_x), int(s), int(avg_x), int(e)))
    return merged


def deduplicate(walls, tol=20):
    unique = []
    for w in walls:
        dup = False
        for u in unique:
            d1 = abs(w[0]-u[0]) + abs(w[1]-u[1]) + abs(w[2]-u[2]) + abs(w[3]-u[3])
            d2 = abs(w[0]-u[2]) + abs(w[1]-u[3]) + abs(w[2]-u[0]) + abs(w[3]-u[1])
            if d1 < tol * 4 or d2 < tol * 4:
                dup = True
                break
        if not dup:
            unique.append(w)
    return unique


def detect_walls(lines, image_gray=None):
    """
    Enhanced wall detection:
    - Snap to H/V
    - Cluster by angle
    - Merge collinear segments
    - Remove duplicates & short noise
    """
    if lines is None:
        return []

    raw = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if line_length(x1, y1, x2, y2) > 40:
            raw.append(snap_line(x1, y1, x2, y2))

    horizontal, vertical, diagonal = cluster_lines(raw)
    merged_h = merge_collinear(horizontal, 'h')
    merged_v = merge_collinear(vertical, 'v')

    all_lines = merged_h + merged_v + diagonal
    all_lines = [l for l in all_lines if line_length(*l) >= 50]
    all_lines = deduplicate(all_lines)

    walls = []
    for x1, y1, x2, y2 in all_lines:
        length = line_length(x1, y1, x2, y2)
        is_h = abs(x2 - x1) >= abs(y2 - y1)
        walls.append({
            "start": (int(x1), int(y1)),
            "end": (int(x2), int(y2)),
            "length": float(length),
            "orientation": "horizontal" if is_h else "vertical",
            "thickness": 12
        })

    walls = remove_duplicate_walls(walls)
    walls.sort(key=lambda w: w["length"], reverse=True)
    return walls
