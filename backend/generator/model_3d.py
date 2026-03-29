import math


PIXEL_TO_METER = 0.025
WALL_HEIGHT = 3.0       # meters
DEFAULT_THICKNESS = 0.23  # meters (standard brick wall)
FLOOR_THICKNESS = 0.15
SCALE = 0.05           # render scale: pixels → Three.js units
MIN_RENDER_WALL_LEN = 0.7
SNAP_GRID = 0.12


def wall_to_3d(wall, index):
    """Convert 2D wall segment to 3D box parameters for Three.js."""
    x1, y1 = wall["start"]
    x2, y2 = wall["end"]

    length = wall["length"] * SCALE
    cx = ((x1 + x2) / 2) * SCALE
    cz = ((y1 + y2) / 2) * SCALE

    angle = math.atan2(y2 - y1, x2 - x1)

    thickness = max(wall.get("thickness", 10), 8) * SCALE
    height = WALL_HEIGHT

    color = (
        "#e74c3c" if wall.get("type") == "load_bearing"
        else "#3498db"
    )

    return {
        "id": f"wall_{index}",
        "type": "wall",
        "wall_type": wall.get("type", "partition"),
        "position": {
            "x": round(cx, 3),
            "y": round(height / 2, 3),
            "z": round(cz, 3)
        },
        "dimensions": {
            "width": round(length, 3),
            "height": round(height, 3),
            "depth": round(max(thickness, 0.15), 3)
        },
        "rotation_y": round(angle, 4),
        "color": color,
        "structural_score": wall.get("structural_score", 50),
        "length_m": round(wall["length"] * PIXEL_TO_METER, 2),
        "orientation": wall.get("orientation", "unknown")
    }


def room_to_3d(room, index):
    """Convert 2D room bounding box to 3D floor slab."""
    x = room["x"] * SCALE
    z = room["y"] * SCALE
    w = room["width"] * SCALE
    d = room["height"] * SCALE
    cx = x + w / 2
    cz = z + d / 2

    return {
        "id": f"floor_{index}",
        "type": "floor",
        "room_label": room.get("label", f"Room {index+1}"),
        "position": {
            "x": round(cx, 3),
            "y": round(-FLOOR_THICKNESS / 2, 3),
            "z": round(cz, 3)
        },
        "dimensions": {
            "width": round(w, 3),
            "height": round(FLOOR_THICKNESS, 3),
            "depth": round(d, 3)
        },
        "color": "#ecf0f1",
        "area_sqm": room.get("area_sqm", 0),
        "center_label": {
            "x": round(cx, 3),
            "z": round(cz, 3)
        }
    }


def door_to_3d(door, index, walls):
    """Represent a door as a gap marker in 3D."""
    cx = (door["x"] + door["width"] / 2) * SCALE
    cz = (door["y"] + door["height"] / 2) * SCALE
    w = max(door.get("width", 80), 40) * SCALE
    h = 2.1  # standard door height

    return {
        "id": f"door_{index}",
        "type": "door",
        "position": {"x": round(cx, 3), "y": round(h / 2, 3), "z": round(cz, 3)},
        "dimensions": {"width": round(w, 3), "height": round(h, 3), "depth": 0.05},
        "color": "#8B4513",
        "opening_type": door.get("type", "door")
    }


def window_to_3d(window, index):
    """Represent a window as a transparent panel in 3D."""
    cx = (window["x"] + window["width"] / 2) * SCALE
    cz = (window["y"] + window["height"] / 2) * SCALE
    w = max(window.get("width", 60), 30) * SCALE
    h = 1.2   # standard window height
    sill = 0.9  # window sill height

    return {
        "id": f"window_{index}",
        "type": "window",
        "position": {"x": round(cx, 3), "y": round(sill + h / 2, 3), "z": round(cz, 3)},
        "dimensions": {"width": round(w, 3), "height": round(h, 3), "depth": 0.05},
        "color": "#87CEEB",
        "transparent": True,
        "opacity": 0.4
    }


def generate_roof(walls):
    """Generate a simple flat roof slab over the entire building footprint."""
    if not walls:
        return None
    xs = [w["start"][0] for w in walls] + [w["end"][0] for w in walls]
    ys = [w["start"][1] for w in walls] + [w["end"][1] for w in walls]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    cx = ((min_x + max_x) / 2) * SCALE
    cz = ((min_y + max_y) / 2) * SCALE
    w = (max_x - min_x) * SCALE
    d = (max_y - min_y) * SCALE

    return {
        "id": "roof",
        "type": "roof",
        "position": {"x": round(cx, 3), "y": round(WALL_HEIGHT + FLOOR_THICKNESS / 2, 3), "z": round(cz, 3)},
        "dimensions": {"width": round(w + 0.5, 3), "height": round(FLOOR_THICKNESS, 3), "depth": round(d + 0.5, 3)},
        "color": "#95a5a6",
        "opacity": 0.55
    }


def compute_building_stats(walls, rooms):
    """Compute overall building statistics."""
    if not walls:
        return {}
    xs = [w["start"][0] for w in walls] + [w["end"][0] for w in walls]
    ys = [w["start"][1] for w in walls] + [w["end"][1] for w in walls]

    bw = (max(xs) - min(xs)) * PIXEL_TO_METER
    bd = (max(ys) - min(ys)) * PIXEL_TO_METER
    total_room_area = sum(r.get("area_sqm", 0) for r in rooms)
    total_wall_len = sum(w["length"] * PIXEL_TO_METER for w in walls)

    return {
        "building_width_m": round(bw, 1),
        "building_depth_m": round(bd, 1),
        "footprint_sqm": round(bw * bd, 1),
        "total_room_area_sqm": round(total_room_area, 1),
        "total_wall_length_m": round(total_wall_len, 1),
        "floor_count": 1,
        "wall_count": len(walls),
        "room_count": len(rooms)
    }


def _distance_point_to_segment(px, py, ax, ay, bx, by):
    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay
    ab2 = (abx * abx) + (aby * aby)
    if ab2 <= 1e-9:
        return math.sqrt((px - ax) ** 2 + (py - ay) ** 2), 0.0

    t = max(0.0, min(1.0, ((apx * abx) + (apy * aby)) / ab2))
    qx = ax + (t * abx)
    qy = ay + (t * aby)
    dist = math.sqrt((px - qx) ** 2 + (py - qy) ** 2)
    return dist, t


def _snap_value(v, step=SNAP_GRID):
    if step <= 0:
        return v
    return round(v / step) * step


def _clean_wall_geometry(walls):
    """Clean noisy segments for rendering without mutating analysis walls."""
    snapped = []
    for wall in walls:
        x1, y1 = wall["start"]
        x2, y2 = wall["end"]
        x1s = _snap_value(x1 * SCALE)
        y1s = _snap_value(y1 * SCALE)
        x2s = _snap_value(x2 * SCALE)
        y2s = _snap_value(y2 * SCALE)

        length = math.sqrt((x2s - x1s) ** 2 + (y2s - y1s) ** 2)
        if length < MIN_RENDER_WALL_LEN:
            continue

        angle = math.atan2(y2s - y1s, x2s - x1s)
        snapped.append({
            "x1": x1s,
            "y1": y1s,
            "x2": x2s,
            "y2": y2s,
            "length": length,
            "angle": angle,
            "type": wall.get("type", "partition")
        })

    # Merge near-collinear segments with similar angle and close endpoints.
    merged = []
    for wall in sorted(snapped, key=lambda w: w["length"], reverse=True):
        absorbed = False
        for m in merged:
            same_type = m["type"] == wall["type"]
            angle_diff = abs((m["angle"] - wall["angle"] + math.pi) % math.pi)
            if angle_diff > math.pi / 2:
                angle_diff = math.pi - angle_diff

            if not same_type or angle_diff > math.radians(8):
                continue

            endpoint_pairs = [
                (m["x1"], m["y1"], wall["x1"], wall["y1"]),
                (m["x1"], m["y1"], wall["x2"], wall["y2"]),
                (m["x2"], m["y2"], wall["x1"], wall["y1"]),
                (m["x2"], m["y2"], wall["x2"], wall["y2"]),
            ]
            min_gap = min(math.sqrt((ax - bx) ** 2 + (ay - by) ** 2) for ax, ay, bx, by in endpoint_pairs)

            if min_gap > 0.35:
                continue

            pts = [
                (m["x1"], m["y1"]),
                (m["x2"], m["y2"]),
                (wall["x1"], wall["y1"]),
                (wall["x2"], wall["y2"]),
            ]
            c = math.cos(m["angle"])
            s = math.sin(m["angle"])
            projections = [p[0] * c + p[1] * s for p in pts]
            min_i = projections.index(min(projections))
            max_i = projections.index(max(projections))
            m["x1"], m["y1"] = pts[min_i]
            m["x2"], m["y2"] = pts[max_i]
            m["length"] = math.sqrt((m["x2"] - m["x1"]) ** 2 + (m["y2"] - m["y1"]) ** 2)
            m["angle"] = math.atan2(m["y2"] - m["y1"], m["x2"] - m["x1"])
            absorbed = True
            break

        if not absorbed:
            merged.append(wall)

    cleaned = []
    for wall in merged:
        length = wall["length"]
        if length < MIN_RENDER_WALL_LEN:
            continue
        center_x = (wall["x1"] + wall["x2"]) / 2.0
        center_y = (wall["y1"] + wall["y2"]) / 2.0
        cleaned.append({
            "type": wall["type"],
            "center": [round(center_x, 3), round(center_y, 3)],
            "length": round(length, 3),
            "angle": round(wall["angle"], 4),
            "_segment": (wall["x1"], wall["y1"], wall["x2"], wall["y2"])
        })

    return cleaned


def _build_warning_overlays(warnings, rooms):
    overlays = []
    if not warnings or not rooms:
        return overlays

    room_lookup = {r.get("label", ""): r for r in rooms}
    severity_to_color = {
        "critical": "#ef4444",
        "high": "#fb923c",
        "medium": "#f59e0b",
        "low": "#fde047"
    }

    for idx, warning in enumerate(warnings):
        room_name = warning.get("room")
        room = room_lookup.get(room_name)
        if not room:
            continue

        cx = (room["x"] + (room["width"] / 2.0)) * SCALE
        cz = (room["y"] + (room["height"] / 2.0)) * SCALE
        radius = max(room["width"], room["height"]) * SCALE * 0.22
        severity = warning.get("severity", "low")

        overlays.append({
            "id": f"warning_{idx}",
            "type": "warning_overlay",
            "severity": severity,
            "color": severity_to_color.get(severity, "#f59e0b"),
            "position": [round(cx, 3), 0.05, round(cz, 3)],
            "radius": round(max(radius, 0.35), 3),
            "message": warning.get("message", "")
        })

    return overlays


def generate_3d(walls, rooms=None, doors=None, windows=None, warnings=None, text_regions=None):

    wall_models = []
    floor_models = []
    door_models = []
    window_models = []
    warning_overlays = []

    # -------------------------
    # Precompute door positions
    # -------------------------
    door_positions = []
    if doors:
        for d in doors:
            door_positions.append((
                d.get("x", 0) * SCALE,
                d.get("y", 0) * SCALE
            ))

    # -------------------------
    # WALLS (with door cutouts)
    # -------------------------
    cleaned_walls = _clean_wall_geometry(walls)
    for wall in cleaned_walls:
        has_door = False
        ax, ay, bx, by = wall["_segment"]
        for dx, dy in door_positions:
            dist, t = _distance_point_to_segment(dx, dy, ax, ay, bx, by)
            if dist <= 0.55 and 0.08 <= t <= 0.92:
                has_door = True
                break

        wall_models.append({
            "type": wall["type"],
            "center": wall["center"],
            "length": wall["length"],
            "angle": wall["angle"],
            "hasDoor": has_door,
            "thickness": 0.42
        })

    # -------------------------
    # FLOORS (clean + centered)
    # -------------------------
    if rooms:
        for i, room in enumerate(rooms):

            cx = (room["x"] + room["width"]/2) * SCALE
            cz = (room["y"] + room["height"]/2) * SCALE

            width_m = room["width"] * PIXEL_TO_METER
            height_m = room["height"] * PIXEL_TO_METER

            area = width_m * height_m

            aspect_ratio = max(width_m, height_m) / max(min(width_m, height_m), 0.1)

            floor_models.append({
                "id": f"floor_{i}",

                "center": [round(cx, 3), round(cz, 3)],
                "width": round(room["width"] * SCALE, 3),
                "depth": round(room["height"] * SCALE, 3),

                # 🔥 ADD THESE (frontend expects them)
                "label": f"Bedroom {i+1}" if area > 10 else f"Small Room {i+1}",
                "area_sqm": round(area, 2),
                "aspect_ratio": round(aspect_ratio, 2)
            })

    # -------------------------
    # DOORS (visual markers)
    # -------------------------
    if doors:
        for i, d in enumerate(doors):

            door_models.append({
                "id": f"door_{i}",
                "position": [
                    round(d.get("x", 0) * SCALE, 3),
                    1,
                    round(d.get("y", 0) * SCALE, 3)
                ]
            })

    # -------------------------
    # WINDOWS
    # -------------------------
    if windows:
        for i, w in enumerate(windows):

            window_models.append({
                "id": f"window_{i}",
                "position": [
                    round(w.get("x", 0) * SCALE, 3),
                    1.5,
                    round(w.get("y", 0) * SCALE, 3)
                ]
            })

    warning_overlays = _build_warning_overlays(warnings, rooms or [])

    # Note: text_regions parameter is used ONLY for improving wall detection accuracy
    # Text annotations are not rendered in 3D to keep the model clean and focused on
    # actual structural elements (walls, rooms, doors, windows, warnings only)

    return {
        "walls": wall_models,
        "floors": floor_models,
        "doors": door_models,
        "windows": window_models,
        "warning_overlays": warning_overlays
    }