from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import shutil
import os
import traceback
import cv2
import numpy as np

from parser.floor_parser import parse_floor_plan
from parser.wall_detector import detect_walls
from parser.room_detector import detect_rooms
from parser.door_window_detector import detect_doors_windows
from structural.load_bearing import detect_load_bearing
from structural.warnings import structural_warnings
from structural.span_detector import detect_large_spans
from materials.recommender import recommend_materials
from materials.cost_estimator import estimate_cost
from generator.model_3d import generate_3d
from generator.export_threejs import export_threejs
from report.report_generator import generate_report
from geometry.wall_graph import build_wall_graph
from structural.boundary import detect_outer_walls
from diagnostics.intermediate_artifacts import save_intermediate_artifacts

app = FastAPI(
    title="Autonomous Structural Intelligence System",
    description="AI-powered floor plan analysis → 3D model + engineering report",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_PATH = os.path.join(BASE_DIR, "..", "sample_input", "input.png")
os.makedirs(os.path.dirname(UPLOAD_PATH), exist_ok=True)


@app.get("/")
def home():
    return {
        "message": "Autonomous Structural Intelligence System v2.0",
        "status": "running",
        "endpoints": ["/upload", "/health", "/docs"]
    }


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.post("/upload")
async def upload(file: UploadFile = File(...), skip_text_filter: bool = Query(False), debug: bool = Query(False)):
    # Validate file type
    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff")):
        raise HTTPException(400, "Unsupported file type. Please upload PNG, JPG, or BMP.")

    try:
        # Save uploaded file
        with open(UPLOAD_PATH, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # ── Stage 1: Image parsing with optional TEXT FILTERING ──────────
        if skip_text_filter:
            # Fallback: parse with text filtering disabled (for diagnostic purposes)
            img = cv2.imread(UPLOAD_PATH)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            denoised = cv2.fastNlMeansDenoising(gray, h=10)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            
            adaptive = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, blockSize=15, C=4)
            _, otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            combined = cv2.bitwise_or(adaptive, otsu)
            
            kernel_clean = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel_clean, iterations=1)
            kernel_dilate = np.ones((2, 2), np.uint8)
            strengthened = cv2.dilate(cleaned, kernel_dilate, iterations=1)
            
            scale = max(img.shape[1], img.shape[0]) / 800.0
            min_line_len = int(60 * scale)
            max_gap = int(20 * scale)
            threshold = int(80 * scale)
            
            lines = cv2.HoughLinesP(strengthened, rho=1, theta=np.pi/180, threshold=threshold, minLineLength=min_line_len, maxLineGap=max_gap)
            text_mask = np.zeros(gray.shape, dtype=np.uint8)
            text_regions = []
        else:
            img, lines, gray, text_mask, text_regions = parse_floor_plan(UPLOAD_PATH, debug=debug)

        # ── Stage 2: Wall detection ─────────────────────────────
        walls = detect_walls(lines, image_gray=gray)

        if not walls:
            return {
                "status": "warning",
                "message": "No walls detected. Try a higher-contrast floor plan image.",
                "summary": {"walls_detected": 0}
            }

        # ── Stage 3: Room detection ─────────────────────────────
        wall_graph = build_wall_graph(walls)
        rooms = detect_rooms(img)
        
        # Validate room detection
        if not rooms:
            # If no rooms detected, create dummy room for the entire image bounds
            h, w = img.shape[:2]
            rooms = [{
                "label": "Space",
                "x": 0,
                "y": 0,
                "width": w,
                "height": h,
                "area": w * h,
                "area_sqm": round((w * h) * 0.025 * 0.025, 2),
                "aspect_ratio": round((w / h) if h != 0 else 1.0, 2)
            }]
        
        doors, windows = detect_doors_windows(img, walls=walls)
        outer_walls, inner_walls = detect_outer_walls(walls)
        load_bearing, partitions = detect_load_bearing(
            walls,
            wall_graph,
            outer_walls
        )

        # Attach type back to main walls list
        lb_ids = {id(w) for w in load_bearing}
        for w in walls:
            if id(w) in lb_ids:
                w["type"] = "load_bearing"
            else:
                w["type"] = "partition"

        # ── Stage 6: Warnings ───────────────────────────────────
        warnings = structural_warnings(walls, rooms)
        span_analysis = detect_large_spans(rooms)

        # ── Stage 7: Materials & cost ───────────────────────────
        recommendations = recommend_materials(load_bearing, partitions)
        cost_estimation = estimate_cost(walls, recommendations)

        # ── Stage 8: Report ─────────────────────────────────────
        report = generate_report(
            walls, rooms, load_bearing,
            recommendations, cost_estimation, warnings
        )


        # ── Stage 9: 3D Model with TEXT ANNOTATIONS ─────────────
        model = generate_3d(walls, rooms, doors, windows, warnings, text_regions=text_regions)
        export_threejs(model)

        # ── Stage 10: Intermediate artifact export ──────────────
        artifact_dir = save_intermediate_artifacts(
            base_dir=BASE_DIR,
            original_image=img,
            gray=gray,
            lines_raw=lines,
            walls=walls,
            rooms=rooms,
            doors=doors,
            windows=windows,
            wall_graph=wall_graph,
            load_bearing=load_bearing,
            partitions=partitions,
            recommendations=recommendations,
            cost_estimation=cost_estimation,
            span_analysis=span_analysis,
            warnings=warnings,
            model=model,
        )

        return {
            "status": "success",

            "summary": {
                "walls_detected": len(walls),
                "rooms_detected": len(rooms),
                "doors_detected": len(doors),
                "windows_detected": len(windows),
                "load_bearing_walls": len(load_bearing),
                "partition_walls": len(partitions)
            },

            "structural_grade": report["structural_grade"],
            "building_stats": model.get("stats", {}),
            "material_recommendations": recommendations,
            "cost_estimation": cost_estimation,
            "structural_warnings": warnings,
            "span_analysis": span_analysis,
            "rooms": rooms,
            "graph_nodes": len(wall_graph["nodes"]),
            "graph_connections": len(wall_graph["graph"]),
            "report": report,
            "intermediate_output_dir": artifact_dir
        }
    

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[ERROR] {tb}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")