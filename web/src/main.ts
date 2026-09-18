/**
 * V1 Interactive Digital Product — Sensor vertical slice.
 *
 * Boot: load GLB (semantic extras) + manifest -> SemanticRegistry -> wire
 * store / state machine / camera / materials / interaction.
 *
 * Flow (spec §61): Overview -> hover -> click system -> X-Ray locate ->
 * Inspect -> extraction + secondary explode -> free orbit -> Back -> exact
 * restoration. Manual interaction and the chapter rail share the same state
 * machine (§45).
 */

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { ExperienceStore } from './experience-store';
import { SemanticRegistry, Manifest, SemanticEntity } from './semantic-registry';
import { TransitionManager } from './transition-manager';
import { CameraController, UNIT } from './camera-controller';
import { MaterialStateManager } from './material-state-manager';
import { ExperienceStateMachine } from './state-machine';
import { InteractionController } from './interaction-controller';

const canvas = document.getElementById('view') as HTMLCanvasElement;
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.localClippingEnabled = true; // fixture open-top cutaway (inspection)
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.95;
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111417);

// Studio environment: soft PBR reflections without an external HDRI file.
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.5;

const camera = new THREE.PerspectiveCamera(
  40,
  window.innerWidth / window.innerHeight,
  0.01,
  50,
);

// restrained studio rig: key + rim so graphite parts keep readable edges
const key = new THREE.DirectionalLight(0xffffff, 1.2);
key.position.set(0.6, 1.1, 0.8);
scene.add(key);
const rim = new THREE.DirectionalLight(0xbfd4ff, 0.7);
rim.position.set(-0.8, 0.6, -0.9);
scene.add(rim);
scene.add(new THREE.AmbientLight(0xffffff, 0.1));

// ground shadow-catcher: soft radial gradient disc under the product
const shadowTex = makeRadialShadowTexture();
const shadow = new THREE.Mesh(
  new THREE.PlaneGeometry(1.6, 1.6),
  new THREE.MeshBasicMaterial({
    map: shadowTex,
    transparent: true,
    depthWrite: false,
    opacity: 0.55,
  }),
);
shadow.rotation.x = -Math.PI / 2;
shadow.position.y = 0;
scene.add(shadow);

function makeRadialShadowTexture(): THREE.Texture {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const ctx = c.getContext('2d')!;
  const g = ctx.createRadialGradient(128, 128, 10, 128, 128, 128);
  g.addColorStop(0, 'rgba(0,0,0,0.85)');
  g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 256, 256);
  const tex = new THREE.CanvasTexture(c);
  return tex;
}

// ---------------------------------------------------------------------------

const store = new ExperienceStore();
const tweens = new TransitionManager();
let registry: SemanticRegistry;
let materials: MaterialStateManager;
let cameraCtl: CameraController;
let machine: ExperienceStateMachine;
let interaction: InteractionController;
let manifest: Manifest;
let extracted = new Set<string>();

async function boot(): Promise<void> {
  manifest = (await (await fetch('./manifest_v1.json')).json()) as Manifest;

  const gltf = await new GLTFLoader().loadAsync('./' + manifest.glb);
  const root = gltf.scene;
  root.scale.setScalar(UNIT); // GLB ships cm -> render in meters
  scene.add(root);
  root.updateMatrixWorld(true);

  // PCB presentation components become real children of CMP_MAIN_PCB so they
  // ride along when the board moves (logical parent, spec §22).
  let board: THREE.Object3D | undefined;
  const compNodes: THREE.Object3D[] = [];
  root.traverse((n) => {
    const ud = n.userData as { semanticId?: string; logicalParent?: string };
    if (ud.semanticId === 'CMP_MAIN_PCB') board = n;
    if (ud.logicalParent) compNodes.push(n);
  });
  if (board) for (const n of compNodes) board.attach(n);

  registry = new SemanticRegistry(root, manifest);
  const problems = registry.validate();
  if (problems.length) console.error('semantic registry:', problems);

  materials = new MaterialStateManager(tweens);
  cameraCtl = new CameraController(camera, canvas, tweens, manifest.cameraPresets);
  machine = new ExperienceStateMachine(store, registry, materials, cameraCtl, tweens);
  interaction = new InteractionController(canvas, camera, registry, materials, {
    onSelect: (entity) => void onSelect(entity),
    onInspect: (entity) => void onInspect(entity),
  });
  interaction.refreshPickables(root);

  cameraCtl.jumpTo('overviewHero');
  store.set({ ready: true, mode: 'overview', cameraPreset: 'overviewHero' });
  buildRail();
  hud('ready');

  // debug hook (spec §43): ?debug=1 surface + console introspection
  (window as unknown as { __app: object }).__app = {
    THREE, scene, camera, cameraCtl, registry, store, machine, tweens,
  };
}

function onSelect(entity: SemanticEntity): void {
  const st = store.get();
  if (st.mode === 'inspection') {
    // inside inspection: cores toggle a secondary extraction (spec §21)
    if (entity.sourcePart && entity.systemId === st.focusedSystem) {
      const id = entity.sourcePart;
      if (entity.inspectable && entity.id === 'CMP_ADXL_SENSOR') {
        if (extracted.has(id)) extracted.delete(id);
        else extracted.add(id);
        void machine.toggleComponentExtract(id, extracted.has(id));
        hud(entity.displayName + (extracted.has(id) ? ' — extracted' : ''));
      } else {
        hud(entity.displayName);
      }
    }
    return;
  }
  store.set({ selectedComponent: entity.id });
  hud(entity.displayName);
  // overview = look-only; structure exploration starts in architecture mode
  if ((st.mode === 'architecture' || st.mode === 'xray') &&
      entity.systemId && entity.inspectable)
    void enterContext(entity.systemId);
}

function onInspect(entity: SemanticEntity): void {
  // overview is look-only: dblclick-inspect is armed in structure views only
  const m = store.get().mode;
  if (entity.systemId && (m === 'architecture' || m === 'xray' || m === 'inspection'))
    void machine.setMode('inspection', entity.systemId);
}

/** Click a system: first show WHERE it is (x-ray locate), spec §13/§18. */
async function enterContext(systemId: string): Promise<void> {
  store.set({ mode: 'xray', focusedSystem: systemId, xrayEnabled: true, xraySystem: systemId });
  void cameraCtl.goTo(`${systemId}.context`, 1.0);
  const sysParts = new Set(registry.system(systemId)!.parts);
  for (const e of registry.components()) {
    const isSystem = sysParts.has(e.sourcePart ?? '');
    const isShell = e.role === 'SECONDARY';
    materials.setLevel(
      e.object3D,
      isSystem ? 'FOCUS' : isShell ? 'XRAY' : 'DISTANT',
      0.7,
    );
  }
  // INSPECT only makes sense when the focused system has moving parts
  // (SYS_TRANSMISSION is FX-only — nothing to stage).
  inspectBtn.style.display =
    registry.system(systemId)!.parts.length ? 'block' : 'none';
}

function buildRail(): void {
  const rail = document.getElementById('rail')!;
  rail.innerHTML = '';
  const items: [string, string, () => void][] = [
    ['01', 'Overview', () => backToOverview()],
    ['02', 'Architecture', () => void machine.setMode('architecture')],
    ['03', 'Sensing', () => void inspectSystem('SYS_SENSOR')],
    ['04', 'Acquisition', () => void inspectSystem('SYS_ACQUISITION')],
    ['05', 'Power', () => void inspectSystem('SYS_POWER')],
    ['06', 'Transmission', () => void focusTransmission()],
  ];
  for (const [num, label, fn] of items) {
    const b = document.createElement('button');
    b.className = 'rail-btn';
    b.innerHTML = `<span class="num">${num}</span>${label}`;
    b.onclick = fn;
    rail.appendChild(b);
  }
}

/** Transmission chapter: the device stays assembled & opaque like overview —
 *  only the antenna + on-board radio module get focus, plus the arc FX. */
async function focusTransmission(): Promise<void> {
  store.set({
    mode: 'xray',
    focusedSystem: 'SYS_TRANSMISSION',
    xrayEnabled: false,
    xraySystem: null,
    selectedComponent: null,
  });
  void cameraCtl.goTo('SYS_TRANSMISSION.context', 1.0);
  await machine.reassemble(1.0);
  // a narrow x-ray window: only the HANDLE turns translucent — the antenna is
  // sealed inside its left leg (internal antenna = waterproofing); the rest
  // of the device stays opaque like overview
  // a narrow x-ray window: the BODY SHELL turns translucent so the
  // module -> coax -> puck antenna chain reads through the enclosure
  {
    const spec = registry.componentSpec('PRT_BODY');
    const e = spec && registry.get(spec.semanticId);
    if (e) materials.setLevel(e.object3D, 'XRAY', 0.8);
  }
  // subtle emissive lift marks the two radio parts
  for (const id of ['CMP_RADIO_ANTENNA', 'CMP_RADIO_MODULE']) {
    const e = registry.get(id);
    if (e) materials.setHover(e.object3D, true);
  }
}

/** Chapter click = straight to inspection layout (spec-rework: the staged
 *  sequence inside enterInspection already shows the locate/x-ray beat). */
async function inspectSystem(sys: string): Promise<void> {
  await machine.setMode('inspection', sys);
  // auto-extracted parts (fixture-released cores) are marked so a click
  // toggles them back IN rather than double-popping
  for (const [pid, spec] of Object.entries(manifest.components))
    if (spec.systemId === sys && spec.extractDirection) extracted.add(pid);
}

const inspectBtn = document.getElementById('inspect-btn') as HTMLButtonElement;
inspectBtn.onclick = () => {
  const sys = store.get().focusedSystem;
  if (sys) void machine.setMode('inspection', sys);
};

const backBtn = document.getElementById('back-btn') as HTMLButtonElement;
backBtn.onclick = () => backToOverview();

function backToOverview(): void {
  extracted.clear();
  inspectBtn.style.display = 'none';
  void machine.setMode('overview');
}

function hud(text: string): void {
  const el = document.getElementById('hud');
  if (el) el.textContent = text;
}

// reflect mode in the UI chrome
store.subscribe((s, prev) => {
  if (s.mode === prev.mode && s.focusedSystem === prev.focusedSystem) return;
  backBtn.style.display = s.mode === 'overview' ? 'none' : 'block';
  interaction?.clearHover();
  interaction?.refreshPickables(scene);
  const sys = s.focusedSystem ? registry?.system(s.focusedSystem) : undefined;
  inspectBtn.style.display =
    s.mode === 'xray' && sys && sys.parts.length ? 'block' : 'none';
  // transmission chapter: antenna -> cloud signal path rendered in-scene
  window.clearTimeout(txTimer);
  if (s.focusedSystem === 'SYS_TRANSMISSION' && s.mode !== 'overview')
    txTimer = window.setTimeout(buildTxFX, 1100);
  else clearTxFX();
  hud(
    s.mode === 'inspection' && sys
      ? s.focusedSystem === 'SYS_TRANSMISSION'
        ? `${sys.displayName} — modem to puck antenna to cloud`
        : `${sys.displayName} — orbit freely, click a core to extract`
      : s.mode === 'xray' && sys
        ? s.focusedSystem === 'SYS_TRANSMISSION'
          ? `${sys.displayName} — field data leaves the device here`
          : `${sys.displayName} — inside the device`
        : '',
  );
});

// ---------------------------------------------------------------------------

function resize(): void {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}
window.addEventListener('resize', resize);
resize();

// ---- transmission data-path FX ---------------------------------------------
// module -> antenna -> cloud, told with icons + motion only (no text):
// blinking activity dot on the radio module, feed-line pulses into the antenna,
// expanding broadcast rings + wifi glyph above the handle, dashed arc carrying
// pulse packets into a cloud node.

let txGroup: THREE.Group | null = null;
let txCurve: THREE.QuadraticBezierCurve3 | null = null;
let txFeed: THREE.QuadraticBezierCurve3 | null = null;
let txPulses: THREE.Mesh[] = [];
let txFeedPulses: THREE.Mesh[] = [];
let txRings: THREE.Mesh[] = [];
let txDot: THREE.Mesh | null = null;
let txT = 0;
let txTimer = 0;

function iconSprite(draw: (g: CanvasRenderingContext2D) => void): THREE.Sprite {
  const c = document.createElement('canvas');
  c.width = 256; c.height = 256;
  draw(c.getContext('2d')!);
  return new THREE.Sprite(new THREE.SpriteMaterial({
    map: new THREE.CanvasTexture(c), transparent: true, depthTest: false,
  }));
}

function wifiSprite(): THREE.Sprite {           // classic wifi glyph: dot + 3 arcs
  const sp = iconSprite((g) => {
    g.strokeStyle = 'rgba(140,210,255,0.95)';
    g.fillStyle = 'rgba(140,210,255,0.95)';
    g.lineWidth = 15; g.lineCap = 'round';
    for (const r of [48, 84, 120]) {
      g.beginPath(); g.arc(128, 196, r, Math.PI * 1.25, Math.PI * 1.75); g.stroke();
    }
    g.beginPath(); g.arc(128, 190, 15, 0, Math.PI * 2); g.fill();
  });
  sp.scale.set(0.028, 0.028, 1);
  return sp;
}

function cloudSprite(): THREE.Sprite {          // cloud glyph + upload arrow
  const sp = iconSprite((g) => {
    g.fillStyle = 'rgba(232,238,244,0.96)';
    const puff = (x: number, y: number, r: number) => {
      g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
    };
    puff(82, 140, 38); puff(128, 112, 50); puff(180, 136, 40); puff(130, 158, 44);
    g.strokeStyle = 'rgba(64,96,128,0.9)';
    g.lineWidth = 13; g.lineCap = 'round'; g.lineJoin = 'round';
    g.beginPath(); g.moveTo(128, 164); g.lineTo(128, 118); g.stroke();
    g.beginPath(); g.moveTo(108, 140); g.lineTo(128, 118); g.lineTo(148, 140); g.stroke();
  });
  sp.scale.set(0.05, 0.05, 1);
  return sp;
}

function clearTxFX(): void {
  if (txGroup) { scene.remove(txGroup); txGroup = null; }
  txPulses = []; txFeedPulses = []; txRings = [];
  txCurve = null; txFeed = null; txDot = null;
  for (const id of ['CMP_RADIO_ANTENNA', 'CMP_RADIO_MODULE']) {
    const e = registry?.get(id);
    if (e) {
      materials.setHover(e.object3D, false);
      materials.restore(e.object3D, 0.4);
    }
  }
}

function buildTxFX(): void {
  clearTxFX();
  const ant = registry.get('CMP_RADIO_ANTENNA');
  const mod = registry.get('CMP_RADIO_MODULE');
  if (!ant) return;
  const g = new THREE.Group();
  g.name = 'TX_FLOW';

  const tip = ant.object3D.getWorldPosition(new THREE.Vector3())
    .add(new THREE.Vector3(0, 0.02, 0));
  const cloudPos = tip.clone().add(new THREE.Vector3(0.11, 0.12, -0.04));
  const ctrl = tip.clone().lerp(cloudPos, 0.45).add(new THREE.Vector3(0, 0.08, 0));
  txCurve = new THREE.QuadraticBezierCurve3(tip, ctrl, cloudPos);

  const line = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(txCurve.getPoints(72)),
    new THREE.LineDashedMaterial({
      color: 0x6fc8ff, dashSize: 0.005, gapSize: 0.003,
      transparent: true, opacity: 0.85,
    }),
  );
  line.computeLineDistances();
  g.add(line);

  const pg = new THREE.SphereGeometry(0.0018, 12, 12);
  const pm = new THREE.MeshBasicMaterial({ color: 0xa8e2ff });
  for (let i = 0; i < 5; i++) {
    const m = new THREE.Mesh(pg, pm);
    g.add(m); txPulses.push(m);
  }

  const cloud = cloudSprite();
  cloud.position.copy(cloudPos);
  g.add(cloud);

  // broadcast: expanding horizontal rings + wifi glyph above the handle
  const ringGeo = new THREE.RingGeometry(0.005, 0.0065, 48);
  const ringBase = tip.clone().add(new THREE.Vector3(0, 0.03, 0));
  for (let i = 0; i < 3; i++) {
    const r = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({
      color: 0x8cd2ff, transparent: true, opacity: 0.8,
      side: THREE.DoubleSide, depthWrite: false,
    }));
    r.rotation.x = -Math.PI / 2;
    r.position.copy(ringBase);
    g.add(r); txRings.push(r);
  }
  const wifi = wifiSprite();
  wifi.position.copy(ringBase).add(new THREE.Vector3(0, 0.036, 0));
  g.add(wifi);
  materials.setHover(ant.object3D, true);

  // feed: module -> antenna base, short dashed hop + blink on the module
  if (mod) {
    const mp = mod.object3D.getWorldPosition(new THREE.Vector3())
      .add(new THREE.Vector3(0, 0.01, 0));
    const feedBase = tip.clone().add(new THREE.Vector3(0, -0.008, 0));
    txFeed = new THREE.QuadraticBezierCurve3(
      mp, mp.clone().lerp(feedBase, 0.5).add(new THREE.Vector3(0, 0.035, 0)), feedBase,
    );
    const fl = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(txFeed.getPoints(32)),
      new THREE.LineDashedMaterial({
        color: 0x6fc8ff, dashSize: 0.005, gapSize: 0.003,
        transparent: true, opacity: 0.6,
      }),
    );
    fl.computeLineDistances();
    g.add(fl);
    for (let i = 0; i < 3; i++) {
      const m = new THREE.Mesh(pg, pm.clone());
      g.add(m); txFeedPulses.push(m);
    }
    txDot = new THREE.Mesh(
      new THREE.SphereGeometry(0.0022, 12, 12),
      new THREE.MeshBasicMaterial({ color: 0x9fdcff, transparent: true }),
    );
    txDot.position.copy(mp);
    g.add(txDot);
    materials.setHover(mod.object3D, true);
  }

  scene.add(g);
  txGroup = g;
}

renderer.setAnimationLoop(() => {
  tweens.update();
  cameraCtl?.update();
  if (txGroup) {
    txT += 0.008;
    if (txCurve) {
      txPulses.forEach((m, i) => {
        const t = (txT + i / txPulses.length) % 1;
        m.position.copy(txCurve!.getPointAt(t));
      });
    }
    if (txFeed) {
      txFeedPulses.forEach((m, i) => {
        const t = (txT * 1.25 + i / txFeedPulses.length) % 1;
        m.position.copy(txFeed!.getPointAt(t));
      });
    }
    txRings.forEach((r, i) => {
      const t = (txT * 0.45 + i / txRings.length) % 1;
      r.scale.setScalar(1 + t * 3.4);
      (r.material as THREE.MeshBasicMaterial).opacity = (1 - t) * 0.75;
      r.position.y += 0;
    });
    if (txDot) {
      (txDot.material as THREE.MeshBasicMaterial).opacity =
        0.35 + 0.65 * Math.abs(Math.sin(txT * 22));
    }
  }
  renderer.render(scene, camera);
});

void boot();
