import math


PIXEL_TO_METER = 0.025
WALL_HEIGHT = 3.0       # meters
DEFAULT_THICKNESS = 0.23  # meters (standard brick wall)
FLOOR_THICKNESS = 0.15
SCALE = 0.05           # render scale: pixels → Three.js units
MIN_RENDER_WALL_LEN = 0.7
SNAP_GRID = 0.12
DOOR_HEIGHT = 2.1
WINDOW_HEIGHT = 1.2
WINDOW_SILL = 0.9


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


def _opening_center(opening):
    ox = opening.get("x", 0)
    oy = opening.get("y", 0)
    ow = opening.get("width", 0)
    oh = opening.get("height", 0)
    return (ox + (ow / 2.0)) * SCALE, (oy + (oh / 2.0)) * SCALE


def _opening_axis(opening):
    ow = float(opening.get("width", 0))
    oh = float(opening.get("height", 0))
    return "horizontal" if ow >= oh else "vertical"


def _wall_axis(wall):
    ang = float(wall.get("angle", 0.0))
    return "horizontal" if abs(math.cos(ang)) >= abs(math.sin(ang)) else "vertical"


def _find_wall_by_source_segment(opening, cleaned_walls):
    src_start = opening.get("source_wall_start")
    src_end = opening.get("source_wall_end")
    if not src_start or not src_end:
        return None

    sx1 = float(src_start[0]) * SCALE
    sy1 = float(src_start[1]) * SCALE
    sx2 = float(src_end[0]) * SCALE
    sy2 = float(src_end[1]) * SCALE
    src_axis = "horizontal" if abs(sx2 - sx1) >= abs(sy2 - sy1) else "vertical"
    best_idx = None
    best_score = float("inf")

    for idx, wall in enumerate(cleaned_walls):
        if _wall_axis(wall) != src_axis:
            continue

        wx1, wy1, wx2, wy2 = wall["_segment"]
        direct = math.sqrt((wx1 - sx1) ** 2 + (wy1 - sy1) ** 2) + math.sqrt((wx2 - sx2) ** 2 + (wy2 - sy2) ** 2)
        reverse = math.sqrt((wx1 - sx2) ** 2 + (wy1 - sy2) ** 2) + math.sqrt((wx2 - sx1) ** 2 + (wy2 - sy1) ** 2)
        endpoint_score = min(direct, reverse)
        len_penalty = abs(float(wall["length"]) - math.sqrt((sx2 - sx1) ** 2 + (sy2 - sy1) ** 2)) * 0.12
        score = endpoint_score + len_penalty

        if score < best_score:
            best_score = score
            best_idx = idx

    if best_idx is None:
        return None
    return best_idx


def _find_nearest_wall_for_opening(opening, cleaned_walls):
    px, py = _opening_center(opening)

    preferred_axis = _opening_axis(opening)
    candidates = [
        (idx, wall) for idx, wall in enumerate(cleaned_walls)
        if _wall_axis(wall) == preferred_axis
    ]
    if not candidates:
        candidates = list(enumerate(cleaned_walls))

    best_idx = None
    best_dist = float("inf")
    best_t = 0.0
    best_pt = (px, py)

    for idx, wall in candidates:
        ax, ay, bx, by = wall["_segment"]
        dist, t = _distance_point_to_segment(px, py, ax, ay, bx, by)
        if t < 0.02 or t > 0.98:
            dist += 0.15
        if dist < best_dist:
            best_dist = dist
            best_idx = idx
            best_t = t
            best_pt = (ax + (bx - ax) * t, ay + (by - ay) * t)

    if best_idx is None:
        return None

    return {
        "wall_idx": best_idx,
        "distance": best_dist,
        "t": best_t,
        "point": best_pt,
    }


def _build_opening_models(openings, cleaned_walls, kind):
    models = []
    if not openings:
        return models

    if kind == "door":
        max_attach_distance = 0.38
        min_t = 0.08
        max_t = 0.92
    else:
        # Windows are visually subtler in 2D plans; allow wider snap tolerance.
        max_attach_distance = 0.9
        min_t = 0.04
        max_t = 0.96

    for i, opening in enumerate(openings):
        nearest = None

        source_wall_idx = _find_wall_by_source_segment(opening, cleaned_walls)
        if source_wall_idx is not None:
            px, py = _opening_center(opening)
            wall = cleaned_walls[source_wall_idx]
            ax, ay, bx, by = wall["_segment"]
            dist, t = _distance_point_to_segment(px, py, ax, ay, bx, by)
            nearest = {
                "wall_idx": source_wall_idx,
                "distance": dist,
                "t": t,
                "point": (ax + (bx - ax) * t, ay + (by - ay) * t),
            }

        if nearest is None:
            nearest = _find_nearest_wall_for_opening(opening, cleaned_walls)

        if nearest and nearest["distance"] <= max_attach_distance and min_t <= nearest["t"] <= max_t:
            wall = cleaned_walls[nearest["wall_idx"]]
            cx, cz = nearest["point"]
            angle = wall["angle"]
            wall_id = f"wall_{nearest['wall_idx']}"
            attached = True
            depth = 0.34
            wall_len = float(wall.get("length", 0.0))
            wall_t = float(nearest["t"])
        else:
            cx, cz = _opening_center(opening)
            angle = 0.0
            wall_id = None
            attached = False
            depth = 0.12
            wall_len = 0.0
            wall_t = 0.5

        rough_span = max(opening.get("width", 0), opening.get("height", 0)) * SCALE

        if kind == "door":
            width = max(0.75, min(max(rough_span, 0.9), 1.4))
            height = DOOR_HEIGHT
            center_y = round(height / 2.0, 3)
            color = "#8B4513"
        else:
            width = max(0.6, min(max(rough_span, 0.8), 2.0))
            height = WINDOW_HEIGHT
            center_y = round(WINDOW_SILL + (height / 2.0), 3)
            color = "#87CEEB"

        models.append({
            "id": f"{kind}_{i}",
            "type": kind,
            "position": [round(cx, 3), center_y, round(cz, 3)],
            "width": round(width, 3),
            "height": round(height, 3),
            "depth": round(depth, 3),
            "rotation_y": round(-angle, 4),
            "wall_id": wall_id,
            "attached_to_wall": attached,
            "wall_length": round(wall_len, 3),
            "wall_t": round(wall_t, 4),
            "opening_kind": opening.get("type") or opening.get("opening_type") or kind,
            "color": color
        })

    return models


def _prune_openings(models, kind):
    if not models:
        return []

    # Keep only openings confidently attached to a wall.
    attached = [m for m in models if m.get("attached_to_wall") and m.get("wall_id")]
    by_wall = {}
    for m in attached:
        by_wall.setdefault(m["wall_id"], []).append(m)

    pruned = []
    min_clearance = 0.95 if kind == "door" else 0.45

    for wall_id, items in by_wall.items():
        items = sorted(items, key=lambda x: x.get("wall_t", 0.5))
        kept = []
        for item in items:
            t = float(item.get("wall_t", 0.5))
            wall_len = float(item.get("wall_length", 0.0))

            # Reject openings too close to wall ends.
            if wall_len > 0 and (t * wall_len < 0.45 or (1.0 - t) * wall_len < 0.45):
                continue

            overlap = False
            for k in kept:
                dt = abs(float(k.get("wall_t", 0.5)) - t)
                ref_len = max(wall_len, float(k.get("wall_length", 0.0)), 1e-6)
                along = dt * ref_len
                need = max(min_clearance, 0.5 * (float(item.get("width", 0.8)) + float(k.get("width", 0.8))))
                if along < need:
                    overlap = True
                    break
            if not overlap:
                kept.append(item)

        pruned.extend(kept)

    pruned.sort(key=lambda x: x["id"])
    return pruned


def _strip_opening_internal_fields(models):
    out = []
    for m in models:
        out.append({
            "id": m.get("id"),
            "type": m.get("type"),
            "position": m.get("position"),
            "width": m.get("width"),
            "height": m.get("height"),
            "depth": m.get("depth"),
            "rotation_y": m.get("rotation_y", 0.0),
            "wall_id": m.get("wall_id"),
            "attached_to_wall": m.get("attached_to_wall", False),
            "wall_t": m.get("wall_t"),
            "opening_kind": m.get("opening_kind"),
            "color": m.get("color"),
        })
    return out


def _snap_value(v, step=SNAP_GRID):
    if step <= 0:
        return v
    return round(v / step) * step


def _clean_wall_geometry(walls):
    """Clean noisy segments for rendering without mutating analysis walls."""
    snapped = []
    for wall_idx, wall in enumerate(walls):
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
            "type": wall.get("type", "partition"),
            "source_indices": [wall_idx]
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
            m["source_indices"] = sorted(set(m.get("source_indices", []) + wall.get("source_indices", [])))
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
            "source_indices": wall.get("source_indices", []),
            "_segment": (wall["x1"], wall["y1"], wall["x2"], wall["y2"])
        })

    return cleaned


def _resolve_warning_wall_id(warning, rooms, wall_models):
    wall_index = warning.get("wall_index")
    if wall_index is not None:
        for wall in wall_models:
            if wall_index in wall.get("source_indices", []):
                return wall.get("id")

    room_name = warning.get("room")
    if not room_name or not rooms or not wall_models:
        return None

    room_lookup = {r.get("label", ""): r for r in rooms}
    room = room_lookup.get(room_name)
    if not room:
        return None

    cx = (room["x"] + (room["width"] / 2.0)) * SCALE
    cz = (room["y"] + (room["height"] / 2.0)) * SCALE

    candidates = [w for w in wall_models if w.get("type") == "load_bearing"]
    if not candidates:
        candidates = wall_models

    best = None
    best_dist = float("inf")
    for wall in candidates:
        wx = wall["center"][0]
        wz = wall["center"][1]
        dist = math.sqrt((wx - cx) ** 2 + (wz - cz) ** 2)
        if dist < best_dist:
            best_dist = dist
            best = wall

    return best.get("id") if best else None


def _build_warning_overlays(warnings, rooms, wall_models):
    overlays = []
    if not warnings:
        return overlays

    room_lookup = {r.get("label", ""): r for r in rooms}
    wall_lookup = {w.get("id"): w for w in wall_models}
    severity_to_color = {
        "critical": "#ef4444",
        "high": "#fb923c",
        "medium": "#f59e0b",
        "low": "#fde047"
    }

    for idx, warning in enumerate(warnings):
        target_wall_id = _resolve_warning_wall_id(warning, rooms, wall_models)

        room_name = warning.get("room")
        room = room_lookup.get(room_name)
        if room:
            cx = (room["x"] + (room["width"] / 2.0)) * SCALE
            cz = (room["y"] + (room["height"] / 2.0)) * SCALE
            radius = max(room["width"], room["height"]) * SCALE * 0.22
        else:
            target_wall = wall_lookup.get(target_wall_id)
            if not target_wall:
                continue
            cx = target_wall["center"][0]
            cz = target_wall["center"][1]
            radius = target_wall.get("length", 1.0) * 0.12

        severity = warning.get("severity", "low")

        overlays.append({
            "id": f"warning_{idx}",
            "type": "warning_overlay",
            "warning_index": idx,
            "severity": severity,
            "color": severity_to_color.get(severity, "#f59e0b"),
            "position": [round(cx, 3), 0.05, round(cz, 3)],
            "radius": round(max(radius, 0.35), 3),
            "message": warning.get("message", ""),
            "target_wall_id": target_wall_id
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
            dx, dy = _opening_center(d)
            door_positions.append((
                dx,
                dy
            ))

    # -------------------------
    # WALLS (with door cutouts)
    # -------------------------
    cleaned_walls = _clean_wall_geometry(walls)
    for i, wall in enumerate(cleaned_walls):
        has_door = False
        ax, ay, bx, by = wall["_segment"]
        for dx, dy in door_positions:
            dist, t = _distance_point_to_segment(dx, dy, ax, ay, bx, by)
            if dist <= 0.55 and 0.08 <= t <= 0.92:
                has_door = True
                break

        wall_models.append({
            "id": f"wall_{i}",
            "type": wall["type"],
            "center": wall["center"],
            "length": wall["length"],
            "angle": wall["angle"],
            "hasDoor": has_door,
            "thickness": 0.42,
            "source_indices": wall.get("source_indices", [])
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
    # DOORS (wall-attached openings)
    # -------------------------
    door_models = _build_opening_models(doors or [], cleaned_walls, kind="door")
    door_models = _prune_openings(door_models, kind="door")
    door_models = _strip_opening_internal_fields(door_models)

    # Recompute hasDoor from final refined door attachments so wall cutouts
    # in the frontend match the actual exported door list.
    for wall in wall_models:
        wall["hasDoor"] = False
    attached_wall_ids = {
        d.get("wall_id") for d in door_models
        if d.get("attached_to_wall") and d.get("wall_id")
    }
    if attached_wall_ids:
        for wall in wall_models:
            if wall.get("id") in attached_wall_ids:
                wall["hasDoor"] = True

    # -------------------------
    # WINDOWS
    # -------------------------
    window_models = _build_opening_models(windows or [], cleaned_walls, kind="window")
    window_models = _prune_openings(window_models, kind="window")
    window_models = _strip_opening_internal_fields(window_models)

    warning_overlays = _build_warning_overlays(warnings, rooms or [], wall_models)

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