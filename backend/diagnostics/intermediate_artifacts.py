import json
import math
import os
from datetime import datetime

import cv2
import numpy as np


ARTIFACT_DIR_NAME = "intermediate_output"


MATERIAL_COLORS = {
    "RCC": (60, 60, 220),
    "AAC Block": (40, 190, 40),
    "Fly Ash Brick": (40, 160, 220),
    "Steel Frame": (90, 90, 90),
    "Precast Concrete": (180, 140, 50),
    "Red Brick": (30, 80, 200),
}


def _ensure_bgr(img):
    if img is None:
        return None
    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img.copy()


def _blank_like(img):
    h, w = img.shape[:2]
    return np.zeros((h, w, 3), dtype=np.uint8)


def _put_title(img, text):
    cv2.putText(img, text, (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 220, 255), 2, cv2.LINE_AA)


def _add_legend(img, items, title="Legend"):
    if not items:
        return

    h, w = img.shape[:2]
    line_h = 18
    pad = 10
    swatch = 12
    box_w = min(360, max(230, int(w * 0.42)))
    box_h = pad * 2 + line_h * (len(items) + 1)
    x0 = max(8, w - box_w - 10)
    y0 = 10

    overlay = img.copy()
    cv2.rectangle(overlay, (x0, y0), (x0 + box_w, min(y0 + box_h, h - 8)), (18, 18, 18), -1)
    cv2.addWeighted(overlay, 0.65, img, 0.35, 0, img)
    cv2.rectangle(img, (x0, y0), (x0 + box_w, min(y0 + box_h, h - 8)), (120, 120, 120), 1)

    cv2.putText(img, title, (x0 + pad, y0 + pad + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (240, 240, 240), 1, cv2.LINE_AA)

    yy = y0 + pad + line_h + 6
    for label, color in items:
        if color is not None:
            cv2.rectangle(img, (x0 + pad, yy - swatch + 2), (x0 + pad + swatch, yy + 2), color, -1)
            cv2.rectangle(img, (x0 + pad, yy - swatch + 2), (x0 + pad + swatch, yy + 2), (220, 220, 220), 1)
            text_x = x0 + pad + swatch + 8
        else:
            text_x = x0 + pad
        cv2.putText(img, str(label), (text_x, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (230, 230, 230), 1, cv2.LINE_AA)
        yy += line_h


def _wall_points(wall):
    x1, y1 = wall.get("start", (0, 0))
    x2, y2 = wall.get("end", (0, 0))
    return int(x1), int(y1), int(x2), int(y2)


def _draw_walls(img, walls, color, thickness=2, draw_index=False):
    for idx, wall in enumerate(walls or []):
        x1, y1, x2, y2 = _wall_points(wall)
        cv2.line(img, (x1, y1), (x2, y2), color, thickness, cv2.LINE_AA)
        if draw_index:
            mx = int((x1 + x2) / 2)
            my = int((y1 + y2) / 2)
            cv2.putText(img, str(idx), (mx, my), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)


def _draw_rooms(img, rooms):
    for room in rooms or []:
        x = int(room.get("x", 0))
        y = int(room.get("y", 0))
        w = int(room.get("width", 0))
        h = int(room.get("height", 0))
        cv2.rectangle(img, (x, y), (x + w, y + h), (255, 180, 0), 2)
        label = room.get("label", "Room")
        cv2.putText(img, label, (x + 3, max(y + 16, 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)


def _draw_openings(img, openings, color, label):
    for i, opn in enumerate(openings or []):
        x = int(opn.get("x", 0))
        y = int(opn.get("y", 0))
        w = int(opn.get("width", 0))
        h = int(opn.get("height", 0))
        cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
        cv2.putText(img, f"{label}{i + 1}", (x, max(y - 5, 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)


def _draw_graph(img, wall_graph):
    graph = (wall_graph or {}).get("graph", {})
    nodes = (wall_graph or {}).get("nodes", [])
    for src, dst_list in graph.items():
        sx, sy = int(src[0]), int(src[1])
        for dst in dst_list:
            dx, dy = int(dst[0]), int(dst[1])
            cv2.line(img, (sx, sy), (dx, dy), (120, 220, 120), 1, cv2.LINE_AA)
    for idx, node in enumerate(nodes):
        x, y = int(node[0]), int(node[1])
        cv2.circle(img, (x, y), 3, (0, 80, 255), -1)
        if idx < 250:
            cv2.putText(img, str(idx), (x + 4, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1, cv2.LINE_AA)


def _span_color(severity):
    if severity == "critical":
        return (40, 40, 220)
    if severity == "high":
        return (20, 140, 255)
    if severity == "medium":
        return (0, 220, 220)
    return (0, 170, 80)


def _save_placeholder(base_img, path, title, text):
    canvas = _blank_like(base_img)
    _put_title(canvas, title)
    cv2.putText(canvas, text, (20, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.imwrite(path, canvas)


def _canonical_key(x1, y1, x2, y2):
    a = (int(x1), int(y1))
    b = (int(x2), int(y2))
    return (a, b) if a <= b else (b, a)


def _preprocess_gray(gray):
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    adaptive = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, blockSize=15, C=4)
    _, otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return cv2.bitwise_or(adaptive, otsu)


def _render_cleaned_geometry(base_img, model):
    canvas = _blank_like(base_img)
    _put_title(canvas, "17_cleaned_geometry")

    walls = (model or {}).get("walls", [])
    if not walls:
        cv2.putText(canvas, "No model walls available", (20, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
        return canvas

    segments = []
    for w in walls:
        c = w.get("center", [0, 0])
        cx = float(c[0])
        cz = float(c[1])
        length = float(w.get("length", 0.0))
        angle = float(w.get("angle", 0.0))
        dx = math.cos(angle) * (length / 2.0)
        dz = math.sin(angle) * (length / 2.0)
        segments.append((cx - dx, cz - dz, cx + dx, cz + dz, w.get("type", "partition")))

    xs = [s[0] for s in segments] + [s[2] for s in segments]
    ys = [s[1] for s in segments] + [s[3] for s in segments]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    dx = max(max_x - min_x, 1e-6)
    dy = max(max_y - min_y, 1e-6)

    h, w = canvas.shape[:2]
    pad = 30

    def map_xy(px, py):
        mx = int(((px - min_x) / dx) * (w - 2 * pad) + pad)
        my = int(((py - min_y) / dy) * (h - 2 * pad) + pad)
        return mx, my

    for x1, y1, x2, y2, wall_type in segments:
        p1 = map_xy(x1, y1)
        p2 = map_xy(x2, y2)
        color = (70, 70, 230) if wall_type == "load_bearing" else (220, 170, 70)
        cv2.line(canvas, p1, p2, color, 3, cv2.LINE_AA)

    return canvas


def _render_3d_preview(base_img, model):
    canvas = _blank_like(base_img)
    _put_title(canvas, "18_3d_projection_preview")

    walls = (model or {}).get("walls", [])
    floors = (model or {}).get("floors", [])
    if not walls and not floors:
        cv2.putText(canvas, "No model data available", (20, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
        return canvas

    all_points = []
    for f in floors:
        cx, cz = f.get("center", [0, 0])
        fw = float(f.get("width", 0.1))
        fd = float(f.get("depth", 0.1))
        all_points.extend([
            (cx - fw / 2, cz - fd / 2),
            (cx + fw / 2, cz - fd / 2),
            (cx + fw / 2, cz + fd / 2),
            (cx - fw / 2, cz + fd / 2),
        ])

    for w in walls:
        cx, cz = w.get("center", [0, 0])
        length = float(w.get("length", 0.1))
        angle = float(w.get("angle", 0.0))
        dx = math.cos(angle) * (length / 2.0)
        dz = math.sin(angle) * (length / 2.0)
        all_points.append((cx - dx, cz - dz))
        all_points.append((cx + dx, cz + dz))

    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    h, wimg = canvas.shape[:2]
    span = max(max_x - min_x, max_y - min_y, 1e-6)
    scale = (min(h, wimg) * 0.55) / span
    ox = int(wimg * 0.5)
    oy = int(h * 0.62)

    def project(x, z, y):
        sx = int((x - z) * scale * 0.9 + ox)
        sy = int((x + z) * scale * 0.45 - y * scale * 0.35 + oy)
        return sx, sy

    for f in floors:
        cx, cz = f.get("center", [0, 0])
        fw = float(f.get("width", 0.1))
        fd = float(f.get("depth", 0.1))
        pts = [
            project(cx - fw / 2, cz - fd / 2, 0.0),
            project(cx + fw / 2, cz - fd / 2, 0.0),
            project(cx + fw / 2, cz + fd / 2, 0.0),
            project(cx - fw / 2, cz + fd / 2, 0.0),
        ]
        poly = np.array(pts, dtype=np.int32)
        cv2.fillPoly(canvas, [poly], (60, 110, 70))
        cv2.polylines(canvas, [poly], True, (100, 180, 120), 1, cv2.LINE_AA)

    wall_height = 3.0
    for wall in walls:
        cx, cz = wall.get("center", [0, 0])
        length = float(wall.get("length", 0.1))
        angle = float(wall.get("angle", 0.0))
        dx = math.cos(angle) * (length / 2.0)
        dz = math.sin(angle) * (length / 2.0)

        p1b = project(cx - dx, cz - dz, 0.0)
        p2b = project(cx + dx, cz + dz, 0.0)
        p1t = project(cx - dx, cz - dz, wall_height)
        p2t = project(cx + dx, cz + dz, wall_height)

        color = (70, 70, 220) if wall.get("type") == "load_bearing" else (220, 170, 70)
        cv2.line(canvas, p1b, p1t, color, 2, cv2.LINE_AA)
        cv2.line(canvas, p2b, p2t, color, 2, cv2.LINE_AA)
        cv2.line(canvas, p1t, p2t, color, 2, cv2.LINE_AA)
        cv2.line(canvas, p1b, p2b, (100, 100, 100), 1, cv2.LINE_AA)

    return canvas


def _render_wireframe_overview(base_img, model):
    canvas = _blank_like(base_img)
    _put_title(canvas, "19_wireframe_overview")

    walls = (model or {}).get("walls", [])
    floors = (model or {}).get("floors", [])
    doors = (model or {}).get("doors", [])
    windows = (model or {}).get("windows", [])

    if not walls and not floors:
        cv2.putText(canvas, "No model data available", (20, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
        return canvas

    points = []

    for f in floors:
        cx, cz = f.get("center", [0, 0])
        fw = float(f.get("width", 0.1))
        fd = float(f.get("depth", 0.1))
        points.extend([
            (cx - fw / 2, cz - fd / 2),
            (cx + fw / 2, cz - fd / 2),
            (cx + fw / 2, cz + fd / 2),
            (cx - fw / 2, cz + fd / 2),
        ])

    wall_segments = []
    for w in walls:
        cx, cz = w.get("center", [0, 0])
        length = float(w.get("length", 0.1))
        angle = float(w.get("angle", 0.0))
        dx = math.cos(angle) * (length / 2.0)
        dz = math.sin(angle) * (length / 2.0)
        x1, y1 = cx - dx, cz - dz
        x2, y2 = cx + dx, cz + dz
        wall_segments.append((x1, y1, x2, y2, w.get("type", "partition")))
        points.extend([(x1, y1), (x2, y2)])

    if not points:
        cv2.putText(canvas, "Insufficient geometry for wireframe", (20, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
        return canvas

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    h, wimg = canvas.shape[:2]
    pad = 28
    span_x = max(max_x - min_x, 1e-6)
    span_y = max(max_y - min_y, 1e-6)

    def map_xy(x, y):
        mx = int(((x - min_x) / span_x) * (wimg - 2 * pad) + pad)
        my = int(((y - min_y) / span_y) * (h - 2 * pad) + pad)
        return mx, my

    for f in floors:
        cx, cz = f.get("center", [0, 0])
        fw = float(f.get("width", 0.1))
        fd = float(f.get("depth", 0.1))
        p1 = map_xy(cx - fw / 2, cz - fd / 2)
        p2 = map_xy(cx + fw / 2, cz + fd / 2)
        cv2.rectangle(canvas, p1, p2, (70, 130, 70), 1)

    for x1, y1, x2, y2, wall_type in wall_segments:
        p1 = map_xy(x1, y1)
        p2 = map_xy(x2, y2)
        color = (220, 220, 220) if wall_type == "load_bearing" else (140, 200, 140)
        cv2.line(canvas, p1, p2, color, 1, cv2.LINE_AA)

    for d in doors:
        px = float(d.get("position", [0, 0, 0])[0])
        pz = float(d.get("position", [0, 0, 0])[2])
        cv2.circle(canvas, map_xy(px, pz), 2, (20, 180, 255), -1)

    for win in windows:
        px = float(win.get("position", [0, 0, 0])[0])
        pz = float(win.get("position", [0, 0, 0])[2])
        cv2.circle(canvas, map_xy(px, pz), 2, (255, 190, 20), -1)

    cv2.putText(canvas, "LB: light gray | PT: green | doors: cyan | windows: amber", (16, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 160, 160), 1, cv2.LINE_AA)
    return canvas


def save_intermediate_artifacts(
    base_dir,
    original_image,
    gray,
    lines_raw,
    walls,
    rooms,
    doors,
    windows,
    wall_graph,
    load_bearing,
    partitions,
    recommendations,
    cost_estimation,
    span_analysis,
    warnings,
    model,
):
    out_dir = os.path.join(base_dir, ARTIFACT_DIR_NAME)
    os.makedirs(out_dir, exist_ok=True)

    original = _ensure_bgr(original_image)
    if original is None:
        raise ValueError("original_image is required for artifact rendering")

    _add_legend(original, [
        ("Base input floor-plan image", (180, 180, 180)),
    ])

    cv2.imwrite(os.path.join(out_dir, "01_original.png"), original)

    preprocessed = _preprocess_gray(gray)
    preprocessed = cv2.cvtColor(preprocessed, cv2.COLOR_GRAY2BGR)
    _add_legend(preprocessed, [
        ("White: likely walls/features", (255, 255, 255)),
        ("Black: background", (0, 0, 0)),
    ])
    cv2.imwrite(os.path.join(out_dir, "02_preprocessed.png"), preprocessed)

    edges = cv2.Canny(gray, 70, 180)
    edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    _add_legend(edges, [
        ("White: detected edges", (255, 255, 255)),
        ("Black: non-edge", (0, 0, 0)),
    ])
    cv2.imwrite(os.path.join(out_dir, "03_edges.png"), edges)

    raw_lines_img = original.copy()
    _put_title(raw_lines_img, "04_lines_raw")
    if lines_raw is not None:
        for ln in lines_raw:
            x1, y1, x2, y2 = ln[0]
            cv2.line(raw_lines_img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 180, 255), 1, cv2.LINE_AA)
    _add_legend(raw_lines_img, [
        ("Orange: raw Hough lines", (0, 180, 255)),
    ])
    cv2.imwrite(os.path.join(out_dir, "04_lines_raw.png"), raw_lines_img)

    merged_lines_img = original.copy()
    _put_title(merged_lines_img, "05_lines_merged")
    _draw_walls(merged_lines_img, walls, (20, 210, 255), thickness=2)
    _add_legend(merged_lines_img, [
        ("Cyan: merged line segments", (20, 210, 255)),
    ])
    cv2.imwrite(os.path.join(out_dir, "05_lines_merged.png"), merged_lines_img)

    walls_img = original.copy()
    _put_title(walls_img, "06_walls_detected")
    _draw_walls(walls_img, walls, (70, 200, 255), thickness=3)
    _add_legend(walls_img, [
        ("Light blue: detected walls", (70, 200, 255)),
    ])
    cv2.imwrite(os.path.join(out_dir, "06_walls_detected.png"), walls_img)

    rooms_img = original.copy()
    _put_title(rooms_img, "07_rooms_detected")
    _draw_rooms(rooms_img, rooms)
    _add_legend(rooms_img, [
        ("Amber boxes: room boundaries", (255, 180, 0)),
        ("White text: room labels", (255, 255, 255)),
    ])
    cv2.imwrite(os.path.join(out_dir, "07_rooms_detected.png"), rooms_img)

    doors_img = original.copy()
    _put_title(doors_img, "08_doors_detected")
    _draw_openings(doors_img, doors, (20, 180, 255), "D")
    _add_legend(doors_img, [
        ("Cyan boxes: detected doors", (20, 180, 255)),
    ])
    cv2.imwrite(os.path.join(out_dir, "08_doors_detected.png"), doors_img)

    windows_img = original.copy()
    _put_title(windows_img, "09_windows_detected")
    _draw_openings(windows_img, windows, (255, 190, 20), "W")
    _add_legend(windows_img, [
        ("Amber boxes: detected windows", (255, 190, 20)),
    ])
    cv2.imwrite(os.path.join(out_dir, "09_windows_detected.png"), windows_img)

    graph_img = original.copy()
    _put_title(graph_img, "10_wall_graph")
    _draw_graph(graph_img, wall_graph)
    _add_legend(graph_img, [
        ("Green lines: graph edges", (120, 220, 120)),
        ("Orange dots: graph nodes", (0, 80, 255)),
    ])
    cv2.imwrite(os.path.join(out_dir, "10_wall_graph.png"), graph_img)

    lb_img = original.copy()
    _put_title(lb_img, "11_load_bearing")
    _draw_walls(lb_img, load_bearing, (60, 60, 220), thickness=3)
    _add_legend(lb_img, [
        ("Red: load-bearing walls", (60, 60, 220)),
    ])
    cv2.imwrite(os.path.join(out_dir, "11_load_bearing.png"), lb_img)

    part_img = original.copy()
    _put_title(part_img, "12_partition_walls")
    _draw_walls(part_img, partitions, (220, 170, 70), thickness=3)
    _add_legend(part_img, [
        ("Tan: partition walls", (220, 170, 70)),
    ])
    cv2.imwrite(os.path.join(out_dir, "12_partition_walls.png"), part_img)

    material_img = original.copy()
    _put_title(material_img, "13_material_overlay")
    for rec in recommendations or []:
        start = rec.get("start", [0, 0])
        end = rec.get("end", [0, 0])
        color = MATERIAL_COLORS.get(rec.get("primary_material"), (200, 200, 200))
        cv2.line(material_img, (int(start[0]), int(start[1])), (int(end[0]), int(end[1])), color, 3, cv2.LINE_AA)
    _add_legend(material_img, [
        ("RCC", MATERIAL_COLORS["RCC"]),
        ("AAC Block", MATERIAL_COLORS["AAC Block"]),
        ("Fly Ash Brick", MATERIAL_COLORS["Fly Ash Brick"]),
        ("Steel Frame", MATERIAL_COLORS["Steel Frame"]),
        ("Precast Concrete", MATERIAL_COLORS["Precast Concrete"]),
        ("Red Brick", MATERIAL_COLORS["Red Brick"]),
    ], title="Material Legend")
    cv2.imwrite(os.path.join(out_dir, "13_material_overlay.png"), material_img)

    cost_img = original.copy()
    _put_title(cost_img, "14_cost_overlay")
    recs = recommendations or []
    wall_costs = (cost_estimation or {}).get("wall_costs", [])
    for i, rec in enumerate(recs):
        if i >= len(wall_costs):
            break
        cost_item = wall_costs[i]
        start = rec.get("start", [0, 0])
        end = rec.get("end", [0, 0])
        x1, y1, x2, y2 = int(start[0]), int(start[1]), int(end[0]), int(end[1])
        cv2.line(cost_img, (x1, y1), (x2, y2), (120, 240, 120), 2, cv2.LINE_AA)
        mid = (int((x1 + x2) / 2), int((y1 + y2) / 2))
        cv2.putText(cost_img, str(cost_item.get("wall_total", 0)), mid, cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)
    _add_legend(cost_img, [
        ("Green lines: priced wall segments", (120, 240, 120)),
        ("White text: wall cost", (255, 255, 255)),
    ])
    cv2.imwrite(os.path.join(out_dir, "14_cost_overlay.png"), cost_img)

    span_img = original.copy()
    _put_title(span_img, "15_span_visualization")
    span_by_room = {item.get("room"): item for item in span_analysis or []}
    for room in rooms or []:
        x = int(room.get("x", 0))
        y = int(room.get("y", 0))
        w = int(room.get("width", 0))
        h = int(room.get("height", 0))
        room_label = room.get("label")
        sev = span_by_room.get(room_label, {}).get("severity", "ok")
        color = _span_color(sev)
        cv2.rectangle(span_img, (x, y), (x + w, y + h), color, 2)
        span_text = str(span_by_room.get(room_label, {}).get("max_span_m", "n/a"))
        cv2.putText(span_img, span_text + "m", (x + 2, max(y + 14, 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
    _add_legend(span_img, [
        ("Red: critical span", (40, 40, 220)),
        ("Orange: high span", (20, 140, 255)),
        ("Yellow: medium span", (0, 220, 220)),
        ("Green: acceptable span", (0, 170, 80)),
    ])
    cv2.imwrite(os.path.join(out_dir, "15_span_visualization.png"), span_img)

    score_img = original.copy()
    _put_title(score_img, "16_structural_scores")
    for idx, wall in enumerate(walls or []):
        x1, y1, x2, y2 = _wall_points(wall)
        score = int(wall.get("structural_score", 50))
        if score >= 75:
            color = (40, 220, 40)
        elif score >= 55:
            color = (0, 220, 220)
        else:
            color = (40, 120, 255)
        cv2.line(score_img, (x1, y1), (x2, y2), color, 3, cv2.LINE_AA)
        cv2.putText(score_img, str(score), (int((x1 + x2) / 2), int((y1 + y2) / 2)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)
    _add_legend(score_img, [
        ("Green: score >= 75", (40, 220, 40)),
        ("Yellow: score 55-74", (0, 220, 220)),
        ("Orange: score < 55", (40, 120, 255)),
    ])
    cv2.imwrite(os.path.join(out_dir, "16_structural_scores.png"), score_img)

    cleaned_img = _render_cleaned_geometry(original, model)
    _add_legend(cleaned_img, [
        ("Red: load-bearing geometry", (70, 70, 230)),
        ("Tan: partition geometry", (220, 170, 70)),
    ])
    cv2.imwrite(os.path.join(out_dir, "17_cleaned_geometry.png"), cleaned_img)

    preview_img = _render_3d_preview(original, model)
    _add_legend(preview_img, [
        ("Green planes: floors", (60, 110, 70)),
        ("Red walls: load-bearing", (70, 70, 220)),
        ("Tan walls: partitions", (220, 170, 70)),
    ])
    cv2.imwrite(os.path.join(out_dir, "18_3d_projection_preview.png"), preview_img)

    wireframe_img = _render_wireframe_overview(original, model)
    _add_legend(wireframe_img, [
        ("Light gray: load-bearing walls", (220, 220, 220)),
        ("Green: partition walls / rooms", (140, 200, 140)),
        ("Cyan dots: doors", (20, 180, 255)),
        ("Amber dots: windows", (255, 190, 20)),
    ])
    cv2.imwrite(os.path.join(out_dir, "19_wireframe_overview.png"), wireframe_img)

    info = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "artifacts_dir": out_dir,
        "counts": {
            "walls": len(walls or []),
            "rooms": len(rooms or []),
            "doors": len(doors or []),
            "windows": len(windows or []),
            "load_bearing": len(load_bearing or []),
            "partitions": len(partitions or []),
            "warnings": len(warnings or []),
            "recommendations": len(recommendations or []),
        },
        "cost_total": (cost_estimation or {}).get("total_cost", 0),
        "files": [
            "01_original.png",
            "02_preprocessed.png",
            "03_edges.png",
            "04_lines_raw.png",
            "05_lines_merged.png",
            "06_walls_detected.png",
            "07_rooms_detected.png",
            "08_doors_detected.png",
            "09_windows_detected.png",
            "10_wall_graph.png",
            "11_load_bearing.png",
            "12_partition_walls.png",
            "13_material_overlay.png",
            "14_cost_overlay.png",
            "15_span_visualization.png",
            "16_structural_scores.png",
            "17_cleaned_geometry.png",
            "18_3d_projection_preview.png",
            "19_wireframe_overview.png",
        ],
    }

    with open(os.path.join(out_dir, "artifacts_info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)

    return out_dir
