import math

def distance(p1, p2):
    return math.sqrt(
        (p1[0]-p2[0])**2 +
        (p1[1]-p2[1])**2
    )


def extract_nodes(walls, threshold=10):

    nodes = []

    for wall in walls:

        for point in [wall["start"], wall["end"]]:

            found = False

            for n in nodes:
                if distance(point, n) < threshold:
                    found = True
                    break

            if not found:
                nodes.append(point)

    return nodes

def find_closest_node(point, nodes, threshold=15):

    closest = None
    min_dist = float("inf")

    for n in nodes:
        d = distance(point, n)
        if d < min_dist:
            min_dist = d
            closest = n

    if min_dist < threshold:
        return tuple(closest)

    return None


def build_graph(walls, nodes):

    graph = {tuple(n): [] for n in nodes}

    for wall in walls:

        start_raw = wall["start"]
        end_raw = wall["end"]

        start = find_closest_node(start_raw, nodes)
        end = find_closest_node(end_raw, nodes)

        # Skip if mapping fails
        if start is None or end is None:
            continue

        graph[start].append(end)
        graph[end].append(start)

    return graph

def compute_node_degrees(graph):

    degrees = {}

    for node in graph:
        degrees[node] = len(graph[node])

    return degrees

def build_wall_graph(walls):

    nodes = extract_nodes(walls)

    graph = build_graph(walls, nodes)

    degrees = compute_node_degrees(graph)

    return {
        "nodes": nodes,
        "graph": graph,
        "degrees": degrees
    }