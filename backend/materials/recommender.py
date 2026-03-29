MATERIAL_SPECS = {
    "RCC": {
        "description": "Reinforced Cement Concrete",
        "compressive_strength_mpa": 25,
        "cost_per_sqm": 2800,
        "fire_rating": "4hr",
        "sound_insulation": "high",
        "sustainability": "medium"
    },
    "AAC Block": {
        "description": "Autoclaved Aerated Concrete Block",
        "compressive_strength_mpa": 4,
        "cost_per_sqm": 750,
        "fire_rating": "4hr",
        "sound_insulation": "high",
        "sustainability": "high"
    },
    "Fly Ash Brick": {
        "description": "Fly Ash Brick",
        "compressive_strength_mpa": 7.5,
        "cost_per_sqm": 850,
        "fire_rating": "2hr",
        "sound_insulation": "medium",
        "sustainability": "high"
    },
    "Steel Frame": {
        "description": "Structural Steel Frame",
        "compressive_strength_mpa": 250,
        "cost_per_sqm": 3500,
        "fire_rating": "1hr",
        "sound_insulation": "low",
        "sustainability": "medium"
    },
    "Precast Concrete": {
        "description": "Precast Concrete Panel",
        "compressive_strength_mpa": 40,
        "cost_per_sqm": 2200,
        "fire_rating": "4hr",
        "sound_insulation": "high",
        "sustainability": "medium"
    },
    "Red Brick": {
        "description": "Traditional Red Clay Brick",
        "compressive_strength_mpa": 5,
        "cost_per_sqm": 950,
        "fire_rating": "2hr",
        "sound_insulation": "medium",
        "sustainability": "low"
    }
}


def recommend_materials(load_bearing, partitions):
    """
    Enhanced material recommendation:
    - Considers structural score, wall length, span
    - Provides primary + 2 alternatives
    - Includes technical justification
    """
    recommendations = []

    for wall in load_bearing:
        score = wall.get("structural_score", 60)
        length = wall.get("length", 100)
        length_m = length * 0.025

        if score >= 80 or length_m > 6.0:
            primary = "RCC"
            alternatives = ["Steel Frame", "Precast Concrete"]
            reason = f"High-load structural wall (score: {score}/100). RCC provides superior strength and durability."
        elif score >= 60:
            primary = "Precast Concrete"
            alternatives = ["RCC", "Steel Frame"]
            reason = f"Medium-load structural wall (score: {score}/100). Precast offers good strength with faster construction."
        else:
            primary = "RCC"
            alternatives = ["Precast Concrete", "Fly Ash Brick"]
            reason = f"Load-bearing classification (score: {score}/100). RCC recommended for safety margin."

        recommendations.append({
            "wall_type": "load_bearing",
            "start": [int(wall["start"][0]), int(wall["start"][1])],
            "end": [int(wall["end"][0]), int(wall["end"][1])],
            "structural_score": score,
            "primary_material": primary,
            "alternatives": alternatives,
            "specs": MATERIAL_SPECS[primary],
            "reason": reason,
            "is_exterior": score >= 75
        })

    for wall in partitions:
        length = wall.get("length", 100)
        length_m = length * 0.025

        if length_m > 5.0:
            primary = "Fly Ash Brick"
            alternatives = ["AAC Block", "Red Brick"]
            reason = "Long partition wall. Fly Ash Brick provides adequate strength and eco-friendliness."
        else:
            primary = "AAC Block"
            alternatives = ["Fly Ash Brick", "Red Brick"]
            reason = "Interior partition wall. AAC Block offers lightweight, excellent thermal insulation."

        recommendations.append({
            "wall_type": "partition",
            "start": [int(wall["start"][0]), int(wall["start"][1])],
            "end": [int(wall["end"][0]), int(wall["end"][1])],
            "structural_score": wall.get("structural_score", 30),
            "primary_material": primary,
            "alternatives": alternatives,
            "specs": MATERIAL_SPECS[primary],
            "reason": reason,
            "is_exterior": False
        })

    return recommendations
