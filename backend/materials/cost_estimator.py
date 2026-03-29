COST_TABLE = {
    "RCC":              {"material": 2800, "labor": 1200, "unit": "sqm"},
    "AAC Block":        {"material": 750,  "labor": 350,  "unit": "sqm"},
    "Fly Ash Brick":    {"material": 850,  "labor": 400,  "unit": "sqm"},
    "Steel Frame":      {"material": 3500, "labor": 1800, "unit": "sqm"},
    "Precast Concrete": {"material": 2200, "labor": 800,  "unit": "sqm"},
    "Red Brick":        {"material": 950,  "labor": 450,  "unit": "sqm"},
}

WALL_HEIGHT_M = 3.0    # standard floor height
PIXEL_TO_METER = 0.025
CONTINGENCY_FACTOR = 1.12   # 12% contingency
GST_RATE = 0.18


def estimate_cost(walls, recommendations):
    """
    Enhanced cost estimation:
    - Per-wall material + labor cost
    - Wall area calculation (length × height)
    - GST + contingency
    - Category breakdown
    """
    wall_costs = []
    total_material = 0
    total_labor = 0
    category_totals = {}

    for rec in recommendations:
        material = rec["primary_material"]
        costs = COST_TABLE.get(material, {"material": 1000, "labor": 500, "unit": "sqm"})

        # Find matching wall for actual length
        start = rec.get("start", [0, 0])
        end = rec.get("end", [0, 0])
        length_px = ((end[0]-start[0])**2 + (end[1]-start[1])**2) ** 0.5
        length_m = max(length_px * PIXEL_TO_METER, 0.5)

        wall_area_sqm = length_m * WALL_HEIGHT_M

        mat_cost = wall_area_sqm * costs["material"]
        lab_cost = wall_area_sqm * costs["labor"]
        wall_total = mat_cost + lab_cost

        total_material += mat_cost
        total_labor += lab_cost

        wtype = rec["wall_type"]
        category_totals[wtype] = category_totals.get(wtype, 0) + wall_total

        wall_costs.append({
            "wall_type": wtype,
            "material": material,
            "length_m": round(length_m, 2),
            "area_sqm": round(wall_area_sqm, 2),
            "material_cost": round(mat_cost),
            "labor_cost": round(lab_cost),
            "wall_total": round(wall_total),
            "structural_score": rec.get("structural_score", 0)
        })

    subtotal = total_material + total_labor
    contingency = subtotal * (CONTINGENCY_FACTOR - 1)
    gst = (subtotal + contingency) * GST_RATE
    grand_total = subtotal + contingency + gst

    # Approximate finishing costs
    finishing_estimate = grand_total * 0.25

    return {
        "breakdown": {
            "material_cost": round(total_material),
            "labor_cost": round(total_labor),
            "subtotal": round(subtotal),
            "contingency_12pct": round(contingency),
            "gst_18pct": round(gst),
            "finishing_estimate": round(finishing_estimate)
        },
        "total_cost": round(grand_total),
        "total_with_finishing": round(grand_total + finishing_estimate),
        "category_totals": {k: round(v) for k, v in category_totals.items()},
        "wall_costs": wall_costs,
        "currency": "INR",
        "disclaimer": "Estimates are indicative. Actual costs depend on local rates, site conditions, and detailed drawings."
    }
