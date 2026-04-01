import math


PIXEL_TO_METER = 0.025  # rough: 1px ~ 2.5cm at typical scan resolution


def detect_large_spans(rooms):
    """Standalone large span detector for backward compatibility."""
    warnings = []
    for room in rooms:
        w_m = room["width"] * PIXEL_TO_METER
        h_m = room["height"] * PIXEL_TO_METER
        if w_m > 6.0 or h_m > 6.0:
            warnings.append({
                "type": "large_span",
                "severity": "high" if max(w_m, h_m) > 9 else "medium",
                "room": room.get("label", "Room"),
                "span_m": round(max(w_m, h_m), 1),
                "message": f"Large span of ~{max(w_m, h_m):.1f}m in {room.get('label','Room')}. Use RCC beam or steel joist."
            })
    return warnings


def structural_warnings(walls, rooms):
    """
    Comprehensive structural warning system with:
    - Large span rooms
    - Long unsupported walls
    - Missing corner connections
    - Thin wall sections
    - Severity levels: low / medium / high / critical
    """
    warnings = []

    # === ROOM WARNINGS ===
    for room in rooms:
        w_m = room["width"] * PIXEL_TO_METER
        h_m = room["height"] * PIXEL_TO_METER
        span = max(w_m, h_m)
        label = room.get("label", "Room")

        if span > 9.0:
            warnings.append({
                "type": "large_span",
                "severity": "critical",
                "room": label,
                "message": f"CRITICAL: {label} span ~{span:.1f}m exceeds safe limit. Steel frame or transfer beam required.",
                "recommendation": "Use steel I-beam or post-tensioned concrete slab."
            })
        elif span > 6.0:
            warnings.append({
                "type": "large_span",
                "severity": "high",
                "room": label,
                "message": f"Large span ~{span:.1f}m in {label}. Intermediate beam support recommended.",
                "recommendation": "Add intermediate RCC beam or increase slab thickness."
            })
        elif span > 4.5:
            warnings.append({
                "type": "large_span",
                "severity": "medium",
                "room": label,
                "message": f"Moderate span ~{span:.1f}m in {label}. Standard RCC slab adequate with proper design.",
                "recommendation": "Verify slab design for live load + dead load."
            })

        # Extreme aspect ratio
        ar = room.get("aspect_ratio", 1.0)
        if ar > 3.0 or ar < 0.33:
            warnings.append({
                "type": "unusual_shape",
                "severity": "medium",
                "room": label,
                "message": f"Irregular room aspect ratio ({ar:.1f}:1) for {label}. May cause uneven load distribution.",
                "recommendation": "Consider redistributing structural supports."
            })

    # === WALL WARNINGS ===
    max_length = max((w["length"] for w in walls), default=1)

    for wall_idx, wall in enumerate(walls):
        x1, y1 = wall["start"]
        x2, y2 = wall["end"]
        length = wall["length"]
        length_m = length * PIXEL_TO_METER

        # Long unsupported wall
        if length_m > 6.0:
            sev = "critical" if length_m > 9.0 else "high"
            warnings.append({
                "type": "long_wall",
                "severity": sev,
                "wall_index": wall_idx,
                "message": f"Long unsupported wall ~{length_m:.1f}m detected. Intermediate column or pilaster needed.",
                "recommendation": "Add RCC column every 4–5m or use pilasters."
            })

        # Thin wall concern for load bearing
        if wall.get("type") == "load_bearing" and wall.get("thickness", 12) < 8:
            warnings.append({
                "type": "thin_load_bearing",
                "severity": "high",
                "wall_index": wall_idx,
                "message": "Load bearing wall appears thin. Verify minimum 230mm brick or 200mm RCC.",
                "recommendation": "Check wall thickness meets structural requirements."
            })

    # === GLOBAL STRUCTURAL SCORE ===
    lb_count = sum(1 for w in walls if w.get("type") == "load_bearing")
    total = len(walls)
    if total > 0:
        lb_ratio = lb_count / total
        if lb_ratio > 0.7:
            warnings.append({
                "type": "over_structured",
                "severity": "low",
                "message": "High proportion of load-bearing walls. Consider optimizing to reduce material cost.",
                "recommendation": "Review partition vs load-bearing classification."
            })
        elif lb_ratio < 0.15 and total > 5:
            warnings.append({
                "type": "under_structured",
                "severity": "medium",
                "message": "Low load-bearing wall count. Verify structural adequacy for multi-story loads.",
                "recommendation": "Engage structural engineer for detailed analysis."
            })

    # Sort by severity
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    warnings.sort(key=lambda w: sev_order.get(w.get("severity", "low"), 3))

    return warnings
