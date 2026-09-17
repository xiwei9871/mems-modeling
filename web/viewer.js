import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const app = document.getElementById("app");
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.8;
app.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x24282f);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.4;

const camera = new THREE.PerspectiveCamera(32, innerWidth / innerHeight, 0.1, 2000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.06;

const keyLight = new THREE.DirectionalLight(0xffffff, 1.5);
keyLight.position.set(30, -40, 70);
scene.add(keyLight);
scene.add(new THREE.AmbientLight(0xffffff, 0.18));

const manifest = await (await fetch("./manifest.json")).json();
const gltf = await new GLTFLoader().loadAsync("./" + manifest.glb);
const model = gltf.scene;
scene.add(model);

// darken materials that wash out under the env light (housing, battery wrap)
const DARKEN = { DarkGrayAnodized: 0.42, BatteryGray: 0.72 };
const matCache = {};
const GHOST = new THREE.MeshStandardMaterial({
  color: 0x4a5058, transparent: true, opacity: 0.14,
  depthWrite: false, roughness: 0.9 });

// part grouping: object name -> part entry
const partOf = {};
for (const p of manifest.parts)
  for (const n of p.objects) partOf[n] = p;

const homePos = new Map();
const nodes = {};
model.traverse((node) => {
  if (!node.name) return;
  nodes[node.name] = node;
  const p = partOf[node.name];
  if (p) node.userData.partId = p.id;
  homePos.set(node, node.position.clone());
  if (node.isMesh && node.material) {
    const k = node.material.name;
    if (DARKEN[k]) {
      if (!matCache[k]) {
        matCache[k] = node.material.clone();
        matCache[k].color.multiplyScalar(DARKEN[k]);
      }
      node.material = matCache[k];
    }
    node.userData.origMat = node.material;
  }
});

const lidSet = new Set(manifest.lid_hide);
const partVisible = {};
let curShot = manifest.shots[0];
let explodeK = 0;
let camTween = null;
let playing = false;
let playTimer = null;

const shotsEl = document.getElementById("shots");
const partsEl = document.getElementById("parts");
const titleEl = document.getElementById("shotTitle");
const subEl = document.getElementById("shotSub");
const explodeEl = document.getElementById("explode");
const playEl = document.getElementById("play");

function subjectSet(shot) {
  const s = new Set();
  for (const pid of shot.subjects || [])
    for (const p of manifest.parts)
      if (p.id === pid) for (const n of p.objects) s.add(n);
  for (const pref of shot.objects || [])
    for (const n of Object.keys(nodes))
      if (n.startsWith(pref)) s.add(n);
  return s;
}

function applyState() {
  const mode = curShot.mode || "full";
  const subj = subjectSet(curShot);
  const lidHidden = curShot.hide_lid;
  for (const p of manifest.parts) {
    const vis = partVisible[p.id] !== false;
    for (const n of p.objects) {
      const node = nodes[n];
      if (!node) continue;
      const isSubj = mode === "full" || subj.has(n);
      node.visible = vis && !(lidHidden && lidSet.has(n)) &&
                     (mode !== "isolate" || isSubj);
      const home = homePos.get(node);
      if (home) {
        const e = p.explode;
        node.position.set(
          home.x + e[0] * explodeK,
          home.y + e[2] * explodeK,   // blender z -> glTF y
          home.z - e[1] * explodeK);  // blender y -> glTF -z
      }
      // GLTF splits multi-material objects into Group + child meshes —
      // ghost/swap every mesh under this object node
      node.traverse((c) => {
        if (c.isMesh)
          c.material = (mode === "dim" && !isSubj) ? GHOST
                                                   : c.userData.origMat;
      });
    }
  }
}

function flyTo(shot) {
  camTween = {
    t0: performance.now(), dur: 800,
    fromPos: camera.position.clone(), toPos: new THREE.Vector3(...shot.pos),
    fromTgt: controls.target.clone(), toTgt: new THREE.Vector3(...shot.target),
  };
}

function gotoShot(shot) {
  curShot = shot;
  explodeK = shot.explode || 0;
  explodeEl.value = Math.round(explodeK * 100);
  applyState();
  flyTo(shot);
  titleEl.textContent = shot.title;
  subEl.textContent = shot.desc || manifest.subtitle;
  [...shotsEl.children].forEach((b) =>
    b.classList.toggle("active", b.dataset.id === shot.id));
}

for (const shot of manifest.shots) {
  const b = document.createElement("button");
  b.textContent = shot.title;
  b.dataset.id = shot.id;
  b.onclick = () => { stopPlay(); gotoShot(shot); };
  shotsEl.appendChild(b);
}

for (const p of manifest.parts) {
  const b = document.createElement("button");
  b.textContent = `${p.name} · ${p.objects.length}`;
  b.onclick = () => {
    partVisible[p.id] = partVisible[p.id] === false;
    b.classList.toggle("off", partVisible[p.id] === false);
    applyState();
  };
  partsEl.appendChild(b);
}

explodeEl.oninput = () => { explodeK = explodeEl.value / 100; applyState(); };

function stopPlay() {
  playing = false;
  playEl.textContent = "▶ story";
  if (playTimer) { clearInterval(playTimer); playTimer = null; }
}
playEl.onclick = () => {
  if (playing) { stopPlay(); return; }
  playing = true;
  playEl.textContent = "⏸ story";
  playTimer = setInterval(() => {
    const i = manifest.shots.indexOf(curShot);
    gotoShot(manifest.shots[(i + 1) % manifest.shots.length]);
  }, 4500);
};

const clock = new THREE.Clock();
function tick() {
  requestAnimationFrame(tick);
  clock.getDelta();
  if (camTween) {
    const k = Math.min(1, (performance.now() - camTween.t0) / camTween.dur);
    const e = 1 - Math.pow(1 - k, 3);
    camera.position.lerpVectors(camTween.fromPos, camTween.toPos, e);
    controls.target.lerpVectors(camTween.fromTgt, camTween.toTgt, e);
    if (k >= 1) camTween = null;
  }
  controls.update();
  renderer.render(scene, camera);
}
gotoShot(manifest.shots[0]);
tick();

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
