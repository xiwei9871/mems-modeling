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
scene.add(new THREE.AmbientLight(0xffffff, 0.25));

const manifest = await (await fetch("./manifest.json")).json();
const gltf = await new GLTFLoader().loadAsync("./" + manifest.glb);
const model = gltf.scene;
scene.add(model);

// part grouping: object name -> part entry
const partOf = {};
for (const p of manifest.parts)
  for (const n of p.objects) partOf[n] = p;

const homePos = new Map();   // object -> assembled local position
const nodes = {};
model.traverse((node) => {
  if (!node.name) return;
  nodes[node.name] = node;
  const p = partOf[node.name];
  if (p) {
    node.userData.partId = p.id;
    node.userData.partName = p.name;
  }
  if (node.isMesh || node.isObject3D) homePos.set(node, node.position.clone());
});

const lidSet = new Set(manifest.lid_hide);
const partVisible = {};      // user toggles
let curShot = manifest.shots[0];
let explodeK = 0;
let camTween = null;

const shotsEl = document.getElementById("shots");
const partsEl = document.getElementById("parts");
const titleEl = document.getElementById("shotTitle");
const subEl = document.getElementById("shotSub");
const explodeEl = document.getElementById("explode");

function applyState() {
  const lidHidden = curShot.hide_lid;
  for (const p of manifest.parts) {
    const vis = partVisible[p.id] !== false;
    for (const n of p.objects) {
      const node = nodes[n];
      if (!node) continue;
      node.visible = vis && !(lidHidden && lidSet.has(n));
      const home = homePos.get(node);
      if (home) {
        const e = p.explode;
        node.position.set(
          home.x + e[0] * explodeK,
          home.y + e[2] * explodeK,   // blender z -> glTF y
          home.z - e[1] * explodeK);  // blender y -> glTF -z
      }
    }
  }
}

function flyTo(shot) {
  camTween = {
    t0: performance.now(), dur: 700,
    fromPos: camera.position.clone(), toPos: new THREE.Vector3(...shot.pos),
    fromTgt: controls.target.clone(), toTgt: new THREE.Vector3(...shot.target),
  };
}

function gotoShot(shot) {
  curShot = shot;
  applyState();
  flyTo(shot);
  titleEl.textContent = shot.title;
  subEl.textContent = manifest.subtitle;
  [...shotsEl.children].forEach((b) =>
    b.classList.toggle("active", b.dataset.id === shot.id));
}

for (const shot of manifest.shots) {
  const b = document.createElement("button");
  b.textContent = shot.title;
  b.dataset.id = shot.id;
  b.onclick = () => gotoShot(shot);
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
