def detect_outer_walls(walls):

    xs = []
    ys = []

    for wall in walls:
        xs.extend([wall["start"][0], wall["end"][0]])
        ys.extend([wall["start"][1], wall["end"][1]])

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    outer_walls = []
    inner_walls = []

    threshold = 20  # tolerance

    for wall in walls:

        x1, y1 = wall["start"]
        x2, y2 = wall["end"]

        # Check if wall lies on boundary
        if (
            abs(x1 - min_x) < threshold or
            abs(x1 - max_x) < threshold or
            abs(y1 - min_y) < threshold or
            abs(y1 - max_y) < threshold or
            abs(x2 - min_x) < threshold or
            abs(x2 - max_x) < threshold or
            abs(y2 - min_y) < threshold or
            abs(y2 - max_y) < threshold
        ):
            outer_walls.append(wall)
        else:
            inner_walls.append(wall)

    return outer_walls, inner_walls