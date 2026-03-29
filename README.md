# 🏗️ StructureAI — Autonomous Structural Intelligence System v2.0

> **Floor Plan Image → AI Analysis → 3D Building Model → Engineering Report**

---

## 🚀 What's New in v2.0

### Backend Improvements
| Module | Enhancement |
|--------|------------|
| **Wall Detection** | Angle-based clustering, collinear merging with gap bridging, axis-snap, deduplication |
| **Floor Parser** | CLAHE contrast enhancement + adaptive + Otsu dual-mask, scale-adaptive Hough params |
| **Room Detection** | Connected component analysis, flood-fill, IoU-based deduplication, auto room labeling |
| **Door/Window Detector** | HoughCircles arc detection + wall-gap scanning + triple-line window detection |
| **Load Bearing** | Boundary detection + wall connectivity graph + multi-factor structural scoring (0–100) |
| **Structural Warnings** | 4-level severity (critical/high/medium/low), span-based physics checks, wall-ratio analysis |
| **Material Recommender** | Score-aware recommendations, span-based logic, detailed specs (strength, fire rating) |
| **Cost Estimator** | Area-based costing (length × height), labor + material split, GST, contingency, finishing |
| **Report Generator** | Structural grade (A+–F), executive summary, key actions, professional disclaimer |
| **3D Generator** | Roof slab, door markers, window markers, per-room floor slabs, building stats |

### Frontend Improvements
- 🎨 **Full dark-mode redesign** — professional engineering UI
- 📊 **Structural grade badge** (A+–F) with score
- 🏗️ **3D viewer** — custom orbit controls (no CDN dependency), roof/floor toggles, wireframe mode, top/iso presets
- 📈 **Span analysis** with horizontal bar charts
- 💰 **Detailed cost breakdown** — material, labor, GST, contingency, finishing
- ⚠️ **Color-coded warnings** — severity levels with recommendations
- 🚪 **Room table** — label, area, span, aspect ratio
- 🧱 **Material cards** — alternatives, specs, structural scores
- ⬇️ **JSON export** + print

---

## 📁 Project Structure

```
autonomous-structural-ai/
├── backend/
│   ├── app.py                    ← FastAPI main (enhanced pipeline)
│   ├── parser/
│   │   ├── floor_parser.py       ← CLAHE + adaptive threshold + Hough
│   │   ├── wall_detector.py      ← Clustering + collinear merge + dedup
│   │   ├── room_detector.py      ← Connected components + room labeling
│   │   └── door_window_detector.py ← Arc + gap + triple-line detection
│   ├── structural/
│   │   ├── load_bearing.py       ← Boundary graph + structural scoring
│   │   ├── warnings.py           ← 4-level severity warning system
│   │   └── span_detector.py      ← Span analysis per room
│   ├── materials/
│   │   ├── recommender.py        ← Score-aware material selection
│   │   ├── cost_estimator.py     ← Area-based cost with GST + contingency
│   │   └── material_db.py        ← Material specs database
│   ├── generator/
│   │   ├── model_3d.py           ← Full scene: walls, floors, doors, windows, roof
│   │   └── export_threejs.py     ← JSON export
│   └── report/
│       └── report_generator.py   ← Structured report with grade
├── frontend/
│   ├── index.html                ← Full redesigned UI (single file)
│   └── model.json                ← Generated 3D scene (auto-updated)
├── sample_input/
│   ├── sample1.jpg
│   └── sample2.jpg
└── requirements.txt
```

---

## ⚡ Quick Start

### 1. Git Clone
```bash
git clone https://github.com/joysarkar83/autonomous-structural-ai.git
cd autonomous-structural-ai
```

### 2. Virtual Environment (Not mandatory but recommended)
```bash
python -m venv venv
On Linux or Mac: source venv/bin/activate
On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Backend
```bash
cd backend
pip install -r ../requirements.txt
python -m uvicorn app:app --reload
```

### 4. Frontend
```bash
cd ../frontend
python -m http.server 5500
```

Open `http://localhost:5500` in your browser.

---

## 🎯 Pipeline Flow

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

---

## 🧪 Test with Sample Images

Sample floor plans are in `sample_input/`. Upload `sample1.jpg` or `sample2.jpg` to test.

For best results use:
- High contrast black-and-white floor plans
- PNG or high-quality JPG
- At least 600×600 px resolution
- Architectural drawings (not hand-sketched)

---

## 🏆 Hackathon Highlights

| Feature | Status |
|---------|--------|
| Real CV pipeline (no mock data) | ✅ |
| Structural engineering scoring | ✅ |
| Interactive 3D viewer | ✅ |
| Exportable JSON report | ✅ |
| Professional UI | ✅ |
| Modular FastAPI backend | ✅ |
| Works on real floor plan images | ✅ |

---

## ⚠️ Disclaimer

This system is an AI prototype for preliminary structural assessment only.
All structural design decisions must be validated by a licensed structural engineer.
