import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const $ = (id) => document.getElementById(id);
// Signs and floor stencils are drawn into textures once, so wait (up to 3 s) for their font first.
await Promise.race([
  Promise.all(["600", "700"].map((w) => document.fonts.load(`${w} 40px "Chakra Petch"`))),
  new Promise((r) => setTimeout(r, 3000)),
]);
const stage = $("stage");

// --- Floor plan (metres). The bot is 1 m tall. ---------------------------------------------
// Socket wall at x = -ROOM.x. Start zone x -11..-9, maze x -9..9 on a 2 m grid, goal x 9..11.
const ROOM = { x: 11, z: 7, h: 11 };
const CELL = 2, MAZE_X0 = -9, MAZE_Z0 = -7, COLS = 9, ROWS = 7;
const GOAL_X = 9.3;
const START = new THREE.Vector3(-9.45, 0, 0);
const SOCKET_POS = new THREE.Vector3(-ROOM.x, 0.75, 0);
const WALL_H = 1.3, WALL_T = 0.26;

const PACE = 6;                      // walk cycle playback rate; ground speed follows it
const WALK_SPEED = 0.22 * PACE;      // matches the foot slide of the walk cycle, so feet don't skate
const TURN_RATE = THREE.MathUtils.degToRad(120);
const BOT_R = 0.3;                   // footprint radius against walls
const CABLE_R = 0.019;
const PLUG_LEN = 0.22, PLUG_R = 0.038;
const SLUMP = THREE.MathUtils.degToRad(20);
const BOT_SOCKET = new THREE.Vector3(-0.245, 0.030, 0); // bot model space: centre of the orange ring, tip just inside it
const POST = 0.34;                   // square posts at wall ends and junctions, wider than the panels

// Levels live in levels.json: five difficulties, each with its own cable colour and spare, and ten mazes.
// The cable is just long enough for the right way through plus its colour's spare; take a long way round
// and it runs out. Each maze is drawn as text, one string per line (see parseMap); the map editor writes
// the same file.
const PIT_INSET = 0.25, PIT_DEPTH = 1.3;
const IN_ROW = 3;                    // the entrance faces the start zone (z = 0)
const LEVEL_COUNT = 10;
const levelData = await (await fetch("levels.json", { cache: "no-store" })).json();
const TESTS = levelData.difficulties.map(({ name, level, hex, spare }) => ({ name, level, hex, spare }));

// A maze as text: 2 * ROWS + 1 lines of 2 * COLS + 1 characters. Even lines hold the wall ends ("+") and
// the walls across ("-"); odd lines hold the walls up and down ("|") and the cells, " " for floor or "O"
// for a pit. The top and bottom lines are the room's walls. The gap in the left edge is the entrance (it
// must be row 3) and the gap in the right edge is the exit. Pit squares joined through open edges make one
// hole, however many there are; a wall between two pit squares keeps a strip of floor under it.
function parseMap(lines) {
  if (lines.length !== 2 * ROWS + 1 || lines.some((l) => l.length !== 2 * COLS + 1)) throw new Error("wrong size");
  const v = [], h = [], pit = new Set(), key = (c, r) => c * 100 + r;
  let exit = -1;
  for (let r = 0; r < ROWS; r++) {
    const line = lines[2 * r + 1];
    for (let i = 0; i <= COLS; i++) if (line[2 * i] === "|") v.push([i, r, r]);
    for (let c = 0; c < COLS; c++) if (line[2 * c + 1] === "O") pit.add(key(c, r));
    if (line[2 * COLS] !== "|") exit = r;
  }
  for (let j = 1; j < ROWS; j++) for (let c = 0; c < COLS; c++) if (lines[2 * j][2 * c + 1] === "-") h.push([j, c, c]);
  const wallV = (i, r) => lines[2 * r + 1][2 * i] === "|", wallH = (j, c) => lines[2 * j][2 * c + 1] === "-";
  // Pit squares joined through open edges, each group one hole. A hole is a set of rectangles: every square
  // set in from its edges, the gaps across its open edges, and the middle of any four squares all open to
  // each other.
  const openTo = (c, r) => [[c + 1, r, !wallV(c + 1, r)], [c - 1, r, !wallV(c, r)], [c, r + 1, r + 1 < ROWS && !wallH(r + 1, c)], [c, r - 1, r > 0 && !wallH(r, c)]]
    .filter(([x, y, o]) => o && pit.has(key(x, y)));
  const pits = [], seen = new Set(), I = PIT_INSET;
  for (const k of pit) {
    if (seen.has(k)) continue;
    const group = [], todo = [[Math.floor(k / 100), k % 100]];
    seen.add(k);
    while (todo.length) {
      const [c, r] = todo.pop();
      group.push([c, r]);
      for (const [x, y] of openTo(c, r)) if (!seen.has(key(x, y))) { seen.add(key(x, y)); todo.push([x, y]); }
    }
    const inGroup = new Set(group.map(([c, r]) => key(c, r)));
    const has = (c, r) => inGroup.has(key(c, r));
    const box = (x0, x1, z0, z1) => ({ minX: x0, maxX: x1, minZ: z0, maxZ: z1 });
    const cells = group.map(([c, r]) => box(MAZE_X0 + c * CELL + I, MAZE_X0 + (c + 1) * CELL - I, MAZE_Z0 + r * CELL + I, MAZE_Z0 + (r + 1) * CELL - I));
    const rects = [...cells];
    for (const [c, r] of group) {
      const x = MAZE_X0 + (c + 1) * CELL, z = MAZE_Z0 + (r + 1) * CELL;
      const right = has(c + 1, r) && !wallV(c + 1, r), down = r + 1 < ROWS && has(c, r + 1) && !wallH(r + 1, c);
      if (right) rects.push(box(x - I, x + I, z - CELL + I, z - I));
      if (down) rects.push(box(x - CELL + I, x - I, z - I, z + I));
      if (right && down && has(c + 1, r + 1) && !wallV(c + 1, r + 1) && !wallH(r + 1, c + 1)) rects.push(box(x - I, x + I, z - I, z + I));
    }
    pits.push({
      cells, rects,
      minX: Math.min(...rects.map((b) => b.minX)), maxX: Math.max(...rects.map((b) => b.maxX)),
      minZ: Math.min(...rects.map((b) => b.minZ)), maxZ: Math.max(...rects.map((b) => b.maxZ)),
    });
  }
  return { v, h, pits, exit, entry: lines[2 * IN_ROW + 1][0] === "|" ? -1 : IN_ROW };
}
const makeLevel = (k, map) => ({ ...TESTS[k], map, ...parseMap(map) });
const LEVELS = levelData.difficulties.map((d, k) => d.levels.map((map) => makeLevel(k, map)));

// --- Renderer, scene, camera ------------------------------------------------------------------
const renderer = new THREE.WebGLRenderer({ canvas: $("view"), antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x15171c);
scene.fog = new THREE.Fog(0x15171c, 26, 60);
const camera = new THREE.PerspectiveCamera(42, 1, 0.05, 200);

const gradient = new THREE.DataTexture(new Uint8Array([70, 150, 255]), 3, 1, THREE.RedFormat);
gradient.minFilter = gradient.magFilter = THREE.NearestFilter;
gradient.needsUpdate = true;
const toon = (o) => new THREE.MeshToonMaterial({ gradientMap: gradient, ...o });
const inkLine = new THREE.LineBasicMaterial({ color: 0x0c0d10 });

scene.add(new THREE.HemisphereLight(0xc4cedd, 0x2a2622, 1.1));
const sun = new THREE.DirectionalLight(0xfff1dc, 2.0);
// One fixed sun whose shadow covers the whole room, so every wall casts its shadow all the time rather than
// only near the bot.
sun.castShadow = true;
sun.position.set(5, 12, 4);
sun.shadow.mapSize.set(4096, 4096);
Object.assign(sun.shadow.camera, { left: -15, right: 15, top: 13, bottom: -13, near: 1, far: 30 });
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.02;
scene.add(sun, sun.target);

function canvasTex(w, h, draw, repeat) {
  const c = document.createElement("canvas");
  c.width = w; c.height = h;
  draw(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(repeat[0], repeat[1]); }
  return t;
}
function stripes(g, w, h, a, b, period) {
  g.fillStyle = b; g.fillRect(0, 0, w, h);
  g.fillStyle = a;
  for (let x = -h; x < w + h; x += period) {
    g.beginPath();
    g.moveTo(x, h); g.lineTo(x + period / 2, h); g.lineTo(x + period / 2 + h, 0); g.lineTo(x + h, 0);
    g.closePath(); g.fill();
  }
}
function inked(mesh) {
  mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry, 30), inkLine));
  return mesh;
}

// --- The test floor --------------------------------------------------------------------------
const W = ROOM.x * 2, D = ROOM.z * 2;
const PX = 128;
const floorTex = canvasTex(W * PX, D * PX, (g, w, h) => {
  const X = (x) => (x + ROOM.x) * PX, Z = (z) => (z + ROOM.z) * PX;
  g.fillStyle = "#4b4f58"; g.fillRect(0, 0, w, h);
  for (let i = 0; i < (w * h) / 110; i++) {
    const v = 70 + Math.random() * 25;
    g.fillStyle = `rgba(${v},${v + 3},${v + 10},0.35)`;
    g.fillRect(Math.random() * w, Math.random() * h, 2 + Math.random() * 3, 2 + Math.random() * 3);
  }
  for (const [x, z] of [[-6, -3.5], [-6, 3.5], [0, -3.5], [0, 3.5], [6, -3.5], [6, 3.5]]) {
    const r = 3.2 * PX;
    const grad = g.createRadialGradient(X(x), Z(z), 0, X(x), Z(z), r);
    grad.addColorStop(0, "rgba(255,236,200,0.14)"); grad.addColorStop(1, "rgba(255,236,200,0)");
    g.fillStyle = grad; g.fillRect(X(x) - r, Z(z) - r, r * 2, r * 2);
  }
  // Start zone: hazard apron and stencil.
  g.save();
  g.beginPath(); g.rect(X(-ROOM.x), Z(-ROOM.z), 2 * PX, D * PX); g.clip();
  g.globalAlpha = 0.35; stripes(g, w, h, "#f2b705", "#1b1b1d", 0.6 * PX);
  g.restore();
  // Goal zone: chequered finish.
  const sq = 0.5 * PX;
  for (let gx = 0; gx < 4; gx++) {
    for (let gz = 0; gz < D * 2; gz++) {
      g.fillStyle = (gx + gz) % 2 ? "rgba(47,191,113,0.55)" : "rgba(236,230,218,0.35)";
      g.fillRect(X(9) + gx * sq, Z(-ROOM.z) + gz * sq, sq, sq);
    }
  }
  g.fillStyle = "rgba(242,183,5,0.95)"; g.fillRect(X(9) - 0.06 * PX, 0, 0.12 * PX, h);
  const stencil = (text, x, z, size, rot, color) => {
    g.save(); g.translate(X(x), Z(z)); g.rotate(rot);
    g.fillStyle = color; g.font = `700 ${size * PX}px "Chakra Petch", sans-serif`;
    g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(text, 0, 0); g.restore();
  };
  stencil("START", -10, -4.2, 0.9, -Math.PI / 2, "rgba(242,183,5,0.85)");
  stencil("GOAL", 10, -3.6, 1.1, Math.PI / 2, "rgba(16,18,22,0.85)");
  stencil("GOAL", 10, 3.6, 1.1, Math.PI / 2, "rgba(16,18,22,0.85)");
  // Wall slots: every line a maze wall can rise from, so the floor always matches the walls.
  const slot = (x0, z0, x1, z1) => {
    const t = 0.32 * PX;
    const horiz = z0 === z1;
    const rx = horiz ? X(x0) : X(x0) - t / 2, rz = horiz ? Z(z0) - t / 2 : Z(z0);
    const rw = horiz ? (x1 - x0) * PX : t, rh = horiz ? t : (z1 - z0) * PX;
    g.fillStyle = "#24262c"; g.fillRect(rx, rz, rw, rh);
    g.fillStyle = "#15161a"; horiz ? g.fillRect(rx, rz + t * 0.4, rw, t * 0.2) : g.fillRect(rx + t * 0.4, rz, t * 0.2, rh);
    g.strokeStyle = "#767c87"; g.lineWidth = 3; g.strokeRect(rx, rz, rw, rh);
  };
  for (let i = 0; i <= COLS; i++) slot(MAZE_X0 + i * CELL, -ROOM.z, MAZE_X0 + i * CELL, ROOM.z);
  for (let j = 1; j < ROWS; j++) slot(MAZE_X0, MAZE_Z0 + j * CELL, MAZE_X0 + COLS * CELL, MAZE_Z0 + j * CELL);
  // Hazard studs where slots cross.
  for (let i = 0; i <= COLS; i++) {
    for (let j = 0; j <= ROWS; j++) {
      g.fillStyle = "#f2b705";
      g.beginPath(); g.arc(X(MAZE_X0 + i * CELL), Z(MAZE_Z0 + j * CELL), 0.1 * PX, 0, Math.PI * 2); g.fill();
      g.fillStyle = "#1b1b1d";
      g.beginPath(); g.arc(X(MAZE_X0 + i * CELL), Z(MAZE_Z0 + j * CELL), 0.045 * PX, 0, Math.PI * 2); g.fill();
    }
  }
});
const floor = new THREE.Mesh(new THREE.PlaneGeometry(W, D), toon({ map: floorTex }));
floor.rotation.x = -Math.PI / 2; // until buildPits gives it holes, laid out in world space
floor.receiveShadow = true;
scene.add(floor);

// --- Pits -------------------------------------------------------------------------------------
// Holes can be any shape made of squares, so they're drawn from a grid PIT_RES fine (every hole edge lies
// on it): the floor is the grid's solid cells merged into rectangles, the pit bottom its hole cells, the
// shaft walls stand along every edge between the two, and a hazard rim one cell wide runs round the
// opening, its stripes laid in world space so they meet cleanly at every corner.
let pits = [], pitBoxes = [];
const pitGroup = new THREE.Group();
scene.add(pitGroup);
const PIT_RES = 0.125, PNX = Math.round(W / PIT_RES), PNZ = Math.round(D / PIT_RES);
const pitWallTex = canvasTex(256, 256, (g, w, h) => {
  g.fillStyle = "#2b2429"; g.fillRect(0, 0, w, h);
  for (let x = 0; x < w; x += 64) {
    g.fillStyle = "#1c171b"; g.fillRect(x, 0, 4, h);
    g.fillStyle = "#3a3036"; g.fillRect(x + 4, 0, 3, h);
  }
  g.fillStyle = "#1c171b"; g.fillRect(0, h / 2 - 2, w, 4);
}, [1, 1]);
const pitFloorTex = canvasTex(256, 256, (g, w, h) => {
  g.fillStyle = "#17181c"; g.fillRect(0, 0, w, h);
  g.fillStyle = "#2c2e35";
  for (let y = 0; y < h; y += 32) for (let x = 0; x < w; x += 32) g.fillRect(x + 4, y + 4, 24, 24);
  g.fillStyle = "#101114";
  for (let y = 0; y < h; y += 32) for (let x = 0; x < w; x += 32) g.fillRect(x + 8, y + 8, 16, 16);
}, [1, 1]);
const pitBandTex = canvasTex(256, 64, (g, w, h) => stripes(g, w, h, "#f2b705", "#1b1b1d", 64), [1, 1]);
const rimTex = canvasTex(128, 128, (g, w, h) => stripes(g, w, h, "#f2b705", "#1b1b1d", 64), [1, 1]);
// The band lies on the shaft wall itself; the depth offset makes it always win against the wall behind it.
const pitWallMat = toon({ map: pitWallTex, side: THREE.DoubleSide });
const pitBandMat = toon({ map: pitBandTex, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4 });
const pitFloorMat = toon({ map: pitFloorTex }), rimMat = toon({ map: rimTex });
// 1 where the cell's centre is in a hole.
function holeGrid(list) {
  const g = new Uint8Array(PNX * PNZ);
  for (const b of list.flatMap((p) => p.rects)) {
    const x0 = Math.round((b.minX + ROOM.x) / PIT_RES), x1 = Math.round((b.maxX + ROOM.x) / PIT_RES);
    const z0 = Math.round((b.minZ + ROOM.z) / PIT_RES), z1 = Math.round((b.maxZ + ROOM.z) / PIT_RES);
    for (let iz = z0; iz < z1; iz++) for (let ix = x0; ix < x1; ix++) g[iz * PNX + ix] = 1;
  }
  return g;
}
// The cells where want(ix, iz) holds, merged into as few rectangles as rows allow: [x0, x1, z0, z1] in metres.
function gridRects(want) {
  const out = [], open = new Map();
  for (let iz = 0; iz <= PNZ; iz++) {
    const runs = new Set();
    if (iz < PNZ) for (let ix = 0; ix < PNX;) {
      if (!want(ix, iz)) { ix++; continue; }
      const a = ix;
      while (ix < PNX && want(ix, iz)) ix++;
      runs.add(`${a},${ix}`);
    }
    for (const [k, r] of open) if (!runs.has(k)) { r[3] = iz; out.push(r); open.delete(k); }
    for (const k of runs) if (!open.has(k)) { const [a, b] = k.split(",").map(Number); open.set(k, [a, b, iz, 0]); }
  }
  return out.map(([a, b, z0, z1]) => [a * PIT_RES - ROOM.x, b * PIT_RES - ROOM.x, z0 * PIT_RES - ROOM.z, z1 * PIT_RES - ROOM.z]);
}
// Flat rectangles at height y facing up, textured by uv(x, z).
function flatGeometry(rects, y, uv) {
  const pos = [], uvs = [], idx = [];
  for (const [x0, x1, z0, z1] of rects) {
    const n = pos.length / 3;
    for (const [x, z] of [[x0, z1], [x1, z1], [x1, z0], [x0, z0]]) { pos.push(x, y, z); uvs.push(...uv(x, z)); }
    idx.push(n, n + 1, n + 2, n, n + 2, n + 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}
// Edges between cells where a(ix, iz) and b(ix, iz) differ, merged along their lines: [x0, z0, x1, z1].
function gridEdges(inside) {
  const out = [];
  for (let ix = 0; ix <= PNX; ix++) {
    let start = -1, side = 0;
    for (let iz = 0; iz <= PNZ; iz++) {
      const l = iz < PNZ && ix > 0 && inside(ix - 1, iz), r = iz < PNZ && ix < PNX && inside(ix, iz), s2 = l === r ? 0 : l ? 1 : 2;
      if (s2 !== side) {
        if (side) out.push([ix * PIT_RES - ROOM.x, start * PIT_RES - ROOM.z, ix * PIT_RES - ROOM.x, iz * PIT_RES - ROOM.z]);
        start = iz; side = s2;
      }
    }
  }
  for (let iz = 0; iz <= PNZ; iz++) {
    let start = -1, side = 0;
    for (let ix = 0; ix <= PNX; ix++) {
      const u = ix < PNX && iz > 0 && inside(ix, iz - 1), d = ix < PNX && iz < PNZ && inside(ix, iz), s2 = u === d ? 0 : u ? 1 : 2;
      if (s2 !== side) {
        if (side) out.push([start * PIT_RES - ROOM.x, iz * PIT_RES - ROOM.z, ix * PIT_RES - ROOM.x, iz * PIT_RES - ROOM.z]);
        start = ix; side = s2;
      }
    }
  }
  return out;
}
// Upright strips along edges, from y0 down to y1, textured along their length.
function wallGeometry(edges, y0, y1, uLen, vLen) {
  const pos = [], uvs = [], idx = [];
  for (const [x0, z0, x1, z1] of edges) {
    const n = pos.length / 3, len = Math.hypot(x1 - x0, z1 - z0);
    pos.push(x0, y0, z0, x1, y0, z1, x1, y1, z1, x0, y1, z0);
    uvs.push(0, 1, len / uLen, 1, len / uLen, 1 - (y0 - y1) / vLen, 0, 1 - (y0 - y1) / vLen);
    idx.push(n, n + 1, n + 2, n, n + 2, n + 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}
function buildPits(list) {
  pits = list;
  pitBoxes = list.flatMap((p) => p.rects);
  for (const o of [...pitGroup.children]) { o.geometry?.dispose(); pitGroup.remove(o); }
  const hole = holeGrid(list), isHole = (ix, iz) => hole[iz * PNX + ix] === 1;
  // The floor: the room's plane less the holes, with the plane's own texture mapping.
  floor.geometry.dispose();
  floor.geometry = flatGeometry(gridRects((ix, iz) => !isHole(ix, iz)), 0, (x, z) => [x / W + 0.5, 0.5 - z / D]);
  floor.rotation.x = 0;
  if (!list.length) return;
  const near = (ix, iz) => {
    for (let dz = -1; dz <= 1; dz++) for (let dx = -1; dx <= 1; dx++) {
      const x = ix + dx, z = iz + dz;
      if (x >= 0 && z >= 0 && x < PNX && z < PNZ && isHole(x, z)) return true;
    }
    return false;
  };
  const isRim = (ix, iz) => !isHole(ix, iz) && near(ix, iz);
  const add = (geo, mat, shadow = true) => { const m = new THREE.Mesh(geo, mat); m.receiveShadow = shadow; pitGroup.add(m); return m; };
  add(flatGeometry(gridRects(isHole), -PIT_DEPTH, (x, z) => [x * 2, -z * 2]), pitFloorMat);
  add(flatGeometry(gridRects(isRim), 0.003, (x, z) => [x / 0.5, -z / 0.5]), rimMat);
  const shaft = gridEdges(isHole);
  add(wallGeometry(shaft, 0, -PIT_DEPTH, 1, 1), pitWallMat);
  add(wallGeometry(shaft, 0, -0.18, 0.6, 0.18), pitBandMat);
  // Ink round the opening and round the rim's outer edge.
  const ink = [];
  for (const [x0, z0, x1, z1] of [...shaft, ...gridEdges((ix, iz) => isHole(ix, iz) || isRim(ix, iz))]) ink.push(x0, 0.006, z0, x1, 0.006, z1);
  const lines = new THREE.BufferGeometry();
  lines.setAttribute("position", new THREE.Float32BufferAttribute(ink, 3));
  pitGroup.add(new THREE.LineSegments(lines, inkLine));
}
const inBox = (b, x, z, m = 0) => x > b.minX - m && x < b.maxX + m && z > b.minZ - m && z < b.maxZ + m;
const pitAt = (x, z, m = 0) => pits.find((p) => p.rects.some((b) => inBox(b, x, z, m)));

const wallTex = canvasTex(256, 512, (g, w, h) => {
  for (let x = 0; x < w; x += 32) {
    const grad = g.createLinearGradient(x, 0, x + 32, 0);
    grad.addColorStop(0, "#7d6a70"); grad.addColorStop(0.45, "#66545a");
    grad.addColorStop(0.55, "#524348"); grad.addColorStop(1, "#736066");
    g.fillStyle = grad; g.fillRect(x, 0, 32, h);
  }
  g.fillStyle = "#40343a"; g.fillRect(0, h - 6, w, 6);
});
const hazardTex = canvasTex(256, 64, (g, w, h) => stripes(g, w, h, "#f2b705", "#1b1b1d", 64));
hazardTex.wrapS = THREE.RepeatWrapping;
function roomWall(len, pos, rotY) {
  const t = wallTex.clone(); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(len / 1.6, ROOM.h / 3.2); t.needsUpdate = true;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(len, ROOM.h), toon({ map: t }));
  m.position.copy(pos); m.position.y = ROOM.h / 2; m.rotation.y = rotY;
  scene.add(m);
  const ht = hazardTex.clone(); ht.repeat.set(len / 1.2, 1); ht.needsUpdate = true;
  const band = new THREE.Mesh(new THREE.PlaneGeometry(len, 0.5), toon({ map: ht }));
  band.position.copy(pos); band.position.y = 0.25; band.rotation.y = rotY;
  band.translateZ(0.02);
  scene.add(band);
}
roomWall(W, new THREE.Vector3(0, 0, -ROOM.z), 0);
roomWall(W, new THREE.Vector3(0, 0, ROOM.z), Math.PI);
roomWall(D, new THREE.Vector3(-ROOM.x, 0, 0), Math.PI / 2);
roomWall(D, new THREE.Vector3(ROOM.x, 0, 0), -Math.PI / 2);
const ceiling = new THREE.Mesh(new THREE.PlaneGeometry(W, D), toon({ color: 0x1f191d, side: THREE.DoubleSide }));
ceiling.rotation.x = Math.PI / 2; ceiling.position.y = ROOM.h;
scene.add(ceiling);

const steel = toon({ color: 0x3a2e34 });
const steelLight = toon({ color: 0x655259 });
const wrapMat = toon({ map: canvasTex(64, 64, (g, w, h) => stripes(g, w, h, "#f2b705", "#1b1b1d", 32), [2, 2]) });
const pillars = []; // the building's columns stand out from the side walls, so the bot collides with them
for (let x = -8; x <= 8; x += 4) {
  for (const z of [-ROOM.z + 0.08, ROOM.z - 0.08]) {
    scene.add(inked(new THREE.Mesh(new THREE.BoxGeometry(0.5, ROOM.h, 0.16), steel)).translateX(x).translateY(ROOM.h / 2).translateZ(z));
    pillars.push({ minX: x - 0.25, maxX: x + 0.25, minZ: z - 0.08, maxZ: z + 0.08 });
  }
}
const lampMat = new THREE.MeshBasicMaterial({ color: 0xfff1d6 });
for (let x = -9; x <= 9; x += 6) {
  for (const y of [ROOM.h - 1.0, ROOM.h - 0.2]) {
    const chord = inked(new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.26, D), steel));
    chord.position.set(x, y, 0); scene.add(chord);
  }
  for (let z = -ROOM.z + 1; z <= ROOM.z - 1; z += 2) {
    const post = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.8, 0.1), steelLight);
    post.position.set(x, ROOM.h - 0.6, z); post.rotation.x = (z / 2) % 2 ? 0.6 : -0.6;
    scene.add(post);
  }
  for (const z of [-3.5, 3.5]) {
    const lamp = inked(new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.12, 0.36), lampMat));
    lamp.position.set(x, ROOM.h - 2.4, z); scene.add(lamp);
    const hood = inked(new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.14, 0.46), steel));
    hood.position.set(x, ROOM.h - 2.3, z); scene.add(hood);
    // Hanger rods from each end of the hood up to a clamp on the truss above.
    const top = new THREE.Vector3(x, ROOM.h - 1.13, z);
    for (const side of [-1, 1]) {
      const foot = new THREE.Vector3(x + side * 0.6, ROOM.h - 2.23, z);
      const span = top.clone().sub(foot);
      const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, span.length(), 8), steelLight);
      rod.position.copy(foot).addScaledVector(span, 0.5);
      rod.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), span.normalize());
      scene.add(rod);
    }
    const clamp = inked(new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.1, 0.3), steel));
    clamp.position.copy(top); scene.add(clamp);
  }
}
const glass = new THREE.MeshBasicMaterial({ color: 0x8fa7c4 });
for (const x of [-7.5, 7.5]) {
  const win = inked(new THREE.Mesh(new THREE.BoxGeometry(4.2, 1.4, 0.05), glass));
  win.position.set(x, 7.6, -ROOM.z + 0.03); scene.add(win);
}
// text is a string, or [words, colour] pieces drawn side by side. A lit sign shows its own colours at
// full strength instead of being shaded by the room's light.
const sign = (text, sub, w, h, pos, rotY, lit = false) => {
  const parts = typeof text === "string" ? [[text, "#ece6da"]] : text;
  const tex = canvasTex(1024, Math.round(1024 * h / w), (g, cw, ch) => {
    g.fillStyle = "#1b1b1d"; g.fillRect(0, 0, cw, ch);
    // Hazard-striped strip along the bottom edge.
    const strip = 22;
    g.save();
    g.translate(0, ch - strip);
    g.beginPath(); g.rect(0, 0, cw, strip); g.clip();
    stripes(g, cw, strip, "#f2b705", "#1b1b1d", 40);
    g.restore();
    g.textAlign = "left"; g.textBaseline = "middle";
    g.font = `700 ${ch * (sub ? 0.42 : 0.6)}px "Chakra Petch", sans-serif`;
    let x = (cw - parts.reduce((s, [t]) => s + g.measureText(t).width, 0)) / 2;
    for (const [t, colour] of parts) {
      g.fillStyle = colour;
      g.fillText(t, x, sub ? ch * 0.38 : ch / 2);
      x += g.measureText(t).width;
    }
    if (sub) {
      g.textAlign = "center";
      g.fillStyle = "#9a978f"; g.font = `600 ${ch * 0.17}px "Chakra Petch", sans-serif`; g.fillText(sub, cw / 2, ch * 0.72);
    }
  });
  const mat = lit ? new THREE.MeshBasicMaterial({ map: tex }) : toon({ map: tex });
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
  m.position.copy(pos); m.rotation.y = rotY; scene.add(m);
};
// The main sign (a modelled lightbox, loaded with the other models) hangs on the front of the wall's
// steel ribs; its back sits 0.30 m behind its origin.
const SIGN_AT = new THREE.Vector3(0, 5.6, -ROOM.z + 0.16 + 0.30);
sign("GOAL", null, 3, 0.9, new THREE.Vector3(ROOM.x - 0.05, 5.4, 0), -Math.PI / 2);
sign("TEST SOCKET", null, 3, 0.7, new THREE.Vector3(-ROOM.x + 0.05, 3.2, 0), Math.PI / 2);
// Roller door behind the goal, for units that pass.
const shutter = canvasTex(64, 256, (g, w, h) => {
  for (let y = 0; y < h; y += 16) { g.fillStyle = "#715e62"; g.fillRect(0, y, w, 10); g.fillStyle = "#4f4146"; g.fillRect(0, y + 10, w, 6); }
}, [5, 4]);
const door = new THREE.Mesh(new THREE.PlaneGeometry(6, 4.2), toon({ map: shutter }));
door.position.set(ROOM.x - 0.03, 2.1, 0); door.rotation.y = -Math.PI / 2; scene.add(door);

// --- Maze walls -------------------------------------------------------------------------------
// Wall panels in the sign's style: a bevelled plum-gunmetal frame round a recessed, chamfered inset,
// with a hazard band along the top, slanted vents, corner bolts and dark ink lines.
function chamferPath(g, x0, y0, x1, y1, c) {
  g.beginPath();
  g.moveTo(x0 + c, y0); g.lineTo(x1 - c, y0); g.lineTo(x1, y0 + c); g.lineTo(x1, y1 - c);
  g.lineTo(x1 - c, y1); g.lineTo(x0 + c, y1); g.lineTo(x0, y1 - c); g.lineTo(x0, y0 + c); g.closePath();
}
function bolt(g, x, y, r) {
  g.fillStyle = "#8a6e70"; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
  g.strokeStyle = "#161114"; g.lineWidth = 2; g.stroke();
  g.fillStyle = "#4a3a3f"; g.beginPath(); g.arc(x + r * 0.25, y + r * 0.25, r * 0.45, 0, 7); g.fill();
}
const panelTex = canvasTex(512, 392, (g, w, h) => {
  const band = 46;
  g.fillStyle = "#5e4a50"; g.fillRect(0, 0, w, h);
  // Frame bevel: lit top-left edges, shadowed bottom-right.
  g.fillStyle = "#7a5f60"; g.fillRect(0, band, w, 5); g.fillRect(0, band, 5, h - band);
  g.fillStyle = "#2d242b"; g.fillRect(0, h - 6, w, 6); g.fillRect(w - 6, band, 6, h - band);
  // Recessed inset with a shadow along its top and left, a lit lower edge, and a seam across it.
  const ix0 = 34, iy0 = band + 30, ix1 = w - 34, iy1 = h - 30;
  chamferPath(g, ix0, iy0, ix1, iy1, 22); g.fillStyle = "#3f3238"; g.fill();
  g.save(); chamferPath(g, ix0, iy0, ix1, iy1, 22); g.clip();
  g.fillStyle = "#2a2126"; g.fillRect(ix0, iy0, ix1 - ix0, 9); g.fillRect(ix0, iy0, 9, iy1 - iy0);
  g.fillStyle = "#5a4549"; g.fillRect(ix0, iy1 - 5, ix1 - ix0, 5);
  const seam = Math.round((iy0 + iy1) / 2);
  g.fillStyle = "#241c21"; g.fillRect(ix0, seam - 2, ix1 - ix0, 4);
  g.fillStyle = "#56434a"; g.fillRect(ix0, seam + 2, ix1 - ix0, 2);
  // Slanted vents low on the right, like the sign's.
  g.fillStyle = "#1a1418";
  for (let k = 0; k < 4; k++) {
    const x = ix1 - 120 + k * 22, y = iy1 - 52;
    g.beginPath(); g.moveTo(x, y + 30); g.lineTo(x + 12, y); g.lineTo(x + 20, y); g.lineTo(x + 8, y + 30); g.closePath(); g.fill();
  }
  g.restore();
  chamferPath(g, ix0, iy0, ix1, iy1, 22); g.strokeStyle = "#161114"; g.lineWidth = 3; g.stroke();
  for (const x of [17, w - 17]) for (const y of [band + 17, h - 17]) bolt(g, x, y, 7);
  g.save(); g.beginPath(); g.rect(0, 0, w, band); g.clip(); stripes(g, w, band, "#f2b705", "#1b1b1d", 60); g.restore();
  g.fillStyle = "#161114"; g.fillRect(0, band - 3, w, 3);
});
const panelMat = toon({ map: panelTex });
const wallEdgeMat = toon({ color: 0x3a2e34 });     // panel ends and the top rail
// Posts: a lit left edge, a centre seam groove, and bolts near the top and bottom.
const postMat = toon({ map: canvasTex(128, 384, (g, w, h) => {
  g.fillStyle = "#463840"; g.fillRect(0, 0, w, h);
  g.fillStyle = "#6a5256"; g.fillRect(0, 0, 6, h);
  g.fillStyle = "#2a2126"; g.fillRect(w - 7, 0, 7, h);
  g.fillStyle = "#241c21"; g.fillRect(w / 2 - 3, 18, 6, h - 36);
  g.fillStyle = "#5c4a50"; g.fillRect(w / 2 + 3, 18, 2, h - 36);
  for (const y of [30, h - 30]) for (const x of [26, w - 26]) bolt(g, x, y, 7);
}) });
const lightBarMat = new THREE.MeshBasicMaterial({ color: 0xffc35a });
// Light-strip layouts along the top of a panel, as [centre, length] in metres from its middle.
const LIGHT_LAYOUTS = [
  [[-0.42, 0.42]],                                   // one strip, left
  [[0.42, 0.42]],                                    // one strip, right
  [[0, 0.62]],                                       // one long strip, centred
  [[-0.45, 0.3], [0.45, 0.3]],                       // a pair at the ends
  [[-0.38, 0.16], [-0.16, 0.16], [0.06, 0.16]],      // a row of three short ones
];
// Post caps: drawn at 512 px so the stripes stay crisp when the camera comes close.
const capMat = toon({ map: canvasTex(512, 512, (g, w, h) => stripes(g, w, h, "#f2b705", "#1b1b1d", 192)) });
const walls = []; // { minX, maxX, minZ, maxZ, mesh, rise, target, h }
// Panels stop at the posts and posts stand alone at each grid point, so no two wall
// pieces overlap or share a face. Panels run 2 cm into their posts.
function wallBoxes(test) {
  const out = [];
  const box = (cx, cz, sx, sz, h, post) => out.push({ cx, cz, sx, sz, h, post,
    minX: cx - sx / 2, maxX: cx + sx / 2, minZ: cz - sz / 2, maxZ: cz + sz / 2 });
  const posts = new Map();
  const post = (x, z) => posts.set(`${x},${z}`, [x, z]);
  for (const [i, r0, r1] of test.v) {
    const x = MAZE_X0 + i * CELL;
    for (let r = r0; r <= r1; r++) {
      const z0 = MAZE_Z0 + r * CELL, z1 = z0 + CELL;
      box(x, (z0 + z1) / 2, WALL_T, CELL - POST + 0.04, WALL_H, false);
      post(x, z0); post(x, z1);
    }
  }
  for (const [j, c0, c1] of test.h) {
    const z = MAZE_Z0 + j * CELL;
    for (let c = c0; c <= c1; c++) {
      const x0 = MAZE_X0 + c * CELL, x1 = x0 + CELL;
      box((x0 + x1) / 2, z, CELL - POST + 0.04, WALL_T, WALL_H, false);
      post(x0, z); post(x1, z);
    }
  }
  for (const [x, z] of posts.values()) {
    const zz = THREE.MathUtils.clamp(z, -ROOM.z + POST / 2 + 0.01, ROOM.z - POST / 2 - 0.01);
    box(x, zz, POST, POST, WALL_H + 0.08, true);
  }
  return out;
}
// One wall per slot position: pieces that stand in the same place in both layouts stay up (or rise
// back if they were sinking); only the others sink or rise.
const wallKey = (b) => `${b.cx.toFixed(3)},${b.cz.toFixed(3)},${b.sx.toFixed(3)},${b.sz.toFixed(3)}`;
function buildWalls(test) {
  const have = new Map(walls.map((w) => [wallKey(w), w]));
  const keep = new Set();
  for (const b of wallBoxes(test)) {
    const old = have.get(wallKey(b));
    if (old) { old.target = 1; keep.add(old); continue; }
    // Panels show the panel texture on their two long faces only; box faces run +x, -x, +y, -y, +z, -z.
    const alongX = b.sx > b.sz;
    const mats = b.post ? postMat : alongX
      ? [wallEdgeMat, wallEdgeMat, wallEdgeMat, wallEdgeMat, panelMat, panelMat]
      : [panelMat, panelMat, wallEdgeMat, wallEdgeMat, wallEdgeMat, wallEdgeMat];
    const mesh = inked(new THREE.Mesh(new THREE.BoxGeometry(b.sx, b.h, b.sz), mats));
    mesh.castShadow = true; mesh.receiveShadow = true;
    mesh.position.set(b.cx, -b.h / 2, b.cz);
    if (!b.post) {
      // A raised rail along the top, and a glowing amber light bar on each face, like the sign's.
      const len = (alongX ? b.sx : b.sz) - 0.06;
      const rail = inked(new THREE.Mesh(alongX ? new THREE.BoxGeometry(len, 0.07, b.sz + 0.05) : new THREE.BoxGeometry(b.sx + 0.05, 0.07, len), wallEdgeMat));
      rail.position.y = b.h / 2 + 0.035;
      mesh.add(rail);
      // Light strips: one of a few layouts, picked from the panel's position so it never changes.
      const layout = LIGHT_LAYOUTS[Math.abs(Math.round(b.cx * 7 + b.cz * 13)) % LIGHT_LAYOUTS.length];
      const off = (alongX ? b.sz : b.sx) / 2 + 0.006;
      for (const side of [-1, 1]) {
        for (const [at, length] of layout) {
          const bar = inked(new THREE.Mesh(alongX ? new THREE.BoxGeometry(length, 0.045, 0.02) : new THREE.BoxGeometry(0.02, 0.045, length), lightBarMat));
          bar.position.set(alongX ? at : side * off, 0.33, alongX ? side * off : at);
          mesh.add(bar);
        }
      }
    }
    if (b.post) {
      const cap = new THREE.Mesh(new THREE.BoxGeometry(POST + 0.02, 0.05, POST + 0.02), capMat);
      cap.position.y = b.h / 2 + 0.025;
      mesh.add(cap);
    }
    scene.add(mesh);
    const w = { ...b, mesh, rise: 0, target: 1 };
    walls.push(w);
    keep.add(w);
  }
  for (const w of walls) if (!keep.has(w)) w.target = -0.02; // sink the rest
  linkWalls();
}
// Each panel's links are the posts at its ends, and each post's are the panels meeting it (panels run
// 2 cm into their posts, so their boxes overlap).
function linkWalls() {
  const live = walls.filter((w) => w.target > 0), e = 0.03;
  for (const w of live) {
    w.links = live.filter((o) => o !== w && o.post !== w.post &&
      o.minX <= w.maxX + e && o.maxX >= w.minX - e && o.minZ <= w.maxZ + e && o.maxZ >= w.minZ - e);
  }
}
function updateWalls(dt) {
  for (let k = walls.length - 1; k >= 0; k--) {
    const w = walls[k];
    w.rise += Math.sign(w.target - w.rise) * Math.min(Math.abs(w.target - w.rise), dt / 1.1);
    w.mesh.position.y = -w.h / 2 + w.rise * w.h;
    if (w.target < 0 && w.rise <= 0) {
      scene.remove(w.mesh);
      walls.splice(k, 1);
    }
  }
}
const solidWalls = () => walls.filter((w) => w.target > 0 && w.rise > 0.5);

// --- Models ---------------------------------------------------------------------------------
const loader = new GLTFLoader();
function toonify(root) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    const m = o.material;
    o.material = toon({ color: m.color, emissive: m.emissive, emissiveIntensity: Math.min(m.emissiveIntensity ?? 1, 1.2) });
    o.castShadow = true;
  });
}
const outlineMat = new THREE.ShaderMaterial({
  uniforms: { thickness: { value: 0.005 }, color: { value: new THREE.Color(0x101114) } },
  vertexShader: `
    #include <common>
    #include <skinning_pars_vertex>
    uniform float thickness;
    attribute float outlineScale; // 0 inside the socket, where the shell would poke into the pin holes
    void main() {
      #include <skinbase_vertex>
      #include <begin_vertex>
      #include <beginnormal_vertex>
      #include <skinnormal_vertex>
      #include <skinning_vertex>
      vec4 mv = modelViewMatrix * vec4(transformed, 1.0);
      mv.xyz += normalize(normalMatrix * objectNormal) * thickness * outlineScale;
      gl_Position = projectionMatrix * mv;
    }`,
  fragmentShader: `
    uniform vec3 color;
    void main() { gl_FragColor = vec4(color, 1.0); }`,
  side: THREE.BackSide,
});

// --- Cable ----------------------------------------------------------------------------------------
// The game measures the cable a route needs with a taut line from the socket that wraps the wall
// corners it is pulled round; it changes smoothly, so the reading never jumps. What you see is a rope
// that lies where the bot dragged it, slides round walls and his body, never bends tighter than
// BEND_R, and is only pulled straight as the cable runs out.

// Drawing buffer for the tube: n + 1 points along the cable, rebuilt every frame.
let rope = null; // { n, seg, len, a, P }
function makeRope(len) {
  const n = Math.max(160, Math.round(len / 0.05));
  return { n, seg: len / n, len, a: 0, P: new Float32Array((n + 1) * 3) };
}
const cableDrops = () => wallEnd.y + 0.5; // socket height down to the floor, and up to the bot's plug
const SOCKET_DROP = 0.9; // length of cable over which it drops from the socket to the floor
const socketFoot = () => new THREE.Vector2(wallEnd.x + 0.05, wallEnd.z);
const angleDiff = (a, b) => Math.atan2(Math.sin(a - b), Math.cos(a - b));
const cross2 = (ax, az, bx, bz) => ax * bz - az * bx;

// Walls standing right now, bucketed on a 1 m grid, and the corners the taut line can wrap.
let wallList = [], wallGrid = new Map(), corners = [], taut = null;
const NO_WALLS = [];
const cellKey = (ix, iz) => (ix + 64) * 256 + iz + 64;
function setWallList(list) {
  if (list.length === wallList.length && list.every((w, i) => w === wallList[i])) return;
  wallList = list;
  wallGrid = new Map();
  for (const w of list) {
    for (let ix = Math.floor(w.minX - 0.3); ix <= Math.floor(w.maxX + 0.3); ix++) {
      for (let iz = Math.floor(w.minZ - 0.3); iz <= Math.floor(w.maxZ + 0.3); iz++) {
        const k = cellKey(ix, iz);
        if (!wallGrid.has(k)) wallGrid.set(k, []);
        wallGrid.get(k).push(w);
      }
    }
  }
  corners = wallCorners(list);
  if (taut) taut.corners = corners;
}
const wallsNear = (x, z) => wallGrid.get(cellKey(Math.floor(x), Math.floor(z))) || NO_WALLS;

// Taut line: anchors are wall corners (kept TAUT_E off the walls) that the line from the socket bends
// round. Corners inside a neighbouring wall piece can't be touched, so they're left out.
const TAUT_E = 0.08;
function wallCorners(boxes) {
  const e = TAUT_E, out = [];
  const buried = (x, z, own) => boxes.some((o) => o !== own && x > o.minX - e && x < o.maxX + e && z > o.minZ - e && z < o.maxZ + e);
  for (const w of boxes) {
    for (const x of [w.minX - e, w.maxX + e]) {
      for (const z of [w.minZ - e, w.maxZ + e]) if (!buried(x, z, w)) out.push(new THREE.Vector2(x, z));
    }
  }
  return out;
}
class Taut {
  constructor(from, at, cornerList) {
    this.anchors = [{ p: from.clone(), s: 0 }];
    this.len = 0; // along the anchors
    this.at = at.clone();
    this.corners = cornerList;
  }
  get last() { return this.anchors[this.anchors.length - 1].p; }
  length() { return this.len + this.last.distanceTo(this.at); }
  moveTo(p) {
    const from = this.at.clone(), steps = Math.max(1, Math.ceil(from.distanceTo(p) / 0.02));
    for (let k = 1; k <= steps; k++) {
      const q = from.clone().lerp(p, k / steps);
      this.step(this.at, q);
      this.at.copy(q);
    }
  }
  step(p0, p1) {
    const A = this.anchors;
    // The last corner lets go once the line bends the other way at it.
    while (A.length > 1) {
      const c = A[A.length - 1], b = A[A.length - 2];
      if (c.s * cross2(c.p.x - b.p.x, c.p.y - b.p.y, p1.x - c.p.x, p1.y - c.p.y) > 0) break;
      A.pop();
      this.len -= c.p.distanceTo(b.p);
    }
    // As the line from the last anchor sweeps from p0 to p1 it catches the first corner in its way,
    // then carries on sweeping round that corner.
    let q = p0.clone();
    for (let guard = 0; guard < 8; guard++) {
      const a = A[A.length - 1].p;
      const ux = q.x - a.x, uz = q.y - a.y;
      const s = Math.sign(cross2(ux, uz, p1.x - a.x, p1.y - a.y));
      if (!s) return;
      let best = null, bestAng = Infinity;
      for (const c of this.corners) {
        const cx = c.x - a.x, cz = c.y - a.y;
        if (cx * cx + cz * cz < 1e-8) continue;
        if (s * cross2(ux, uz, cx, cz) <= 0) continue;
        if (s * cross2(p1.x - q.x, p1.y - q.y, c.x - q.x, c.y - q.y) < 0) continue;
        if (s * cross2(a.x - p1.x, a.y - p1.y, c.x - p1.x, c.y - p1.y) < 0) continue;
        const ang = Math.atan2(Math.abs(cross2(ux, uz, cx, cz)), ux * cx + uz * cz);
        if (ang < bestAng) { bestAng = ang; best = c; }
      }
      if (!best) return;
      A.push({ p: best.clone(), s });
      this.len += best.distanceTo(a);
      const fx = best.x - a.x, fz = best.y - a.y, ex = p1.x - q.x, ez = p1.y - q.y;
      const den = cross2(ex, ez, fx, fz);
      const u = Math.abs(den) < 1e-12 ? 0 : cross2(a.x - q.x, a.y - q.y, fx, fz) / den;
      q = new THREE.Vector2(q.x + ex * THREE.MathUtils.clamp(u, 0, 1), q.y + ez * THREE.MathUtils.clamp(u, 0, 1));
    }
  }
}

// Shortest way from a to f that keeps outside the bot's body.
function aroundBot(a, f) {
  const R = BODY_R, ax = a.x - bot.pos.x, az = a.y - bot.pos.z, fx = f.x - bot.pos.x, fz = f.y - bot.pos.z;
  const da = Math.hypot(ax, az), df = Math.hypot(fx, fz), straight = a.distanceTo(f);
  if (da <= R || df <= R) return straight;
  const ex = f.x - a.x, ez = f.y - a.y;
  const t = THREE.MathUtils.clamp(-(ax * ex + az * ez) / Math.max(1e-9, ex * ex + ez * ez), 0, 1);
  if (Math.hypot(ax + ex * t, az + ez * t) >= R) return straight;
  const theta = Math.acos(THREE.MathUtils.clamp((ax * fx + az * fz) / (da * df), -1, 1));
  const phi = Math.acos(R / da) + Math.acos(R / df);
  return Math.sqrt(da * da - R * R) + Math.sqrt(df * df - R * R) + R * Math.max(0, theta - phi);
}

// The drawn rope: 2D points on the floor from the socket to the bot's plug. Two points at each end are
// pinned so the cable leaves the socket and the plug straight along their axes.
const SEG = 0.07, ROPE_K = 0.085, ROPE_D = 0.17, BODY_R = 0.31, BEND_R = 0.16, STEP_MAX = 0.03, ITER = 6;
let rp = [], ropeFree = false, ropeTarget = 0, fallT = 0, cableOut = 0, winding = 0;
const tailPins = () => [botEnd.clone().addScaledVector(botDir, 0.13), botEnd.clone().addScaledVector(botDir, 0.06)];

// Keep a rope point ROPE_D from every wall and pit opening, with corners rounded off, and outside the bot when close
// to him along the cable. Walls are at least 0.43 m thick with that margin and points move at most
// STEP_MAX at a time, so a point can never be pushed out through the far side.
function pushRope(p, nearBot) {
  if (nearBot) {
    const dx = p.x - bot.pos.x, dz = p.y - bot.pos.z, d = Math.hypot(dx, dz);
    if (d < BODY_R) {
      if (d > 1e-6) { p.x = bot.pos.x + (dx / d) * BODY_R; p.y = bot.pos.z + (dz / d) * BODY_R; } else p.x += BODY_R;
    }
  }
  for (let pass = 0; pass < 2; pass++) {
    let moved = false;
    for (const w of pitBoxes.length ? wallsNear(p.x, p.y).concat(pitBoxes) : wallsNear(p.x, p.y)) {
      const x0 = w.minX + ROPE_K, x1 = w.maxX - ROPE_K, z0 = w.minZ + ROPE_K, z1 = w.maxZ - ROPE_K;
      const cx = THREE.MathUtils.clamp(p.x, x0, x1), cz = THREE.MathUtils.clamp(p.y, z0, z1);
      const dx = p.x - cx, dz = p.y - cz, d2 = dx * dx + dz * dz;
      if (d2 >= ROPE_D * ROPE_D) continue;
      moved = true;
      if (d2 > 1e-12) {
        const d = Math.sqrt(d2);
        p.x = cx + (dx / d) * ROPE_D; p.y = cz + (dz / d) * ROPE_D;
      } else {
        const opts = [[x0 - ROPE_D - p.x, 0], [x1 + ROPE_D - p.x, 0], [0, z0 - ROPE_D - p.y], [0, z1 + ROPE_D - p.y]];
        opts.sort((a, b) => Math.hypot(...a) - Math.hypot(...b));
        p.x += opts[0][0]; p.y += opts[0][1];
      }
    }
    if (!moved) break;
  }
  p.x = THREE.MathUtils.clamp(p.x, -ROOM.x + 0.1, ROOM.x - 0.1);
  p.y = THREE.MathUtils.clamp(p.y, -ROOM.z + 0.1, ROOM.z - 0.1);
}
function moveToward(p, tx, tz, nearBot) {
  let dx = tx - p.x, dz = tz - p.y;
  const d = Math.hypot(dx, dz);
  if (d > STEP_MAX) { dx *= STEP_MAX / d; dz *= STEP_MAX / d; }
  p.x += dx; p.y += dz;
  pushRope(p, nearBot);
}
function polyLen(pts) {
  let s = 0;
  for (let i = 1; i < pts.length; i++) s += pts[i].distanceTo(pts[i - 1]);
  return s;
}
function pinRope() {
  const f = socketFoot(), m = rp.length;
  rp[0].copy(f);
  rp[1].set(f.x + SEG, f.y);
  if (!ropeFree) {
    const [a, b] = tailPins();
    rp[m - 2].set(a.x, a.z);
    rp[m - 1].set(b.x, b.z);
    // Backed up to a wall, the cable leaving the plug bends away from it rather than into it.
    pushRope(rp[m - 2], false);
    pushRope(rp[m - 1], false);
  }
}
function resampleRope(count) {
  const cum = [0];
  for (let i = 1; i < rp.length; i++) cum.push(cum[i - 1] + rp[i].distanceTo(rp[i - 1]));
  const total = cum[cum.length - 1], out = [];
  let s = 0;
  for (let k = 0; k <= count; k++) {
    const d = (k / count) * total;
    while (s < cum.length - 2 && cum[s + 1] < d) s++;
    const t = THREE.MathUtils.clamp((d - cum[s]) / Math.max(1e-9, cum[s + 1] - cum[s]), 0, 1);
    out.push(rp[s].clone().lerp(rp[s + 1], t));
  }
  rp = out;
}
// Slack rope keeps its shape: just split long links (the end being dragged on) and drop bunched points.
function tidyRope() {
  for (let i = 1; i < rp.length - 1; i++) {
    if (rp[i].distanceTo(rp[i + 1]) > SEG * 1.5) { rp.splice(i + 1, 0, rp[i].clone().lerp(rp[i + 1], 0.5)); i--; }
  }
  const keep = ropeFree ? 1 : 2;
  for (let i = 2; i < rp.length - 1 - keep; i++) {
    if (rp[i].distanceTo(rp[i - 1]) < SEG * 0.4) { rp.splice(i, 1); i--; }
  }
}
// How far the cable near the bot winds round his body (radians). Cable counts fully against his body
// and fades out by 0.55 m from his centre, so the count changes smoothly.
function ropeWinding() {
  const cx = bot.pos.x, cz = bot.pos.z;
  let w = 0;
  for (let i = rp.length - 1; i > 0; i--) {
    const a = rp[i], b = rp[i - 1];
    const r = Math.hypot((a.x + b.x) / 2 - cx, (a.y + b.y) / 2 - cz);
    const k = THREE.MathUtils.clamp((0.55 - r) / 0.2, 0, 1);
    if (k > 0) w += k * angleDiff(Math.atan2(b.y - cz, b.x - cx), Math.atan2(a.y - cz, a.x - cx));
  }
  return Math.abs(w);
}
// Cable wound round him past half a turn is cable used.
const wrapExtra = () => BODY_R * Math.max(0, winding - Math.PI);

function simRope(dt) {
  pinRope();
  const len = polyLen(rp);
  if (ropeFree) {
    // The reel winds the loose end back in, stopping while the end still lies on the flat floor (past the
    // stretch where the cable climbs to the socket).
    ropeTarget = Math.max(SOCKET_DROP + 0.6, ropeTarget - dt * 1.6);
  } else {
    const rem = THREE.MathUtils.clamp(1 - needed / rope.len, 0, 1);
    const geo = taut.len + aroundBot(taut.last, rp[rp.length - 1]);
    ropeTarget = (geo + wrapExtra()) * (1.015 + 0.07 * rem) + 0.08 + 0.6 * rem;
  }
  const pulled = len > ropeTarget;
  if (pulled) resampleRope(Math.max(5, Math.ceil(ropeTarget / SEG)));
  else tidyRope();
  pinRope();
  const m = rp.length, hi = ropeFree ? m - 1 : m - 3;
  const rest = ropeTarget / (m - 1);
  const nearFrom = m - 1 - Math.ceil(4 / SEG);
  const pull = (i, j) => {
    const p = rp[i], q = rp[j], dx = p.x - q.x, dz = p.y - q.y, d = Math.hypot(dx, dz);
    if (d > rest) moveToward(p, q.x + (dx / d) * rest, q.y + (dz / d) * rest, i >= nearFrom);
  };
  for (let it = 0; it < ITER; it++) {
    if (pulled) {
      for (let i = 2; i <= hi; i++) pull(i, i - 1);
      for (let i = Math.min(hi, m - 2); i >= 2; i--) pull(i, i + 1);
    }
    // Ease out any bend tighter than BEND_R.
    for (let i = 2; i <= Math.min(hi, m - 2); i++) {
      const a = rp[i - 1], b = rp[i], c = rp[i + 1];
      const abx = b.x - a.x, abz = b.y - a.y, bcx = c.x - b.x, bcz = c.y - b.y;
      const l1 = Math.hypot(abx, abz), l2 = Math.hypot(bcx, bcz);
      if (l1 < 1e-6 || l2 < 1e-6) continue;
      const theta = Math.acos(THREE.MathUtils.clamp((abx * bcx + abz * bcz) / (l1 * l2), -1, 1));
      const most = (0.5 * (l1 + l2)) / BEND_R;
      if (theta <= most) continue;
      const k = 0.5 * (1 - most / theta);
      moveToward(b, b.x + ((a.x + c.x) / 2 - b.x) * k, b.y + ((a.y + c.y) / 2 - b.y) * k, i >= nearFrom);
    }
    if (!pulled && it >= 1) break;
  }
  if (!pulled) for (let i = Math.max(2, nearFrom); i <= hi; i++) pushRope(rp[i], true);
  cableOut = polyLen(rp);
  if (!ropeFree) winding = ropeWinding();
}

// The rope in 3D. It drops from the socket in one smooth curve, runs along the floor, and rises to the
// plug the same way; near the bot it stays at plug height while it's wound round him. When the ends are
// too close for both drops to reach the floor, the cable hangs between them in one sag.
// The cable hanging from the plug is drawn as one curve to where it lands, HANG out along the floor
// rope, so slack bunched under the plug never shows as a fold. Returns the landing index, or -1 when
// the straight way there would pass through the bot or a wall.
const HANG = 0.75;
function hangLanding() {
  const fx = botEnd.x + botDir.x * 0.06, fz = botEnd.z + botDir.z * 0.06;
  let j = -1;
  for (let i = rp.length - 1; i >= 3; i--) {
    if (Math.hypot(rp[i].x - fx, rp[i].y - fz) >= HANG) { j = i; break; }
  }
  if (j < 3) return -1;
  const ax = fx - bot.pos.x, az = fz - bot.pos.z, ex = rp[j].x - fx, ez = rp[j].y - fz;
  const t = THREE.MathUtils.clamp(-(ax * ex + az * ez) / Math.max(1e-9, ex * ex + ez * ez), 0, 1);
  if (Math.hypot(ax + ex * t, az + ez * t) < BODY_R - 0.02) return -1;
  const a = new THREE.Vector3(fx, 0.3, fz), b = new THREE.Vector3(rp[j].x, 0.3, rp[j].y);
  return wallList.some((w) => segmentHitsBox(a, b, w)) ? -1 : j;
}
function cablePoints() {
  const out = [wallEnd.clone()], m = rp.length;
  const arc = new Float32Array(m), fromHead = new Float32Array(m);
  for (let i = m - 2; i >= 0; i--) arc[i] = arc[i + 1] + rp[i].distanceTo(rp[i + 1]);
  for (let i = 1; i < m; i++) fromHead[i] = fromHead[i - 1] + rp[i].distanceTo(rp[i - 1]);
  const smooth = (t) => 1 - t * t * (3 - 2 * t);
  const head = (i) => wallEnd.y * smooth(Math.min(1, fromHead[i] / SOCKET_DROP));
  const h = new Float32Array(m);
  // sc: how much cable near the plug lies against his body (wound round him).
  let landing = -1, sc = 0;
  if (!ropeFree) {
    for (let i = m - 1; i >= 0 && arc[i] - sc <= 0.35; i--) {
      if (Math.hypot(rp[i].x - bot.pos.x, rp[i].y - bot.pos.z) < 0.42) sc = arc[i];
    }
    if (sc === 0) landing = hangLanding();
  }
  if (landing >= 0) {
    // The floor rope stays on the floor; the hanging curve is added below.
  } else if (!ropeFree) {
    const H0 = botEnd.y;
    const hw = (s) => Math.max(0.25, H0 - (0.05 * s) / (2 * Math.PI * BODY_R));
    const hc = hw(sc), drop = 0.3 + hc * 1.6;
    for (let i = 0; i < m; i++) {
      const t = Math.min(1, Math.max(0, arc[i] - sc) / drop);
      h[i] = arc[i] <= sc ? hw(arc[i]) : hc * (1 - t * t * (3 - 2 * t));
    }
  } else {
    // The freed end falls to the floor.
    const H = botEnd.y * Math.max(0, 1 - fallT / 0.3) ** 2;
    for (let i = 0; i < m; i++) { const t = Math.min(1, arc[i] / 0.8); h[i] = H * (1 - t * t * (3 - 2 * t)); }
  }
  // Join the socket's drop with the plug's: a smooth maximum, so where they overlap there's no crease.
  for (let i = 0; i < m; i++) {
    const a = head(i), b = h[i], k = Math.min(0.1, 2 * Math.min(a, b));
    const w = k > 1e-6 ? Math.max(0, k - Math.abs(a - b)) / k : 0;
    h[i] = Math.max(a, b) + w * w * k * 0.25;
  }
  // Two light smoothing passes over the drawn copy round off what's left of the link-to-link corners;
  // they move points by millimetres, well inside the wall margin.
  let sm = rp.map((p, i) => new THREE.Vector3(p.x, Math.max(CABLE_R, h[i]), p.y));
  for (let pass = 0; pass < 2; pass++) {
    const next = sm.map((p) => p.clone());
    for (let i = 2; i < m - 2; i++) next[i].lerp(sm[i - 1].clone().add(sm[i + 1]).multiplyScalar(0.5), 0.5);
    sm = next;
  }
  if (landing >= 0) {
    // From the landing point, carrying on the floor rope's direction, up to the plug along its axis.
    const P0 = sm[landing], back = Math.max(0, landing - 3);
    const dir = new THREE.Vector3(rp[landing].x - rp[back].x, 0, rp[landing].y - rp[back].y);
    if (dir.lengthSq() < 1e-8) dir.set(botEnd.x - P0.x, 0, botEnd.z - P0.z);
    dir.normalize();
    const span = Math.hypot(botEnd.x - P0.x, botEnd.z - P0.z);
    const P1 = P0.clone().addScaledVector(dir, span * 0.4);
    const P2 = botEnd.clone().addScaledVector(botDir, 0.42);
    out.push(...sm.slice(0, landing + 1));
    for (let k = 1; k <= 16; k++) {
      const t = k / 16, u = 1 - t;
      out.push(new THREE.Vector3()
        .addScaledVector(P0, u * u * u).addScaledVector(P1, 3 * u * u * t)
        .addScaledVector(P2, 3 * u * t * t).addScaledVector(botEnd, t * t * t));
    }
    return out;
  }
  out.push(...sm);
  if (!ropeFree) out.push(botEnd.clone());
  return out;
}

function drawCable(dt) {
  if (ropeFree) fallT += dt;
  simRope(dt);
  const pts = cablePoints();
  const cum = [0];
  for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + pts[i].distanceTo(pts[i - 1]));
  const total = cum[cum.length - 1];
  rope.drawn = total;
  const { n, P } = rope;
  let s = 0;
  for (let i = 0; i <= n; i++) {
    const d = (i / n) * total;
    while (s < cum.length - 2 && cum[s + 1] < d) s++;
    const t = THREE.MathUtils.clamp((d - cum[s]) / Math.max(1e-6, cum[s + 1] - cum[s]), 0, 1);
    const v = pts[s].clone().lerp(pts[s + 1], t);
    P[i * 3] = v.x; P[i * 3 + 1] = v.y; P[i * 3 + 2] = v.z;
  }
  if (ropeFree) {
    // The loose plug rides on the end of the cable. The plug is thicker than the cable, so the last
    // stretch of cable rises smoothly to the plug's axis height; the plug then sits on the floor with
    // the cable running straight into its boot.
    const step = total / n, rise = 0.35, back = 0.12, axisY = PLUG_R + 0.002; // 2 mm clear of the floor
    for (let i = n, sBack = 0; i >= 0 && sBack <= rise; i--, sBack += step) {
      const w = 1 - sBack / rise, e = w * w * (3 - 2 * w);
      P[i * 3 + 1] = Math.max(P[i * 3 + 1], CABLE_R + (axisY - CABLE_R) * e);
    }
    const end = new THREE.Vector3(P[n * 3], P[n * 3 + 1], P[n * 3 + 2]);
    const k = Math.max(0, n - Math.max(1, Math.round(back / Math.max(step, 1e-6))));
    const dir = new THREE.Vector3(P[k * 3], P[k * 3 + 1], P[k * 3 + 2]).sub(end);
    if (dir.lengthSq() < 1e-10) dir.copy(botDir).negate();
    // Resting on the floor, the plug lies level.
    if (end.y <= axisY + 0.005) dir.y = 0;
    if (dir.lengthSq() < 1e-10) dir.set(1, 0, 0);
    dir.normalize();
    botPlug.quaternion.setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir);
    botPlug.position.copy(end).addScaledVector(dir, -PLUG_LEN);
  }
}

class Tube {
  constructor(n, radius, radial, material) {
    this.n = n; this.r = radius; this.radial = radial;
    const verts = (n + 1) * radial;
    this.pos = new Float32Array(verts * 3);
    this.nrm = new Float32Array(verts * 3);
    const idx = [];
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < radial; j++) {
        const a = i * radial + j, b = i * radial + ((j + 1) % radial);
        idx.push(a, b, a + radial, b, b + radial, a + radial);
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage));
    geo.setAttribute("normal", new THREE.BufferAttribute(this.nrm, 3).setUsage(THREE.DynamicDrawUsage));
    geo.setIndex(idx);
    this.mesh = new THREE.Mesh(geo, material);
    this.mesh.frustumCulled = false;
  }
  update(frames) {
    const { pos, nrm, radial, r, n } = this;
    for (let i = 0; i <= n; i++) {
      const f = frames[i];
      for (let j = 0; j < radial; j++) {
        const a = (j / radial) * Math.PI * 2, ca = Math.cos(a), sa = Math.sin(a);
        const nx = f.n.x * ca + f.b.x * sa, ny = f.n.y * ca + f.b.y * sa, nz = f.n.z * ca + f.b.z * sa;
        const k = (i * radial + j) * 3;
        nrm[k] = nx; nrm[k + 1] = ny; nrm[k + 2] = nz;
        pos[k] = f.p.x + nx * r; pos[k + 1] = f.p.y + ny * r; pos[k + 2] = f.p.z + nz * r;
      }
    }
    this.mesh.geometry.attributes.position.needsUpdate = true;
    this.mesh.geometry.attributes.normal.needsUpdate = true;
  }
  dispose() { scene.remove(this.mesh); this.mesh.geometry.dispose(); }
}

let frames = [];
function buildFrames() {
  const { n, P, a } = rope;
  for (let i = a; i <= n; i++) frames[i].p.set(P[i * 3], P[i * 3 + 1], P[i * 3 + 2]);
  for (let i = a; i <= n; i++) {
    frames[i].t.subVectors(frames[Math.min(n, i + 1)].p, frames[Math.max(a, i - 1)].p);
    if (frames[i].t.lengthSq() < 1e-12) frames[i].t.copy(wallDir);
    frames[i].t.normalize();
  }
  const f0 = frames[a];
  f0.n.set(0, 1, 0).addScaledVector(f0.t, -f0.t.y);
  if (f0.n.lengthSq() < 1e-8) f0.n.set(1, 0, 0);
  f0.n.normalize();
  f0.b.crossVectors(f0.t, f0.n);
  for (let i = a + 1; i <= n; i++) {
    const f = frames[i], prev = frames[i - 1];
    f.n.copy(prev.n).addScaledVector(f.t, -prev.n.dot(f.t));
    if (f.n.lengthSq() < 1e-8) f.n.copy(prev.n);
    f.n.normalize();
    f.b.crossVectors(f.t, f.n);
  }
  for (let i = 0; i < a; i++) {
    const f = frames[i];
    f.p.copy(f0.p); f.t.copy(f0.t); f.n.copy(f0.n); f.b.copy(f0.b);
  }
}

const cableMat = toon({ color: 0x2fbf71 });
const inkMat = new THREE.MeshBasicMaterial({ color: 0x101114, side: THREE.BackSide });
const bandMat = toon({ color: 0xa2a8b2 });
let cable = null, cableInk = null, bands = null;
const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _up = new THREE.Vector3(0, 1, 0), _one = new THREE.Vector3(1, 1, 1);
function buildCableMeshes() {
  if (cable) { cable.dispose(); cableInk.dispose(); scene.remove(bands); bands.dispose(); }
  const n = rope.n;
  cable = new Tube(n, CABLE_R, 10, cableMat);
  cable.mesh.castShadow = true;
  cableInk = new Tube(n, CABLE_R + 0.006, 8, inkMat);
  scene.add(cable.mesh, cableInk.mesh);
  const count = Math.max(1, Math.ceil(rope.len * 1.1 / BAND_GAP));
  bands = new THREE.InstancedMesh(new THREE.CylinderGeometry(CABLE_R * 1.45, CABLE_R * 1.45, 0.045, 14), bandMat, count);
  bands.castShadow = true; bands.frustumCulled = false;
  scene.add(bands);
  frames = Array.from({ length: n + 1 }, () => ({ p: new THREE.Vector3(), t: new THREE.Vector3(), n: new THREE.Vector3(), b: new THREE.Vector3() }));
}
// A band every BAND_GAP metres along the cable as drawn; bands past the plug end are hidden.
const BAND_GAP = 1.6, _zero = new THREE.Vector3(0, 0, 0);
function updateBands() {
  const total = rope.drawn || rope.len;
  for (let k = 0; k < bands.count; k++) {
    const d = (k + 1) * BAND_GAP;
    const f = frames[Math.max(rope.a, Math.min(rope.n - 2, Math.round((d / total) * rope.n)))];
    _q.setFromUnitVectors(_up, f.t);
    _m.compose(f.p, _q, d < total - 0.4 ? _one : _zero);
    bands.setMatrixAt(k, _m);
  }
  bands.instanceMatrix.needsUpdate = true;
}

// Tension: the length the cable needs against the length it has. 100% pulls the plug.
let needed = 0;
function cableState() {
  return { out: cableOut, taut: needed, tension: Math.min(1.2, needed / rope.len) };
}

// --- Bot -------------------------------------------------------------------------------------
const bot = { pos: START.clone(), heading: 0, weight: 0, speed: 0, vel: new THREE.Vector3() };
const botRoot = new THREE.Group();
scene.add(botRoot);
let mixer = null, walk = null, botPlug = null, wallPlug = null, model = null, bodyBone = null, meshes = [];
let plugInBone = null;
const wallEnd = new THREE.Vector3(), wallDir = new THREE.Vector3(1, 0, 0);
const botEnd = new THREE.Vector3(), botDir = new THREE.Vector3();
const wrapAngle = (a) => Math.atan2(Math.sin(a), Math.cos(a));

function pushOutOfWalls(p, r) {
  const solids = solidWalls().concat(pillars);
  for (const w of solids) {
    const cx = THREE.MathUtils.clamp(p.x, w.minX, w.maxX), cz = THREE.MathUtils.clamp(p.z, w.minZ, w.maxZ);
    const dx = p.x - cx, dz = p.z - cz, d2 = dx * dx + dz * dz;
    if (d2 >= r * r) continue;
    if (d2 > 1e-8) {
      const d = Math.sqrt(d2);
      p.x = cx + (dx / d) * r; p.z = cz + (dz / d) * r;
    } else {
      const opts = [[w.minX - r - p.x, 0], [w.maxX + r - p.x, 0], [0, w.minZ - r - p.z], [0, w.maxZ + r - p.z]];
      opts.sort((a, b) => Math.hypot(...a) - Math.hypot(...b));
      p.x += opts[0][0]; p.z += opts[0][1];
    }
  }
  // The plug sticks out behind him; keep it 10 cm off the walls too, by moving him.
  const bx = p.x - Math.cos(bot.heading) * 0.45, bz = p.z + Math.sin(bot.heading) * 0.45;
  for (const w of solids) {
    const cx = THREE.MathUtils.clamp(bx, w.minX, w.maxX), cz = THREE.MathUtils.clamp(bz, w.minZ, w.maxZ);
    const dx = bx - cx, dz = bz - cz, d = Math.hypot(dx, dz), need = 0.1;
    if (d >= need) continue;
    if (d > 1e-6) { p.x += (dx / d) * (need - d); p.z += (dz / d) * (need - d); }
    else { p.x += Math.cos(bot.heading) * need; p.z -= Math.sin(bot.heading) * need; }
  }
  p.x = THREE.MathUtils.clamp(p.x, -ROOM.x + 0.9, ROOM.x - r);
  p.z = THREE.MathUtils.clamp(p.z, -ROOM.z + r, ROOM.z - r);
}

// Manual driving.
let manual = true;
const keys = new Set();
const KEYMAP = { KeyW: "fwd", ArrowUp: "fwd", KeyS: "back", ArrowDown: "back", KeyA: "left", ArrowLeft: "left", KeyD: "right", ArrowRight: "right",
};
addEventListener("keydown", (e) => {
  if (e.target.closest?.("input, textarea") && !(e.code === "Escape" && e.target.type === "range")) return;
  if (e.ctrlKey || e.metaKey || e.altKey) return; // leave browser shortcuts (Ctrl+R reloads) alone
  if ($("loading")) return; // nothing to drive or open until the test floor has loaded
  if (e.code === "Escape") { e.preventDefault(); if (!$("editor").hidden) closeEditor(); else toggleMenu(); return; }
  if (!$("editor").hidden) return;
  // In the menu, 1-5 start that difficulty, as if its button were clicked.
  const digit = /^(Digit|Numpad)([1-5])$/.exec(e.code);
  if (digit && !$("menu").hidden && $("soundView").inert) {
    e.preventDefault();
    $("tests").querySelector(`.test[data-k="${digit[2] - 1}"]`)?.click();
    return;
  }
  const k = KEYMAP[e.code];
  if (!k || !$("menu").hidden) return;
  e.preventDefault();
  keys.add(k);
});
addEventListener("keyup", (e) => { const k = KEYMAP[e.code]; if (k) keys.delete(k); });
addEventListener("blur", () => keys.clear());

// Autopilot: plan a route around the walls on a fine grid, then follow it.
const NAV = 0.25, NX = Math.round(W / NAV), NZ = Math.round(D / NAV);
let route = [], routeIdx = 0, lastPlan = 0;
function planRoute(from, boxes = walls.filter((w) => w.target > 0), holes = pits) {
  const blocked = new Uint8Array(NX * NZ);
  const inflate = BOT_R + 0.18;
  const sw = boxes.concat(pillars);
  for (let iz = 0; iz < NZ; iz++) {
    for (let ix = 0; ix < NX; ix++) {
      const x = -ROOM.x + (ix + 0.5) * NAV, z = -ROOM.z + (iz + 0.5) * NAV;
      let b = x < -ROOM.x + 0.9 || x > ROOM.x - inflate || z < -ROOM.z + inflate || z > ROOM.z - inflate;
      for (const w of sw) {
        if (b) break;
        const dx = Math.max(w.minX - x, 0, x - w.maxX), dz = Math.max(w.minZ - z, 0, z - w.maxZ);
        if (dx * dx + dz * dz < inflate * inflate) b = true;
      }
      if (!b && holes.some((p) => p.rects.some((r) => inBox(r, x, z, inflate)))) b = true;
      blocked[iz * NX + ix] = b ? 1 : 0;
    }
  }
  const idx = (x, z) => Math.min(NZ - 1, Math.max(0, Math.floor((z + ROOM.z) / NAV))) * NX + Math.min(NX - 1, Math.max(0, Math.floor((x + ROOM.x) / NAV)));
  const start = idx(from.x, from.z);
  const goalX = GOAL_X + 0.8;
  const h = (i) => Math.max(0, goalX - (-ROOM.x + ((i % NX) + 0.5) * NAV));
  const g = new Float32Array(NX * NZ).fill(Infinity), prev = new Int32Array(NX * NZ).fill(-1);
  const done = new Uint8Array(NX * NZ);
  // Binary heap of [f, node].
  const heap = [];
  const push = (f, n) => {
    heap.push([f, n]);
    for (let i = heap.length - 1; i > 0;) {
      const p = (i - 1) >> 1;
      if (heap[p][0] <= heap[i][0]) break;
      [heap[p], heap[i]] = [heap[i], heap[p]]; i = p;
    }
  };
  const pop = () => {
    const top = heap[0], last = heap.pop();
    if (heap.length) {
      heap[0] = last;
      for (let i = 0; ;) {
        const l = 2 * i + 1, r = l + 1;
        let m = i;
        if (l < heap.length && heap[l][0] < heap[m][0]) m = l;
        if (r < heap.length && heap[r][0] < heap[m][0]) m = r;
        if (m === i) break;
        [heap[m], heap[i]] = [heap[i], heap[m]]; i = m;
      }
    }
    return top;
  };
  push(h(start), start);
  g[start] = 0;
  let end = -1;
  while (heap.length) {
    const [, cur] = pop();
    if (done[cur]) continue;
    done[cur] = 1;
    const cx = cur % NX, cz = (cur / NX) | 0;
    if (-ROOM.x + (cx + 0.5) * NAV >= goalX) { end = cur; break; }
    for (let dz = -1; dz <= 1; dz++) for (let dx = -1; dx <= 1; dx++) {
      if (!dx && !dz) continue;
      const nx = cx + dx, nz = cz + dz;
      if (nx < 0 || nz < 0 || nx >= NX || nz >= NZ) continue;
      const ni = nz * NX + nx;
      if (blocked[ni] || (dx && dz && (blocked[cz * NX + nx] || blocked[nz * NX + cx]))) continue;
      const ng = g[cur] + (dx && dz ? Math.SQRT2 : 1) * NAV;
      if (ng < g[ni]) { g[ni] = ng; prev[ni] = cur; push(ng + h(ni), ni); }
    }
  }
  if (end < 0) return { points: [], length: Infinity };
  const cells = [];
  for (let c = end; c >= 0; c = prev[c]) cells.push(c);
  cells.reverse();
  const pts = cells.map((c) => new THREE.Vector2(-ROOM.x + ((c % NX) + 0.5) * NAV, -ROOM.z + (((c / NX) | 0) + 0.5) * NAV));
  pts[0].set(from.x, from.z);
  const clear = (a, b) => {
    const steps = Math.ceil(a.distanceTo(b) / (NAV * 0.5));
    for (let s = 1; s < steps; s++) {
      const x = a.x + (b.x - a.x) * (s / steps), z = a.y + (b.y - a.y) * (s / steps);
      if (blocked[idx(x, z)]) return false;
    }
    return true;
  };
  const smooth = [pts[0]];
  for (let i = 0; i < pts.length - 1;) {
    let j = pts.length - 1;
    while (j > i + 1 && !clear(pts[i], pts[j])) j--;
    smooth.push(pts[j]);
    i = j;
  }
  let length = 0;
  for (let i = 1; i < smooth.length; i++) length += smooth[i].distanceTo(smooth[i - 1]);
  return { points: smooth, length };
}

function steer(dt) {
  let turn = 0, move = 0;
  if (manual) {
    turn = (keys.has("left") ? 1 : 0) - (keys.has("right") ? 1 : 0);
    move = (keys.has("fwd") ? 1 : 0) - (keys.has("back") ? 1 : 0);
    bot.heading += turn * TURN_RATE * dt;
  } else {
    if (routeIdx >= route.length && game.time - lastPlan > 1) {
      lastPlan = game.time;
      const r = planRoute(bot.pos); route = r.points; routeIdx = 1;
    }
    if (routeIdx < route.length) {
      const t = route[routeIdx];
      const dx = t.x - bot.pos.x, dz = t.y - bot.pos.z;
      if (Math.hypot(dx, dz) < 0.35) routeIdx++;
      const diff = wrapAngle(Math.atan2(-dz, dx) - bot.heading);
      const step = THREE.MathUtils.clamp(diff, -TURN_RATE * dt, TURN_RATE * dt);
      bot.heading += step;
      turn = Math.sign(step);
      move = Math.max(0, Math.cos(diff)) ** 3;
    }
  }
  const fwd = new THREE.Vector3(Math.cos(bot.heading), 0, -Math.sin(bot.heading));
  const goal = move || turn ? 1 : 0;
  bot.weight += (goal - bot.weight) * Math.min(1, dt * 5);
  const speed = move ? WALK_SPEED * (move > 0 ? Math.abs(move) : 0.6) * Math.sign(move) : 0;
  bot.pos.addScaledVector(fwd, speed * bot.weight * dt);
  bot.vel.copy(fwd).multiplyScalar(speed * bot.weight);
  pushOutOfWalls(bot.pos, BOT_R);
  if (walk) {
    walk.setEffectiveWeight(bot.weight);
    walk.timeScale = (move < 0 ? -0.6 : move ? Math.max(0.35, move) : 0.6) * PACE;
  }
  if (move > 0.05 && game.state === "playing" && game.started === null) game.started = game.time;
}

function updateBot(dt) {
  if (unplugged || fall || game.state !== "playing") {
    bot.weight += (0 - bot.weight) * Math.min(1, dt * 6);
    if (walk) walk.setEffectiveWeight(bot.weight);
  } else {
    steer(dt);
    const hole = pitAt(bot.pos.x, bot.pos.z);
    if (hole) startFall(hole);
  }
  botRoot.position.copy(bot.pos);
  botRoot.rotation.y = bot.heading;
}

function updatePins() {
  botRoot.updateMatrixWorld(true);
  if (unplugged) return;
  botPlug.localToWorld(botEnd.set(PLUG_LEN, 0, 0));
  botDir.set(1, 0, 0).transformDirection(botPlug.matrixWorld);
}

// --- Unplugging and powering down -----------------------------------------------------------
let unplugged = false;
let power = 1;
const _v = new THREE.Vector3(), _q2 = new THREE.Quaternion(), _q3 = new THREE.Quaternion();
const sparkCount = 40;
const sparkPos = new Float32Array(sparkCount * 3), sparkVel = new Float32Array(sparkCount * 3);
const sparkGeo = new THREE.BufferGeometry();
sparkGeo.setAttribute("position", new THREE.BufferAttribute(sparkPos, 3));
const sparkMat = new THREE.PointsMaterial({ color: 0xffb02e, size: 0.035, transparent: true, opacity: 0, depthWrite: false });
const sparks = new THREE.Points(sparkGeo, sparkMat);
sparks.frustumCulled = false;
scene.add(sparks);
let sparkLife = 0;
function burst(at, dir) {
  for (let i = 0; i < sparkCount; i++) {
    sparkPos.set([at.x, at.y, at.z], i * 3);
    const v = new THREE.Vector3(dir.x + (Math.random() - 0.5) * 1.6, 0.6 + Math.random() * 1.4, dir.z + (Math.random() - 0.5) * 1.6)
      .normalize().multiplyScalar(1 + Math.random() * 2);
    sparkVel.set([v.x, v.y, v.z], i * 3);
  }
  sparkLife = 0.7;
}
function updateSparks(dt) {
  if (sparkLife <= 0) return;
  sparkLife -= dt;
  for (let i = 0; i < sparkCount; i++) {
    const k = i * 3;
    sparkVel[k + 1] -= 9.8 * dt;
    for (let a = 0; a < 3; a++) sparkPos[k + a] += sparkVel[k + a] * dt;
    if (sparkPos[k + 1] < 0.01) { sparkPos[k + 1] = 0.01; sparkVel[k + 1] *= -0.3; }
  }
  sparkGeo.attributes.position.needsUpdate = true;
  sparkMat.opacity = Math.max(0, sparkLife / 0.7);
}
function unplug() {
  unplugged = true;
  keys.clear();
  ropeFree = true;
  fallT = 0;
  ropeTarget = polyLen(rp);
  botPlug.removeFromParent();
  scene.add(botPlug);
  botPlug.scale.set(1, 1, 1);
  burst(botEnd.clone().addScaledVector(botDir, -PLUG_LEN), botDir);
  sfx("unplug"); sfx("power_down", { delay: 0.2 });
  finish(false);
}
function replug() {
  botPlug.removeFromParent();
  bodyBone.add(botPlug);
  plugInBone.decompose(botPlug.position, botPlug.quaternion, botPlug.scale);
  unplugged = false;
}

// Tip the body forward about the hip line when powered down, keeping the feet planted.
// The mixer skips writing bones whose value hasn't changed, so its pose is restored before
// each update; otherwise the tilt would compound every frame.
const thighs = [], legs = []; // legs: [thigh, shin, foot] per side
const pose = { saved: false, bodyPos: new THREE.Vector3(), bodyQ: new THREE.Quaternion(), legQ: [] };
function restorePose() {
  if (!pose.saved) return;
  bodyBone.position.copy(pose.bodyPos); bodyBone.quaternion.copy(pose.bodyQ);
  legs.flat().forEach((b, i) => b.quaternion.copy(pose.legQ[i]));
}
function savePose() {
  pose.bodyPos.copy(bodyBone.position); pose.bodyQ.copy(bodyBone.quaternion);
  pose.legQ = legs.flat().map((b) => b.quaternion.clone());
  pose.saved = true;
}
// Turn a bone by angle about a world axis, keeping its parent where it is.
function turnBone(bone, axis, angle) {
  const world = bone.getWorldQuaternion(new THREE.Quaternion());
  const turned = new THREE.Quaternion().setFromAxisAngle(axis, angle).multiply(world);
  bone.quaternion.copy(bone.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(turned));
  bone.updateMatrixWorld(true);
}
// Joyful stomping after a pass: knees up in turn and a happy wiggle, with the other foot always
// planted on the floor. t is seconds since he started; it eases in over the first half second.
let footRestY = 0; // height of his feet above the floor when standing
function applyStomp(t) {
  if (t < 0) return;
  const ease = Math.min(1, t / 0.5);
  const phase = t * 1.3 * Math.PI * 2; // 1.3 stomps a second: left knee up, then right
  model.updateMatrixWorld(true);
  const side = new THREE.Vector3(0, 0, 1).applyQuaternion(botRoot.quaternion);   // knee-up axis
  const ahead = new THREE.Vector3(1, 0, 0).applyQuaternion(botRoot.quaternion);  // wiggle axis
  const body = bodyBone;
  const legWorld = legs.map(([thigh]) => thigh.getWorldQuaternion(new THREE.Quaternion()));
  // Rock over onto the planted leg as the other knee comes up: one full rock per left-right pair.
  turnBone(body, ahead, 0.12 * Math.sin(phase) * ease);
  // Keep the legs hanging straight down under the wiggling body before lifting them.
  const bodyInv = body.getWorldQuaternion(new THREE.Quaternion()).invert();
  legs.forEach(([thigh], i) => { thigh.quaternion.copy(bodyInv.clone().multiply(legWorld[i])); thigh.updateMatrixWorld(true); });
  // The two lifts are never above zero together, so one foot is always down.
  const lifts = legs.map((_, i) => 0.85 * Math.max(0, Math.sin(phase + i * Math.PI)) ** 1.5 * ease);
  legs.forEach(([thigh, shin, foot], i) => {
    turnBone(thigh, side, lifts[i]);
    turnBone(shin, side, -1.8 * lifts[i]);
    turnBone(foot, side, 0.8 * lifts[i]);
  });
  // Move the body so the lower foot (the planted one) sits exactly on the floor.
  const low = Math.min(...legs.map(([, , foot]) => foot.getWorldPosition(new THREE.Vector3()).y));
  const dy = footRestY - (low - botRoot.position.y);
  body.position.copy(body.parent.worldToLocal(body.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, dy, 0))));
  body.updateMatrixWorld(true);
}
function applySlump(s) {
  if (s <= 0) return;
  const e = s * s * (3 - 2 * s);
  const body = bodyBone;
  model.updateMatrixWorld(true);
  const thighWorld = thighs.map((t) => t.getWorldQuaternion(new THREE.Quaternion()));
  const hip = thighs[0].getWorldPosition(new THREE.Vector3()).add(thighs[1].getWorldPosition(_v)).multiplyScalar(0.5);
  const axis = new THREE.Vector3(0, 0, 1).applyQuaternion(botRoot.quaternion);
  const tilt = _q2.setFromAxisAngle(axis, -SLUMP * e);
  const pos = body.getWorldPosition(new THREE.Vector3()).sub(hip).applyQuaternion(tilt).add(hip);
  const rot = tilt.clone().multiply(body.getWorldQuaternion(new THREE.Quaternion()));
  body.position.copy(body.parent.worldToLocal(pos));
  body.quaternion.copy(body.parent.getWorldQuaternion(_q3).invert().multiply(rot));
  body.updateMatrixWorld(true);
  const bodyInv = body.getWorldQuaternion(new THREE.Quaternion()).invert();
  thighs.forEach((t, i) => t.quaternion.copy(bodyInv.clone().multiply(thighWorld[i])));
}
function setPowerLook(p) {
  const c = 0.45 + 0.55 * p;
  meshes.forEach((m) => {
    if (m.userData.glow) return;
    const t = m.userData.tint;
    m.material.color.setRGB(c * (t ? t.r : 1), c * (t ? t.g : 1), c * (t ? t.b : 1));
    const want = p < 0.55 ? m.userData.offMap : m.userData.onMap;
    if (want && m.material.map !== want) m.material.map = want;
  });
}

// --- Falling into a pit ---------------------------------------------------------------------------
// He drops in along a gravity curve, turning over on the way down into one of FALL_POSES picked at random,
// thuds onto the bottom and settles. The plug pops out as he tips in, which ends the turn.
// A pose: pitch (tipping back, +, or forward, -), roll (onto his left side, +), yaw, and per leg [swing
// (knee forward/up), knee (bend, negative), ankle, splay (outward)], left leg first.
const FALL_POSES = [
  { name: "on his back", pitch: 1.35, roll: 0.15, yaw: 0.3, legs: [[1.1, -0.5, 0.4, 0.2], [0.8, -0.9, 0.3, 0.35]] },
  { name: "face down", pitch: -1.3, roll: -0.1, yaw: -0.2, legs: [[-0.6, -0.4, -0.3, 0.15], [-0.3, -1.1, -0.2, 0.3]] },
  { name: "on his left side", pitch: 0.2, roll: 1.4, yaw: 0.6, legs: [[0.5, -1.2, 0.4, 0.1], [1.0, -0.4, 0.2, -0.2]] },
  { name: "on his right side", pitch: -0.15, roll: -1.4, yaw: -0.5, legs: [[0.9, -0.3, 0.3, -0.2], [0.3, -1.4, 0.5, 0.1]] },
  { name: "sitting", pitch: 0.55, roll: 0.05, yaw: 0, legs: [[1.4, -0.15, 0.6, 0.35], [1.3, -0.3, 0.5, 0.4]] },
  { name: "on his head", pitch: 2.55, roll: 0.25, yaw: 0.8, legs: [[0.4, -0.2, 0.2, 0.7], [-0.3, -0.6, 0.1, 0.6]] },
  { name: "slumped on his knees", pitch: -0.55, roll: 0.1, yaw: -0.4, legs: [[1.0, -2.1, 0.7, 0.15], [0.9, -2.0, 0.6, 0.2]] },
  { name: "doing the splits", pitch: 0.3, roll: 0.25, yaw: 1.2, legs: [[1.3, -0.1, 0.4, 0.1], [-0.8, -0.2, -0.3, 0.1]] },
  { name: "tangled up", pitch: 0.95, roll: 0.6, yaw: -0.9, legs: [[0.7, -1.6, 0.5, -0.45], [1.2, -0.7, 0.3, -0.5]] },
  { name: "flat like a frog", pitch: -0.35, roll: -0.05, yaw: 0.5, legs: [[0.6, -1.5, 0.6, 0.75], [0.6, -1.5, 0.6, 0.75]] },
];
const FALL_TIME = 0.5, SETTLE_TIME = 0.22, BODY_UP = 0.58; // BODY_UP: his body's centre above his feet
let fall = null; // { pit, pose, from, to, q0, q1, t, done, focus }
let footBox = null; // a foot's block in its bone's frame: { center, quat, half }
function measureFoot() {
  model.updateMatrixWorld(true);
  const foot = legs[0][2], rootQ = botRoot.getWorldQuaternion(new THREE.Quaternion());
  footBox = {
    center: foot.worldToLocal(botRoot.localToWorld(new THREE.Vector3(0.0185, 0.076, -0.1035))),
    quat: foot.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(rootQ),
    half: new THREE.Vector3(0.136, 0.074, 0.065),
  };
}
// Bend the legs into the pose, e of the way from standing; the body's tumble is the root's rotation.
function poseLegs(pose, e) {
  const side = new THREE.Vector3(0, 0, 1).applyQuaternion(botRoot.quaternion);
  const ahead = new THREE.Vector3(1, 0, 0).applyQuaternion(botRoot.quaternion);
  legs.forEach(([thigh, shin, foot], i) => {
    const [swing, knee, ankle, splay] = pose.legs[i];
    turnBone(thigh, ahead, (i === 0 ? 1 : -1) * splay * e);
    turnBone(thigh, side, swing * e);
    turnBone(shin, side, knee * e);
    turnBone(foot, side, ankle * e);
  });
}
const _corner = new THREE.Vector3(), _boxQ = new THREE.Matrix4();
// The lowest point of him as posed now: the bottom of his round body, or a corner of a foot.
function lowestPoint(center) {
  model.updateMatrixWorld(true);
  let low = center.y - 0.27;
  for (const [, , foot] of legs) {
    _boxQ.compose(footBox.center, footBox.quat, _one).premultiply(foot.matrixWorld);
    for (let k = 0; k < 8; k++) {
      _corner.set(k & 1 ? footBox.half.x : -footBox.half.x, k & 2 ? footBox.half.y : -footBox.half.y, k & 4 ? footBox.half.z : -footBox.half.z).applyMatrix4(_boxQ);
      low = Math.min(low, _corner.y);
    }
  }
  return low;
}
// Put him with his body's centre at c and turned by q, the legs e of the way into the pose.
function placeFall(c, q, e) {
  restorePose();
  botRoot.quaternion.copy(q);
  botRoot.position.copy(c).sub(_v.set(0, BODY_UP, 0).applyQuaternion(q));
  botRoot.updateMatrixWorld(true);
  poseLegs(fall.pose, e);
}
function startFall(pit) {
  game.fell = true;
  keys.clear();
  const pose = FALL_POSES[Math.floor(Math.random() * FALL_POSES.length)];
  const heading = new THREE.Quaternion().setFromAxisAngle(_up, bot.heading);
  const q1 = heading.clone().multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(pose.roll, pose.yaw, pose.pitch, "YXZ")));
  // He lands a little way into the pit along his way in, kept clear of the shaft's walls.
  const m = 0.5, fwd = bot.vel.lengthSq() > 1e-4 ? bot.vel.clone().setY(0).normalize() : new THREE.Vector3(Math.cos(bot.heading), 0, -Math.sin(bot.heading));
  const ax = bot.pos.x + fwd.x * 0.55, az = bot.pos.z + fwd.z * 0.55;
  const sq = pit.cells.reduce((a, b) => (Math.hypot((b.minX + b.maxX) / 2 - ax, (b.minZ + b.maxZ) / 2 - az) < Math.hypot((a.minX + a.maxX) / 2 - ax, (a.minZ + a.maxZ) / 2 - az) ? b : a));
  const lx = THREE.MathUtils.clamp(ax, sq.minX + m, sq.maxX - m), lz = THREE.MathUtils.clamp(az, sq.minZ + m, sq.maxZ - m);
  fall = { pit, pose, q0: heading, q1, t: 0, done: false, from: new THREE.Vector3(bot.pos.x, BODY_UP, bot.pos.z), to: new THREE.Vector3(lx, 0, lz), focus: new THREE.Vector3() };
  // Rest height: pose him fully at the bottom, then lift him so his lowest point touches the floor.
  placeFall(fall.to.setY(0), q1, 1);
  fall.to.y = -PIT_DEPTH - lowestPoint(fall.to);
  placeFall(fall.from, fall.q0, 0);
  fall.focus.copy(fall.from);
  sfx("pit_fall");
  unplug();
}
const _fallQ = new THREE.Quaternion(), _fallC = new THREE.Vector3();
function stepFall(dt) {
  if (fall.done) { placeFall(fall.focus, fall.q1, 1); return; }
  fall.t += dt;
  const u = Math.min(1, fall.t / FALL_TIME);
  // Across steadily, down under gravity; he turns over and his legs go as he drops.
  _fallC.lerpVectors(fall.from, fall.to, u);
  _fallC.y = fall.from.y + (fall.to.y - fall.from.y) * u * u;
  const turn = THREE.MathUtils.smootherstep(u, 0, 1);
  _fallQ.slerpQuaternions(fall.q0, fall.q1, turn);
  let e = turn;
  if (fall.t > FALL_TIME) {
    // The thud: he squashes down a couple of centimetres and the limbs fling a little past the pose.
    const s = Math.min(1, (fall.t - FALL_TIME) / SETTLE_TIME), k = Math.sin(Math.PI * s) * (1 - s);
    _fallC.y -= 0.035 * Math.sin(Math.PI * s);
    e = 1 + 0.18 * k;
    if (s >= 1) { fall.done = true; e = 1; _fallC.copy(fall.to); }
  }
  placeFall(_fallC, _fallQ, e);
  fall.focus.copy(_fallC);
}
function endFall() {
  fall = null;
  game.fell = false;
  botRoot.quaternion.identity();
}

// --- Load and assemble ----------------------------------------------------------------------
const [botGltf, plugGltf, outletGltf, signGltf] = await Promise.all(["bot", "plug", "outlet", "sign"].map((n) => loader.loadAsync(`assets/${n}.glb`)));
model = botGltf.scene;
model.position.y = 0.5;
botRoot.add(model);
model.traverse((o) => { if (o.isMesh) meshes.push(o); });
const maxAniso = renderer.capabilities.getMaxAnisotropy();
meshes.forEach((o) => {
  const { name, map } = o.material;
  if (map) map.anisotropy = maxAniso;
  if (name === "bot_glow") { // the socket's pin holes: always lit, never dimmed with the rest of him
    o.material = new THREE.MeshBasicMaterial({ color: 0xff7a14 });
    o.userData.glow = true;
    return;
  }
  if (name.includes("decal")) { // full-resolution logos laid over the paint, without an outline
    o.material = new THREE.MeshBasicMaterial({ map, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
    o.userData.decal = true;
    o.userData.tint = new THREE.Color(0.81, 0.79, 0.85); // the chevron's yellow under the baked shading
    return;
  }
  o.material = new THREE.MeshBasicMaterial({ map: map || null });
  o.castShadow = true;
  const g = o.geometry;
  g.setAttribute("outlineScale", g.getAttribute("_outline") || new THREE.BufferAttribute(new Float32Array(g.attributes.position.count).fill(1), 1));
  const ol = o.isSkinnedMesh ? new THREE.SkinnedMesh(g, outlineMat) : new THREE.Mesh(g, outlineMat);
  if (o.isSkinnedMesh) ol.bind(o.skeleton, o.bindMatrix);
  ol.frustumCulled = false;
  o.add(ol);
});
const offMap = await new THREE.TextureLoader().loadAsync("assets/bot_off.jpg");
meshes.forEach((o) => {
  const on = o.material.map;
  if (!on || o.userData.decal) return;
  offMap.flipY = on.flipY; offMap.colorSpace = on.colorSpace;
  offMap.wrapS = on.wrapS; offMap.wrapT = on.wrapT; offMap.anisotropy = on.anisotropy;
  o.userData.onMap = on; o.userData.offMap = offMap;
});
offMap.needsUpdate = true;
mixer = new THREE.AnimationMixer(model);
walk = mixer.clipAction(botGltf.animations[0]);
walk.play();
walk.setEffectiveWeight(0);

const plugTemplate = plugGltf.scene;
toonify(plugTemplate);
botRoot.position.copy(bot.pos);
botRoot.updateMatrixWorld(true);
bodyBone = model.getObjectByName("body");
botPlug = plugTemplate.clone();
{
  const local = new THREE.Matrix4().compose(BOT_SOCKET, new THREE.Quaternion().setFromAxisAngle(_up, Math.PI), _one);
  const world = new THREE.Matrix4().multiplyMatrices(model.matrixWorld, local);
  plugInBone = new THREE.Matrix4().copy(bodyBone.matrixWorld).invert().multiply(world);
  plugInBone.decompose(botPlug.position, botPlug.quaternion, botPlug.scale);
  bodyBone.add(botPlug);
}
const boneOf = (name) => model.getObjectByName(name.replace(".", "")) || model.getObjectByName(name);
for (const side of ["L", "R"]) {
  thighs.push(boneOf(`thigh.${side}`));
  legs.push([boneOf(`thigh.${side}`), boneOf(`shin.${side}`), boneOf(`foot.${side}`)]);
}
model.updateMatrixWorld(true);
footRestY = legs[0][2].getWorldPosition(new THREE.Vector3()).y - botRoot.position.y;
measureFoot();
// A fall carries him well below his resting bounds, so never cull him by them.
meshes.forEach((o) => { o.frustumCulled = false; });
// The sign and the outlet: lettered faces and lights glow (unlit); the rest takes the toon shading.
function addPainted(root, pos) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    const m = o.material, name = m.name || "";
    o.material = /face|light/.test(name)
      ? new THREE.MeshBasicMaterial({ map: m.map, color: 0xffffff })
      : toon({ map: m.map || null, color: m.map ? 0xffffff : m.color });
    o.add(new THREE.LineSegments(new THREE.EdgesGeometry(o.geometry, 30), inkLine));
  });
  root.position.copy(pos);
  scene.add(root);
}
addPainted(signGltf.scene, SIGN_AT);
addPainted(outletGltf.scene, SOCKET_POS);
outletGltf.scene.rotation.y = Math.PI / 2; // modelled facing +z; the socket wall faces +x
wallPlug = plugTemplate.clone();
wallPlug.position.set(-ROOM.x + 0.062, SOCKET_POS.y, 0);
scene.add(wallPlug);
wallPlug.updateMatrixWorld(true);
wallPlug.localToWorld(wallEnd.set(PLUG_LEN, 0, 0));

function layCable() {
  updatePins();
  setWallList(solidWalls());
  const f = socketFoot(), [a, b] = tailPins();
  taut = new Taut(f, new THREE.Vector2(bot.pos.x, bot.pos.z), corners);
  ropeFree = false; fallT = 0; winding = 0; ropeTarget = 0;
  const end = new THREE.Vector2(a.x, a.z), steps = Math.max(3, Math.ceil(f.distanceTo(end) / SEG));
  rp = [];
  for (let k = 0; k <= steps; k++) rp.push(f.clone().lerp(end, k / steps));
  rp.push(new THREE.Vector2(b.x, b.z));
}

// --- Game state -------------------------------------------------------------------------------
const game = { test: null, level: 0, run: 0, state: "menu", time: 0, started: null, peak: 0, lifted: 0, over: 0, autopilot: false, cheer: 0, fell: false, fromEditor: false };
// Best times by "difficulty.level". Times saved before levels existed count as level 1.
let best = {};
try { best = JSON.parse(localStorage.getItem("abp-best") || "{}"); } catch { best = {}; }
for (const key of Object.keys(best)) {
  if (/^\d+$/.test(key)) { best[`${key}.0`] ??= best[key]; delete best[key]; }
}
const bestOf = (k, l) => best[`${k}.${l}`];
// A difficulty starts at its first level not yet passed (the last one once all are passed). That is
// also as far as the next-level button goes.
const firstOpen = (k) => { const i = LEVELS[k].findIndex((_, l) => !bestOf(k, l)); return i < 0 ? LEVEL_COUNT - 1 : i; };
const fmt = (t) => `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, "0")}`;

// withIntro: the camera opens on the sign, then swings round and closes in on the bot before he walks.
function startTest(k, l, withIntro = false) {
  const t = LEVELS[k][l];
  const run = ++game.run;
  camIntro = withIntro ? { t: 0, run } : null;
  applySavedFold(); // a results card may have opened a folded HUD
  game.test = k; game.level = l; game.state = "rising"; game.time = 0; game.started = null; game.peak = 0; game.lifted = 0; game.over = 0;
  game.autopilot = !manual;
  clearTimeout(resultTimer);
  $("menu").hidden = true; $("result").hidden = true;
  document.documentElement.style.setProperty("--accent", t.hex);
  cableMat.color.set(t.hex);
  $("testName").textContent = `${t.level} ${l + 1}/${LEVEL_COUNT}`;
  updateLevelButtons();
  $("pullLim").textContent = `${Math.round(t.spare * 1000) / 10}%`;
  if (fall) endFall();
  if (unplugged) replug();
  buildPits(t.pits);
  power = 1;
  bot.pos.copy(START); bot.heading = 0; bot.weight = 0;
  botRoot.position.copy(bot.pos); botRoot.rotation.y = 0;
  updateCamera(0, true);
  restorePose(); mixer.update(0); savePose();
  keys.clear();
  rope = makeRope(t.len);
  buildCableMeshes();
  buildWalls(t);
  layCable();
  needed = 0;
  route = []; routeIdx = 0;
  sfx("walls_rise");
  updateMusic();
  if (!withIntro) setTimeout(() => { if (game.run === run && game.state === "rising") beginPlay(); }, 1300);
}
function beginPlay() {
  game.state = "playing";
  sfx("power_up");
  if (!manual) { const r = planRoute(bot.pos); route = r.points; routeIdx = 1; }
}

function finish(passed) {
  if (game.state !== "playing") return;
  game.state = passed ? "passed" : "failed";
  game.cheer = game.time + 0.4; // he settles for a moment, then stomps for joy
  if (passed) sfx("pass");
  const k = game.test, l = game.level, key = `${k}.${l}`;
  const time = game.started === null ? 0 : game.time - game.started;
  if (passed && !game.autopilot && !game.fromEditor && (!best[key] || time < best[key])) {
    best[key] = time;
    try { localStorage.setItem("abp-best", JSON.stringify(best)); } catch { /* storage unavailable */ }
  }
  // Settle the card's contents now; it only appears after a beat, and is dropped if a new test starts.
  // The HUD above it already shows the level, cable and time, so the card is just the verdict and buttons.
  const acts = [];
  updateLevelButtons(); // a pass can unlock the next level
  const next = nextLevel(k, l);
  if (passed && next && !game.fromEditor) acts.push(`<button class="primary" data-act="next">Next · ${TESTS[next[0]].level} ${next[1] + 1}/${LEVEL_COUNT}</button>`);
  // Same order as the control bar: Menu, then Retry.
  acts.push(game.fromEditor ? `<button data-act="editor">Editor</button>` : `<button data-act="menu">Menu</button>`, `<button ${passed ? "" : 'class="primary"'} data-act="retry">Retry</button>`);
  clearTimeout(resultTimer);
  resultTimer = setTimeout(() => {
    const v = $("verdict");
    v.textContent = passed ? "PASS" : game.fell ? "FELL IN" : "UNPLUGGED";
    v.className = "verdict " + (passed ? "pass" : "fail");
    if (!passed) sfx("fail");
    $("actions").innerHTML = acts.join("");
    // The results are worth seeing: open the HUD if it was folded away. This doesn't change the saved
    // choice, so it folds again on the next level.
    document.querySelector(".hud").classList.remove("folded");
    $("hudToggle").setAttribute("aria-expanded", "true");
    $("hudToggle").title = $("hudToggle").ariaLabel = "Hide panels";
    $("result").hidden = false;
  }, passed ? 600 : 1600);
}
let resultTimer = null;
// The level after this one: the next in this difficulty, then the first of the next difficulty.
function nextLevel(k, l) {
  if (l + 1 < LEVEL_COUNT) return [k, l + 1];
  return k + 1 < TESTS.length ? [k + 1, 0] : null;
}
$("actions").addEventListener("click", (e) => {
  const act = e.target.closest("button")?.dataset.act;
  if (act === "next") { const n = nextLevel(game.test, game.level); if (n) startTest(n[0], n[1], true); }
  if (act === "retry") startTest(game.test, game.level);
  if (act === "menu") showMenu();
  if (act === "editor") openEditor();
});

function renderMenu() {
  $("tests").innerHTML = TESTS.map((t, k) => {
    // Levels passed in this difficulty, and the total of their best times.
    const times = LEVELS[k].map((_, l) => bestOf(k, l)).filter((v) => v);
    const total = times.reduce((a, v) => a + v, 0);
    const coil = `<svg class="coil" viewBox="0 0 120 14" aria-hidden="true">
      <path d="M6 7 H 114" fill="none" stroke="#101114" stroke-width="9" stroke-linecap="round"/>
      <path d="M6 7 H 114" fill="none" stroke="${t.hex}" stroke-width="5" stroke-linecap="round"/></svg>`;
    const pips = Array.from({ length: LEVEL_COUNT }, (_, i) => `<span class="${i < times.length ? "on" : ""}"></span>`).join("");
    return `<button class="test" data-k="${k}" style="--c:${t.hex}">
      ${coil}<b>${t.level}</b><small>${LEVEL_COUNT} levels<br>${Math.round(t.spare * 1000) / 10}% slack</small>
      <span class="pips" aria-label="${times.length} of ${LEVEL_COUNT} levels passed">${pips}</span>
      <span class="best ${times.length === LEVEL_COUNT ? "pass" : ""}">Time · ${times.length ? fmt(total) : "—"}</span></button>`;
  }).join("");
}
$("tests").addEventListener("click", (e) => {
  const k = e.target.closest(".test")?.dataset.k;
  if (k !== undefined) { game.fromEditor = false; startTest(Number(k), firstOpen(Number(k)), true); }
});
function showMenu() { renderMenu(); showSound(false); $("result").hidden = true; $("menu").hidden = false; fitMenu(); updateMusic(); }
// Shrink the whole menu to fit the space under the sign rather than letting it scroll.
function fitMenu() {
  const menu = $("menu"), frost = menu.querySelector(".frost");
  if (menu.hidden) return;
  frost.style.zoom = 1;
  const room = menu.clientHeight * (1 - 0.31) - 16 - 32, wide = menu.clientWidth - 32;
  const scale = Math.min(1, room / frost.offsetHeight, wide / Math.max(frost.offsetWidth, frost.scrollWidth));
  frost.style.zoom = Math.max(0.4, scale).toFixed(3);
}
addEventListener("resize", fitMenu);
function toggleMenu() {
  if (!$("menu").hidden && !$("soundView").inert) { showSound(false); return; }
  if (!$("menu").hidden && game.test !== null) { $("menu").hidden = true; updateMusic(); return; }
  showMenu();
}
$("menuBtn").onclick = showMenu;

// Sound settings: a volume and mute per channel, remembered between visits. Audio code reads
// soundGain("bgm") or soundGain("fx") and can listen with onSoundChange(fn).
const SOUND_CHANNELS = { bgm: "BGM", fx: "FX" };
const sound = { bgm: { vol: 0.3, muted: false }, fx: { vol: 0.25, muted: false } };
try { Object.entries(JSON.parse(localStorage.getItem("abp-sound") || "{}")).forEach(([k, v]) => sound[k] && Object.assign(sound[k], v)); } catch { /* storage unavailable */ }
const soundListeners = new Set();
const soundGain = (k) => (sound[k].muted ? 0 : sound[k].vol);
const onSoundChange = (fn) => soundListeners.add(fn);
const SPEAKER = '<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"/>';
const WAVES = '<path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"/>';
const CROSS = '<path d="M16 9.5l5 5M21 9.5l-5 5"/>';
function renderSound() {
  $("mix").innerHTML = Object.entries(SOUND_CHANNELS).map(([k, name]) => {
    const s = sound[k], pct = Math.round(s.vol * 100);
    return `<div class="row ${s.muted ? "muted" : ""}" data-k="${k}">
      <label for="vol-${k}">${name}</label>
      <button class="icon" data-mute aria-pressed="${s.muted}" aria-label="Mute ${name}" title="${s.muted ? "Unmute" : "Mute"} ${name}">
        <svg viewBox="0 0 24 24" aria-hidden="true">${SPEAKER}${s.muted ? CROSS : WAVES}</svg></button>
      <input type="range" id="vol-${k}" min="0" max="100" step="1" value="${pct}">
      <output for="vol-${k}">${pct}%</output></div>`;
  }).join("");
}
function saveSound() {
  try { localStorage.setItem("abp-sound", JSON.stringify(sound)); } catch { /* storage unavailable */ }
  soundListeners.forEach((fn) => fn(sound));
}
$("mix").addEventListener("input", (e) => {
  const row = e.target.closest(".row");
  if (!row || e.target.type !== "range") return;
  const s = sound[row.dataset.k];
  s.vol = e.target.value / 100;
  row.querySelector("output").textContent = `${e.target.value}%`;
  saveSound();
});
$("mix").addEventListener("click", (e) => {
  const row = e.target.closest(".row");
  if (!row || !e.target.closest("[data-mute]")) return;
  sound[row.dataset.k].muted = !sound[row.dataset.k].muted;
  renderSound(); saveSound();
  $("mix").querySelector(`[data-k="${row.dataset.k}"] [data-mute]`).focus();
});
// Erasing progress asks first, in place of the button.
const ERASE_INFO = "Best times and unlocked levels in every difficulty.";
function setErase(mode) {
  $("erase").className = `erase ${mode}`;
  $("eraseMsg").textContent = mode === "ask" ? "Erase all progress? This can't be undone." : mode === "done" ? "Progress erased." : ERASE_INFO;
  $("eraseBtn").hidden = mode !== "";
  $("eraseNo").hidden = $("eraseYes").hidden = mode !== "ask";
}
$("eraseBtn").onclick = () => { setErase("ask"); $("eraseNo").focus(); };
$("eraseNo").onclick = () => { setErase(""); $("eraseBtn").focus(); };
$("eraseYes").onclick = () => {
  for (const key of Object.keys(best)) delete best[key];
  try { localStorage.removeItem("abp-best"); } catch { /* storage unavailable */ }
  renderMenu(); updateLevelButtons();
  setErase("done"); $("soundBack").focus();
};
function showSound(on) {
  if (on) { renderSound(); setErase(""); }
  $("mainView").inert = on; $("soundView").inert = !on;
  $("settingsBtn").setAttribute("aria-expanded", String(on));
  $("settingsBtn").title = $("settingsBtn").ariaLabel = on ? "Back to levels" : "Settings";
  if (on) $("soundView").querySelector("input")?.focus();
}
$("settingsBtn").onclick = () => showSound($("soundView").inert);
$("soundBack").onclick = () => { showSound(false); $("settingsBtn").focus(); };

// --- Map editor ------------------------------------------------------------------------------------
// The real maze, seen straight down through an orthographic camera, with an SVG laid over it in world
// metres (x across, z down the screen). Clicking between two squares adds or removes a wall, on a square
// adds or removes a pit, and on the right-hand edge moves the exit there; walls rise and sink as in play.
// Edits change the level in play straight away (so Play test uses them) and are kept until the page
// reloads. Export and import move one level through a file; on the local dev server, Save to game writes
// every level back to levels.json.
const ED_VIEW = { x0: -ROOM.x, x1: ROOM.x, z0: -ROOM.z, z1: ROOM.z };
const edCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 30);
edCam.up.set(0, 0, -1);
const ed = { k: 0, l: 0, canSave: false };
const edBase = () => levelData.difficulties[ed.k].levels[ed.l];
const edLevel = () => LEVELS[ed.k][ed.l];
const edDirty = (k, l) => LEVELS[k][l].map.join("\n") !== levelData.difficulties[k].levels[l].join("\n");
const anyDirty = () => LEVELS.some((ls, k) => ls.some((_, l) => edDirty(k, l)));
function edSetMap(map) {
  LEVELS[ed.k][ed.l] = measureLevel(makeLevel(ed.k, map));
  edShow(false);
}
// Lay the level out on the test floor: walls rise or sink to match, the pits open, the bot waits at the start.
function edShow(fresh) {
  const t = edLevel();
  if (fresh) {
    if (fall) endFall();
    if (unplugged) replug();
    power = 1;
    bot.pos.copy(START); bot.heading = 0; bot.weight = 0;
    botRoot.position.copy(bot.pos); botRoot.rotation.set(0, 0, 0);
    restorePose(); mixer.update(0); savePose();
    cableMat.color.set(t.hex);
  }
  buildWalls(t);
  buildPits(t.pits);
  rope = makeRope(Number.isFinite(t.len) ? t.len : 30);
  buildCableMeshes();
  layCable();
  edRender();
}
// Fit the camera so the room's floor fills the overlay's drawing exactly, wherever it sits on screen.
function edFrame() {
  const sv = $("edGrid").getBoundingClientRect(), st = stage.getBoundingClientRect();
  const vw = ED_VIEW.x1 - ED_VIEW.x0, vh = ED_VIEW.z1 - ED_VIEW.z0;
  const k = Math.min(sv.width / vw, sv.height / vh);          // pixels per metre, as the SVG's "meet" draws it
  const cx = sv.left - st.left + (vw * k) / 2, cy = sv.top - st.top + sv.height / 2; // drawn at the left, centred down
  const wx = (ED_VIEW.x0 + ED_VIEW.x1) / 2, wz = (ED_VIEW.z0 + ED_VIEW.z1) / 2;
  edCam.left = wx - cx / k; edCam.right = wx + (st.width - cx) / k;
  edCam.top = -(wz - cy / k); edCam.bottom = -(wz + (st.height - cy) / k);
  edCam.position.set(0, ROOM.h - 3.2, 0);
  edCam.lookAt(0, 0, 0);
  edCam.updateProjectionMatrix();
}
// Change one character of the map text.
function edPoke(line, col, ch) {
  const map = edLevel().map.slice();
  map[line] = map[line].slice(0, col) + ch + map[line].slice(col + 1);
  edSetMap(map);
}
function edClick(e) {
  const t = e.target.closest("[data-a]");
  if (!t) return;
  const [a, x, y] = t.dataset.a.split(",").map((s, i) => (i ? Number(s) : s));
  const map = edLevel().map;
  if (a === "v") edPoke(2 * y + 1, 2 * x, map[2 * y + 1][2 * x] === "|" ? " " : "|");
  if (a === "h") edPoke(2 * y, 2 * x + 1, map[2 * y][2 * x + 1] === "-" ? " " : "-");
  if (a === "p") edPoke(2 * y + 1, 2 * x + 1, map[2 * y + 1][2 * x + 1] === "O" ? " " : "O");
  if (a === "x") {
    const next = map.slice();
    for (let r = 0; r < ROWS; r++) { const n = 2 * r + 1; next[n] = next[n].slice(0, 2 * COLS) + (r === y ? " " : "|"); }
    edSetMap(next);
  }
  edMsg("");
}
function edMsg(text, kind = "") {
  $("edMsg").textContent = text;
  $("edMsg").className = "ed-msg" + (kind ? " " + kind : "");
}
function edRender() {
  const t = edLevel(), map = t.map, svg = [];
  const X = (i) => MAZE_X0 + i * CELL, Z = (j) => MAZE_Z0 + j * CELL, f = (v) => v.toFixed(2);
  // The right way through, as the autopilot would walk it.
  const route = planRoute(START, wallBoxes(t), t.pits).points;
  if (route.length) {
    const pts = route.map((p) => `${f(p.x)},${f(p.y)}`).join(" ");
    svg.push(`<polyline points="${pts}" fill="none" stroke="#101114" stroke-width="0.28" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"/>`);
    svg.push(`<polyline points="${pts}" fill="none" stroke="${t.hex}" stroke-width="0.16" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="0.5 0.25"/>`);
  }
  // Click targets: squares (not the entrance square), inside edges, and the right-hand edge for the exit.
  for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) {
    if (c === 0 && r === IN_ROW) continue;
    const tip = map[2 * r + 1][2 * c + 1] === "O" ? "Fill in the pit" : "Open a pit";
    svg.push(`<rect class="cellhit" data-a="p,${c},${r}" x="${f(X(c) + 0.45)}" y="${f(Z(r) + 0.45)}" width="${CELL - 0.9}" height="${CELL - 0.9}" rx="0.15"><title>${tip}</title></rect>`);
  }
  const hit = (a, x1, y1, x2, y2, title) => svg.push(`<line class="hit" data-a="${a}" x1="${f(x1)}" y1="${f(y1)}" x2="${f(x2)}" y2="${f(y2)}" stroke-width="0.5" stroke-linecap="round"><title>${title}</title></line>`);
  for (let i = 1; i < COLS; i++) for (let r = 0; r < ROWS; r++) hit(`v,${i},${r}`, X(i), Z(r) + 0.35, X(i), Z(r + 1) - 0.35, map[2 * r + 1][2 * i] === "|" ? "Remove the wall" : "Add a wall");
  for (let j = 1; j < ROWS; j++) for (let c = 0; c < COLS; c++) hit(`h,${c},${j}`, X(c) + 0.35, Z(j), X(c + 1) - 0.35, Z(j), map[2 * j][2 * c + 1] === "-" ? "Remove the wall" : "Add a wall");
  for (let r = 0; r < ROWS; r++) if (r !== t.exit) hit(`x,${COLS},${r}`, X(COLS), Z(r) + 0.35, X(COLS), Z(r + 1) - 0.35, "Move the exit here");
  const el = $("edGrid");
  el.setAttribute("viewBox", `${ED_VIEW.x0} ${ED_VIEW.z0} ${ED_VIEW.x1 - ED_VIEW.x0} ${ED_VIEW.z1 - ED_VIEW.z0}`);
  el.innerHTML = svg.join("");
  const ok = Number.isFinite(t.len);
  edStats(t);
  $("edInfo").textContent = ok ? `Right way ${t.route.toFixed(1)} m · cable ${t.len} m${edDirty(ed.k, ed.l) ? " · edited" : ""}` : "No way through: open a wall";
  $("edInfo").classList.toggle("bad", !ok);
  $("edPlay").disabled = !ok;
  $("edRevert").disabled = !edDirty(ed.k, ed.l);
  $("edSave").disabled = !anyDirty() || LEVELS.flat().some((x) => !Number.isFinite(x.len));
}
// The maze in numbers: what's built, how the squares connect, and what the cable has to cover.
function edStats(t) {
  const map = t.map, ok = Number.isFinite(t.len);
  let walls = 0, pitCells = 0, open = 0, deadEnds = 0;
  for (let i = 1; i < COLS; i++) for (let r = 0; r < ROWS; r++) if (map[2 * r + 1][2 * i] === "|") walls++; else open++;
  for (let j = 1; j < ROWS; j++) for (let c = 0; c < COLS; c++) if (map[2 * j][2 * c + 1] === "-") walls++; else open++;
  for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) {
    if (map[2 * r + 1][2 * c + 1] === "O") pitCells++;
    const ways = [map[2 * r + 1][2 * c] !== "|", map[2 * r + 1][2 * c + 2] !== "|", map[2 * r][2 * c + 1] !== "-", map[2 * r + 2][2 * c + 1] !== "-"]
      .filter(Boolean).length;
    if (ways === 1) deadEnds++;
  }
  // Each opening beyond what joins every square once adds a loop: a second way round.
  const loops = Math.max(0, open - (COLS * ROWS - 1));
  const rows = [
    ["Walls", walls], ["Openings", open], ["Loops", loops], ["Dead ends", deadEnds],
    null,
    ["Pits", t.pits.length], ["Pit squares", pitCells],
    null,
    ["Exit row", t.exit + 1],
    ["Right way", ok ? `${t.route.toFixed(1)} m` : "none"],
    ["Cable", ok ? `${t.len} m` : "—"],
    ["Slack", `${Math.round(t.spare * 1000) / 10}%`],
  ];
  $("edStats").innerHTML = rows.map((r) => (r ? `<dt>${r[0]}</dt><dd${!ok && r[0] === "Right way" ? ' class="bad"' : ""}>${r[1]}</dd>` : '<span class="gap"></span>')).join("");
}
function edFill() {
  $("edDiff").innerHTML = TESTS.map((t, k) => `<option value="${k}">${t.level}</option>`).join("");
  $("edLevel").innerHTML = Array.from({ length: LEVEL_COUNT }, (_, l) => `<option value="${l}">Level ${l + 1}</option>`).join("");
}
function edSelect(k, l) {
  ed.k = k; ed.l = l;
  $("edDiff").value = String(k); $("edLevel").value = String(l);
  edShow(true);
}
function openEditor() {
  $("menu").hidden = true; $("result").hidden = true;
  $("editor").hidden = false;
  keys.clear();
  clearTimeout(resultTimer);
  camIntro = null;
  game.state = "menu"; game.run++;
  edSelect(game.test ?? ed.k, game.test === null ? ed.l : game.level);
  edMsg("");
  // Only the local dev server can save into the game's own files.
  fetch("/__dev/ping").then((r) => r.ok && r.json()).then((j) => { ed.canSave = !!j?.save; $("edSave").hidden = !ed.canSave; }).catch(() => {});
}
function closeEditor() {
  $("editor").hidden = true;
  showMenu();
}
// The levels file, laid out so each maze reads as a picture in a diff.
function levelsText() {
  const q = JSON.stringify;
  return '{\n  "version": 1,\n  "difficulties": [\n' + TESTS.map((d, k) =>
    `    {\n      "name": ${q(d.name)}, "level": ${q(d.level)}, "hex": ${q(d.hex)}, "spare": ${d.spare},\n      "levels": [\n` +
    LEVELS[k].map((t) => "        [\n" + t.map.map((row) => `          ${q(row)}`).join(",\n") + "\n        ]").join(",\n") +
    "\n      ]\n    }").join(",\n") + "\n  ]\n}\n";
}
$("editorBtn").onclick = openEditor;
$("edClose").onclick = closeEditor;
$("edGrid").addEventListener("click", edClick);
$("edDiff").onchange = () => { edSelect(Number($("edDiff").value), ed.l); $("edDiff").blur(); };
$("edLevel").onchange = () => { edSelect(ed.k, Number($("edLevel").value)); $("edLevel").blur(); };
$("edRevert").onclick = () => { edSetMap(edBase().slice()); edMsg("Level put back as saved."); };
// Clear: no walls inside and no pits; the room's walls, the entrance and the exit stay.
$("edClear").onclick = () => {
  const exit = edLevel().exit, map = [];
  for (let y = 0; y <= 2 * ROWS; y++) {
    if (y % 2 === 0) map.push("+" + (y === 0 || y === 2 * ROWS ? "-+" : " +").repeat(COLS));
    else {
      const r = (y - 1) / 2;
      map.push((r === IN_ROW ? " " : "|") + " ".repeat(2 * COLS - 1) + (r === exit ? " " : "|"));
    }
  }
  edSetMap(map);
  edMsg("Map cleared. Revert level brings it back.");
};
$("edPlay").onclick = () => {
  $("editor").hidden = true;
  game.fromEditor = true;
  startTest(ed.k, ed.l);
};
$("edExport").onclick = () => {
  const t = edLevel(), name = `abp-${t.level.toLowerCase().replace(/\s+/g, "-")}-${ed.l + 1}.json`;
  const text = JSON.stringify({ type: "alans-bot-plugs-level", version: 1, name: `${t.level} ${ed.l + 1}`, map: t.map }, null, 2) + "\n";
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: "application/json" }));
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  edMsg(`Exported ${name}.`, "good");
};
$("edImport").onclick = () => $("edFile").click();
$("edFile").onchange = async () => {
  const file = $("edFile").files[0];
  $("edFile").value = "";
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    const map = Array.isArray(data) ? data : data.map;
    const parsed = parseMap(map);
    if (parsed.entry !== IN_ROW) throw new Error("the entrance must be open on row 4");
    if (parsed.exit < 0) throw new Error("there is no exit");
    edSetMap(map.slice());
    edMsg(`Imported ${file.name} into ${TESTS[ed.k].level} ${ed.l + 1}.`, "good");
  } catch (err) {
    edMsg(`Couldn't import ${file.name}: ${err.message}.`, "bad");
  }
};
$("edSave").onclick = async () => {
  const text = levelsText();
  try {
    const r = await fetch("/__dev/levels", { method: "POST", headers: { "Content-Type": "application/json" }, body: text });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || r.status);
    levelData.difficulties.forEach((d, k) => { d.levels = LEVELS[k].map((t) => t.map.slice()); });
    edRender();
    edMsg(`Saved to ${j.saved}.`, "good");
  } catch (err) {
    edMsg(`Couldn't save: ${err.message}.`, "bad");
  }
};
addEventListener("beforeunload", (e) => { if (anyDirty()) e.preventDefault(); });
edFill();

// --- Audio -----------------------------------------------------------------------------------------
// Browsers only start audio after a click or key press, so the context and the music wait for one.
// Each effect has a level that evens out the generated files, an optional start offset that skips a
// silent lead-in, and an optional length after which it fades out.
const SFX = {
  step_a: { gain: 0.55, len: 0.14 }, step_b: { gain: 0.45, len: 0.14 }, // he takes about 12 steps a second
  walls_rise: { gain: 1.6 }, power_up: { gain: 0.6 }, unplug: { gain: 1.8, offset: 0.24 },
  power_down: { gain: 2.2 }, pass: { gain: 0.7 }, fail: { gain: 0.6 }, stomp: { gain: 0.5 },
  cable_strain: { gain: 2.5 }, click: { gain: 0.35 }, pit_fall: { gain: 1.0 },
};
const BGM_LEVEL = 0.4; // the tracks are mastered loud; keep them under the effects
// One track per difficulty, from mellow to dark, with a trim that evens out their loudness. tail: seconds
// of near-silence at the end to skip when looping.
const BGM = [
  { name: "bgm_very_easy", gain: 1.32 }, { name: "bgm_easy", gain: 1.16 }, { name: "bgm_medium", gain: 0.89 },
  { name: "bgm_hard", gain: 1.01 }, { name: "bgm_extra_hard", gain: 0.71, tail: 1 },
];
const TITLE_BGM = { name: "bgm_title", gain: 0.85, tail: 3 }; // while the menu is open; a little under the level tracks
const audio = { ctx: null, bufs: {}, pending: {}, bgm: null, fx: null, music: null, strain: null };
// The files download with the page; they're decoded once the context exists.
const audioFiles = Object.fromEntries([...Object.keys(SFX), ...[...BGM, TITLE_BGM].map((t) => t.name)].map((name) =>
  [name, fetch(`assets/audio/${name}.mp3`).then((r) => (r.ok ? r.arrayBuffer() : null)).catch(() => null)]));
function decodeAudio(name) {
  const ctx = audio.ctx;
  return (audio.pending[name] ??= audioFiles[name].then((b) => b && ctx.decodeAudioData(b.slice(0)))
    .then((buf) => { if (buf) audio.bufs[name] = buf; return buf; }).catch(() => null));
}
function initAudio() {
  if (audio.ctx) { if (audio.ctx.state === "suspended" && !document.hidden) audio.ctx.resume(); return; }
  const ctx = audio.ctx = new AudioContext();
  audio.bgm = ctx.createGain(); audio.fx = ctx.createGain();
  audio.bgm.connect(ctx.destination); audio.fx.connect(ctx.destination);
  applySoundLevels();
  Object.keys(SFX).forEach(decodeAudio);
  updateMusic();
}
// The title track while the menu is open, otherwise the current difficulty's.
function updateMusic() { playMusic($("menu").hidden ? BGM[game.test ?? 0] : TITLE_BGM); }
// Crossfade to a track. A decoded track takes about 37 MB, so only the playing one is kept.
function playMusic(track) {
  if (!audio.ctx || audio.music?.name === track.name) return;
  const ctx = audio.ctx, old = audio.music;
  const cur = audio.music = { name: track.name, src: null, gain: ctx.createGain() };
  cur.gain.gain.value = 0; cur.gain.connect(audio.bgm);
  if (old) {
    old.gain.gain.setTargetAtTime(0, ctx.currentTime, 0.4);
    old.src?.stop(ctx.currentTime + 2);
    setTimeout(() => {
      old.gain.disconnect();
      if (audio.music.name !== old.name) { delete audio.bufs[old.name]; delete audio.pending[old.name]; }
    }, 2100);
  }
  decodeAudio(track.name).then((buf) => {
    if (audio.music !== cur) {
      if (audio.music.name !== cur.name) { delete audio.bufs[cur.name]; delete audio.pending[cur.name]; }
      return;
    }
    if (!buf) return;
    const src = cur.src = ctx.createBufferSource();
    src.buffer = buf; src.loop = true; src.loopEnd = buf.duration - (track.tail ?? 0);
    src.connect(cur.gain); src.start();
    cur.gain.gain.setTargetAtTime(track.gain, ctx.currentTime, 0.4);
  });
}
function applySoundLevels() {
  if (!audio.ctx) return;
  const t = audio.ctx.currentTime;
  audio.bgm.gain.setTargetAtTime(soundGain("bgm") * BGM_LEVEL, t, 0.05);
  audio.fx.gain.setTargetAtTime(soundGain("fx"), t, 0.05);
}
onSoundChange(applySoundLevels);
addEventListener("pointerdown", initAudio, true);
addEventListener("keydown", initAudio, true);
document.addEventListener("visibilitychange", () => {
  if (!audio.ctx) return;
  if (document.hidden) audio.ctx.suspend(); else audio.ctx.resume();
});
// Play an effect once: vol scales its level, rate its pitch, delay is in seconds. One asked for while
// its file is still decoding (on the first click) plays when ready, unless that's too late to match.
function sfx(name, opts = {}) {
  if (!audio.ctx) return;
  if (!audio.bufs[name]) {
    const asked = performance.now();
    audio.pending[name]?.then((buf) => { if (buf && performance.now() - asked < 300) sfx(name, opts); });
    return;
  }
  const { vol = 1, rate = 1, delay = 0 } = opts, buf = audio.bufs[name];
  if (audio.ctx.state !== "running") return;
  const src = audio.ctx.createBufferSource(), g = audio.ctx.createGain();
  src.buffer = buf; src.playbackRate.value = rate;
  g.gain.value = SFX[name].gain * vol;
  src.connect(g).connect(audio.fx);
  const at = audio.ctx.currentTime + delay, len = SFX[name].len;
  src.start(at, SFX[name].offset || 0);
  if (len) { g.gain.setTargetAtTime(0, at + len, 0.015); src.stop(at + len + 0.1); }
}
// The cable's strain loop fades in as the cable nears the end of its slack.
function setStrain(level) {
  if (!audio.ctx || audio.ctx.state !== "running") return;
  if (!audio.strain) {
    const buf = audio.bufs.cable_strain;
    if (!buf || level <= 0) return;
    const src = audio.ctx.createBufferSource(), g = audio.ctx.createGain();
    src.buffer = buf; src.loop = true; g.gain.value = 0;
    src.connect(g).connect(audio.fx); src.start();
    audio.strain = g;
  }
  audio.strain.gain.setTargetAtTime(SFX.cable_strain.gain * level, audio.ctx.currentTime, 0.08);
}
// Footsteps follow the walk clip: the feet touch down at 0 and halfway through the cycle, so a foot
// lands whenever the clip moves into the other half, walking forward or back.
let stepHalf = 0, stompCount = 0;
function updateStepSounds() {
  if (!walk) return;
  const half = Math.floor((((walk.time / walk.getClip().duration) % 1) + 1) % 1 * 2);
  if (half === stepHalf) return;
  stepHalf = half;
  if (bot.weight < 0.25 || game.state !== "playing" || unplugged) return;
  sfx(half ? "step_b" : "step_a", { vol: bot.weight * (0.85 + Math.random() * 0.3), rate: 0.92 + Math.random() * 0.16 });
}
// One stomp sound each time a foot lands in the victory dance (see applyStomp), for the first few.
function updateStompSounds() {
  if (game.state !== "passed") { stompCount = 0; return; }
  const n = Math.floor((game.time - game.cheer) * 1.3 * 2);
  if (n > stompCount) { stompCount = n; sfx("stomp", { rate: 0.95 + Math.random() * 0.1 }); }
}
// Menu, control bar and result buttons click.
document.addEventListener("click", (e) => { if (e.target.closest("button")) sfx("click"); });
// Fold the HUD down to its title bar; remembered between visits.
function setFolded(on) {
  document.querySelector(".hud").classList.toggle("folded", on);
  const t = $("hudToggle");
  t.setAttribute("aria-expanded", String(!on));
  t.title = t.ariaLabel = on ? "Show panels" : "Hide panels";
  try { localStorage.setItem("abp-folded", on ? "1" : "0"); } catch { /* storage unavailable */ }
}
$("hudToggle").onclick = () => { setFolded(!document.querySelector(".hud").classList.contains("folded")); $("hudToggle").blur(); };
function applySavedFold() {
  let on = false;
  try { on = localStorage.getItem("abp-folded") === "1"; } catch { /* storage unavailable */ }
  setFolded(on);
}
applySavedFold();
$("restart").onclick = () => { if (game.test !== null) startTest(game.test, game.level); };
// Step back through this difficulty's levels, or forward up to the one you're trying to beat.
function updateLevelButtons() {
  const on = game.test !== null;
  $("prevLevel").disabled = !on || game.level <= 0;
  $("nextLevel").disabled = !on || game.level >= firstOpen(game.test);
}
$("prevLevel").onclick = () => { if (!$("prevLevel").disabled) startTest(game.test, game.level - 1); $("prevLevel").blur(); };
$("nextLevel").onclick = () => { if (!$("nextLevel").disabled) startTest(game.test, game.level + 1); $("nextLevel").blur(); };

// --- Camera and controls -------------------------------------------------------------------------
// Follow: over the bot's shoulder, just above the wall tops, turning as he turns.
// Overhead: looking almost straight down on him; the scroll wheel raises and lowers it, never so high
// that the whole maze fits in view.
const FOLLOW_UP = 1.85, FOLLOW_BACK = 2.3, FOLLOW_AHEAD = 1.0;
const OVERHEAD_MIN = 3.5, OVERHEAD_TILT = 0.12; // tilt: sideways offset per metre of height (about 83 degrees)
let follow = true, camYaw = 0, overheadH = 6;
const camLook = new THREE.Vector3(), camGoalPos = new THREE.Vector3(), camGoalLook = new THREE.Vector3();
function overheadMax() {
  // Highest the camera may go while the view stays narrower than the maze in both directions.
  const v = 2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  return Math.min(ROOM.h - 2.8, (COLS * CELL * 0.8) / (v * camera.aspect), (ROWS * CELL * 0.8) / v);
}
// After a pass the camera swings round to face him, as close as the room behind him allows.
const cheering = () => game.state === "passed" && !camIntro;
// After an unplug the camera circles him slowly, above the wall tops, so his face and his open plug
// come round in turn.
const mourning = () => game.state === "failed" && !camIntro;
const ORBIT_SPEED = 0.6, ORBIT_DIST = 1.7, ORBIT_UP = 1.55;
function camGoal() {
  if (fall && !camIntro) {
    // Circle high over the pit, looking steeply down at him where he landed, clear of the walls round it.
    const fx = Math.cos(camYaw), fz = -Math.sin(camYaw), cx = fall.to.x, cz = fall.to.z;
    camGoalPos.set(cx - fx * 1.0, 3.6, cz - fz * 1.0);
    camGoalPos.x = THREE.MathUtils.clamp(camGoalPos.x, -ROOM.x + 0.3, ROOM.x - 0.3);
    camGoalPos.z = THREE.MathUtils.clamp(camGoalPos.z, -ROOM.z + 0.3, ROOM.z - 0.3);
    camGoalLook.copy(fall.focus);
    return;
  }
  if (mourning()) {
    const fx = Math.cos(camYaw), fz = -Math.sin(camYaw);
    camGoalPos.set(bot.pos.x - fx * ORBIT_DIST, ORBIT_UP, bot.pos.z - fz * ORBIT_DIST);
    camGoalPos.x = THREE.MathUtils.clamp(camGoalPos.x, -ROOM.x + 0.3, ROOM.x - 0.3);
    camGoalPos.z = THREE.MathUtils.clamp(camGoalPos.z, -ROOM.z + 0.3, ROOM.z - 0.3);
    camGoalLook.set(bot.pos.x, 0.45, bot.pos.z);
    return;
  }
  if (cheering()) {
    const fx = Math.cos(camYaw), fz = -Math.sin(camYaw);
    let reach = 2.0;
    if (fx > 1e-3) reach = Math.min(reach, (ROOM.x - 0.3 - bot.pos.x) / fx);
    if (fx < -1e-3) reach = Math.min(reach, (-ROOM.x + 0.3 - bot.pos.x) / fx);
    if (fz > 1e-3) reach = Math.min(reach, (ROOM.z - 0.3 - bot.pos.z) / fz);
    if (fz < -1e-3) reach = Math.min(reach, (-ROOM.z + 0.3 - bot.pos.z) / fz);
    reach = Math.max(1.0, reach);
    camGoalPos.set(bot.pos.x - fx * reach, 0.75 + reach * 0.2, bot.pos.z - fz * reach);
    // Aim a little to his left so he sits right of centre, clear of the results card.
    camGoalLook.set(bot.pos.x + fz * 0.35, 0.55, bot.pos.z - fx * 0.35);
    return;
  }
  if (follow) {
    const fx = Math.cos(camYaw), fz = -Math.sin(camYaw);
    camGoalPos.set(bot.pos.x - fx * FOLLOW_BACK, FOLLOW_UP, bot.pos.z - fz * FOLLOW_BACK);
    camGoalLook.set(bot.pos.x + fx * FOLLOW_AHEAD, 0.45, bot.pos.z + fz * FOLLOW_AHEAD);
  } else {
    camGoalPos.set(bot.pos.x, overheadH, bot.pos.z + overheadH * OVERHEAD_TILT);
    camGoalLook.set(bot.pos.x, 0, bot.pos.z);
  }
  camGoalPos.x = THREE.MathUtils.clamp(camGoalPos.x, -ROOM.x + 0.3, ROOM.x - 0.3);
  camGoalPos.z = THREE.MathUtils.clamp(camGoalPos.z, -ROOM.z + 0.3, ROOM.z - 0.3);
  if (follow) {
    // Backed up against the room's wall, rise instead, so he doesn't fill the view.
    // Aim back toward him by the same amount, so he stays in the middle of the view.
    const d = Math.hypot(camGoalPos.x - bot.pos.x, camGoalPos.z - bot.pos.z);
    const rise = Math.max(0, FOLLOW_BACK - d) * 1.1;
    camGoalPos.y += rise;
    const pull = Math.min(FOLLOW_AHEAD + 0.3, rise * 0.9);
    camGoalLook.x -= Math.cos(camYaw) * pull;
    camGoalLook.z += Math.sin(camYaw) * pull;
  }
}
// In Follow, walls between the camera and the bot fade so they never hide him.
const ghosts = new Map();
function ghostOf(mat) {
  if (!ghosts.has(mat)) {
    const g = mat.clone();
    g.transparent = true; g.opacity = 0.28; g.depthWrite = false;
    ghosts.set(mat, g);
  }
  return ghosts.get(mat);
}
function setGhost(w, on) {
  if (!!w.ghost === on) return;
  w.ghost = on;
  // The whole wall, its rail, light bars and cap included; panels carry one material per face.
  w.mesh.traverse((o) => {
    if (o.isLineSegments) { o.visible = !on; return; }
    if (!o.isMesh) return;
    if (!o.userData.solid) o.userData.solid = o.material;
    const solid = o.userData.solid;
    o.material = !on ? solid : Array.isArray(solid) ? solid.map(ghostOf) : ghostOf(solid);
  });
  w.mesh.castShadow = !on;
}
function segmentHitsBox(a, b, w) {
  let t0 = 0, t1 = 1;
  const lo = [w.minX - 0.02, 0, w.minZ - 0.02], hi = [w.maxX + 0.02, (w.h + 0.08) * w.rise, w.maxZ + 0.02];
  const p = [a.x, a.y, a.z], d = [b.x - a.x, b.y - a.y, b.z - a.z];
  for (let k = 0; k < 3; k++) {
    if (Math.abs(d[k]) < 1e-9) { if (p[k] < lo[k] || p[k] > hi[k]) return false; continue; }
    let ta = (lo[k] - p[k]) / d[k], tb = (hi[k] - p[k]) / d[k];
    if (ta > tb) [ta, tb] = [tb, ta];
    t0 = Math.max(t0, ta); t1 = Math.min(t1, tb);
    if (t0 > t1) return false;
  }
  return true;
}
const _sight = Array.from({ length: 5 }, () => new THREE.Vector3());
// Never during the opening shot: the walls stay solid until the bot starts. Only walls between the
// camera and the bot fade; a panel takes the posts at its ends with it, and faded walls stay faded a
// moment after they stop blocking, so the view doesn't flicker as the camera moves.
const FADE_HOLD = 0.35;
function fadeBlockers() {
  const on = (follow || cheering() || mourning()) && !camIntro && $("editor").hidden;
  const now = performance.now() / 1000;
  if (on) {
    // Only sight lines to the bot himself (feet, middle, head, and both sides of his body): walls ahead
    // of him never fade.
    // Fallen into a pit, he lies where the ragdoll left him.
    const at = fall ? fall.focus : bot.pos, y0 = fall ? fall.focus.y - 0.4 : 0;
    const vx = at.x - camera.position.x, vz = at.z - camera.position.z, vl = Math.hypot(vx, vz) || 1;
    const sx = (-vz / vl) * 0.25, sz = (vx / vl) * 0.25;
    _sight[0].set(at.x, y0 + 0.08, at.z);
    _sight[1].set(at.x, y0 + 0.5, at.z);
    _sight[2].set(at.x, y0 + 0.95, at.z);
    _sight[3].set(at.x + sx, y0 + 0.5, at.z + sz);
    _sight[4].set(at.x - sx, y0 + 0.5, at.z - sz);
    // Only walls that block the view fade, and a post never fades without a panel. A blocking panel takes
    // the posts at its two ends with it. A post that blocks on its own takes the one panel meeting it
    // that lies nearest the camera-to-bot line (and that panel's other end post).
    const group = new Set();
    const addPanel = (pnl) => { group.add(pnl); for (const l of pnl.links || []) group.add(l); };
    const cx = camera.position.x, cz = camera.position.z, dx = at.x - cx, dz = at.z - cz;
    const dd = dx * dx + dz * dz || 1;
    const offLine = (w) => {
      const px = (w.minX + w.maxX) / 2, pz = (w.minZ + w.maxZ) / 2;
      const t = Math.max(0, Math.min(1, ((px - cx) * dx + (pz - cz) * dz) / dd));
      return Math.hypot(cx + dx * t - px, cz + dz * t - pz);
    };
    for (const w of walls) {
      if (!_sight.some((s) => segmentHitsBox(camera.position, s, w))) continue;
      if (!w.post) { addPanel(w); continue; }
      group.add(w);
      const panels = (w.links || []).filter((l) => !l.post);
      if (panels.length) addPanel(panels.reduce((a, b) => (offLine(a) <= offLine(b) ? a : b)));
    }
    for (const w of group) w.fadeUntil = now + FADE_HOLD;
  }
  for (const w of walls) setGhost(w, on && (w.fadeUntil || 0) > now);
}
// Opening shot: hold on the sign, then swing round in an arc and close in on the bot.
const INTRO_HOLD = 1.0, INTRO_MOVE = 2.8;
// The opening pose frames the sign in the top of the view, with the test floor below it. The first menu
// sits over this same shot, so starting a test carries straight on from it.
const INTRO_FROM = new THREE.Vector3(0, 4.4, 6.4), INTRO_LOOK = new THREE.Vector3(0, 2.3, -ROOM.z);
let camIntro = null; // { t, k, hold } while the opening shot plays; hold keeps it on the sign
const _bz = new THREE.Vector3();
function introCamera(dt) {
  camIntro.t = camIntro.hold ? 0 : camIntro.t + dt;
  const u = THREE.MathUtils.clamp((camIntro.t - INTRO_HOLD) / INTRO_MOVE, 0, 1);
  const e = u * u * u * (u * (u * 6 - 15) + 10);
  const mid = _bz.set((INTRO_FROM.x + camGoalPos.x) / 2 - 1.5, 5.6, 4.5);
  const a = 1 - e;
  camera.position.set(0, 0, 0).addScaledVector(INTRO_FROM, a * a).addScaledVector(mid, 2 * a * e).addScaledVector(camGoalPos, e * e);
  const lookE = THREE.MathUtils.smoothstep(Math.min(1, u * 1.3), 0, 1);
  camLook.copy(INTRO_LOOK).lerp(camGoalLook, lookE);
  camera.lookAt(camLook);
  if (camIntro.t >= INTRO_HOLD + INTRO_MOVE) {
    const run = camIntro.run;
    camIntro = null;
    if (game.run === run && game.state === "rising") beginPlay();
  }
}
function updateCamera(dt, snap) {
  // The status plate only shows once the opening shot is over and the level is ready.
  stage.classList.toggle("intro", !!camIntro);
  // Behind him while playing; swung round in front of him (a slower, wider arc) after a pass.
  if (mourning()) camYaw += ORBIT_SPEED * dt;
  else {
    const yawGoal = bot.heading + (cheering() ? Math.PI : 0);
    camYaw += angleDiff(yawGoal, camYaw) * (snap ? 1 : 1 - Math.exp(-dt * (cheering() ? 1.6 : 3)));
  }
  overheadH = THREE.MathUtils.clamp(overheadH, OVERHEAD_MIN, overheadMax());
  camGoal();
  if (camIntro) {
    introCamera(dt);
    fadeBlockers();
    return;
  }
  const k = snap ? 1 : 1 - Math.exp(-dt * 5);
  camera.position.lerp(camGoalPos, k);
  camLook.lerp(camGoalLook, k);
  camera.lookAt(camLook);
  fadeBlockers();
}
function setCam(mode) {
  follow = mode === "follow";
  $("camToggle").setAttribute("aria-checked", String(!follow));
  $("camToggle").title = `Camera: ${follow ? "Follow" : "Overhead"}`;
  $("camToggle").blur();
}
$("camToggle").onclick = () => setCam(follow ? "overhead" : "follow");
renderer.domElement.addEventListener("wheel", (e) => {
  e.preventDefault();
  if (!follow) overheadH = THREE.MathUtils.clamp(overheadH * Math.exp(e.deltaY * 0.0012), OVERHEAD_MIN, overheadMax());
}, { passive: false });
// Autopilot is for testing only: open the page with ?autopilot to have the bot drive itself.
function setDrive(isManual) {
  manual = isManual;
  keys.clear();
  if (!manual) {
    game.autopilot = true;
    if (game.state === "playing") { const r = planRoute(bot.pos); route = r.points; routeIdx = 1; }
  }
}
if (new URLSearchParams(location.search).has("autopilot")) setDrive(false);
let paused = false;
function resize() {
  const { clientWidth: w, clientHeight: h } = stage;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(stage);
resize();

// Each level's cable length: the correct route through its maze, pulled tight the same way the game
// measures your walk, plus the colour's spare.
// A maze with no way through gets route Infinity.
function measureLevel(t) {
  const boxes = wallBoxes(t);
  const r = planRoute(START, boxes, t.pits);
  if (!r.points.length) { t.route = t.len = Infinity; return t; }
  const line = new Taut(socketFoot(), new THREE.Vector2(START.x, START.z), wallCorners(boxes));
  for (const p of r.points.slice(1)) line.moveTo(p);
  t.route = line.length() + cableDrops();
  t.len = Math.ceil(t.route * (1 + t.spare) * 2) / 2;
  return t;
}
LEVELS.flat().forEach(measureLevel);

// Ready: show the first level laid out behind the menu.
rope = makeRope(LEVELS[0][0].len);
buildCableMeshes();
buildWalls(LEVELS[0][0]);
buildPits(LEVELS[0][0].pits);
for (const w of walls) { w.rise = 1; w.mesh.position.y = w.h / 2; }
layCable();
camIntro = { t: 0, run: null, hold: true }; // the first menu sits over the sign
updateCamera(0, true);
// Loaded: wait for Space (or a click or tap) before the title menu. That press also starts the audio.
{
  const loading = $("loading");
  loading.innerHTML = "<span>Press Space to start your shift.</span>";
  loading.classList.add("ready");
  const start = (e) => {
    if (e.type === "keydown" && e.code !== "Space") return;
    e.preventDefault();
    removeEventListener("keydown", start, true);
    removeEventListener("pointerdown", start, true);
    loading.remove();
    showMenu();
  };
  addEventListener("keydown", start, true);
  addEventListener("pointerdown", start, true);
}

// --- Loop --------------------------------------------------------------------------------------
const clock = new THREE.Clock();
let hudTimer = 0;
let state = cableState();
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 1 / 20);
  if (!paused) {
    game.time += dt;
    updateWalls(dt);
    setWallList(solidWalls());
    updateBot(dt);
    power = unplugged ? Math.max(0, power - dt / 1.2) : Math.min(1, power + dt / 0.8);
    if (fall) stepFall(dt);
    else {
      restorePose();
      mixer.update(dt);
      updateStepSounds();
      savePose();
      applySlump(1 - power);
    }
    if (game.state === "passed") applyStomp(game.time - game.cheer);
    updateStompSounds();
    setPowerLook(power);
    updatePins();
    if (!unplugged && game.state !== "menu") {
      taut.moveTo(new THREE.Vector2(bot.pos.x, bot.pos.z));
      needed = taut.length() + cableDrops() + wrapExtra();
    }
    drawCable(dt);
    updateSparks(dt);
    state = cableState();
    if (game.state === "playing" && !unplugged) {
      game.peak = Math.max(game.peak, state.tension);
      game.over = state.tension >= 1 ? game.over + dt : 0;
      if (game.over > 0.2) unplug();
      else if (bot.pos.x > GOAL_X) finish(true);
    }
    setStrain(game.state === "playing" && !unplugged ? THREE.MathUtils.smoothstep(state.tension, 0.8, 1) : 0);
  }
  buildFrames();
  cable.update(frames);
  cableInk.update(frames);
  updateBands();

  updateCamera(dt, false);

  hudTimer -= dt;
  if (hudTimer <= 0) {
    hudTimer = 0.1;
    // The gauge shows the cable still on the reel: full at the start, empty when the plug pulls out.
    const left = unplugged ? 0 : Math.max(0, rope.len - state.taut);
    const low = left < Math.max(1.5, rope.len * 0.15);
    if (game.test !== null) {
      $("cableUsed").textContent = Math.min(state.taut, rope.len).toFixed(1);
      $("cableTotal").textContent = ` / ${rope.len.toFixed(1)} m`;
    }
    $("meter").style.width = ((left / rope.len) * 100).toFixed(0) + "%";
    // Nearly out: the bar and the cable-used figure blink red together.
    const blink = low && !unplugged && game.state === "playing";
    $("meterBox").classList.toggle("warn", blink);
    $("cableUsed").classList.toggle("warn", blink);
    $("toGoal").textContent = Math.max(0, GOAL_X - bot.pos.x).toFixed(1) + " m";
    const run = game.started === null ? 0 : (game.state === "playing" ? game.time - game.started : null);
    if (run !== null) $("clock").textContent = fmt(run);
    const idle = bot.weight < 0.5;
    const st = $("state");
    st.textContent = unplugged ? "Unplugged · off" : game.state === "passed" ? "Passed" : game.state === "rising" ? "Walls rising"
      : game.state !== "playing" ? "Ready" : paused ? "Paused" : low ? "Cable low" : idle ? "Idle" : manual ? "Walking" : "Autopilot";
    st.classList.toggle("idle", !unplugged && (idle || paused || low || game.state !== "playing"));
    st.classList.toggle("off", unplugged);
  }
  // The editor looks down from below the sign, which would hide the maze's back row, so it's left out.
  const editing = !$("editor").hidden;
  signGltf.scene.visible = !editing;
  if (editing) { edFrame(); renderer.render(scene, edCam); } else renderer.render(scene, camera);
});
