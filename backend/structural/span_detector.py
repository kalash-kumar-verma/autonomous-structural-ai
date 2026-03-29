PIXEL_TO_METER = 0.025


def detect_large_spans(rooms):
    """Detect rooms with structurally significant spans."""
    results = []
    for room in rooms:
        w_m = room["width"] * PIXEL_TO_METER
        h_m = room["height"] * PIXEL_TO_METER
        max_span = max(w_m, h_m)
        results.append({
            "room": room.get("label", "Room"),
            "span_width_m": round(w_m, 2),
            "span_height_m": round(h_m, 2),
            "max_span_m": round(max_span, 2),
            "requires_beam": max_span > 4.5,
            "severity": (
                "critical" if max_span > 9.0 else
                "high" if max_span > 6.0 else
                "medium" if max_span > 4.5 else
                "ok"
            )
        })
    results.sort(key=lambda r: r["max_span_m"], reverse=True)
    return results
