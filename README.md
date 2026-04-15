# Autonomous Structural AI

Autonomous Structural AI is an end-to-end floor-plan intelligence system that transforms a 2D architectural image into structural insights, a 3D building model, and an engineering-style report.

It combines computer vision, structural heuristics, material recommendation logic, and interactive visualization in a single workflow.

## What this project does

Given a floor plan image (`PNG/JPG/BMP`), the system:

- Parses and enhances the drawing using CV preprocessing
- Detects walls, rooms, doors, and windows
- Classifies walls into load-bearing vs partition candidates
- Generates structural warnings with severity levels
- Detects large spans and potential structural risk zones
- Recommends materials by wall type and score
- Estimates construction cost (material + labor + GST + contingency)
- Produces a structural grade report
- Exports a 3D scene (`model.json`) for interactive frontend rendering

## Tech stack

### Backend
- FastAPI
- Uvicorn
- OpenCV
- NumPy

### Frontend
- HTML/CSS/JavaScript
- Three.js (`r128`) for 3D visualization

## Repository structure

```text
autonomous-structural-ai/
├── backend/
│   ├── app.py
│   ├── parser/
│   │   ├── floor_parser.py
│   │   ├── wall_detector.py
│   │   ├── room_detector.py
│   │   └── door_window_detector.py
│   ├── structural/
│   │   ├── load_bearing.py
│   │   ├── warnings.py
│   │   └── span_detector.py
│   ├── materials/
│   │   ├── recommender.py
│   │   ├── cost_estimator.py
│   │   └── material_db.py
│   ├── generator/
│   │   ├── model_3d.py
│   │   └── export_threejs.py
│   ├── report/
│   │   └── report_generator.py
│   └── ...
├── frontend/
│   ├── index.html
│   ├── script.js
│   ├── style.css
│   └── model.json
├── sample_input/
│   ├── sample1.jpg
│   └── sample2.jpg
├── requirements.txt
└── serve_frontend.py
```

## Installation Guide

### 1. Git Clone
```bash
git clone https://github.com/joysarkar83/autonomous-structural-ai.git
cd autonomous-structural-ai
```

### 2. Virtual Environment (Not mandatory but recommended)
```bash
python -m venv venv
source venv/bin/activate #On Linux or Mac
venv\Scripts\activate #On Windows
pip install -r requirements.txt
```

### 3. Backend
```bash
cd backend
python -m uvicorn app:app --reload
```

### 4. Frontend
```bash
#Create New Terminal
cd frontend
python -m http.server 5500
```

Open `http://localhost:5500` in your browser.


## Pipeline Flow

```
Upload PNG/JPG
     │
     ▼
parse_floor_plan()          ← CLAHE + adaptive threshold + Hough
     │
     ▼
detect_walls()              ← Cluster → merge collinear → dedup
     │
     ├──► detect_rooms()    ← Connected components + room labeling
     │
     ├──► detect_doors_windows()  ← Arcs + gap scan + triple lines
     │
     ▼
detect_load_bearing()       ← Boundary + graph + structural score
     │
     ├──► structural_warnings()   ← 4-level severity system
     ├──► detect_large_spans()    ← Span physics checks
     ├──► recommend_materials()   ← Score-aware recommendations
     ├──► estimate_cost()         ← Area-based + GST + contingency
     └──► generate_report()       ← Grade A+–F + executive summary
          │
          ▼
     generate_3d()          ← Walls + floors + doors + windows + roof
          │
          ▼
     export_threejs()        ← model.json → Three.js renderer
```

## API overview

### `GET /`
Basic service info and available endpoints.

### `GET /health`
Health status and version check.

### `POST /upload`
Main analysis endpoint.

**Input**
- `multipart/form-data`
- Field: `file` (image)

**Optional query params**
- `skip_text_filter` (bool): bypass text-filter path for diagnostics
- `debug` (bool): enable debug behavior in parsing stages

**Response includes**
- `summary` (wall/room/door/window counts)
- `structural_grade`
- `building_stats`
- `material_recommendations`
- `cost_estimation`
- `structural_warnings`
- `span_analysis`
- `rooms`
- `report`
- `intermediate_output_dir`

## Analysis pipeline

1. Floor plan parsing and line extraction
2. Wall detection and cleanup
3. Room detection
4. Door/window detection
5. Load-bearing inference
6. Structural warnings + span checks
7. Material recommendation
8. Cost estimation
9. Report generation
10. 3D model generation and export

## Frontend features

- Drag-and-drop floor plan upload
- Live analysis progress steps
- Structural grade card and metrics
- Interactive 3D viewer with:
  - rotation, zoom, pan
  - top/iso/front presets
  - wireframe mode
  - layer toggles (load-bearing, partition, rooms, doors, windows, warnings)
- Warning-to-wall highlighting in 3D
- Room analysis, span analysis, cost and material panels
- JSON export and print-friendly report workflow

## Input recommendations

For best analysis quality, use:

- High-contrast architectural floor plans
- PNG or high-quality JPG/BMP
- At least `600 x 600` resolution
- Clean drawings rather than hand sketches

## Dependencies

From `requirements.txt`:

- `fastapi==0.111.0`
- `uvicorn==0.29.0`
- `python-multipart==0.0.9`
- `opencv-python==4.9.0.80`
- `numpy==1.26.4`

## Important notes

- This system is intended for preliminary structural analysis.
- Generated recommendations and reports should be reviewed by a licensed structural engineer before real-world execution.
- Cost outputs are indicative and region/site dependent.

## License

ISC
