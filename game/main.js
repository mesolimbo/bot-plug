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

// Five difficulties, each with its own cable colour and spare, and five levels. Each level is a real
// maze built from a fixed seed: a full maze, then extra openings that each add a second way through,
// 3 to 8 cells longer than the right one. That leaves islands on the route you can pass either side
// of. The cable is just long enough for the right way plus its colour's spare; take a long way round
// and it runs out.
const TESTS = [
  // One seed per level, picked so each maze gets its full count of islands and the right way gets
  // longer level by level: about 24-33 m for Very Easy up to 37-49 m for Extra Hard.
  { name: "Green", level: "Very Easy", hex: "#2fbf71", spare: 0.10, loops: 3, seeds: [17, 219, 151, 138, 286] },
  { name: "Blue", level: "Easy", hex: "#3b82f6", spare: 0.08, loops: 4, seeds: [22, 1224, 1127, 1110, 1189] },
  { name: "Yellow", level: "Medium", hex: "#f2c230", spare: 0.06, loops: 5, seeds: [8, 2202, 2211, 2151, 2108] },
  { name: "Orange", level: "Hard", hex: "#f28b30", spare: 0.045, loops: 6, seeds: [14, 3112, 3194, 3100, 3115] },
  { name: "Red", level: "Extra Hard", hex: "#e5484d", spare: 0.03, loops: 7, seeds: [5, 4128, 4155, 4287, 4295] },
];

function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
// vWall[i][r]: wall on x-line i (x = -9 + 2i) across row r. hWall[j][c]: wall on z-line j across column c.
function makeMaze(test) {
  const rand = rng(test.seed);
  const vWall = Array.from({ length: COLS + 1 }, () => Array(ROWS).fill(true));
  const hWall = Array.from({ length: ROWS + 1 }, () => Array(COLS).fill(true));
  const IN_ROW = 3;
  const seen = Array.from({ length: COLS }, () => Array(ROWS).fill(false));
  const stack = [[0, IN_ROW]];
  seen[0][IN_ROW] = true;
  while (stack.length) {
    const [c, r] = stack[stack.length - 1];
    const next = [[c + 1, r], [c - 1, r], [c, r + 1], [c, r - 1]]
      .filter(([x, y]) => x >= 0 && y >= 0 && x < COLS && y < ROWS && !seen[x][y]);
    if (!next.length) { stack.pop(); continue; }
    const [x, y] = next[Math.floor(rand() * next.length)];
    if (x !== c) vWall[Math.max(x, c)][r] = false; else hWall[Math.max(y, r)][c] = false;
    seen[x][y] = true;
    stack.push([x, y]);
  }
  vWall[0][IN_ROW] = false;                              // entrance from the start zone
  const OUT_ROW = Math.floor(rand() * ROWS);
  vWall[COLS][OUT_ROW] = false;                          // exit into the goal zone

  // Walking distances in cells, from the entrance and to the exit, through the current openings.
  const dist = (c0, r0) => {
    const d = Array.from({ length: COLS }, () => Array(ROWS).fill(Infinity));
    d[c0][r0] = 0;
    const q = [[c0, r0]];
    while (q.length) {
      const [c, r] = q.shift();
      const step = (x, y, open) => { if (open && d[x][y] === Infinity) { d[x][y] = d[c][r] + 1; q.push([x, y]); } };
      if (c + 1 < COLS) step(c + 1, r, !vWall[c + 1][r]);
      if (c > 0) step(c - 1, r, !vWall[c][r]);
      if (r + 1 < ROWS) step(c, r + 1, !hWall[r + 1][c]);
      if (r > 0) step(c, r - 1, !hWall[r][c]);
    }
    return d;
  };
  // Each extra opening adds a second way through that is 3 to 8 cells longer than the right one.
  let made = 0;
  for (let tries = 0; made < test.loops && tries < 4000; tries++) {
    const dE = dist(0, IN_ROW), dX = dist(COLS - 1, OUT_ROW);
    const best = dE[COLS - 1][OUT_ROW];
    const vertical = rand() < 0.5;
    const i = 1 + Math.floor(rand() * (vertical ? COLS - 1 : ROWS - 1));
    const k = Math.floor(rand() * (vertical ? ROWS : COLS));
    if (vertical ? !vWall[i][k] : !hWall[i][k]) continue;
    const [ac, ar, bc, br] = vertical ? [i - 1, k, i, k] : [k, i - 1, k, i];
    const via = Math.min(dE[ac][ar] + 1 + dX[bc][br], dE[bc][br] + 1 + dX[ac][ar]);
    if (via - best < 3 || via - best > 8) continue;
    if (vertical) vWall[i][k] = false; else hWall[i][k] = false;
    made++;
  }
  test.made = made;
  test.v = []; test.h = [];
  for (let i = 0; i <= COLS; i++) for (let r = 0; r < ROWS; r++) if (vWall[i][r]) test.v.push([i, r, r]);
  for (let j = 1; j < ROWS; j++) for (let c = 0; c < COLS; c++) if (hWall[j][c]) test.h.push([j, c, c]);
}
const LEVEL_COUNT = 5;
const LEVELS = TESTS.map((d) => d.seeds.map((seed) => {
  const m = { ...d, seed };
  makeMaze(m);
  return m;
}));

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
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -7, right: 7, top: 7, bottom: -7, near: 1, far: 40 });
sun.shadow.bias = -0.0005;
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
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
scene.add(floor);

const wallTex = canvasTex(256, 512, (g, w, h) => {
  for (let x = 0; x < w; x += 32) {
    const grad = g.createLinearGradient(x, 0, x + 32, 0);
    grad.addColorStop(0, "#7a808b"); grad.addColorStop(0.45, "#626873");
    grad.addColorStop(0.55, "#4f545e"); grad.addColorStop(1, "#6e747f");
    g.fillStyle = grad; g.fillRect(x, 0, 32, h);
  }
  g.fillStyle = "#3d414a"; g.fillRect(0, h - 6, w, 6);
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
const ceiling = new THREE.Mesh(new THREE.PlaneGeometry(W, D), toon({ color: 0x1c1e24, side: THREE.DoubleSide }));
ceiling.rotation.x = Math.PI / 2; ceiling.position.y = ROOM.h;
scene.add(ceiling);

const steel = toon({ color: 0x343842 });
const steelLight = toon({ color: 0x5b616c });
const wrapMat = toon({ map: canvasTex(64, 64, (g, w, h) => stripes(g, w, h, "#f2b705", "#1b1b1d", 32), [2, 2]) });
for (let x = -8; x <= 8; x += 4) {
  for (const z of [-ROOM.z + 0.08, ROOM.z - 0.08]) {
    scene.add(inked(new THREE.Mesh(new THREE.BoxGeometry(0.5, ROOM.h, 0.16), steel)).translateX(x).translateY(ROOM.h / 2).translateZ(z));
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
// The main sign hangs on the front of the wall's steel ribs, on a dark backing board.
const SIGN_AT = new THREE.Vector3(0, 5.6, -ROOM.z + 0.26);
{
  const board = inked(new THREE.Mesh(new THREE.BoxGeometry(9.3, 2.5, 0.08), steel));
  board.position.set(SIGN_AT.x, SIGN_AT.y, SIGN_AT.z - 0.05); scene.add(board);
}
sign([["ALAN'S ", "#ece6da"], ["BOT PLUGS", "#f2b705"]], "QUALITY CONTROL CENTER - TEST FLOOR", 9, 2.2, SIGN_AT, 0, true);
sign("GOAL", null, 3, 0.9, new THREE.Vector3(ROOM.x - 0.05, 5.4, 0), -Math.PI / 2);
sign("TEST SOCKET", null, 3, 0.7, new THREE.Vector3(-ROOM.x + 0.05, 3.2, 0), Math.PI / 2);
// Roller door behind the goal, for units that pass.
const shutter = canvasTex(64, 256, (g, w, h) => {
  for (let y = 0; y < h; y += 16) { g.fillStyle = "#6c717b"; g.fillRect(0, y, w, 10); g.fillStyle = "#4b4f58"; g.fillRect(0, y + 10, w, 6); }
}, [5, 4]);
const door = new THREE.Mesh(new THREE.PlaneGeometry(6, 4.2), toon({ map: shutter }));
door.position.set(ROOM.x - 0.03, 2.1, 0); door.rotation.y = -Math.PI / 2; scene.add(door);

// --- Maze walls -------------------------------------------------------------------------------
const panelTex = canvasTex(256, 168, (g, w, h) => {
  g.fillStyle = "#666c77"; g.fillRect(0, 0, w, h);
  g.fillStyle = "#575d68"; g.fillRect(10, 30, w - 20, h - 40);
  g.strokeStyle = "#454a54"; g.lineWidth = 3; g.strokeRect(10, 30, w - 20, h - 40);
  g.fillStyle = "#8a909b";
  for (const x of [18, w - 18]) for (const y of [40, h - 18]) { g.beginPath(); g.arc(x, y, 3.5, 0, 7); g.fill(); }
  g.save(); g.beginPath(); g.rect(0, 0, w, 22); g.clip(); stripes(g, w, 22, "#f2b705", "#1b1b1d", 30); g.restore();
});
const panelMat = toon({ map: panelTex });
const postMat = toon({ color: 0x3b3f48 });
const capMat = toon({ map: canvasTex(64, 64, (g, w, h) => stripes(g, w, h, "#f2b705", "#1b1b1d", 24)) });
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
    const mesh = inked(new THREE.Mesh(new THREE.BoxGeometry(b.sx, b.h, b.sz), b.post ? postMat : panelMat));
    mesh.castShadow = true; mesh.receiveShadow = true;
    mesh.position.set(b.cx, -b.h / 2, b.cz);
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
    void main() {
      #include <skinbase_vertex>
      #include <begin_vertex>
      #include <beginnormal_vertex>
      #include <skinnormal_vertex>
      #include <skinning_vertex>
      vec4 mv = modelViewMatrix * vec4(transformed, 1.0);
      mv.xyz += normalize(normalMatrix * objectNormal) * thickness;
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

// Keep a rope point ROPE_D from every wall, with corners rounded off, and outside the bot when close
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
    for (const w of wallsNear(p.x, p.y)) {
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
    ropeTarget = Math.max(0.8, ropeTarget - dt * 1.6); // the reel winds the loose end back in
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
    // The loose plug rides on the end of the cable.
    const end = new THREE.Vector3(P[n * 3], P[n * 3 + 1], P[n * 3 + 2]);
    const prev = new THREE.Vector3(P[(n - 3) * 3], P[(n - 3) * 3 + 1], P[(n - 3) * 3 + 2]);
    const dir = prev.sub(end).normalize();
    botPlug.quaternion.setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir);
    botPlug.position.copy(end).addScaledVector(dir, -PLUG_LEN);
    botPlug.position.y = Math.max(PLUG_R, botPlug.position.y);
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
const bot = { pos: START.clone(), heading: 0, weight: 0, speed: 0 };
const botRoot = new THREE.Group();
scene.add(botRoot);
let mixer = null, walk = null, botPlug = null, wallPlug = null, model = null, bodyBone = null, meshes = [];
let plugInBone = null;
const wallEnd = new THREE.Vector3(), wallDir = new THREE.Vector3(1, 0, 0);
const botEnd = new THREE.Vector3(), botDir = new THREE.Vector3();
const wrapAngle = (a) => Math.atan2(Math.sin(a), Math.cos(a));

function pushOutOfWalls(p, r) {
  for (const w of solidWalls()) {
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
  for (const w of solidWalls()) {
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
  if (e.target.closest?.("input, textarea")) return;
  if (e.ctrlKey || e.metaKey || e.altKey) return; // leave browser shortcuts (Ctrl+R reloads) alone
  if (e.code === "Escape") { e.preventDefault(); toggleMenu(); return; }
  if (e.code === "KeyR" && game.test !== null && $("menu").hidden) { e.preventDefault(); startTest(game.test, game.level); return; }
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
function planRoute(from, boxes = walls.filter((w) => w.target > 0)) {
  const blocked = new Uint8Array(NX * NZ);
  const inflate = BOT_R + 0.18;
  const sw = boxes;
  for (let iz = 0; iz < NZ; iz++) {
    for (let ix = 0; ix < NX; ix++) {
      const x = -ROOM.x + (ix + 0.5) * NAV, z = -ROOM.z + (iz + 0.5) * NAV;
      let b = x < -ROOM.x + 0.9 || x > ROOM.x - inflate || z < -ROOM.z + inflate || z > ROOM.z - inflate;
      for (const w of sw) {
        if (b) break;
        const dx = Math.max(w.minX - x, 0, x - w.maxX), dz = Math.max(w.minZ - z, 0, z - w.maxZ);
        if (dx * dx + dz * dz < inflate * inflate) b = true;
      }
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
  pushOutOfWalls(bot.pos, BOT_R);
  if (walk) {
    walk.setEffectiveWeight(bot.weight);
    walk.timeScale = (move < 0 ? -0.6 : move ? Math.max(0.35, move) : 0.6) * PACE;
  }
  if (move > 0.05 && game.state === "playing" && game.started === null) game.started = game.time;
}

function updateBot(dt) {
  if (unplugged || game.state !== "playing") {
    bot.weight += (0 - bot.weight) * Math.min(1, dt * 6);
    if (walk) walk.setEffectiveWeight(bot.weight);
  } else {
    steer(dt);
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
const thighs = [];
const pose = { saved: false, bodyPos: new THREE.Vector3(), bodyQ: new THREE.Quaternion(), thighQ: [new THREE.Quaternion(), new THREE.Quaternion()] };
function restorePose() {
  if (!pose.saved) return;
  bodyBone.position.copy(pose.bodyPos); bodyBone.quaternion.copy(pose.bodyQ);
  thighs.forEach((t, i) => t.quaternion.copy(pose.thighQ[i]));
}
function savePose() {
  pose.bodyPos.copy(bodyBone.position); pose.bodyQ.copy(bodyBone.quaternion);
  thighs.forEach((t, i) => pose.thighQ[i].copy(t.quaternion));
  pose.saved = true;
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
    m.material.color.setRGB(c, c, c);
    const want = p < 0.55 ? m.userData.offMap : m.userData.onMap;
    if (want && m.material.map !== want) m.material.map = want;
  });
}

// --- Load and assemble ----------------------------------------------------------------------
const [botGltf, plugGltf, socketGltf] = await Promise.all(["bot", "plug", "wall_socket"].map((n) => loader.loadAsync(`assets/${n}.glb`)));
model = botGltf.scene;
model.position.y = 0.5;
botRoot.add(model);
model.traverse((o) => { if (o.isMesh) meshes.push(o); });
meshes.forEach((o) => {
  o.material = new THREE.MeshBasicMaterial({ map: o.material.map || null });
  o.castShadow = true;
  const ol = o.isSkinnedMesh ? new THREE.SkinnedMesh(o.geometry, outlineMat) : new THREE.Mesh(o.geometry, outlineMat);
  if (o.isSkinnedMesh) ol.bind(o.skeleton, o.bindMatrix);
  ol.frustumCulled = false;
  o.add(ol);
});
const offMap = await new THREE.TextureLoader().loadAsync("assets/bot_off.jpg");
meshes.forEach((o) => {
  const on = o.material.map;
  if (!on) return;
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
for (const side of ["L", "R"]) thighs.push(boneOf(`thigh.${side}`));
const socket = socketGltf.scene;
toonify(socket);
socket.position.copy(SOCKET_POS);
scene.add(socket);
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
const game = { test: null, level: 0, run: 0, state: "menu", time: 0, started: null, peak: 0, lifted: 0, over: 0, autopilot: false };
// Best times by "difficulty.level". Times saved before levels existed count as level 1.
let best = {};
try { best = JSON.parse(localStorage.getItem("abp-best") || "{}"); } catch { best = {}; }
for (const key of Object.keys(best)) {
  if (/^\d+$/.test(key)) { best[`${key}.0`] ??= best[key]; delete best[key]; }
}
const bestOf = (k, l) => best[`${k}.${l}`];
// A difficulty starts at its first level not yet passed.
const firstOpen = (k) => Math.max(0, LEVELS[k].findIndex((_, l) => !bestOf(k, l)));
const fmt = (t) => `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, "0")}`;

// withIntro: the camera opens on the sign, then swings round and closes in on the bot before he walks.
function startTest(k, l, withIntro = false) {
  const t = LEVELS[k][l];
  const run = ++game.run;
  camIntro = withIntro ? { t: 0, run } : null;
  game.test = k; game.level = l; game.state = "rising"; game.time = 0; game.started = null; game.peak = 0; game.lifted = 0; game.over = 0;
  game.autopilot = !manual;
  clearTimeout(resultTimer);
  $("menu").hidden = true; $("result").hidden = true;
  document.documentElement.style.setProperty("--accent", t.hex);
  cableMat.color.set(t.hex);
  $("testName").textContent = `${t.level} · ${l + 1}/${LEVEL_COUNT}`;
  $("pullLim").textContent = `${Math.round(t.spare * 1000) / 10}%`;
  if (unplugged) replug();
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
  if (!withIntro) setTimeout(() => { if (game.run === run && game.state === "rising") beginPlay(); }, 1300);
}
function beginPlay() {
  game.state = "playing";
  if (!manual) { const r = planRoute(bot.pos); route = r.points; routeIdx = 1; }
}

function finish(passed) {
  if (game.state !== "playing") return;
  game.state = passed ? "passed" : "failed";
  const k = game.test, l = game.level, t = LEVELS[k][l], key = `${k}.${l}`;
  const time = game.started === null ? 0 : game.time - game.started;
  const progress = THREE.MathUtils.clamp((bot.pos.x - START.x) / (GOAL_X - START.x), 0, 1);
  let isBest = false;
  if (passed && !game.autopilot && (!best[key] || time < best[key])) {
    best[key] = time; isBest = true;
    try { localStorage.setItem("abp-best", JSON.stringify(best)); } catch { /* storage unavailable */ }
  }
  // Settle the card's contents now; it only appears after a beat, and is dropped if a new test starts.
  const rows = [
    ["Level", `${t.level} ${l + 1}/${LEVEL_COUNT} · ${t.name.toLowerCase()} cable`],
    ["Cable", `${t.len.toFixed(1)} m · ${Math.round(t.spare * 1000) / 10}% spare`],
    passed ? ["Time", fmt(time) + (isBest ? " · best" : "")] : ["Route covered", `${Math.round(progress * 100)}%`],
    ["Least cable left", `${Math.max(0, t.len * (1 - game.peak)).toFixed(1)} m`],
  ];
  if (game.autopilot) rows.push(["Driver", "Autopilot (no best time)"]);
  const acts = [];
  const next = nextLevel(k, l);
  if (passed && next) acts.push(`<button class="primary" data-act="next">Next level · ${TESTS[next[0]].level} ${next[1] + 1}/${LEVEL_COUNT}</button>`);
  acts.push(`<button ${passed ? "" : 'class="primary"'} data-act="retry">Retry</button>`, `<button data-act="menu">All tests</button>`);
  clearTimeout(resultTimer);
  resultTimer = setTimeout(() => {
    const v = $("verdict");
    v.textContent = passed ? "PASS" : "UNPLUGGED";
    v.className = "verdict " + (passed ? "pass" : "fail");
    $("stats").innerHTML = rows.map(([a, b]) => `<dt>${a}</dt><dd>${b}</dd>`).join("");
    $("actions").innerHTML = acts.join("");
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
});

function renderMenu() {
  $("tests").innerHTML = TESTS.map((t, k) => {
    // Levels passed in this difficulty, and the total of their best times.
    const times = LEVELS[k].map((_, l) => bestOf(k, l)).filter((v) => v);
    const total = times.reduce((a, v) => a + v, 0);
    const coil = `<svg class="coil" viewBox="0 0 120 34" aria-hidden="true">
      <path d="M4 26 C 20 4, 34 4, 40 17 S 60 30, 70 17 S 92 4, 100 17 S 112 28, 116 20" fill="none" stroke="#101114" stroke-width="9" stroke-linecap="round"/>
      <path d="M4 26 C 20 4, 34 4, 40 17 S 60 30, 70 17 S 92 4, 100 17 S 112 28, 116 20" fill="none" stroke="${t.hex}" stroke-width="5" stroke-linecap="round"/></svg>`;
    const pips = Array.from({ length: LEVEL_COUNT }, (_, i) => `<span class="${i < times.length ? "on" : ""}"></span>`).join("");
    return `<button class="test" data-k="${k}" style="--c:${t.hex}">
      ${coil}<b>${t.level}</b><small>${LEVEL_COUNT} levels<br>${Math.round(t.spare * 1000) / 10}% spare</small>
      <span class="pips" aria-label="${times.length} of ${LEVEL_COUNT} levels passed">${pips}</span>
      <span class="best ${times.length === LEVEL_COUNT ? "pass" : ""}">Time · ${times.length ? fmt(total) : "—"}</span></button>`;
  }).join("");
}
$("tests").addEventListener("click", (e) => {
  const k = e.target.closest(".test")?.dataset.k;
  if (k !== undefined) startTest(Number(k), firstOpen(Number(k)), true);
});
function showMenu() { renderMenu(); $("result").hidden = true; $("menu").hidden = false; }
function toggleMenu() {
  if (!$("menu").hidden && game.test !== null) { $("menu").hidden = true; return; }
  showMenu();
}
$("menuBtn").onclick = showMenu;
$("restart").onclick = () => { if (game.test !== null) startTest(game.test, game.level); };

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
function camGoal() {
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
  for (const o of [w.mesh, ...w.mesh.children]) {
    if (o.isLineSegments) { o.visible = !on; continue; }
    if (!o.userData.solid) o.userData.solid = o.material;
    o.material = on ? ghostOf(o.userData.solid) : o.userData.solid;
  }
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
const _sight = [new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()];
// Never during the opening shot: the walls stay solid until the bot starts.
function fadeBlockers() {
  // Only sight lines to the bot himself (feet, middle, head): walls ahead of him never fade.
  _sight[0].set(bot.pos.x, 0.08, bot.pos.z);
  _sight[1].set(bot.pos.x, 0.5, bot.pos.z);
  _sight[2].set(bot.pos.x, 0.95, bot.pos.z);
  for (const w of walls) setGhost(w, follow && !camIntro && _sight.some((s) => segmentHitsBox(camera.position, s, w)));
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
  camYaw += angleDiff(bot.heading, camYaw) * (snap ? 1 : 1 - Math.exp(-dt * 3));
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
  $("camFollow").setAttribute("aria-pressed", String(follow));
  $("camOverhead").setAttribute("aria-pressed", String(!follow));
  $("camFollow").blur(); $("camOverhead").blur();
}
$("camFollow").onclick = () => setCam("follow");
$("camOverhead").onclick = () => setCam("overhead");
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
$("pause").onclick = () => {
  paused = !paused;
  $("pause").textContent = paused ? "Resume" : "Pause";
  $("pause").setAttribute("aria-pressed", String(paused));
};
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
for (const t of LEVELS.flat()) {
  const boxes = wallBoxes(t);
  const r = planRoute(START, boxes);
  const line = new Taut(socketFoot(), new THREE.Vector2(START.x, START.z), wallCorners(boxes));
  for (const p of r.points.slice(1)) line.moveTo(p);
  t.route = line.length() + cableDrops();
  t.len = Math.ceil(t.route * (1 + t.spare) * 2) / 2;
}

// Ready: show the first level laid out behind the menu.
rope = makeRope(LEVELS[0][0].len);
buildCableMeshes();
buildWalls(LEVELS[0][0]);
for (const w of walls) { w.rise = 1; w.mesh.position.y = w.h / 2; }
layCable();
$("loading").remove();
camIntro = { t: 0, run: null, hold: true }; // the first menu sits over the sign
updateCamera(0, true);
showMenu();

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
    restorePose();
    mixer.update(dt);
    savePose();
    power = unplugged ? Math.max(0, power - dt / 1.2) : Math.min(1, power + dt / 0.8);
    applySlump(1 - power);
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
  }
  buildFrames();
  cable.update(frames);
  cableInk.update(frames);
  updateBands();

  updateCamera(dt, false);
  sun.position.set(bot.pos.x + 5, 12, bot.pos.z + 4);
  sun.target.position.copy(bot.pos);

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
    const blink = low && !unplugged;
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
  renderer.render(scene, camera);
});
