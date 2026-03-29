import json
import os


def export_threejs(data):

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Go up to project root
    project_root = os.path.abspath(
        os.path.join(BASE_DIR, "..", "..")
    )

    # Correct frontend path
    output_path = os.path.join(
        project_root,
        "frontend",
        "model.json"
    )

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print("✅ model.json written to:", output_path)