// ── State ──────────────────────────────────────────────────
let analysisData = null;
const API = "http://127.0.0.1:8000";

const STEPS = [
    "Image Parsing", "Wall Detection", "Room Detection",
    "Doors & Windows", "Load Bearing", "Structural Analysis",
    "Materials", "Cost Estimation", "3D Generation"
];

// ── File input ─────────────────────────────────────────────
const fileInput = document.getElementById("file-input");
const previewImg = document.getElementById("preview-img");
const uploadPrompt = document.getElementById("upload-prompt");
const analyzeBtn = document.getElementById("analyze-btn");

fileInput.addEventListener("change", () => {
    const f = fileInput.files[0]; if (!f) return;
    previewImg.src = URL.createObjectURL(f);
    previewImg.style.display = "block";
    uploadPrompt.style.display = "none";
    analyzeBtn.disabled = false;
    document.getElementById("btn-text").textContent = `Analyze "${f.name}"`;
});

const zone = document.getElementById("upload-zone");
zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("dragover"); });
zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
zone.addEventListener("drop", e => {
    e.preventDefault(); zone.classList.remove("dragover");
    const f = e.dataTransfer.files[0]; if (!f) return;
    const dt = new DataTransfer(); dt.items.add(f);
    fileInput.files = dt.files; fileInput.dispatchEvent(new Event("change"));
});

// ── Analyze ────────────────────────────────────────────────
async function analyze() {
    const file = fileInput.files[0];
    if (!file) return showToast("Please select a floor plan image.", "error");

    analyzeBtn.disabled = true;
    document.getElementById("spinner").style.display = "block";
    document.getElementById("btn-text").textContent = "Analyzing...";
    document.getElementById("results").style.display = "none";
    document.getElementById("progress-section").style.display = "block";

    initSteps();
    const iv = animateProgress();

    try {
        const fd = new FormData();
        fd.append("file", file);
        const res = await fetch(`${API}/upload`, { method: "POST", body: fd });
        const data = await res.json();
        clearInterval(iv);
        setProgress(100, "Analysis complete");
        markAllDone();
        if (data.status === "success") {
            analysisData = data;
            await new Promise(r => setTimeout(r, 500));
            renderResults(data);
            showToast("Analysis complete!", "success");
        } else {
            showToast(data.message || "Analysis returned a warning.", "error");
        }
    } catch (e) {
        clearInterval(iv);
        setProgress(0, "Connection failed");
        showToast(`Cannot reach backend at ${API}. Is FastAPI running?`, "error");
        console.error(e);
    } finally {
        analyzeBtn.disabled = false;
        document.getElementById("spinner").style.display = "none";
        document.getElementById("btn-text").textContent = "Re-analyze";
        setTimeout(() => { document.getElementById("progress-section").style.display = "none"; }, 1500);
    }
}

// ── Progress ───────────────────────────────────────────────
function initSteps() {
    document.getElementById("steps").innerHTML =
        STEPS.map((s, i) => `<span class="step-tag" id="st-${i}">${s}</span>`).join("");
    setProgress(5, "Uploading image...");
}
function animateProgress() {
    let step = 0; activateStep(0);
    return setInterval(() => {
        if (step < STEPS.length - 1) {
            doneStep(step); step++; activateStep(step);
            setProgress(Math.min(5 + (step + 1) * 10, 90), `Running: ${STEPS[step]}...`);
        }
    }, 700);
}
function setProgress(pct, label) {
    document.getElementById("progress-fill").style.width = pct + "%";
    document.getElementById("progress-label").textContent = label;
    document.getElementById("progress-pct").textContent = pct + "%";
}
function activateStep(i) {
    document.querySelectorAll(".step-tag").forEach(el => el.classList.remove("active"));
    document.getElementById(`st-${i}`)?.classList.add("active");
}
function doneStep(i) {
    const el = document.getElementById(`st-${i}`);
    if (el) { el.classList.remove("active"); el.classList.add("done"); el.textContent = STEPS[i]; }
}
function markAllDone() { STEPS.forEach((_, i) => doneStep(i)); }

// ── Render results ─────────────────────────────────────────
function renderResults(data) {
    document.getElementById("results").style.display = "block";
    renderGrade(data.structural_grade);
    renderMetrics(data);
    renderWarnings(data.structural_warnings);
    renderRooms(data.rooms || data.model?.rooms || []);
    renderCost(data.cost_estimation);
    renderSpans(data.span_analysis);
    renderMaterials(data.material_recommendations);
    load3D();
    setTimeout(() => window.scrollTo({ top: 280, behavior: "smooth" }), 100);
}

function renderGrade(grade) {
    if (!grade) return;
    const letter = grade.grade;
    const cls = letter.includes("+") ? "grade-A" : `grade-${letter}`;
    const labels = {
        "A+": "Excellent Structure", "A": "Excellent Structure",
        "B": "Good Structure", "C": "Fair Structure",
        "D": "Needs Attention", "F": "Critical Issues"
    };
    document.getElementById("grade-card").innerHTML = `
          <div class="grade-ring ${cls}">${letter}</div>
          <div class="grade-meta">
            <div class="grade-eyebrow">Structural Safety Grade</div>
            <div class="grade-title">${labels[letter] || "Structural Grade"}</div>
            <div class="grade-desc">${grade.interpretation || ""}</div>
          </div>
          <div class="grade-score-wrap">
            <div class="grade-score-num">${grade.score}</div>
            <div class="grade-score-lbl">/ 100 Score</div>
          </div>
        `;
}

function renderMetrics(data) {
    const rooms = data.rooms || [];
    const summary = data.summary || {};
    const totalArea = rooms.reduce((s, r) => s + (r.area_sqm || 0), 0);
    const avgRoom = rooms.length ? totalArea / rooms.length : 0;
    const lbCount = summary.load_bearing_walls || 0;
    const wallCount = summary.walls_detected || 1;
    const lbRatio = lbCount / wallCount;
    const avgAR = rooms.length
        ? rooms.reduce((acc, r) => acc + (Number(r.aspect_ratio) || 1), 0) / rooms.length
        : 1;
    const shapeEff = Math.max(0, Math.min(100, 100 - (Math.abs(avgAR - 1) * 40)));
    document.getElementById("metrics-grid").innerHTML = `
          <div class="stat-card">
            <div class="stat-eyebrow">Total Area</div>
            <div class="stat-value">${totalArea.toFixed(1)}<span style="font-size:16px;font-weight:500"> m²</span></div>
            <div class="stat-sub">All rooms combined</div>
          </div>
          <div class="stat-card">
            <div class="stat-eyebrow">Avg Room Size</div>
            <div class="stat-value">${avgRoom.toFixed(1)}<span style="font-size:16px;font-weight:500"> m²</span></div>
            <div class="stat-sub">Planning efficiency</div>
          </div>
          <div class="stat-card">
            <div class="stat-eyebrow">Load-Bearing Ratio</div>
            <div class="stat-value">${(lbRatio * 100).toFixed(0)}<span style="font-size:16px;font-weight:500">%</span></div>
            <div class="stat-sub">${lbCount} of ${wallCount} walls structural</div>
          </div>
          <div class="stat-card">
            <div class="stat-eyebrow">Shape Efficiency</div>
            <div class="stat-value">${shapeEff.toFixed(0)}<span style="font-size:16px;font-weight:500">%</span></div>
            <div class="stat-sub">Avg aspect ratio ${avgAR.toFixed(2)}</div>
          </div>
        `;
}

function renderWarnings(ws) {
    const el = document.getElementById("warnings-list");
    if (!ws?.length) { el.innerHTML = `<div class="empty">No structural warnings detected</div>`; return; }
    el.innerHTML = ws.map((w, i) => `
          <div class="warning-item w-${w.severity}" data-warning-index="${i}" onclick="onWarningClick(${i})">
            <div class="w-sev ${w.severity}">${w.severity?.toUpperCase()}</div>
            <div class="w-msg">${w.message}</div>
            ${w.recommendation ? `<div class="w-rec">${w.recommendation}</div>` : ""}
          </div>
        `).join("");
}

function renderRooms(rooms) {
    const el = document.getElementById("rooms-list");
    if (!rooms?.length) { el.innerHTML = `<div class="empty">No rooms detected</div>`; return; }
    el.innerHTML = `
          <table>
            <thead><tr><th>Room</th><th>Area</th><th>Span</th><th>AR</th></tr></thead>
            <tbody>
              ${rooms.slice(0, 10).map((r, i) => {
        const name = r.label || r.room_label || r.name || `Room ${i + 1}`;
        const area = r.area_sqm ?? (r.width && r.height ? r.width * r.height * 0.025 * 0.025 : 0);
        const ar = r.aspect_ratio ?? 1;
        const span = r.width && r.depth
            ? Math.max(r.width, r.depth) * 0.025
            : Math.sqrt(area || 1);
        return `<tr>
                  <td><span class="room-tag">${name}</span></td>
                  <td>${Number(area).toFixed(1)} m&sup2;</td>
                  <td>${Number(span).toFixed(1)} m</td>
                  <td>${Number(ar).toFixed(2)}</td>
                </tr>`;
    }).join("")}
            </tbody>
          </table>
        `;
}

function renderCost(cost) {
    const el = document.getElementById("cost-list");
    if (!cost) { el.innerHTML = `<div class="empty">No cost data</div>`; return; }
    const b = cost.breakdown || {};
    const rows = [
        ["Material Cost", b.material_cost],
        ["Labor Cost", b.labor_cost],
        ["Contingency (12%)", b.contingency_12pct],
        ["GST (18%)", b.gst_18pct],
        ["Construction Total", cost.total_cost],
        ["+ Finishing (~25%)", cost.total_with_finishing],
    ];
    el.innerHTML = rows.map((r, i) => `
          <div class="cost-row ${i >= rows.length - 2 ? "total" : ""}">
            <span class="cost-label">${r[0]}</span>
            <span class="cost-val">&#8377;${fmt(r[1] || 0)}</span>
          </div>
        `).join("") +
        `<div style="font-size:11px;color:var(--text-secondary);margin-top:10px">${cost.disclaimer || ""}</div>`;
}

function renderSpans(spans) {
    const el = document.getElementById("span-list");
    if (!spans?.length) { el.innerHTML = `<div class="empty">No span data</div>`; return; }
    const maxSpan = Math.max(...spans.map(s => s.max_span_m), 1);
    el.innerHTML = spans.slice(0, 8).map(s => `
          <div class="span-row">
            <span class="span-name">${s.room}</span>
            <div class="span-track"><div class="span-fill span-${s.severity || 'ok'}" style="width:${(s.max_span_m / maxSpan) * 100}%"></div></div>
            <span class="span-val">${s.max_span_m}m</span>
          </div>
        `).join("");
}

function renderMaterials(recs) {
    const el = document.getElementById("materials-list");
    if (!recs?.length) { el.innerHTML = `<div class="empty">No recommendations</div>`; return; }
    el.innerHTML = recs.slice(0, 8).map(r => `
          <div class="mat-row">
            <div class="mat-dot" style="background:${r.wall_type === 'load_bearing' ? 'var(--lb-color)' : 'var(--pt-color)'}"></div>
            <div style="flex:1">
              <div class="mat-name">${r.primary_material}<span class="mat-type-badge">${r.wall_type.replace("_", " ")}</span></div>
              <div class="mat-reason">${r.reason}</div>
              <div class="mat-alts">${(r.alternatives || []).map(a => `<span class="alt-chip">${a}</span>`).join("")}</div>
            </div>
            <div class="mat-score">${r.structural_score}/100</div>
          </div>
        `).join("");
}

// ── 3D Scene ───────────────────────────────────────────────
let scene3d = null;
const layers = { lb: true, pt: true, rooms: true, doors: true, windows: true, warnings: true };
const meshGroups = { lb: [], pt: [], rooms: [], doors: [], windows: [], warnings: [] };
const wallMeshesById = new Map();
const warningToWallId = new Map();
const activeHighlights = [];
let pendingWarningIndex = null;
let rotX = 0.45, rotY = 0.55, zoom = 60, panX = 0, panZ = 0;
let cx3d = 0, cz3d = 0;
let baseZoom = 60;
let wireOn = false;
let _setViewFn = null;

function load3D() {
    fetch("model.json")
        .then(r => { if (!r.ok) throw new Error(`model.json ${r.status}`); return r.json(); })
        .then(data => build3DScene(data))
        .catch(err => {
            document.getElementById("viewer").innerHTML =
                `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-secondary);flex-direction:column;gap:14px">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                <div>3D model unavailable: ${err.message}</div>
                <div style="font-size:11px">Ensure backend is running and model.json was exported.</div>
              </div>`;
        });
}

function build3DScene(data) {
    const container = document.getElementById("viewer");
    container.innerHTML = "";
    Object.keys(meshGroups).forEach(k => { meshGroups[k] = []; });
    wallMeshesById.clear();
    warningToWallId.clear();
    clearWallHighlight();

    (data.warning_overlays || []).forEach(ov => {
        if (Number.isInteger(ov.warning_index) && ov.target_wall_id) {
            warningToWallId.set(ov.warning_index, ov.target_wall_id);
        }
    });

    const W = container.offsetWidth || 800;
    const H = container.offsetHeight || 520;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b1020);
    scene.fog = new THREE.FogExp2(0x0b1020, 0.007);
    scene3d = scene;

    const camera = new THREE.PerspectiveCamera(52, W / H, 0.1, 2000);
    const modelRoot = new THREE.Group();
    scene.add(modelRoot);

    // Lights
    scene.add(new THREE.AmbientLight(0xe6ecff, 0.42));
    const sun = new THREE.DirectionalLight(0xf8faff, 1.0);
    sun.position.set(40, 60, 30);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    scene.add(sun);
    const fill = new THREE.DirectionalLight(0x4fd1c5, 0.28);
    fill.position.set(-30, 25, -20);
    scene.add(fill);
    const bounce = new THREE.DirectionalLight(0x2f4268, 0.14);
    bounce.position.set(0, -10, 20);
    scene.add(bounce);

    // Grid
    const grid = new THREE.GridHelper(400, 80, 0x2f4268, 0x1b2740);
    grid.position.y = -0.08;
    scene.add(grid);
    const axes = new THREE.AxesHelper(5);
    axes.material.transparent = true;
    axes.material.opacity = 0.25;
    scene.add(axes);

    // Floor slabs
    (data.floors || []).forEach(f => {
        const w = f.width || 0.1, d = f.depth || 0.1;
        const cx = f.center?.[0] ?? 0, cz = f.center?.[1] ?? 0;
        const geo = new THREE.BoxGeometry(w, 0.15, d);
        const mat = new THREE.MeshStandardMaterial({ color: 0x1b2740, roughness: 0.88 });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.set(cx, -0.075, cz);
        mesh.receiveShadow = true;
        modelRoot.add(mesh);
        meshGroups.rooms.push(mesh);
    });

    // Walls
    const matLB = new THREE.MeshStandardMaterial({ color: 0xf9735b, roughness: 0.65, metalness: 0.04 });
    const matPT = new THREE.MeshStandardMaterial({ color: 0x4fd1c5, roughness: 0.75, metalness: 0.02 });
    const matLintel = new THREE.MeshStandardMaterial({ color: 0xa9b6d3, roughness: 0.8 });
    const WALL_H = 3.0;
    const THICK = 0.36;

    const doorsByWall = new Map();
    (data.doors || []).forEach(d => {
        if (!d.attached_to_wall || !d.wall_id) return;
        if (!doorsByWall.has(d.wall_id)) doorsByWall.set(d.wall_id, []);
        doorsByWall.get(d.wall_id).push({
            t: Math.min(0.96, Math.max(0.04, Number(d.wall_t ?? 0.5))),
            width: Math.max(0.6, Number(d.width || 0.9))
        });
    });

    (data.walls || []).forEach(wall => {
        const isLB = wall.type === "load_bearing";
        const mat = isLB ? matLB : matPT;
        const group = isLB ? meshGroups.lb : meshGroups.pt;
        const wallId = wall.id;

        const wallThick = wall.thickness || THICK;
        const wallDoors = doorsByWall.get(wallId) || [];
        if (wallDoors.length > 0) {
            const sorted = wallDoors
                .map(o => {
                    const c = (o.t - 0.5) * wall.length;
                    const half = Math.min(o.width * 0.5, wall.length * 0.22);
                    return [c - half, c + half];
                })
                .sort((a, b) => a[0] - b[0]);

            // Merge overlapping opening intervals in local wall coordinates.
            const merged = [];
            sorted.forEach(([a, b]) => {
                if (!merged.length || a > merged[merged.length - 1][1] + 0.05) {
                    merged.push([a, b]);
                } else {
                    merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], b);
                }
            });

            const wallStart = -wall.length / 2;
            const wallEnd = wall.length / 2;
            const solids = [];
            let cursor = wallStart;
            merged.forEach(([a, b]) => {
                const aa = Math.max(a, wallStart + 0.05);
                const bb = Math.min(b, wallEnd - 0.05);
                if (aa > cursor + 0.05) solids.push([cursor, aa]);
                cursor = Math.max(cursor, bb);
            });
            if (cursor < wallEnd - 0.05) solids.push([cursor, wallEnd]);

            const cos = Math.cos(wall.angle), sin = Math.sin(wall.angle);

            solids.forEach(([s0, s1]) => {
                const segLen = s1 - s0;
                if (segLen < 0.06) return;
                const localMid = (s0 + s1) / 2;
                const geo = new THREE.BoxGeometry(segLen, WALL_H, wallThick);
                const mesh = new THREE.Mesh(geo, mat.clone());
                mesh.position.set(
                    wall.center[0] + localMid * cos,
                    WALL_H / 2,
                    wall.center[1] + localMid * sin
                );
                mesh.rotation.y = -wall.angle;
                mesh.castShadow = true;
                mesh.receiveShadow = true;
                modelRoot.add(mesh);
                group.push(mesh);
                registerWallMesh(wallId, mesh);
            });

            merged.forEach(([a, b]) => {
                const openW = Math.max(0.18, b - a);
                const localMid = (a + b) / 2;
                const lintel = new THREE.Mesh(new THREE.BoxGeometry(openW, 0.22, wallThick), matLintel.clone());
                lintel.position.set(
                    wall.center[0] + localMid * cos,
                    WALL_H - 0.11,
                    wall.center[1] + localMid * sin
                );
                lintel.rotation.y = -wall.angle;
                modelRoot.add(lintel);
                group.push(lintel);
                registerWallMesh(wallId, lintel);
            });
        } else {
            const geo = new THREE.BoxGeometry(wall.length, WALL_H, wallThick);
            const mesh = new THREE.Mesh(geo, mat.clone());
            mesh.position.set(wall.center[0], WALL_H / 2, wall.center[1]);
            mesh.rotation.y = -wall.angle;
            mesh.castShadow = true; mesh.receiveShadow = true;
            modelRoot.add(mesh); group.push(mesh);
            registerWallMesh(wallId, mesh);
        }
    });

    // Doors (framed opening + leaf)
    const doorFrameMat = new THREE.MeshStandardMaterial({ color: 0x8b5a2b, roughness: 0.72, metalness: 0.08 });
    const doorLeafMat = new THREE.MeshStandardMaterial({ color: 0x6f3f1f, roughness: 0.68, metalness: 0.1 });

    (data.doors || []).forEach(door => {
        const pos = door.position || [0, 1.05, 0];
        const width = Math.max(door.width || 0.9, 0.65);
        const height = Math.max(door.height || 2.1, 1.9);
        const depth = Math.max(door.depth || 0.12, 0.08);
        const ry = door.rotation_y || 0;

        const group = new THREE.Group();
        group.position.set(pos[0], 0, pos[2]);
        group.rotation.y = ry;

        const postW = Math.min(0.08, width * 0.12);
        const topH = 0.09;

        const leftPost = new THREE.Mesh(new THREE.BoxGeometry(postW, height, depth), doorFrameMat.clone());
        leftPost.position.set(-width / 2 + postW / 2, height / 2, 0);
        leftPost.castShadow = true;
        group.add(leftPost);

        const rightPost = new THREE.Mesh(new THREE.BoxGeometry(postW, height, depth), doorFrameMat.clone());
        rightPost.position.set(width / 2 - postW / 2, height / 2, 0);
        rightPost.castShadow = true;
        group.add(rightPost);

        const topPost = new THREE.Mesh(new THREE.BoxGeometry(width, topH, depth), doorFrameMat.clone());
        topPost.position.set(0, height - topH / 2, 0);
        topPost.castShadow = true;
        group.add(topPost);

        // Slightly open leaf for better 3D readability
        const leafW = Math.max(width - postW * 2 - 0.02, 0.45);
        const leaf = new THREE.Mesh(new THREE.BoxGeometry(leafW, Math.max(height - 0.06, 1.8), 0.035), doorLeafMat.clone());
        leaf.position.set(-width / 2 + postW + leafW / 2, (height - 0.06) / 2, depth * 0.22);
        leaf.rotation.y = -0.32;
        leaf.castShadow = true;
        group.add(leaf);

        modelRoot.add(group);
        meshGroups.doors.push(group);
    });

    // Windows (frame + glass + mullion)
    const winFrameMat = new THREE.MeshStandardMaterial({ color: 0xb6c0cc, roughness: 0.5, metalness: 0.2 });
    const winGlassMat = new THREE.MeshStandardMaterial({
        color: 0x8ecdf4,
        transparent: true,
        opacity: 0.34,
        roughness: 0.15,
        metalness: 0.0
    });

    (data.windows || []).forEach(win => {
        const pos = win.position || [0, 1.5, 0];
        const width = Math.max(win.width || 1.1, 0.5);
        const height = Math.max(win.height || 1.2, 0.6);
        const depth = Math.max(win.depth || 0.1, 0.06);
        const ry = win.rotation_y || 0;

        const group = new THREE.Group();
        group.position.set(pos[0], 0, pos[2]);
        group.rotation.y = ry;

        const frameT = Math.min(0.06, width * 0.12);

        const top = new THREE.Mesh(new THREE.BoxGeometry(width, frameT, depth), winFrameMat.clone());
        top.position.set(0, pos[1] + height / 2 - frameT / 2, 0);
        group.add(top);

        const bottom = new THREE.Mesh(new THREE.BoxGeometry(width, frameT, depth), winFrameMat.clone());
        bottom.position.set(0, pos[1] - height / 2 + frameT / 2, 0);
        group.add(bottom);

        const left = new THREE.Mesh(new THREE.BoxGeometry(frameT, height, depth), winFrameMat.clone());
        left.position.set(-width / 2 + frameT / 2, pos[1], 0);
        group.add(left);

        const right = new THREE.Mesh(new THREE.BoxGeometry(frameT, height, depth), winFrameMat.clone());
        right.position.set(width / 2 - frameT / 2, pos[1], 0);
        group.add(right);

        const mullion = new THREE.Mesh(new THREE.BoxGeometry(frameT * 0.9, Math.max(height - frameT * 2, 0.3), depth * 0.9), winFrameMat.clone());
        mullion.position.set(0, pos[1], 0);
        group.add(mullion);

        const glass = new THREE.Mesh(new THREE.BoxGeometry(Math.max(width - frameT * 2.3, 0.2), Math.max(height - frameT * 2.3, 0.2), 0.015), winGlassMat.clone());
        glass.position.set(0, pos[1], 0);
        group.add(glass);

        modelRoot.add(group);
        meshGroups.windows.push(group);
    });

    // Room labels as sprites
    (data.floors || []).forEach(f => {
        const label = f.label || f.room_label || "";
        if (!label) return;
        const cx = f.center?.[0] ?? 0, cz = f.center?.[1] ?? 0;

        const canvas = document.createElement("canvas");
        canvas.width = 256; canvas.height = 64;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "rgba(15,23,42,0.72)";
        ctx.fillRect(4, 4, 248, 56);
        ctx.font = "bold 20px Inter, Arial, sans-serif";
        ctx.fillStyle = "rgba(255,255,255,0.82)";
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText(label, 128, 32);

        const tex = new THREE.CanvasTexture(canvas);
        const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }));
        sprite.position.set(cx, 0.7, cz);
        sprite.scale.set(4.5, 1.1, 1);
        modelRoot.add(sprite);
        meshGroups.rooms.push(sprite);
    });

    // Structural warning overlays in scene
    (data.warning_overlays || []).forEach(ov => {
        const color = ov.color || "#FBBF24";
        const radius = ov.radius || 0.5;
        const pos = ov.position || [0, 0.05, 0];

        const ring = new THREE.Mesh(
            new THREE.CylinderGeometry(radius, radius, 0.04, 40),
            new THREE.MeshStandardMaterial({
                color,
                transparent: true,
                opacity: 0.45,
                roughness: 0.4,
                emissive: new THREE.Color(color),
                emissiveIntensity: 0.2
            })
        );
        ring.position.set(pos[0], 0.02, pos[2]);
        ring.receiveShadow = true;
        modelRoot.add(ring);
        meshGroups.warnings.push(ring);

        const halo = new THREE.Mesh(
            new THREE.RingGeometry(radius * 1.1, radius * 1.35, 48),
            new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.38, side: THREE.DoubleSide })
        );
        halo.rotation.x = -Math.PI / 2;
        halo.position.set(pos[0], 0.025, pos[2]);
        modelRoot.add(halo);
        meshGroups.warnings.push(halo);
    });

    // True camera auto-fit from rendered model bounds
    const box = new THREE.Box3().setFromObject(modelRoot);
    const size = new THREE.Vector3();
    const center = new THREE.Vector3();
    box.getSize(size);
    box.getCenter(center);

    cx3d = Number.isFinite(center.x) ? center.x : 0;
    cz3d = Number.isFinite(center.z) ? center.z : 0;

    const maxDim = Math.max(size.x || 1, size.z || 1, 8);
    const fov = camera.fov * (Math.PI / 180);
    const fitDistance = (maxDim / 2) / Math.tan(fov / 2);
    baseZoom = Math.max(10, fitDistance * 1.2);
    zoom = baseZoom;

    // Layer bar
    document.getElementById("layer-bar").innerHTML = `
          <label class="layer-toggle on" id="lb-wrap">
            <input type="checkbox" id="lb-toggle" checked onchange="toggleLayer('lb')" />
            <span class="layer-dot" style="background:#F9735B"></span>
            <span class="layer-label">Load Bearing</span>
          </label>
          <label class="layer-toggle on" id="pt-wrap">
            <input type="checkbox" id="pt-toggle" checked onchange="toggleLayer('pt')" />
            <span class="layer-dot" style="background:#4FD1C5"></span>
            <span class="layer-label">Partitions</span>
          </label>
          <label class="layer-toggle on" id="rooms-wrap">
            <input type="checkbox" id="rooms-toggle" checked onchange="toggleLayer('rooms')" />
            <span class="layer-dot" style="background:#34D399"></span>
            <span class="layer-label">Rooms</span>
          </label>
                    <label class="layer-toggle on" id="doors-wrap">
                        <input type="checkbox" id="doors-toggle" checked onchange="toggleLayer('doors')" />
                        <span class="layer-dot" style="background:#8B4513"></span>
                        <span class="layer-label">Doors</span>
                    </label>
                    <label class="layer-toggle on" id="windows-wrap">
                        <input type="checkbox" id="windows-toggle" checked onchange="toggleLayer('windows')" />
                        <span class="layer-dot" style="background:#87CEEB"></span>
                        <span class="layer-label">Windows</span>
                    </label>
          <label class="layer-toggle on" id="warnings-wrap">
            <input type="checkbox" id="warnings-toggle" checked onchange="toggleLayer('warnings')" />
            <span class="layer-dot" style="background:#FBBF24"></span>
            <span class="layer-label">Warnings</span>
          </label>
          <button class="layer-btn" id="wire-btn" onclick="toggleWireframe()">Wireframe</button>
        `;
    Object.keys(layers).forEach(syncLayerToggle);

    // Mouse/touch
    let dragging = false, lastX = 0, lastY = 0, rightDrag = false;
    renderer.domElement.addEventListener("mousedown", e => {
        dragging = true; lastX = e.clientX; lastY = e.clientY; rightDrag = e.button === 2; e.preventDefault();
    });
    renderer.domElement.addEventListener("mousemove", e => {
        if (!dragging) return;
        const dx = e.clientX - lastX, dy = e.clientY - lastY;
        if (rightDrag) { panX -= dx * 0.08; panZ -= dy * 0.08; }
        else { rotY -= dx * 0.007; rotX -= dy * 0.007; rotX = Math.max(-1.45, Math.min(1.45, rotX)); }
        lastX = e.clientX; lastY = e.clientY;
    });
    renderer.domElement.addEventListener("mouseup", () => dragging = false);
    renderer.domElement.addEventListener("contextmenu", e => e.preventDefault());
    renderer.domElement.addEventListener("wheel", e => {
        e.preventDefault(); e.stopPropagation();
        zoom = Math.max(5, Math.min(300, zoom + e.deltaY * 0.06));
    }, { passive: false });

    // Damped animation
    let aRX = rotX, aRY = rotY, aZ = zoom, aPX = 0, aPZ = 0;
    const DAMP = 0.1;

    _setViewFn = (rx, ry, z) => { rotX = rx; rotY = ry; zoom = z; };

    if (Number.isInteger(pendingWarningIndex)) {
        const idx = pendingWarningIndex;
        pendingWarningIndex = null;
        focusWarningWall(idx, false);
    }

    const animate = () => {
        requestAnimationFrame(animate);
        aRX += (rotX - aRX) * DAMP; aRY += (rotY - aRY) * DAMP;
        aZ += (zoom - aZ) * DAMP; aPX += (panX - aPX) * DAMP; aPZ += (panZ - aPZ) * DAMP;
        const r = aZ;
        camera.position.set(
            cx3d + aPX + r * Math.sin(aRY) * Math.cos(aRX),
            r * Math.sin(aRX) + 3,
            cz3d + aPZ + r * Math.cos(aRY) * Math.cos(aRX)
        );
        camera.lookAt(cx3d + aPX, 1.5, cz3d + aPZ);
        renderer.render(scene, camera);
    };
    animate();

    window.addEventListener("resize", () => {
        const nw = container.offsetWidth;
        camera.aspect = nw / H; camera.updateProjectionMatrix();
        renderer.setSize(nw, H);
    });
}

// ── Layer controls ──────────────────────────────────────────
function toggleLayer(key) {
    layers[key] = !layers[key];
    (meshGroups[key] || []).forEach(m => m.visible = layers[key]);
    syncLayerToggle(key);
}
function syncLayerToggle(key) {
    document.getElementById(`${key}-toggle`) && (document.getElementById(`${key}-toggle`).checked = layers[key]);
    document.getElementById(`${key}-wrap`)?.classList.toggle("on", layers[key]);
}
function registerWallMesh(wallId, mesh) {
    if (!wallId || !mesh?.isMesh) return;
    if (!wallMeshesById.has(wallId)) wallMeshesById.set(wallId, []);
    wallMeshesById.get(wallId).push(mesh);
}
function clearWallHighlight() {
    activeHighlights.forEach(mesh => {
        if (!mesh?.material || !mesh.userData._origHighlight) return;
        const orig = mesh.userData._origHighlight;
        mesh.material.color.setHex(orig.color);
        if (mesh.material.emissive) mesh.material.emissive.setHex(orig.emissive);
        if (typeof orig.emissiveIntensity === "number") mesh.material.emissiveIntensity = orig.emissiveIntensity;
    });
    activeHighlights.length = 0;
}
function highlightWarningCard(index) {
    document.querySelectorAll(".warning-item").forEach(card => card.classList.remove("active"));
    document.querySelector(`.warning-item[data-warning-index='${index}']`)?.classList.add("active");
}
function toggleLayerVisibilityOnly(key, visible) {
    layers[key] = visible;
    (meshGroups[key] || []).forEach(m => m.visible = visible);
    syncLayerToggle(key);
}
function focusWarningWall(index, withToast = true) {
    const wallId = warningToWallId.get(index);
    if (!wallId) {
        if (withToast) showToast("No specific wall linked for this warning.", "error");
        return;
    }
    const meshes = wallMeshesById.get(wallId) || [];
    if (!meshes.length) {
        if (withToast) showToast("Linked wall mesh was not found.", "error");
        return;
    }

    toggleLayerVisibilityOnly("lb", true);
    toggleLayerVisibilityOnly("pt", true);
    clearWallHighlight();

    meshes.forEach(mesh => {
        if (!mesh.material) return;
        if (!mesh.userData._origHighlight) {
            mesh.userData._origHighlight = {
                color: mesh.material.color?.getHex?.() ?? 0xffffff,
                emissive: mesh.material.emissive?.getHex?.() ?? 0x000000,
                emissiveIntensity: mesh.material.emissiveIntensity ?? 0
            };
        }
        mesh.material.color.setHex(0xfacc15);
        if (mesh.material.emissive) mesh.material.emissive.setHex(0x7c2d12);
        if (typeof mesh.material.emissiveIntensity === "number") mesh.material.emissiveIntensity = 0.55;
        activeHighlights.push(mesh);
    });

    const box = new THREE.Box3();
    meshes.forEach(m => box.expandByObject(m));
    const center = new THREE.Vector3();
    box.getCenter(center);
    if (Number.isFinite(center.x) && Number.isFinite(center.z)) {
        panX = center.x - cx3d;
        panZ = center.z - cz3d;
        zoom = Math.max(8, baseZoom * 0.72);
    }
    highlightWarningCard(index);
}
function onWarningClick(index) {
    if (!scene3d) {
        pendingWarningIndex = index;
        showToast("3D model is still loading. Will highlight when ready.", "error");
        return;
    }
    focusWarningWall(index);
}
function toggleWireframe() {
    wireOn = !wireOn;
    scene3d?.traverse(obj => { if (obj.isMesh && obj.material) obj.material.wireframe = wireOn; });
    document.getElementById("wire-btn")?.classList.toggle("on", wireOn);
}
function setTopView() { rotX = 1.45; rotY = 0; _setViewFn?.(1.45, 0, baseZoom); }
function setIsoView() { rotX = 0.45; rotY = 0.55; _setViewFn?.(0.45, 0.55, baseZoom); }
function setFrontView() { rotX = 0; rotY = 0; _setViewFn?.(0, 0, baseZoom); }
function resetView() { rotX = 0.45; rotY = 0.55; panX = 0; panZ = 0; _setViewFn?.(0.45, 0.55, baseZoom); }

// ── Utilities ──────────────────────────────────────────────
function fmt(n) { if (!n) return "0"; return Number(n).toLocaleString("en-IN"); }
function showToast(msg, type = "info") {
    const t = document.getElementById("toast");
    t.textContent = msg; t.className = `show ${type}`;
    setTimeout(() => t.classList.remove("show"), 4000);
}
function downloadJSON() {
    if (!analysisData) return showToast("No data to export.", "error");
    const blob = new Blob([JSON.stringify(analysisData, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = `structural-report-${Date.now()}.json`; a.click();
    showToast("Report downloaded.", "success");
}
function printReport() { window.print(); }