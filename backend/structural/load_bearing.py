import math


def wall_length(wall):
    x1, y1 = wall["start"]
    x2, y2 = wall["end"]

    return math.sqrt(
        (x2-x1)**2 +
        (y2-y1)**2
    )


def detect_load_bearing(walls, wall_graph, outer_walls):

    degrees = wall_graph["degrees"]

    load_bearing = []
    partitions = []

    # ✅ MOVE IT HERE (INSIDE FUNCTION)
    outer_set = set([
        (tuple(w["start"]), tuple(w["end"]))
        for w in outer_walls
    ])

    for wall in walls:

        start = tuple(wall["start"])
        end = tuple(wall["end"])

        # 🔥 RULE 0: outer walls
        if (start, end) in outer_set or (end, start) in outer_set:
            wall["type"] = "load_bearing"
            load_bearing.append(wall)
            continue

        d1 = degrees.get(start, 1)
        d2 = degrees.get(end, 1)

        length = wall_length(wall)

        if d1 >= 3 or d2 >= 3:
            wall["type"] = "load_bearing"
            load_bearing.append(wall)
            continue

        if d1 >= 2 and d2 >= 2:
            wall["type"] = "load_bearing"
            load_bearing.append(wall)
            continue

        if length > 150:
            wall["type"] = "load_bearing"
            load_bearing.append(wall)
            continue

        wall["type"] = "partition"
        partitions.append(wall)

    return load_bearing, partitions