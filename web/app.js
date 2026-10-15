import * as THREE from './vendor/three.module.js';
import { MapControls } from './vendor/MapControls.js';

// Colours are authored in sRGB and drawn as they are.
THREE.ColorManagement.enabled = false;

const SKY = '#e4e8ea';
const LAND = '#f4f3ef';
const WATER = '#a9bccb';
const MAQUETTE = '#efeee9';
const GROUP_COLORS = ['#c8102e', '#1f4e8c', '#d99a12', '#2e8b57', '#7b3fa0', '#00909a', '#8c5a2b', '#d6336c'];
const MAX_GROUPS = GROUP_COLORS.length;
const ATTR_W = 256;
const WORKERS = Math.min(4, navigator.hardwareConcurrency || 2);
const MODE = { period: 0, floors: 1, layers: 2 };

const [config, layers, attrBuf] = await Promise.all([
  fetch('data/city.json').then(r => r.json()),
  fetch('data/layers.json').then(r => r.json()),
  fetch('data/attrs.bin').then(r => r.arrayBuffer()),
]);
const attrs = new DataView(attrBuf);
const periods = config.periods;

// ---------- Language ----------
// The viewer is in Russian; the walk module speaks through t() like the other cities' viewers.
const LANG = 'ru';
const RU = {
 "As many as fit": "Сколько поместится",
 "Back to the start": "С возвратом",
 "Cancel": "Отмена",
 "Change": "Изменить",
 "Choose what interests you, where you start and how far you want to go. The walk links the buildings with stories on the way.": "Выберите, что вам интересно, откуда начать и как далеко идти. Маршрут свяжет дома с историями по пути.",
 "Click the map where the walk should start.": "Нажмите на карту там, где начать прогулку.",
 "Close": "Закрыть",
 "From the graph": "Из графа", "Back to the graph": "Назад к графу", "Generate a walk": "Построить прогулку", "Graph": "Граф",
 "Download the walk with its stories (KML), for Google My Maps: Create a new map, then Import.": "Скачать прогулку с историями (KML) для Google Мои карты: создайте карту и выберите «Импорт».",
 "Fewer stops than asked: that is all the stories you chose.": "Остановок меньше, чем просили: других историй по выбранным темам нет.",
 "Google Maps takes nine stops; the paler ones lie on the way.": "Google Карты принимают девять точек; бледные остановки лежат по пути.",
 "How far": "Как далеко",
 "How many stops": "Сколько остановок",
 "Lived or worked here": "Жил или работал здесь",
 "Longer than asked: few of the stories you chose lie that close.": "Длиннее, чем просили: выбранных историй рядом мало.",
 "Make my walk": "Построить прогулку",
 "No stories within reach. Try a longer walk or more interests.": "Рядом нет историй. Попробуйте длиннее или больше тем.",
 "Nothing chosen: the walk takes every story.": "Ничего не выбрано: в прогулку войдут все истории.",
 "One way": "В одну сторону",
 "Open in Google Maps": "Открыть в Google Картах",
 "Pick on the map": "Выбрать на карте",
 "Plan a walk": "Прогулка",
 "Point on the map": "Точка на карте",
 "Shorter than asked: the stories you chose lie close together.": "Короче, чем просили: выбранные истории близко друг к другу.",
 "Source": "Источник",
 "Start": "Старт",
 "Start from where you are: share your location, or choose a start below.": "Начните оттуда, где вы сейчас: поделитесь местоположением или выберите старт ниже.",
 "Straight lines on the map; Google Maps shows the walking route.": "На карте прямые линии; пешеходный маршрут покажут Google Карты.",
 "The location was not shared. Pick a start on the map instead.": "Местоположение не получено. Выберите старт на карте.",
 "This browser does not share its location.": "Этот браузер не сообщает местоположение.",
 "What interests you": "Что интересно",
 "Where you start": "Откуда",
 "You seem to be outside the city, so the walk starts at {s}.": "Похоже, вы не в городе, поэтому прогулка начнётся от точки «{s}».",
 "Your location": "Ваше местоположение",
 "Your point": "Ваша точка",
 "Your walk": "Ваша прогулка",
 "about {m} min": "около {m} мин",
 "Share my location": "Поделиться местоположением",
 "Asking for your location…": "Запрашиваем местоположение…",
 "Generate a walk": "Построить прогулку",
 "Buildings today": "Здания сегодня",
 "All layers": "Все слои",
 "Storeys": "Этажность",
 "A hint may help.": "Подсказка может помочь.",
 "Any of {n} buildings counts.": "Подойдёт любое из {n} зданий.",
 "Best": "Лучший результат",
 "Continue": "Продолжить",
 "Found!": "Найдено!",
 "Hint": "Подсказка",
 "Next riddle": "Следующая загадка",
 "Not this one, but very close.": "Не то, но совсем рядом.",
 "Not this one. Far off.": "Не то. Далеко.",
 "Not this one. Still a few streets away.": "Не то. Ещё несколько улиц.",
 "Not this one. You are getting warm.": "Не то. Уже теплее.",
 "One of the buildings that answer the riddle.": "Одно из зданий, которые подходят под загадку.",
 "Open the layer": "Открыть слой",
 "Photo": "Фото",
 "Play again": "Ещё раз",
 "Quest complete": "Квест пройден",
 "Quests": "Квесты",
 "Riddles hidden in the city. Find each building on the map, using its colours and layers, and click it. Every riddle is worth three tiles; hints cost one.": "Загадки, спрятанные в городе. Найдите каждое здание на карте с помощью её цветов и слоёв и нажмите на него. Загадка стоит три очка, подсказка отнимает одно.",
 "Right": "Верно",
 "See all quests": "Все квесты",
 "Show me": "Показать",
 "Shown, not found: no tiles.": "Показано, а не найдено: без очков.",
 "Today’s photo of the building to find": "Сегодняшнее фото здания, которое нужно найти",
 "Without a single hint.": "Без единой подсказки.",
 "Your tiles": "Ваши очки",
 "Easy": "Лёгкий",
 "Medium": "Средний",
 "Hard": "Трудный",
 "Colour by period": "Раскрасить по эпохам",
 "Colour by floors": "Раскрасить по этажности",
 "Colour by energy label": "Раскрасить по энергометкам"
};
const t = s => RU[s] || s;
const tr = (o, k) => o?.[k];
const L10 = o => o?.ru || o?.en || '';

// ---------- Scene ----------
const canvas = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setClearColor(SKY);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, 5, 60000);
const controls = new MapControls(camera, canvas);
controls.enableDamping = true;
// Left drag turns and tilts the city; right drag, or Shift with the left, moves it.
controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
controls.rotateSpeed = 0.6;
controls.maxPolarAngle = Math.PI * 0.47;
controls.minDistance = 60;
controls.maxDistance = 30000;

function goHome() {
  const h = config.home, az = THREE.MathUtils.degToRad(h.azimuth), el = THREE.MathUtils.degToRad(h.elevation);
  const d = h.span * 0.9;
  controls.target.set(h.x, 0, h.z);
  camera.position.set(h.x + d * Math.cos(el) * Math.sin(az), d * Math.sin(el), h.z + d * Math.cos(el) * Math.cos(az));
  controls.update();
}
goHome();

// Land and water: flat polygons in the local frame (see pipeline/s04_water.py).
async function loadPolygons(url) {
  const buf = await (await fetch(url)).arrayBuffer();
  const [nPoly, nRing, nVert] = new Uint32Array(buf, 0, 3);
  const ringStart = new Uint32Array(buf, 12, nPoly + 1);
  const vertStart = new Uint32Array(buf, 12 + 4 * (nPoly + 1), nRing + 1);
  const xz = new Float32Array(buf, 12 + 4 * (nPoly + 1) + 4 * (nRing + 1), 2 * nVert);
  const ring = r => {
    const pts = [];
    for (let v = vertStart[r]; v < vertStart[r + 1]; v++) pts.push(new THREE.Vector2(xz[2 * v], -xz[2 * v + 1]));
    return pts;
  };
  const shapes = [];
  for (let p = 0; p < nPoly; p++) {
    const shape = new THREE.Shape(ring(ringStart[p]));
    for (let r = ringStart[p] + 1; r < ringStart[p + 1]; r++) shape.holes.push(new THREE.Path(ring(r)));
    shapes.push(shape);
  }
  const g = new THREE.ShapeGeometry(shapes);
  g.rotateX(-Math.PI / 2);
  return g;
}
const flat = new THREE.Group();
scene.add(flat);
const [landGeo, waterGeo] = await Promise.all([loadPolygons('data/land.bin'), loadPolygons('data/water.bin')]);
const land = new THREE.Mesh(landGeo, new THREE.MeshBasicMaterial({ color: LAND }));
const water = new THREE.Mesh(waterGeo, new THREE.MeshBasicMaterial({ color: WATER }));
land.position.y = -0.05;
water.position.y = -0.4;
flat.add(land, water);

// ---------- Street and canal names ----------
// Flat on the ground, turned along the street (pipeline/s07_labels.py). Textures are drawn on first use.
const labelData = await fetch('data/labels.json').then(r => r.json());
const labelGroup = new THREE.Group();
scene.add(labelGroup);
const labelTex = new Map();
const LABEL_PX = 64;
function textureFor(L) {
  let t = labelTex.get(L.name + L.water);
  if (t) return t;
  const c = document.createElement('canvas'), ctx = c.getContext('2d');
  const font = `${L.water ? 'italic 500' : '700'} ${LABEL_PX * 0.62}px "Onest", sans-serif`;
  ctx.font = font;
  c.width = Math.ceil(ctx.measureText(L.name).width + LABEL_PX * 0.4);
  c.height = LABEL_PX;
  ctx.font = font;
  ctx.textBaseline = 'middle';
  ctx.lineWidth = LABEL_PX * 0.12;
  ctx.strokeStyle = L.water ? 'rgba(200,214,213,0.95)' : 'rgba(250,249,246,0.95)';
  ctx.fillStyle = L.water ? '#1f4f5e' : '#25292c';
  ctx.strokeText(L.name, LABEL_PX * 0.2, LABEL_PX / 2);
  ctx.fillText(L.name, LABEL_PX * 0.2, LABEL_PX / 2);
  t = new THREE.CanvasTexture(c);
  t.anisotropy = 4;
  t.userData = { aspect: c.width / c.height };
  labelTex.set(L.name + L.water, t);
  return t;
}
const labelPlane = new THREE.PlaneGeometry(1, 1);
const labels = labelData.flatMap(L => L.pts.map(([x, z, ang, len]) => ({ L, x, z, ang, len, mesh: null })))
  .sort((a, b) => a.L.tier - b.L.tier || b.len - a.len);
function updateLabels(dist) {
  const flipLabels = Math.abs(controls.getAzimuthalAngle()) > Math.PI / 2;
  if (!document.fonts.check('700 16px "Onest"')) return;
  // Label height in metres, roughly constant on screen; the canals and main streets read larger.
  // Names appear only up close: rivers, canals and the main avenues from 4.5 km, other streets from 1.3 km.
  const h1 = THREE.MathUtils.clamp(dist * 0.014, 6, 45), h2 = THREE.MathUtils.clamp(dist * 0.011, 4, 14);
  const near = Math.max(900, dist * 1.1), far = Math.max(3000, dist * 1.8);
  const TIER1_FROM = 4500, TIER2_FROM = 1300;
  // Greedy collision: canals and main streets first, then the longest stretches; a label is dropped
  // when an accepted one already sits within a few label heights of it.
  const taken = new Map(), C = h1 * 5; // one grid, cells as wide as the largest separation
  const cellOf = (x, z) => `${Math.floor(x / C)},${Math.floor(z / C)}`;
  const clear = (l, sep) => {
    const cx = Math.floor(l.x / C), cz = Math.floor(l.z / C);
    for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) {
      for (const q of taken.get(`${cx + i},${cz + j}`) || []) if ((q.x - l.x) ** 2 + (q.z - l.z) ** 2 < sep * sep) return false;
    }
    return true;
  };
  for (const l of labels) {
    const d = Math.hypot(l.x - camera.position.x, l.z - camera.position.z);
    let show = d < (l.L.tier === 1 ? far : near) && dist < (l.L.tier === 1 ? TIER1_FROM : TIER2_FROM);
    const sep = (l.L.tier === 1 ? h1 : h2) * 5;
    if (show && !clear(l, sep)) show = false;
    if (show) {
      const key = cellOf(l.x, l.z);
      if (!taken.has(key)) taken.set(key, []);
      taken.get(key).push(l);
    }
    if (show && !l.mesh) {
      const tex = textureFor(l.L);
      l.mesh = new THREE.Mesh(labelPlane, new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false }));
      // Turn about the vertical first, then lay the plane flat.
      l.mesh.rotation.set(-Math.PI / 2, 0, 0, "YXZ");
      l.mesh.position.set(l.x, l.L.water ? 0.4 : 0.6, l.z);
      l.mesh.renderOrder = 2;
      labelGroup.add(l.mesh);
    }
    if (l.mesh) {
      const h = l.L.tier === 1 ? h1 : h2;
      const w = h * l.mesh.material.map.userData.aspect;
      // A name much longer than its stretch of street would spill over the buildings.
      if (show && w > l.len * 1.6 && l.L.tier === 2) show = false;
      l.mesh.visible = show;
      if (show) {
        l.mesh.scale.set(w, h, 1);
        // ang is measured towards +z; Y turns towards -z. Half a turn more when the camera faces south,
        // so names always read left to right on screen.
        l.mesh.rotation.y = THREE.MathUtils.degToRad(-l.ang) + (flipLabels ? Math.PI : 0);
      }
    }
  }
}

// ---------- Shared uniforms ----------
const col = c => new THREE.Color(c);
const FOCUS_MAX = 160;  // buildings a walk can light up at once
const uniforms = {
  uYear: { value: config.yearMax },
  uYearFrom: { value: config.yearMin - 1 },
  uMode: { value: MODE.period },
  uPalette: { value: periods.map(p => col(p.color)) },
  uMask: { value: periods.map(() => 1) },
  uGroupBit: { value: Array(MAX_GROUPS).fill(-1) },
  uGroupColor: { value: GROUP_COLORS.map(col) },
  uMaquette: { value: col(MAQUETTE) },
  uUnknownColor: { value: col(config.unknown.color) },
  uUnknown: { value: 1 },
  uHover: { value: -1 },
  uSelected: { value: -1 },
  uFocus: { value: Array(FOCUS_MAX).fill(-1) },
  uFocusGroup: { value: Array(FOCUS_MAX).fill(0) },
  uFocusN: { value: 0 },
  uFogColor: { value: col(SKY) },
  uFog: { value: new THREE.Vector2(9000, 26000) },
  uNow: { value: 0 },        // seconds, for tiles dropping in as they load
  uPlaying: { value: 0 },    // while the film plays buildings fly in rather than grow
  uRise: { value: 0.01 },    // years a building's entrance spans; only the film widens it
  // Search: one texel per building, lit (255) or not; while uPickOn is 1 the unlit ones dim.
  uPick: { value: null },
  uPickOn: { value: 0 },
};
const PICK_ROWS = Math.ceil(config.stats.buildings / ATTR_W);
const pickData = new Uint8Array(ATTR_W * PICK_ROWS);
const pickTex = new THREE.DataTexture(pickData, ATTR_W, PICK_ROWS, THREE.RedFormat, THREE.UnsignedByteType);
pickTex.needsUpdate = true;
uniforms.uPick.value = pickTex;

const VERT = /* glsl */`
  in float bld;
  uniform sampler2D uAttr;
  uniform float uYear, uYearFrom, uMode, uHover, uSelected, uNow, uBorn, uPlaying, uRise;
  uniform vec3 uPalette[${periods.length}];
  uniform float uMask[${periods.length}];
  uniform int uGroupBit[${MAX_GROUPS}];
  uniform float uFocus[${FOCUS_MAX}];
  uniform int uFocusGroup[${FOCUS_MAX}];
  uniform int uFocusN;
  uniform vec3 uGroupColor[${MAX_GROUPS}];
  uniform vec3 uMaquette, uUnknownColor;
  uniform float uUnknown;
  uniform sampler2D uPick;
  uniform float uPickOn;
  out vec3 vColor;
  out vec3 vWorld;
  out float vGid;

  vec3 floorsRamp(float f) {
    float t = clamp(log(f) / log(40.0), 0.0, 1.0);
    vec3 a = vec3(0.86, 0.89, 0.90), b = vec3(0.49, 0.66, 0.75), c = vec3(0.17, 0.36, 0.55), d = vec3(0.05, 0.10, 0.25);
    return t < 0.33 ? mix(a, b, t / 0.33) : t < 0.66 ? mix(b, c, (t - 0.33) / 0.33) : mix(c, d, (t - 0.66) / 0.34);
  }

  bool hasBit(vec4 words, int bit) {
    int w = bit / 16;
    float v = w == 0 ? words.x : w == 1 ? words.y : w == 2 ? words.z : words.w;
    return ((int(v + 0.5) >> (bit - w * 16)) & 1) == 1;
  }

  void main() {
    int i = int(bld + 0.5);
    ivec2 tc = ivec2(2 * (i % ${ATTR_W}), i / ${ATTR_W});
    vec4 a = texelFetch(uAttr, tc, 0);
    vec4 lay = texelFetch(uAttr, tc + ivec2(1, 0), 0);
    float year = a.x;
    int pf = int(a.y + 0.5);
    int period = min(pf % 16, ${periods.length - 1});
    int flag = pf / 16;
    vGid = a.w;
    bool unknown = flag == 5;
    bool filtered = uMode < 0.5 && (unknown ? uUnknown < 0.5 : uMask[period] < 0.5);
    float g = clamp((uYear - year + 1.0) / uRise, 0.0, 1.0);
    g = g * g * (3.0 - 2.0 * g);
    if (g <= 0.003 || (unknown && uYear < ${config.yearMax}.0) || filtered) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }

    // Entrances, only while the film plays and while tiles load: a building drops in from its own side of the
    // sky, the same side every time (seeded by its id). Filters and scrubbing change the city at once.
    vec3 p = position;
    float seed = fract(sin(a.w * 12.9898) * 43758.5453);
    float arrive = clamp((uNow - uBorn) / 0.9 - seed * 0.35, 0.0, 1.0);
    float fly = 1.0 - arrive;
    if (uPlaying > 0.5) fly = max(fly, 1.0 - g);
    if (fly > 0.0) {
      float e = fly * fly * fly;
      float ang = seed * 6.2831853;
      // positions are in decimetres: a few hundred metres sideways and up
      p += vec3(cos(ang), 0.0, sin(ang)) * (1800.0 + 1600.0 * fract(seed * 7.13)) * e;
      p.y += (2600.0 + 2400.0 * fract(seed * 3.71)) * e;
    }
    vec3 c;
    if (uMode < 0.5) {
      c = unknown ? uUnknownColor : uPalette[period];
      if (flag == 1 || flag == 2 || flag == 4) c = mix(c, uMaquette, 0.45);
    } else if (uMode < 1.5) {
      c = floorsRamp(a.z);
    } else {
      c = uMaquette;
      for (int g = 0; g < ${MAX_GROUPS}; g++) {
        if (uGroupBit[g] >= 0 && hasBit(lay, uGroupBit[g])) { c = uGroupColor[g]; break; }
      }
    }
    if (uFocusN > 0) {
      c = uMaquette;
      for (int k = 0; k < ${FOCUS_MAX}; k++) {
        if (k >= uFocusN) break;
        if (abs(vGid - uFocus[k]) < 0.5) { c = uGroupColor[uFocusGroup[k]]; break; }
      }
    }
    if (year <= uYearFrom) c = mix(c, uMaquette, 0.8);
    if (vGid == uHover || vGid == uSelected) c = mix(c, vec3(0.0), 0.35);
    if (uPickOn > 0.5) {
      int gi = int(vGid + 0.5);
      if (texelFetch(uPick, ivec2(gi % ${ATTR_W}, gi / ${ATTR_W}), 0).r < 0.5) c = mix(c, uMaquette, 0.78);
    }
    vColor = c;
    vec4 w = modelMatrix * vec4(p, 1.0);
    vWorld = w.xyz;
    gl_Position = projectionMatrix * viewMatrix * w;
  }
`;

const FRAG = /* glsl */`
  precision highp float;
  uniform vec3 uFogColor;
  uniform vec2 uFog;
  in vec3 vColor;
  in vec3 vWorld;
  in float vGid;
  out vec4 outColor;
  void main() {
    #ifdef PICK
      float id = vGid + 1.0;
      outColor = vec4(mod(id, 256.0), mod(floor(id / 256.0), 256.0), floor(id / 65536.0), 255.0) / 255.0;
    #else
      vec3 n = normalize(cross(dFdx(vWorld), dFdy(vWorld)));
      // Low afternoon sun from the south-west, a soft sky from above.
      float sun = max(dot(n, normalize(vec3(-0.55, 0.55, 0.62))), 0.0);
      float light = n.y > 0.9 ? 1.04 : 0.66 + 0.34 * sun;
      float foot = mix(0.82, 1.0, clamp(vWorld.y / 12.0, 0.0, 1.0));
      vec3 c = vColor * light * foot;
      float d = length(vWorld - cameraPosition);
      c = mix(c, uFogColor, smoothstep(uFog.x, uFog.y, d));
      outColor = vec4(c, 1.0);
    #endif
  }
`;

function makeMaterial(tex, pick, born) {
  return new THREE.ShaderMaterial({
    glslVersion: THREE.GLSL3,
    uniforms: { ...uniforms, uAttr: { value: tex }, uBorn: born },
    vertexShader: VERT,
    fragmentShader: FRAG,
    defines: pick ? { PICK: 1 } : {},
    side: THREE.DoubleSide,
  });
}

// ---------- Tiles ----------
const meshes = [];
let loaded = 0;
const queue = [...config.tiles];
const pool = Array.from({ length: WORKERS }, () => new Worker('worker.js', { type: 'module' }));

function addTile(m) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(m.pos, 3));
  g.setAttribute('bld', new THREE.BufferAttribute(m.bld, 1));
  g.setIndex(new THREE.BufferAttribute(m.idx, 1));
  const rows = Math.ceil(m.nB / ATTR_W);
  const data = new Float32Array(ATTR_W * 2 * rows * 4);
  data.set(m.attr);
  const tex = new THREE.DataTexture(data, ATTR_W * 2, rows, THREE.RGBAFormat, THREE.FloatType);
  tex.needsUpdate = true;
  const born = { value: performance.now() / 1000 };
  const mesh = new THREE.Mesh(g, makeMaterial(tex, false, born));
  mesh.userData = { draw: mesh.material, pick: makeMaterial(tex, true, born) };
  mesh.scale.setScalar(0.1);
  mesh.position.set(m.origin[0], 0, m.origin[1]);
  scene.add(mesh);
  meshes.push(mesh);
}

// Tiles come in packs (see pipeline/s03_tiles.py); a tile is ready once its pack has arrived.
const packs = Object.fromEntries(config.packs.map(name => [name, fetch(`data/${name}`).then(r => r.arrayBuffer())]));
for (const w of pool) {
  const next = async () => {
    const t = queue.shift();
    if (!t) return;
    const buf = (await packs[t.pack]).slice(t.offset, t.offset + t.length);
    w.postMessage({ buf, id: t.file }, [buf]);
  };
  w.onmessage = ({ data }) => {
    addTile(data);
    loaded++;
    document.getElementById('progress').textContent = Math.round(100 * loaded / config.tiles.length);
    if (loaded === config.tiles.length) document.getElementById('loading').hidden = true;
    next();
  };
  next();
}

// ---------- Picking ----------
const pickTarget = new THREE.WebGLRenderTarget(1, 1);
const pickPixel = new Uint8Array(4);
function pick(x, y) {
  const w = renderer.domElement.clientWidth, h = renderer.domElement.clientHeight;
  camera.setViewOffset(w, h, x, y, 1, 1);
  for (const m of meshes) m.material = m.userData.pick;
  flat.visible = false;
  labelGroup.visible = false;
  renderer.setRenderTarget(pickTarget);
  renderer.setClearColor(0x000000, 0);
  renderer.clear();
  renderer.render(scene, camera);
  renderer.readRenderTargetPixels(pickTarget, 0, 0, 1, 1, pickPixel);
  renderer.setRenderTarget(null);
  renderer.setClearColor(SKY, 1);
  flat.visible = true;
  labelGroup.visible = true;
  for (const m of meshes) m.material = m.userData.draw;
  camera.clearViewOffset();
  return pickPixel[0] + pickPixel[1] * 256 + pickPixel[2] * 65536 - 1;
}

// ---------- Building lookup ----------
const SOURCE = ['', 'реестр многоквартирных домов ГИС ЖКХ', 'OpenStreetMap', 'реестр объектов культурного наследия (Wikidata)',
  'база «How old is this house» (Кон-Тики)', 'ручная проверка по Википедии'];
function dateNote(b, x = {}) {
  if (b.flag === 5) return 'Год постройки неизвестен: здания нет ни в ГИС ЖКХ, ни в реестре наследия, и в OpenStreetMap дата не указана. Здание серое и появляется на карте, когда таймлайн доходит до сегодняшнего дня.';
  if (b.flag === 4) return `Датировка по реестру наследия${x.y ? `: «${esc(x.y)}»` : ''}; на карте год разнесён по этому промежутку.`;
  if (b.flag === 3 && x.y) return `Датировка по реестру наследия: «${esc(x.y)}».`;
  if (b.flag === 1 && b.src === 1) return 'В ГИС ЖКХ стоит 1917 год — так обычно отмечают дома, построенные до революции. Читайте как «до 1918»; на карте год разнесён по 1880–1917.';
  if (b.flag === 1) return `В источнике (${SOURCE[b.src]}) указан диапазон лет; на карте год разнесён по нему.`;
  return `Год: ${SOURCE[b.src]}.`;
}
const groupsByBit = layers.flatMap(L => L.groups.map(g => ({ ...g, layer: L })));

function building(gid) {
  const o = gid * config.attrStride;
  const lay0 = attrs.getUint32(o + 20, true), lay1 = attrs.getUint32(o + 24, true);
  const osm = attrs.getFloat64(o, true);
  return {
    osm: osm > 0 ? `way/${osm}` : `relation/${-osm}`,
    id: String(osm),
    bag: String(osm),
    height: attrs.getUint16(o + 8, true) / 10,
    fsrc: attrs.getUint8(o + 10),
    flag: attrs.getUint8(o + 11),
    year: attrs.getInt16(o + 12, true),
    src: attrs.getInt16(o + 14, true),
    q: attrs.getUint32(o + 16, true),
    wk: attrs.getInt32(o + 28, true),
    groups: groupsByBit.filter(g => g.bit < 32 ? (lay0 >>> g.bit) & 1 : (lay1 >>> (g.bit - 32)) & 1),
  };
}

const periodOf = y => periods.find(p => y >= p.from && y <= p.to) || periods[0];

// ---------- Building card ----------
// Hover shows a light card that follows the pointer; a click pins it, with the article extract and links.
let wiki = [], extras = {};
fetch('data/wiki.json').then(r => r.json()).then(w => { wiki = w; });
fetch('data/extras.json').then(r => r.json()).then(e => { extras = e; });
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const link = (href, text) => `<a href="${esc(href)}" target="_blank" rel="noopener">${esc(text)}</a>`;
const STOREYS = ['по данным OpenStreetMap', 'по высоте ÷ 3,2 м', 'оценка по типу здания'];

function groupColor(g) {
  return GROUP_COLORS[g.layer.groups.findIndex(x => x.bit === g.bit)] || GROUP_COLORS[0];
}

// The card reads top to bottom: photo, name and year; what the building is; the layers it belongs to;
// the facts; how its date was found; where to read more.
function cardHtml(gid, pinned) {
  const b = building(gid);
  const w = b.wk >= 0 ? wiki[b.wk] : null;
  const x = extras[gid] || {};
  const im = w?.image?.thumb ? w.image : null;
  const unknown = b.flag === 5;
  const period = unknown ? { label: config.unknown.label, color: config.unknown.color } : periodOf(b.year);
  const facts = [
    ['Высота', `${b.height.toFixed(1).replace('.', ',')} м`],
    ['Этажность', STOREYS[b.fsrc]],
    w?.architects?.length ? [w.architects.length > 1 ? 'Архитекторы' : 'Архитектор', w.architects.map(esc).join(', ')]
      : x.a && [x.a.includes(',') ? 'Архитекторы' : 'Архитектор', esc(x.a)],
    w?.styles?.length ? ['Стиль', w.styles.map(esc).join(', ')] : x.s && ['Стиль', esc(x.s)],
  ].filter(Boolean);
  const credit = im && (pinned
    ? `${link(im.page || im.thumb, im.artist || 'Wikimedia Commons')}${im.license ? `, ${im.licenseUrl ? link(im.licenseUrl, im.license) : esc(im.license)}` : ''}`
    : `${esc(im.artist || 'Wikimedia Commons')}${im.license ? `, ${esc(im.license)}` : ''}`);
  const sources = [
    w?.wiki?.url && link(w.wiki.url, w.wiki.lang === 'ru' ? 'Википедия' : 'Wikipedia (англ.)'),
    b.q && link(`https://www.wikidata.org/wiki/Q${b.q}`, 'Wikidata'),
    x.wv && link(`https://ru.wikivoyage.org/wiki/${encodeURIComponent(x.wv.replace(/ /g, '_'))}`, 'Википутеводитель'),
    x.cw && link(`https://www.citywalls.ru/house${x.cw}.html`, 'Citywalls'),
    link(`https://www.openstreetmap.org/${b.osm}`, 'OpenStreetMap'),
  ].filter(Boolean);
  // Each layer the building is in, with its story: the plaque's words, the MPVO report, the documented history.
  const clip = (t, n) => t.length > n ? t.slice(0, n - 1).trimEnd() + '…' : t;
  const inLayers = b.groups.map(g => {
    const note = g.layer.notes?.[b.id];
    const story = note ? (pinned ? esc(note.story) : esc(clip(note.story, 160))) : '';
    return `<li><i style="background:${groupColor(g)}"></i><div><b>${esc(g.layer.title)}</b> <span>${esc(g.label)}</span>
      ${note?.name ? `<p class="note-name">${esc(note.name)}</p>` : ''}
      ${story ? `<p>${story}${pinned && note.source ? ` ${link(note.source, 'Источник')}` : ''}</p>` : ''}</div></li>`;
  }).join('');
  return `
    ${pinned ? '<button class="card-close" aria-label="Закрыть">×</button>' : ''}
    ${im ? `<figure class="photo"><img src="${esc(im.thumb)}" alt="" onerror="this.parentElement.remove()"><figcaption>Фото: ${credit}</figcaption></figure>` : ''}
    <header class="card-head">
      ${w?.label || x.n ? `<h3>${esc(w?.label || x.n)}</h3>` : ''}
      <div class="when"><span class="y">${unknown ? '—' : `${b.flag && b.flag !== 3 ? 'ок. ' : ''}${b.year}`}</span>
        <span class="period"><i style="background:${period.color}"></i>${esc(period.label)}</span></div>
    </header>
    ${pinned && w?.wiki?.extract ? `<section><p class="extract">${esc(w.wiki.extract)}</p></section>` : ''}
    ${w?.fact ? `<section><h4>Интересный факт</h4><p class="fact">${esc(pinned || w.fact.length < 170 ? w.fact : w.fact.slice(0, 168).trimEnd() + '…')}</p></section>` : ''}
    ${inLayers ? `<section><h4>В слоях</h4><ul class="chips">${inLayers}</ul></section>` : ''}
    <section><dl>${facts.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl></section>
    <section><h4>Датировка</h4><p class="why">${dateNote(b, x)}</p></section>
    ${pinned ? `<section class="sources"><h4>Подробнее</h4><p>${sources.join(', ')}</p></section>`
      : `<p class="hint">${w?.wiki || b.groups.some(g => g.layer.notes?.[b.id]) ? 'Нажмите, чтобы прочитать историю целиком' : 'Нажмите, чтобы закрепить карточку'}</p>`}`;
}

const card = document.getElementById('card');
let pinnedGid = -1;
function placeCard(x, y) {
  const r = card.getBoundingClientRect();
  card.style.left = Math.max(12, Math.min(x + 18, innerWidth - r.width - 12)) + 'px';
  card.style.top = Math.max(12, Math.min(y + 18, innerHeight - r.height - 12)) + 'px';
}
let hoverGid = -1;
function showCard(gid, x, y) {
  if (pinnedGid >= 0 || phone.matches) return;
  if (gid < 0) { card.hidden = true; hoverGid = -1; return; }
  if (gid !== hoverGid || card.hidden) {
    // Re-render only when the building changes, so the photo is not reloaded every frame.
    hoverGid = gid;
    card.innerHTML = cardHtml(gid, false);
    card.classList.remove('pinned');
    card.hidden = false;
    card.querySelector('img')?.addEventListener('load', () => placeCard(...(pointer || [x, y])));
  }
  placeCard(x, y);
}
function pinCard(gid, x, y) {
  pinnedGid = gid;
  hoverGid = -1;
  uniforms.uSelected.value = gid;
  if (gid < 0) { card.hidden = true; card.classList.remove('pinned'); return; }
  card.innerHTML = cardHtml(gid, true);
  card.classList.add('pinned');
  if (phone.matches) setCollapsed(true);
  card.hidden = false;
  card.querySelector('.card-close').onclick = () => pinCard(-1);
  card.querySelector('img')?.addEventListener('load', () => placeCard(x, y));
  placeCard(x, y);
}
addEventListener('keydown', e => { if (e.key === 'Escape') pinCard(-1); });

// A click (not a drag) pins the building under the pointer, or clears the pin on empty ground.
let pointer = null, dragging = false, downAt = null;
canvas.addEventListener('pointermove', e => { pointer = [e.clientX, e.clientY]; });
canvas.addEventListener('pointerdown', e => {
  dragging = true; downAt = [e.clientX, e.clientY];
  if (pinnedGid < 0) card.hidden = true;
});
canvas.addEventListener('pointerup', e => {
  dragging = false;
  if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 5) return;
  if (pickingStart) {
    const at = groundAt(e.clientX, e.clientY);
    if (at) { pickingStart = false; walkPrefs.at = at; walkPrefs.atLabel = t('Point on the map'); walkEl.hidden = true; openWalks(); }
    return;
  }
  const gid = pick(e.clientX, e.clientY);
  pinCard(gid === pinnedGid ? -1 : gid, e.clientX, e.clientY);
  questClick(gid);
});
canvas.addEventListener('pointerleave', () => { pointer = null; if (pinnedGid < 0) card.hidden = true; uniforms.uHover.value = -1; });

// ---------- Flying to a building ----------
let bagIndex = null;
function gidOf(bag) {
  if (!bagIndex) {
    bagIndex = new Map();
    for (let g = 0; g < config.stats.buildings; g++) {
      bagIndex.set(String(attrs.getFloat64(g * config.attrStride, true)), g);
    }
  }
  return bagIndex.get(bag) ?? -1;
}
let flight = null;
function flyTo(x, z, done, distance = 520) {
  const dir = camera.position.clone().sub(controls.target).normalize();
  if (dir.y < 0.45) { dir.y = 0.45; dir.normalize(); }
  const target = new THREE.Vector3(x, 0, z);
  flight = { t0: performance.now(), dur: 1400, fromT: controls.target.clone(), toT: target,
    fromP: camera.position.clone(), toP: target.clone().add(dir.multiplyScalar(distance)), done };
}
function stepFlight(now) {
  if (!flight) return;
  const k = Math.min(1, (now - flight.t0) / flight.dur), e = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
  controls.target.lerpVectors(flight.fromT, flight.toT, e);
  camera.position.lerpVectors(flight.fromP, flight.toP, e);
  if (k >= 1) { const d = flight.done; flight = null; d?.(); }
}

// Walk shows as on while a walk is open; on a phone the timeline steps aside.
function markWalk() {
  document.querySelector('.walks-open').setAttribute('aria-pressed', String(!!walkRoute));
  document.querySelector('.quests-open')?.setAttribute('aria-pressed', String(!!quest));
  document.body.classList.toggle('walking', !!walkRoute || !!quest);
}

// Local metres <-> WGS84 through UTM zone 36N (EPSG:32636), the frame the pipeline works in.
const UTM = { a: 6378137, f: 1 / 298.257223563, k0: 0.9996, lon0: 33 * Math.PI / 180, E0: 500000 };
function toLatLon(x, z) {
  const E = x + config.origin[0] - UTM.E0, N = config.origin[1] - z;
  const { a, f, k0 } = UTM, e2 = f * (2 - f), ep2 = e2 / (1 - e2);
  const M = N / k0, mu = M / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256));
  const e1 = (1 - Math.sqrt(1 - e2)) / (1 + Math.sqrt(1 - e2));
  const p1 = mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * Math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * Math.sin(4 * mu)
    + (151 * e1 ** 3 / 96) * Math.sin(6 * mu);
  const C1 = ep2 * Math.cos(p1) ** 2, T1 = Math.tan(p1) ** 2, N1 = a / Math.sqrt(1 - e2 * Math.sin(p1) ** 2);
  const R1 = a * (1 - e2) / (1 - e2 * Math.sin(p1) ** 2) ** 1.5, D = E / (N1 * k0);
  const lat = p1 - (N1 * Math.tan(p1) / R1) * (D ** 2 / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 ** 2 - 9 * ep2) * D ** 4 / 24
    + (61 + 90 * T1 + 298 * C1 + 45 * T1 ** 2 - 252 * ep2 - 3 * C1 ** 2) * D ** 6 / 720);
  const lon = UTM.lon0 + (D - (1 + 2 * T1 + C1) * D ** 3 / 6 + (5 - 2 * C1 + 28 * T1 - 3 * C1 ** 2 + 8 * ep2 + 24 * T1 ** 2) * D ** 5 / 120) / Math.cos(p1);
  return [lat * 180 / Math.PI, lon * 180 / Math.PI];
}
function fromLatLon(latd, lond) {
  const { a, f, k0 } = UTM, e2 = f * (2 - f), ep2 = e2 / (1 - e2);
  const lat = latd * Math.PI / 180, lon = lond * Math.PI / 180;
  const N = a / Math.sqrt(1 - e2 * Math.sin(lat) ** 2), T = Math.tan(lat) ** 2, C = ep2 * Math.cos(lat) ** 2, A = Math.cos(lat) * (lon - UTM.lon0);
  const M = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * lat - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * Math.sin(2 * lat)
    + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * Math.sin(4 * lat) - (35 * e2 ** 3 / 3072) * Math.sin(6 * lat));
  const E = UTM.E0 + k0 * N * (A + (1 - T + C) * A ** 3 / 6 + (5 - 18 * T + T ** 2 + 72 * C - 58 * ep2) * A ** 5 / 120);
  const Nn = k0 * (M + N * Math.tan(lat) * (A ** 2 / 2 + (5 - T + 9 * C + 4 * C ** 2) * A ** 4 / 24 + (61 - 58 * T + T ** 2 + 600 * C - 330 * ep2) * A ** 6 / 720));
  return [E - config.origin[0], -(Nn - config.origin[1])];
}
// ---------- Walks ----------
// Where a walk can start besides the walker's location: the city config's list, else the map's centre.
const STARTS = [{ ru: 'Дворцовая площадь', x: 0, z: 0 }, { ru: 'Московский вокзал', x: 2545, z: 1128 }];
// A walk through the stories the walker cares about: pick interests, a start and a distance; the stops are the
// buildings with a story in those layers, chosen greedily by story per metre and ordered by 2-opt. Distances are
// straight lines times a detour factor; Google Maps gives the real walking route.
const DETOUR = 1.3, WALK_KMH = 4.5, STOP_MIN = 3, MAX_STOPS = 20;
const GOOGLE_LEG = 9;  // a Google Maps link takes at most 9 waypoints
const walkEl = document.getElementById('walk');
const walksDlg = document.getElementById('walks');
const walkGroup = new THREE.Group();
walkGroup.renderOrder = 5;
scene.add(walkGroup);
let walkPrefs = { layers: [], start: 0, km: 3, loop: true, at: null, stops: 0 }, walkRoute = null, pickingStart = false;

// Every building with a story, merged across layers: one stop can carry several stories.
let poiCache = null;
function pois() {
  if (poiCache) return poiCache;
  const by = new Map();
  for (const L of layers) for (const [bag, n] of Object.entries(L.notes || {})) {
    if (!n.at) continue;
    const p = by.get(bag) || { bag, bags: [bag], x: n.at[0], z: n.at[1], notes: [] };
    p.notes.push({ L, n });
    by.set(bag, p);
  }
  // One stop per named place: a complex of several buildings (a laboratory, a hofje) carries the same story on
  // each of them; keep the building nearest their middle.
  const byName = new Map();
  for (const p of by.values()) {
    const key = p.notes.map(x => x.n.name).find(Boolean) || p.bag;
    (byName.get(key) || byName.set(key, []).get(key)).push(p);
  }
  poiCache = [];
  for (const ps of byName.values()) {
    const mx = ps.reduce((a, p) => a + p.x, 0) / ps.length, mz = ps.reduce((a, p) => a + p.z, 0) / ps.length;
    const keep = ps.reduce((a, p) => Math.hypot(p.x - mx, p.z - mz) < Math.hypot(a.x - mx, a.z - mz) ? p : a);
    const seen = new Set(keep.notes.map(x => x.L.id));
    keep.bags = [...new Set(ps.flatMap(p => p.bags))];
    for (const p of ps) for (const x of p.notes) if (!seen.has(x.L.id)) { keep.notes.push(x); seen.add(x.L.id); }
    poiCache.push(keep);
  }
  return poiCache;
}
const walkLayers = () => layers.filter(L => Object.values(L.notes || {}).filter(n => n.at).length >= 3);
const poiName = p => { if (p.name) return p.name; const n = p.notes.find(x => x.n.name && !x.n.people) || p.notes[0]; return tr(n.n, 'name') || n.n.name; };
function poiScore(p, chosen) {
  const hit = p.notes.filter(x => !chosen.length || chosen.includes(x.L.id)).length;
  if (!hit) return 0;
  const g = gidOf(p.bag), w = g >= 0 ? wiki[building(g).wk] : null;
  return 1 + 0.5 * (hit - 1) + (w?.image ? 0.4 : 0) + 0;
}
const dist = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
function pathLen(pts) { let d = 0; for (let i = 1; i < pts.length; i++) d += dist(pts[i - 1], pts[i]); return d; }
function planWalkWithGap({ layers: chosen, km, loop, stops: asked, custom }, start, gap) {
  const budget = km * 1000 / DETOUR;
  const S = { x: start[0], z: start[1], start: true };
  let cand = (custom || pois().map(p => ({ ...p, score: poiScore(p, chosen) })))
    .filter(p => p.score > 0 && dist(p, S) <= (loop ? budget / 2 : budget));
  // Stops keep a spacing that grows with the walk, so a long walk goes somewhere instead of circling the Markt;
  // a closer one merges into the higher scored stop (a church with three entries is one stop).
  cand.sort((a, b) => b.score - a.score);
  cand = cand.filter((p, i) => !cand.slice(0, i).some(q => dist(p, q) < 25));
  const route = loop ? [S, S] : [S];
  const cap = asked || MAX_STOPS;
  const max = loop ? cap : cap + 1;
  while (route.length - (loop ? 2 : 1) < max) {
    let best = null;
    for (const c of cand) {
      if (route.includes(c) || route.some(r => !r.start && dist(r, c) < gap)) continue;
      for (let i = 0; i < route.length; i++) {
        const next = route[i + 1];
        const add = next ? dist(route[i], c) + dist(c, next) - dist(route[i], next) : dist(route[i], c);
        if (!next && loop) continue;
        if (pathLen(route) + add > budget) continue;
        const ratio = c.score / (add + gap);
        if (!best || ratio > best.ratio) best = { c, i, ratio };
      }
    }
    if (!best) break;
    route.splice(best.i + 1, 0, best.c);
  }
  // 2-opt over the stops between the fixed ends
  for (let improved = true; improved;) {
    improved = false;
    const last = loop ? route.length - 2 : route.length - 1;
    for (let i = 1; i < last; i++) for (let j = i + 1; j <= last; j++) {
      const a = route[i - 1], b = route[i], c = route[j], d = route[j + 1];
      const before = dist(a, b) + (d ? dist(c, d) : 0), after = dist(a, c) + (d ? dist(b, d) : 0);
      if (after < before - 1) { route.splice(i, j - i + 1, ...route.slice(i, j + 1).reverse()); improved = true; }
    }
  }
  return { start: S, stops: route.filter(p => !p.start), loop, length: pathLen(route) * DETOUR, route,
    score: route.reduce((n, p) => n + (p.score || 0), 0) };
}
// A wide spacing first; when the chosen stories are few and close together, tighter spacings keep them all.
function planAtLength(prefs, start) {
  const wide = Math.min(400, Math.max(30, prefs.km * 1000 / DETOUR / ((prefs.stops || MAX_STOPS) * 2.2)));
  const plans = [wide, wide / 2, wide / 4, 25].map(g => planWalkWithGap(prefs, start, g));
  const most = Math.max(...plans.map(p => p.stops.length));
  return plans.find(p => p.stops.length >= most);  // the widest spacing that loses no stop
}
// A walk with one or two stops is not a walk: when the chosen stories lie further away than the distance allows,
// the distance grows (up to three times) until there are a few of them, and the card says so.
const MIN_STOPS = 4;
function planWalk(prefs, start) {
  const available = prefs.custom ? prefs.custom.length : pois().filter(p => poiScore(p, prefs.layers) > 0).length;
  const want = Math.min(prefs.stops || MIN_STOPS, available);
  let w = planAtLength(prefs, start);
  for (let k = 1.25; w.stops.length < want && k <= 4.01; k += 0.25) {
    w = planAtLength({ ...prefs, km: prefs.km * k }, start);
    w.stretched = true;
  }
  return w;
}
// A stop goes to Google Maps by name and address, so Google opens its own card for the place (often with the
// Wikipedia summary); a stop without an address, and the start, go by coordinates.
const poiAddress = p => p.notes.map(x => x.n.address || x.n.people?.find(q => q.address)?.address).find(Boolean);
function poiQuery(p) {
  const addr = poiAddress(p), name = poiName(p);
  if (!addr) return null;
  return [name && name !== addr ? name : null, addr, 'Санкт-Петербург'].filter(Boolean).join(', ');
}
// One Google Maps link: it takes at most 9 waypoints, so a longer walk sends the 9 best stops in walking order;
// the others lie on the way between them.
function googleStops(w) {
  const max = w.loop ? GOOGLE_LEG : GOOGLE_LEG + 1;
  if (w.stops.length <= max) return w.stops;
  const keep = new Set([...w.stops].sort((a, b) => b.score - a.score).slice(0, max));
  return w.stops.filter(p => keep.has(p));
}
function googleUrl(w) {
  const ll = p => (!p.start && poiQuery(p)) || toLatLon(p.x, p.z).map(v => v.toFixed(6)).join(',');
  const stops = googleStops(w).map(ll);
  const dest = w.loop ? ll(w.start) : stops.pop();
  const u = new URL('https://www.google.com/maps/dir/');
  u.searchParams.set('api', '1');
  u.searchParams.set('origin', ll(w.start));
  u.searchParams.set('destination', dest);
  if (stops.length) u.searchParams.set('waypoints', stops.join('|'));
  u.searchParams.set('travelmode', 'walking');
  return u.toString();
}
// The walk as KML, for Google My Maps or any map app: every stop with its story, its sources and a photo.
function walkKml(w) {
  const x = v => String(v ?? '').replace(/[<>&]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]));
  const pt = p => toLatLon(p.x, p.z).reverse().join(',') + ',0';
  const marks = w.stops.map((p, i) => {
    const g = gidOf(p.bag), wk = g >= 0 ? wiki[building(g).wk] : null, img = wk?.image?.thumb;
    const art = wk && (LANG === 'nl' ? wk.wiki_nl || wk.wiki : wk.wiki || wk.wiki_nl);
    const stories = p.notes.map(n => n.n.people
      ? `<p>${n.n.people.map(q => `${x(q.person)} (<a href="${x(q.url)}">Wikipedia</a>)`).join(', ')}</p>`
      : `<p>${x(tr(n.n, 'story'))}${n.n.source ? ` <a href="${x(n.n.source)}">${x(t('Source'))}</a>` : ''}</p>`).join('');
    const desc = `${img ? `<img src="${x(img)}" width="300"/>` : ''}${stories}${art?.url ? `<p><a href="${x(art.url)}">Wikipedia</a></p>` : ''}`;
    return `<Placemark><name>${i + 1}. ${x(poiName(p))}</name><description><![CDATA[${desc}]]></description>
<Point><coordinates>${pt(p)}</coordinates></Point></Placemark>`;
  }).join('\n');
  const line = [w.start, ...w.stops, ...(w.loop ? [w.start] : [])].map(pt).join(' ');
  return `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>LAYRS: Петербург: ${x(t('Your walk'))}</name>
<Placemark><name>${x(t('Start'))}</name><Point><coordinates>${pt(w.start)}</coordinates></Point></Placemark>
${marks}
<Placemark><name>${x(t('Your walk'))}</name><LineString><tessellate>1</tessellate><coordinates>${line}</coordinates></LineString></Placemark>
</Document></kml>`;
}
function downloadKml(w) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([walkKml(w)], { type: 'application/vnd.google-earth.kml+xml' }));
  a.download = `layrs-${config.city}-walk.kml`;
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
// ---- on the map: a ribbon along the walk and a numbered disc over every stop
function discTexture(text, fill, ink) {
  const c = document.createElement('canvas'); c.width = c.height = 96;
  const g = c.getContext('2d');
  g.beginPath(); g.arc(48, 48, 40, 0, Math.PI * 2); g.fillStyle = fill; g.fill();
  g.lineWidth = 7; g.strokeStyle = '#ffffff'; g.stroke();
  g.fillStyle = ink; g.font = '800 44px "Schibsted Grotesk", Arial, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText(text, 48, 51);
  const t = new THREE.CanvasTexture(c); t.anisotropy = 4;
  return t;
}
// While a walk is shown the city is a plain model and only the walk's buildings carry colour (the graph's focus).
function lightWalk(w) {
  if (!w) { uniforms.uFocusN.value = 0; return; }
  const gids = [...new Set(w.stops.flatMap(p => p.bags.map(gidOf)))].filter(g => g >= 0).slice(0, FOCUS_MAX);
  uniforms.uFocus.value = [...gids, ...Array(FOCUS_MAX - gids.length).fill(-1)];
  uniforms.uFocusGroup.value = Array(FOCUS_MAX).fill(0);
  uniforms.uFocusN.value = gids.length;
}
function drawWalk(w) {
  walkGroup.clear();
  lightWalk(w);
  if (!w) return;
  const accent = getComputedStyle(document.documentElement).getPropertyValue('--red').trim() || '#b8892a';
  const pts = w.route, pos = [];
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i], len = dist(a, b) || 1, nx = -(b.z - a.z) / len * 3.5, nz = (b.x - a.x) / len * 3.5;
    pos.push(a.x + nx, 1, a.z + nz, a.x - nx, 1, a.z - nz, b.x + nx, 1, b.z + nz,
      a.x - nx, 1, a.z - nz, b.x - nx, 1, b.z - nz, b.x + nx, 1, b.z + nz);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  const ribbon = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: accent, transparent: true, opacity: 0.85,
    side: THREE.DoubleSide, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4 }));
  walkGroup.add(ribbon);
  const marker = (p, text, fill, ink) => {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: discTexture(text, fill, ink), depthTest: false, sizeAttenuation: false }));
    s.scale.set(0.034, 0.034, 1);
    s.position.set(p.x, 30, p.z);
    s.renderOrder = 20;
    walkGroup.add(s);
  };
  marker(w.start, '★', '#ffffff', accent);
  w.stops.forEach((p, i) => marker(p, String(i + 1), accent, '#ffffff'));
}
// ---- the planner
function startPoint() {
  if (walkPrefs.at) return walkPrefs.at;
  const s = STARTS[walkPrefs.start] || STARTS[0];
  return [s.x, s.z];
}
function renderWalkPlanner(msg = '') {
  const L = walkLayers(), sel = walkPrefs.layers;
  const startName = walkPrefs.at ? (walkPrefs.atLabel || t('Your point')) : L10(STARTS[walkPrefs.start]);
  document.getElementById('walks-body').innerHTML = `
    <h2 id="walks-title">${t('Plan a walk')}</h2>
    <p class="w-lede">${t('Choose what interests you, where you start and how far you want to go. The walk links the buildings with stories on the way.')}</p>
    <h3>${t('Where you start')}</h3>
    <div class="w-locate">${walkPrefs.atLabel === t('Your location')
      ? `<p class="w-note">${t('Start')}: ${esc(startName)}</p>`
      : `<button class="w-share" data-geo>${t(locating ? 'Asking for your location…' : 'Share my location')}</button>
         <p class="w-note">${t('Start from where you are: share your location, or choose a start below.')}</p>`}</div>
    <div class="w-chips">${STARTS.map((s, i) => `<button class="w-chip" data-start="${i}" aria-pressed="${!walkPrefs.at && walkPrefs.start === i}">${esc(L10(s))}</button>`).join('')}
      <button class="w-chip" data-pick aria-pressed="${walkPrefs.atLabel === t('Point on the map')}">${t('Pick on the map')}</button></div>
    ${walkPrefs.atLabel === t('Your location') ? '' : `<p class="w-note">${t('Start')}: ${esc(startName)}</p>`}
    <h3>${t('What interests you')}</h3>
    <div class="w-chips">${L.map(l => `<button class="w-chip" data-l="${l.id}" aria-pressed="${sel.includes(l.id)}">${sectionIcon(l.section)}${esc(tr(l, 'title'))}</button>`).join('')}</div>
    <p class="w-note">${sel.length ? '' : t('Nothing chosen: the walk takes every story.')}</p>
    <h3>${t('How far')}</h3>
    <div class="w-chips">${[1, 2, 3, 5, 8].map(k => `<button class="w-chip" data-km="${k}" aria-pressed="${walkPrefs.km === k}">${k} km</button>`).join('')}
      <span class="w-sep"></span>
      <button class="w-chip" data-loop="1" aria-pressed="${walkPrefs.loop}">${t('Back to the start')}</button>
      <button class="w-chip" data-loop="0" aria-pressed="${!walkPrefs.loop}">${t('One way')}</button></div>
    <h3>${t('How many stops')}</h3>
    <div class="w-chips">${[0, 5, 10, 15, 20].map(n => `<button class="w-chip" data-stops="${n}" aria-pressed="${walkPrefs.stops === n}">${n ? n : t('As many as fit')}</button>`).join('')}</div>
    ${msg ? `<p class="w-msg">${esc(msg)}</p>` : ''}
    <div class="w-go"><button class="w-make">${t('Make my walk')}</button></div>`;
  const body = document.getElementById('walks-body');
  body.querySelectorAll('[data-l]').forEach(b => b.onclick = () => {
    const id = b.dataset.l;
    walkPrefs.layers = sel.includes(id) ? sel.filter(x => x !== id) : [...sel, id];
    renderWalkPlanner();
  });
  body.querySelectorAll('[data-start]').forEach(b => b.onclick = () => { walkPrefs.start = +b.dataset.start; walkPrefs.at = null; walkPrefs.atLabel = null; renderWalkPlanner(); });
  body.querySelectorAll('[data-km]').forEach(b => b.onclick = () => { walkPrefs.km = +b.dataset.km; renderWalkPlanner(); });
  body.querySelectorAll('[data-stops]').forEach(b => b.onclick = () => { walkPrefs.stops = +b.dataset.stops; renderWalkPlanner(); });
  body.querySelectorAll('[data-loop]').forEach(b => b.onclick = () => { walkPrefs.loop = b.dataset.loop === '1'; renderWalkPlanner(); });
  body.querySelector('[data-geo]')?.addEventListener('click', requestLocation);
  body.querySelector('[data-pick]').onclick = () => { pickingStart = true; walksDlg.close(); showWalkHint(); };
  body.querySelector('.w-make').onclick = makeWalk;
}
let locating = false, locationAsked = false;
function requestLocation() {
  locationAsked = true;
  if (!navigator.geolocation) { renderWalkPlanner(t('This browser does not share its location.')); return; }
  locating = true; renderWalkPlanner();
  navigator.geolocation.getCurrentPosition(pos => {
    locating = false;
    const [x, z] = fromLatLon(pos.coords.latitude, pos.coords.longitude);
    if (Math.hypot(x, z) > 6000) { renderWalkPlanner(t('You seem to be outside the city, so the walk starts at {s}.').replace('{s}', L10(STARTS[0]))); return; }
    walkPrefs.at = [x, z]; walkPrefs.atLabel = t('Your location'); renderWalkPlanner();
  }, () => { locating = false; renderWalkPlanner(t('The location was not shared. Pick a start on the map instead.')); },
  { enableHighAccuracy: true, timeout: 10000 });
}
function showWalkHint() {
  walkEl.hidden = false;
  walkEl.className = 'walkcard';
  walkEl.innerHTML = `<header><b>${t('Plan a walk')}</b></header><p class="q-riddle">${t('Click the map where the walk should start.')}</p>
    <div class="q-actions"><button class="w-cancel">${t('Cancel')}</button></div>`;
  walkEl.querySelector('.w-cancel').onclick = () => { pickingStart = false; walkEl.hidden = true; openWalks(); };
}
// A click on the ground while picking: where the pointer ray meets the ground plane.
function groundAt(cx, cy) {
  const r = canvas.getBoundingClientRect();
  camera.updateMatrixWorld();
  const ray = new THREE.Raycaster();
  ray.setFromCamera(new THREE.Vector2((cx - r.left) / r.width * 2 - 1, -((cy - r.top) / r.height) * 2 + 1), camera);
  const hit = new THREE.Vector3();
  return ray.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), hit) ? [hit.x, hit.z] : null;
}
function makeWalk() {
  const w = planWalk(walkPrefs, startPoint());
  if (!w.stops.length) { renderWalkPlanner(t('No stories within reach. Try a longer walk or more interests.')); return; }
  walkRoute = w;
  walksDlg.close();
  drawWalk(w);
  walkEl.hidden = true;
  renderWalk();
  // on a phone a new walk opens folded to its bar, so the route on the map is what one sees first
  if (phone.matches) walkEl.classList.add('folded');
  const xs = w.route.map(p => p.x), zs = w.route.map(p => p.z);
  const span = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...zs) - Math.min(...zs));
  flyTo((Math.max(...xs) + Math.min(...xs)) / 2, (Math.max(...zs) + Math.min(...zs)) / 2, null, Math.max(600, span * 2.2));
  const u = new URL(location.href);
  if (walkPrefs.custom) u.searchParams.delete('walk'); else u.searchParams.set('walk', [walkPrefs.km, walkPrefs.loop ? 1 : 0, startPoint().map(Math.round).join('_'), walkPrefs.layers.join('.'), walkPrefs.stops].join('~'));
  history.replaceState(null, '', u);
}
function renderWalk() {
  const w = walkRoute;
  if (!w) return;
  const mins = Math.round(w.length / 1000 / WALK_KMH * 60 + w.stops.length * STOP_MIN);
  const inGoogle = new Set(googleStops(w));
  const folded = !walkEl.hidden && walkEl.classList.contains('folded');
  walkEl.hidden = false;
  walkEl.className = 'walkcard' + (folded ? ' folded' : '');
  walkEl.innerHTML = `
    <button class="q-close" aria-label="${t('Close')}">×</button>
    <header><b>${t('Your walk')}</b><span class="w-meta">${(w.length / 1000).toFixed(1).replace('.', ',')} km · ${t('about {m} min').replace('{m}', mins)}</span></header>
    <div class="q-actions"><a class="w-google" href="${esc(googleUrl(w))}" target="_blank" rel="noopener">${t('Open in Google Maps')}</a>
      <button class="w-change">${t('Change')}</button>
      <button class="w-kml" title="${t('Download the walk with its stories (KML), for Google My Maps: Create a new map, then Import.')}" aria-label="${t('Download the walk with its stories (KML), for Google My Maps: Create a new map, then Import.')}"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2v8m0 0-3-3m3 3 3-3M3 12.5v1.5h10v-1.5"/></svg></button></div>
    <ol class="w-stops">${w.stops.map((p, i) => {
      const pref = [...p.notes].sort((a, b) => (walkPrefs.layers.includes(b.L.id) ? 1 : 0) - (walkPrefs.layers.includes(a.L.id) ? 1 : 0));
      const story = pref.map(x => x.n.people ? `${t('Lived or worked here')}: ${x.n.people.map(q => q.person).join(', ')}` : tr(x.n, 'story')).find(Boolean) || '';
      const off = !inGoogle.has(p);
      return `<li${off ? ' class="w-off"' : ''}><button data-i="${i}"><span class="w-num">${i + 1}</span><span><b>${esc(poiName(p))}</b><em>${esc(story)}</em></span></button></li>`;
    }).join('')}</ol>
    <p class="q-credit">${walkPrefs.stops && w.stops.length < walkPrefs.stops ? t('Fewer stops than asked: that is all the stories you chose.') + ' ' : ''}${w.stretched ? t('Longer than asked: few of the stories you chose lie that close.') + ' '
      : w.length < walkPrefs.km * 600 ? t('Shorter than asked: the stories you chose lie close together.') + ' ' : ''}${t('Straight lines on the map; Google Maps shows the walking route.')}${inGoogle.size < w.stops.length
      ? ' ' + t('Google Maps takes nine stops; the paler ones lie on the way.') : ''}</p>`;
  markWalk();
  walkEl.querySelector('.q-close').onclick = () => { walkEl.hidden = true; walkRoute = null; drawWalk(null); markWalk();
    const u = new URL(location.href); u.searchParams.delete('walk'); history.replaceState(null, '', u); };
  walkEl.querySelector('.w-change').onclick = openWalks;
  walkEl.querySelector('.w-kml').onclick = () => downloadKml(w);
  // On a phone the list folds to its title bar and the Google Maps button; a tap on the bar opens it again.
  walkEl.querySelector('header').onclick = () => walkEl.classList.toggle('folded');
  walkEl.querySelectorAll('[data-i]').forEach(b => b.onclick = () => {
    const p = w.stops[+b.dataset.i], g = gidOf(p.bag);
    if (phone.matches) walkEl.classList.add('folded');
    flyTo(p.x, p.z, () => { if (g >= 0) pinCard(g, innerWidth / 3, innerHeight / 2); }, 330);
  });
}
// A walk straight from a layer's page or from the graph: the stories of that layer, or one stop per graph group.
function walkFromLayer(L) {
  walkPrefs = { ...walkPrefs, layers: [L.id], custom: null, stops: 0 };
  makeWalk();
}
function walkFromGroups(groups) {
  // One stop per building of the selection: a story's stop where it has one, else the building under the name of
  // its graph group (a person's several houses become several stops). Neighbours closer than 25 m merge later.
  const seen = new Set(), custom = [];
  for (const g of groups) for (const gid of g.gids) {
    const b = building(gid), own = pois().find(p => p.bags.includes(b.bag));
    const key = own ? own.bag : b.bag;
    if (seen.has(key)) continue;
    seen.add(key);
    const w = wiki[b.wk];
    custom.push(own ? { ...own, score: 1.5 + (w?.image ? 0.4 : 0) }
      : { bag: b.bag, bags: [b.bag], x: b.x ?? g.pos?.[b.bag]?.x, z: b.z ?? g.pos?.[b.bag]?.z,  // positions come from the graph here
          name: (w && tr(w, 'label')) || g.label, notes: [], score: 1 + (w?.image ? 0.4 : 0) });
  }
  walkPrefs = { ...walkPrefs, custom, stops: Math.min(MAX_STOPS, custom.length) };
  makeWalk();
}
function openWalks() {
  renderWalkPlanner();
  walksDlg.showModal();
  if (!locationAsked && !walkPrefs.at) requestLocation();  // the walk starts where the walker is, if they agree
}
document.querySelector('.walks-open').onclick = () => { walkPrefs.custom = null; openWalks(); };
walksDlg.querySelector('.about-close').onclick = () => walksDlg.close();
walksDlg.addEventListener('click', e => { if (e.target === walksDlg) walksDlg.close(); });
// A shared link restores the walk: ?walk=km~loop~x_z~layer.layer
{
  const q = new URLSearchParams(location.search).get('walk');
  if (q) {
    const [km, loop, at, ls, ns] = q.split('~');
    const [x, z] = (at || '').split('_').map(Number);
    walkPrefs = { km: +km || 3, loop: loop !== '0', start: 0, at: Number.isFinite(x) && Number.isFinite(z) ? [x, z] : null,
      atLabel: t('Point on the map'), stops: +ns || 0, layers: (ls || '').split('.').filter(id => layers.some(L => L.id === id)) };
    setTimeout(makeWalk, 0);
  }
}

// ---------- Quests ----------
// Chains of riddles (pipeline/quests.py); each is solved by finding the building on the map and clicking it.
// A riddle is worth three tiles; every hint costs one, "Show me" all of them. Progress stays in this browser.
let quests = [], quest = null, step = 0, hintsShown = 0, solved = false, misses = 0, questFolded = false, revealed = false;
fetch('data/quests.json').then(r => r.ok ? r.json() : []).then(q => { quests = q; }).catch(() => {});
const questEl = document.getElementById('quest');
const questsDlg = document.getElementById('quests');
const LEVEL = ['', 'Easy', 'Medium', 'Hard'];
const store = () => { try { return JSON.parse(localStorage.getItem('quests2') || '{}'); } catch { return {}; } };
function save(id, patch) {
  try { const p = store(); p[id] = { ...(p[id] || {}), ...patch }; localStorage.setItem('quests2', JSON.stringify(p)); } catch {}
}
const tiles = (n, of) => `<span class="q-tiles" aria-label="${n} / ${of}">${Array.from({ length: of }, (_, i) =>
  `<i class="${i < n ? 'on' : ''}"></i>`).join('')}</span>`;
const levelMark = lv => `<span class="q-level l${lv}">${tiles(lv, 3)}${t(LEVEL[lv])}</span>`;

function renderQuestList() {
  const p = store();
  const total = quests.reduce((n, q) => n + (p[q.id]?.best || 0), 0), max = quests.length * 15;
  document.getElementById('quests-body').innerHTML = `
    <h2 id="quests-title">${t('Quests')}</h2>
    <p class="q-lede">${t('Riddles hidden in the city. Find each building on the map, using its colours and layers, and click it. Every riddle is worth three tiles; hints cost one.')}</p>
    <p class="q-score">${t('Your tiles')}: <b>${total}</b> / ${max}</p>
    <ul class="q-grid">${quests.map(q => {
      const st = p[q.id] || {}, done = Math.min(st.step || 0, q.steps.length), complete = done >= q.steps.length;
      const label = complete ? t('Play again') : done ? t('Continue') : t('Start');
      return `<li class="q-tile l${q.level}${complete ? ' complete' : ''}">
        ${levelMark(q.level)}
        <h3>${esc(L10(q.title))}</h3>
        <p>${esc(L10(q.intro))}</p>
        <footer><span class="q-progress">${complete ? `${t('Best')}: ${st.best || 0} / 15` : `${done} / ${q.steps.length}`}</span>
          <button class="q-start" data-q="${q.id}">${label}</button></footer></li>`;
    }).join('')}</ul>`;
  questsDlg.querySelectorAll('.q-start').forEach(b => b.onclick = () => {
    const q = quests.find(q => q.id === b.dataset.q), st = store()[q.id] || {};
    const fresh = !st.step || st.step >= q.steps.length;
    startQuest(q, fresh ? 0 : st.step, fresh ? 0 : st.score || 0);
    questsDlg.close();
  });
}
function openQuests() { renderQuestList(); questsDlg.showModal(); }
document.querySelector('.quests-open').onclick = openQuests;
questsDlg.querySelector('.about-close').onclick = () => questsDlg.close();
questsDlg.addEventListener('click', e => { if (e.target === questsDlg) questsDlg.close(); });

let score = 0;
function startQuest(q, n, sc = 0) {
  quest = q; step = n; score = sc;
  resetStep();
  save(q.id, { step: n, score: sc });
  renderQuest();
}
function resetStep() { hintsShown = 0; solved = false; misses = 0; revealed = false; questFolded = false; }
function closeQuest() { quest = null; questEl.hidden = true; markWalk(); }
function setModeNamed(name) {
  if (name === 'floors' || name === 'energy') { setBuildingView(MODE[name]); return; }
  const m = { period: MODE.period, layers: MODE.layers }[name];
  document.querySelector(`.modes button[data-mode="${m}"]`)?.click();
}
function showLayer(id) {
  const L = layers.find(L => L.id === id);
  if (!L) return;
  setModeNamed('layers');
  setLayer(L);
  if (phone.matches) setCollapsed(false);
}
function isAnswer(gid, a) {
  if (gid < 0) return false;
  const b = building(gid);
  if (a.bags) return a.bags.includes(b.bag);
  if (a.before && !(b.year < a.before)) return false;
  if (a.after && !(b.year > a.after)) return false;
  if (a.bits && !a.bits.every(bit => b.groups.some(g => g.bit === bit))) return false;
  return true;
}
// The answer's buildings: listed for a story, found by scanning the city for a rule (once per riddle).
let answerCache = null;
function answerGids(a) {
  if (answerCache?.a === a) return answerCache.g;
  const g = a.bags ? a.bags.map(gidOf).filter(g => g >= 0)
    : Array.from({ length: config.stats.buildings }, (_, i) => i).filter(i => isAnswer(i, a));
  answerCache = { a, g };
  return g;
}
const MODE_LABEL = { period: 'Colour by period', floors: 'Colour by floors', energy: 'Colour by energy label' };
const stepTiles = () => revealed ? 0 : Math.max(1, 3 - hintsShown);
function renderQuest() {
  if (!quest) return;
  const s = quest.steps[step], last = step === quest.steps.length - 1;
  const hints = s.hints.slice(0, hintsShown).map(h => `<li>${esc(L10(h))}</li>`).join('');
  const im = s.photo, moreHints = hintsShown < s.hints.length;
  questEl.className = `quest l${quest.level}${solved ? ' solved' : ''}${questFolded && !solved ? ' folded' : ''}`;
  questEl.innerHTML = `
    <button class="q-close" aria-label="${t('Close')}">×</button>
    <header><b>${esc(L10(quest.title))}</b>${levelMark(quest.level)}</header>
    <div class="q-steps">${quest.steps.map((_, i) => `<i class="${i < step || (i === step && solved) ? 'done' : i === step ? 'now' : ''}"></i>`).join('')}
      <span>${step + 1} / ${quest.steps.length}</span></div>
    ${im && !solved ? `<figure class="q-photo"><img src="${esc(im.thumb)}" alt="${t('Today’s photo of the building to find')}"></figure>
      <p class="q-credit">${t('Photo')}: ${link(im.page, [im.artist, im.license].filter(Boolean).join(', ') || 'Wikimedia Commons')}</p>` : ''}
    <p class="q-riddle">${esc(L10(s.riddle))}</p>
    ${s.count ? `<p class="q-count">${t('Any of {n} buildings counts.').replace('{n}', fmt(s.count))}</p>` : ''}
    ${hints ? `<ul class="q-hints">${hints}</ul>` : ''}
    ${solved ? foundHtml(s) : `<p class="q-feedback"></p>`}
    <div class="q-actions">${solved
      ? (last ? `<button class="primary q-list">${t('See all quests')}</button>`
              : `<button class="primary q-next">${t('Next riddle')}</button>`)
      : `${moreHints ? `<button class="q-hint">${t('Hint')} <small>−1</small></button>` : ''}
         ${s.layer ? `<button class="q-layer">${t('Open the layer')}</button>` : ''}${s.mode ? `<button class="q-mode">${t(MODE_LABEL[s.mode])}</button>` : ''}
         ${s.answer.bags ? `<button class="q-reveal">${t('Show me')}</button>` : ''}
         <span class="q-worth">${tiles(stepTiles(), 3)}</span>`}</div>`;
  questEl.hidden = false;
  markWalk();
  // On a phone the riddle folds to its title bar so the map stays usable; a tap on the bar opens it again.
  questEl.querySelector('header').onclick = () => { questFolded = !questFolded; questEl.classList.toggle('folded', questFolded); };
  questEl.querySelector('.q-close').onclick = closeQuest;
  const foldOnPhone = () => { if (phone.matches) { questFolded = true; questEl.classList.add('folded'); } };
  questEl.querySelector('.q-hint')?.addEventListener('click', () => { hintsShown++; renderQuest(); });
  questEl.querySelector('.q-layer')?.addEventListener('click', () => { showLayer(s.layer); foldOnPhone(); });
  questEl.querySelector('.q-mode')?.addEventListener('click', () => { setModeNamed(s.mode); foldOnPhone(); });
  questEl.querySelector('.q-reveal')?.addEventListener('click', () => {
    const g = answerGids(s.answer)[0];
    if (g === undefined) return;
    revealed = true;
    const b = building(g);
    flyTo(b.x, b.z, () => solve(g), 420);
  });
  questEl.querySelector('.q-next')?.addEventListener('click', () => { step++; resetStep(); answerCache = null; save(quest.id, { step, score }); renderQuest(); });
  questEl.querySelector('.q-list')?.addEventListener('click', () => { closeQuest(); openQuests(); });
}
function foundHtml(s) {
  const f = s.found, got = stepTiles(), last = step === quest.steps.length - 1;
  const head = `<div class="q-stamp" aria-hidden="true">${t('Found!')}</div>`;
  const tally = `<p class="q-earned">${tiles(got, 3)} ${got === 3 ? t('Without a single hint.') : revealed ? t('Shown, not found: no tiles.') : ''}</p>`;
  const end = last ? `<p class="q-final">${t('Quest complete')}: <b>${score}</b> / ${quest.steps.length * 3}</p>` : '';
  if (!f) return `<div class="q-found">${head}<b>${t('Right')}</b><p>${t('One of the buildings that answer the riddle.')}</p>${tally}${end}</div>`;
  return `<div class="q-found">${head}<b>${esc(LANG === 'nl' ? (f.name_nl || f.name) : f.name)}</b>
    <p>${esc(LANG === 'nl' ? (f.story_nl || f.story) : f.story)} ${link(f.source, t('Source'))}</p>${tally}${end}</div>`;
}
function solve(gid) {
  solved = true;
  questFolded = false;
  score += stepTiles();
  const st = store()[quest.id] || {};
  const patch = { step: step + 1, score };
  if (step === quest.steps.length - 1) patch.best = Math.max(st.best || 0, score);
  save(quest.id, patch);
  if (gid >= 0 && pinnedGid !== gid) uniforms.uSelected.value = gid;  // "Show me" marks it; a click has pinned it already
  renderQuest();
}
// Called on every click on the map while a quest is open.
function questClick(gid) {
  if (!quest || solved || gid < 0) return;
  const s = quest.steps[step];
  if (isAnswer(gid, s.answer)) { solve(gid); return; }
  misses++;
  const fb = questEl.querySelector('.q-feedback');
  if (!fb) return;
  const b = building(gid), targets = answerGids(s.answer);
  const d = targets.length ? Math.min(...targets.map(g => { const a = building(g); return Math.hypot(a.x - b.x, a.z - b.z); })) : Infinity;
  let msg = d < 60 ? t('Not this one, but very close.') : d < 250 ? t('Not this one. You are getting warm.')
    : d < 800 ? t('Not this one. Still a few streets away.') : t('Not this one. Far off.');
  if (misses >= 3 && hintsShown < s.hints.length) msg += ' ' + t('A hint may help.');
  fb.textContent = msg;
  fb.className = `q-feedback ${d < 60 ? 'hot' : d < 250 ? 'warm' : 'cold'}`;
  void fb.offsetWidth; fb.classList.add('miss');
}

// ---------- From the graph ----------
// graph.html opens the map with ./?focus=<id>,<id>: the buildings of those people, events or places light up,
// each selection in its own colour, and the rest of the city turns into a white model.
const focusEl = document.getElementById('focus');
const focusIds = (new URLSearchParams(location.search).get('focus') || '').split(',').filter(Boolean);
if (focusIds.length) fetch('data/graph.json').then(r => r.json()).then(G => showFocus(G, focusIds)).catch(() => {});
function showFocus(G, ids) {
  const groups = [], pts = [];
  ids.forEach((id, i) => {
    const node = G.nodes.find(n => n.id === id), place = G.places[id];
    if (!node && !place) return;
    const ps = place ? [place] : G.links.filter(l => l.e === id).map(l => G.places[l.p]);
    const bags = ps.flatMap(p => p.bags);
    pts.push(...ps.map(p => ({ x: p.x, z: p.z })));  // the attribute table here has no positions: take the graph's
    const label = place ? place.name : node.label;
    const pos = {};
    for (const p of ps) for (const k of p.bags) pos[k] = { x: p.x, z: p.z };
    groups.push({ label, pos, color: i % GROUP_COLORS.length, gids: [...new Set(bags)].map(gidOf).filter(g => g >= 0) });
  });
  const gids = [], grp = [];
  for (const g of groups) for (const gid of g.gids) {
    if (!gids.includes(gid) && gids.length < FOCUS_MAX) { gids.push(gid); grp.push(g.color); }
  }
  if (!gids.length) return;
  uniforms.uFocus.value = [...gids, ...Array(FOCUS_MAX - gids.length).fill(-1)];
  uniforms.uFocusGroup.value = [...grp, ...Array(FOCUS_MAX - grp.length).fill(0)];
  uniforms.uFocusN.value = gids.length;
  const cx = pts.reduce((a, b) => a + b.x, 0) / pts.length, cz = pts.reduce((a, b) => a + b.z, 0) / pts.length;
  const spread = Math.max(...pts.map(b => Math.hypot(b.x - cx, b.z - cz)));
  flyTo(cx, cz, null, Math.min(4200, Math.max(380, spread * 2.4)));
  const back = `graph.html?select=${encodeURIComponent(ids.join(','))}`;
  focusEl.innerHTML = `<header><b>${t('From the graph')}</b><button class="f-close" aria-label="${t('Close')}">×</button></header>
    <ul>${groups.map(g => `<li><i style="background:${GROUP_COLORS[g.color]}"></i><span>${esc(g.label)}</span>
      <small>${g.gids.length}</small></li>`).join('')}</ul>
    <div class="f-actions"><button class="make-walk">${t('Generate a walk')}</button><a class="f-back" href="${back}">${t('Back to the graph')}</a></div>`;
  focusEl.hidden = false;
  focusEl.querySelector('.make-walk').onclick = () => { focusEl.hidden = true; walkFromGroups(groups); };
  focusEl.querySelector('.f-close').onclick = () => {
    uniforms.uFocusN.value = 0;
    focusEl.hidden = true;
    const u = new URL(location.href); u.searchParams.delete('focus'); history.replaceState(null, '', u);
  };
}

// ---------- Panel ----------
const panelEl = document.getElementById('panel');
const panel = document.getElementById('panel-body');
const sheetHandle = panelEl.querySelector('.sheet-handle');
const phone = matchMedia('(max-width: 720px)');
// On a phone the panel is a sheet: folded to one line until opened, and folded again when a building is pinned.
function setCollapsed(c) {
  panelEl.classList.toggle('collapsed', c);
  sheetHandle.setAttribute('aria-expanded', String(!c));
  sheetHandle.textContent = 'Легенда';
  sheetHandle.setAttribute('aria-label', c ? 'Показать легенду' : 'Скрыть легенду');
}
let sheetSwiped = false;
sheetHandle.onclick = () => { if (sheetSwiped) { sheetSwiped = false; return; } setCollapsed(!panelEl.classList.contains('collapsed')); };
// On a phone the open legend folds when the map is touched, or when its bar is swiped down.
let sheetDown = null;
sheetHandle.addEventListener('pointerdown', e => { sheetDown = e.clientY; });
sheetHandle.addEventListener('pointerup', e => {
  if (sheetDown !== null && e.clientY - sheetDown > 30) { setCollapsed(true); sheetSwiped = true; }
  sheetDown = null;
});
document.getElementById('scene')?.addEventListener('pointerdown', () => {
  if (phone.matches && !panelEl.classList.contains('collapsed')) setCollapsed(true);
});
setCollapsed(phone.matches);
phone.addEventListener('change', () => setCollapsed(phone.matches));

const ICON = {
  'Buildings today': '<path d="M2.5 14.5h11"/><rect x="3" y="8" width="2.6" height="6.5"/><rect x="6.7" y="4" width="2.6" height="10.5"/><rect x="10.4" y="6" width="2.6" height="8.5"/>',
  'Люди и события': '<circle cx="8" cy="5" r="2.6"/><path d="M3 14.5c.4-3 2.4-4.6 5-4.6s4.6 1.6 5 4.6"/>',
  'Город': '<path d="M2 14.5h12"/><path d="M3 14.5V6h4v8.5M7 14.5V3h6v11.5"/><path d="M9 5.5h2M9 8h2M9 10.5h2"/>',
  'Архитектура': '<path d="M2 5.5 8 2l6 3.5z"/><path d="M3.5 6v7M6.5 6v7M9.5 6v7M12.5 6v7M2 14.5h12"/>',
  'Империя': '<path d="M3 12.5h10l1-6.5-3.5 3L8 3.5 5.5 9 2 6z"/><path d="M3 14.5h10"/>',
  'Советский город': '<rect x="2.5" y="5" width="5" height="9.5"/><rect x="8.5" y="2" width="5" height="12.5"/><path d="M4.5 7.5h1M4.5 10h1M10.5 4.5h1M10.5 7h1M10.5 9.5h1"/>',
  'Память': '<path d="M8 1.5c-.8 2-2.5 2.8-2.5 4.8a2.5 2.5 0 0 0 5 0C10.5 4.3 8.8 3.5 8 1.5z"/><path d="M5 14.5h6M8 9v5.5"/>',
};
const sectionIcon = sec => `<svg class="icon" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round">${ICON[sec] || ''}</svg>`;
const totals = periods.map(() => 0);
for (const v of Object.values(config.histogram)) v.forEach((n, i) => totals[i] += n);
const fmt = n => n.toLocaleString('ru');
let activeLayer = null;
const SECTION_ORDER = ['Люди и события', 'Город', 'Архитектура', 'Империя', 'Советский город', 'Память'];
const groupOn = {};

// Storeys are a view of the buildings themselves; it lives in the layers list.
function setBuildingView(m) {
  document.querySelectorAll('.modes button[data-mode]').forEach(x => x.setAttribute('aria-pressed', x.dataset.mode === String(MODE.layers)));
  activeLayer = null;
  uniforms.uGroupBit.value = Array(MAX_GROUPS).fill(-1);
  uniforms.uMode.value = m;
  if (!phone.matches) setCollapsed(false);
  renderPanel(); drawHist();
}
function renderPanel() {
  const mode = uniforms.uMode.value;
  if (mode === MODE.period) {
    const unknownBtn = `<button class="swatch" data-i="unknown" aria-pressed="${!!uniforms.uUnknown.value}">
        <i style="background:${config.unknown.color}"></i><span>${config.unknown.label}</span><span class="n">${fmt(config.unknown.count)}</span>
      </button>`;
    panel.innerHTML = `<h2>Построено</h2><div class="swatches">${periods.map((p, i) => `
      <button class="swatch" data-i="${i}" aria-pressed="${!!uniforms.uMask.value[i]}">
        <i style="background:${p.color}"></i><span>${p.label}</span><span class="n">${fmt(totals[i])}</span>
      </button>`).join('')}${unknownBtn}</div>
      <p class="note">Нажмите на эпоху, чтобы оставить только её. Бледные здания датированы приблизительно. Год известен у ${fmt(config.stats.dated)} зданий из ${fmt(config.stats.buildings)}.</p>`;
    panel.querySelectorAll('.swatch').forEach(b => b.onclick = () => {
      if (b.dataset.i === 'unknown') {
        uniforms.uUnknown.value = uniforms.uUnknown.value ? 0 : 1;
      } else {
        const i = +b.dataset.i, m = uniforms.uMask.value;
        const solo = m.every((v, j) => (j === i) === !!v);
        uniforms.uMask.value = periods.map((_, j) => (solo || j === i) ? 1 : 0);
        uniforms.uUnknown.value = solo ? 1 : 0;
      }
      renderPanel(); drawHist();
    });
  } else if (mode === MODE.floors) {
    panel.innerHTML = `<button class="back">Все слои</button><h2 class="layer-title">${sectionIcon('Buildings today')}Этажность</h2>
      <div class="ramp" style="background:linear-gradient(90deg,#dbe3e6,#7da8bf,#2b5c8c,#0d1a40)"></div>
      <div class="ramp-scale"><span>1</span><span>3</span><span>8</span><span>20</span><span>40+</span></div>
      <p class="note">Этажность указана в OpenStreetMap у ${fmt(config.stats.floorsTagged)} зданий; у остальных ${fmt(config.stats.floorsDefault + config.stats.floorsHeight)} она оценена по высоте или типу здания.</p>`;
    panel.querySelector('.back').onclick = () => { uniforms.uMode.value = MODE.layers; renderPanel(); drawHist(); };
  } else if (!activeLayer) {
    const sections = [...new Set(layers.map(L => L.section))].sort((a, b) => SECTION_ORDER.indexOf(a) - SECTION_ORDER.indexOf(b));
    panel.innerHTML = `<nav class="section-nav" aria-label="Разделы">${sections.map(sec => `
      <button data-sec="${esc(sec)}" title="${esc(sec)}" aria-label="${esc(sec)}">${sectionIcon(sec)}</button>`).join('')}</nav>` +
      sections.map(sec => `<h2 class="section" id="sec-${sections.indexOf(sec)}">${sectionIcon(sec)}${esc(sec)}</h2><div class="layers">${layers.filter(L => L.section === sec).map(L => `
      <button class="layer" data-id="${L.id}">
        <b>${esc(L.title)}</b><span class="n">${fmt(L.count)}</span><span class="era">${esc(L.era)}</span>
      </button>`).join('')}</div>`).join('');
    panel.querySelector('.section-nav').insertAdjacentHTML('afterend', `<h2 class="section" id="sec-today">${sectionIcon('Buildings today')}Здания сегодня</h2>
      <div class="layers"><button class="layer view" data-view="floors"><b>Этажность</b><span class="n">${fmt(config.stats.buildings)}</span><span class="era"></span></button></div>`);
    panel.querySelector('.section-nav').insertAdjacentHTML('afterbegin', `<button data-sec="today" title="Здания сегодня" aria-label="Здания сегодня">${sectionIcon('Buildings today')}</button>`);
    panel.querySelector('.layer.view').onclick = () => setBuildingView(MODE.floors);
    panel.querySelectorAll('.layer:not(.view)').forEach(b => b.onclick = () => {
      const L = layers.find(l => l.id === b.dataset.id);
      setLayer(L); fitToLayer(L);
    });
    panel.querySelectorAll('.section-nav button').forEach(b => b.onclick = () =>
      panel.querySelector(b.dataset.sec === 'today' ? '#sec-today' : `#sec-${sections.indexOf(b.dataset.sec)}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  } else {
    panel.innerHTML = `<button class="back">Все слои</button>
      <h2 class="layer-title">${sectionIcon(activeLayer.section)}${esc(activeLayer.title)}</h2><p class="layer-era">${activeLayer.era}</p>
      ${Object.values(activeLayer.notes || {}).some(n => n.at) ? `<button class="make-walk">Построить прогулку</button>` : ''}${layerDetail(activeLayer)}`;
    panel.querySelector('.back').onclick = () => setLayer(null);
    panel.querySelector('.make-walk')?.addEventListener('click', () => { if (phone.matches) setCollapsed(true); walkFromLayer(activeLayer); });
    panel.querySelectorAll('.story').forEach(b => b.onclick = () => {
      const n = activeLayer.notes[b.dataset.bag];
      flyTo(n.at[0], n.at[1], () => {
        const gid = gidOf(b.dataset.bag);
        if (gid >= 0) pinCard(gid, innerWidth * 0.62, innerHeight * 0.18);
      });
    });
    panel.querySelectorAll('.swatch').forEach(b => b.onclick = () => {
      groupOn[b.dataset.bit] = groupOn[b.dataset.bit] === false;
      setLayer(activeLayer); fitToLayer(activeLayer);
    });
  }
}

function layerDetail(L) {
  const groups = L.groups.length > 1 ? `<div class="swatches">${L.groups.map((g, i) => `
    <button class="swatch" data-bit="${g.bit}" aria-pressed="${groupOn[g.bit] !== false}">
      <i style="background:${GROUP_COLORS[i]}"></i><span>${g.label}</span><span class="n">${fmt(g.count)}</span>
    </button>`).join('')}</div>` : '';
  const named = Object.entries(L.notes || {}).filter(([, n]) => n.name && n.at);
  const stories = named.length ? `<h2 class="section">Здания и их истории</h2><ul class="stories">${named.map(([bag, n]) => `
    <li><button class="story" data-bag="${bag}"><b>${esc(n.name)}</b><span>${esc(n.story)}</span></button></li>`).join('')}</ul>` : '';
  return `<div class="layer-detail"><p>${L.text}</p>${groups}${stories}
    ${L.caveat ? `<p class="caveat">${L.caveat}</p>` : ''}
    <a href="${L.source.url}" target="_blank" rel="noopener">${L.source.label}</a></div>`;
}

function fitToLayer(L) {
  if (!L) return;
  // The attribute table here has no positions: frame the buildings the layer tells stories about.
  const pts = Object.values(L.notes || {}).filter(n => n.at);
  const xs = pts.map(n => n.at[0]), zs = pts.map(n => n.at[1]);
  if (!xs.length) return;
  const cut = a => { a.sort((p, q) => p - q); const k = a.length > 50 ? Math.floor(a.length * 0.02) : 0; return [a[k], a[a.length - 1 - k]]; };
  const [x0, x1] = cut(xs), [z0, z1] = cut(zs);
  // On a wide screen the panel covers the left of the view: frame the points in the part to its right.
  const pr = !phone.matches && !panelEl.classList.contains('collapsed') ? panelEl.getBoundingClientRect().right : 0;
  const free = Math.max(0.4, 1 - pr / innerWidth);
  const half = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  const span = Math.max(z1 - z0, (x1 - x0) / (camera.aspect * free), 120);
  const distance = Math.min(7000, Math.max(320, span / 2 / half * 1.35));
  const right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0).setY(0).normalize();
  const shift = (pr / innerWidth / 2) * 2 * distance * half * camera.aspect;
  const cx = (x0 + x1) / 2 - right.x * shift, cz = (z0 + z1) / 2 - right.z * shift;
  if (Number.isFinite(cx) && Number.isFinite(cz) && Number.isFinite(distance)) flyTo(cx, cz, null, distance);
}

function setLayer(L) {
  activeLayer = L;
  history.replaceState(null, '', L ? `#layer=${L.id}` : location.pathname + location.search);
  const bits = Array(MAX_GROUPS).fill(-1);
  if (L) L.groups.forEach((g, i) => { if (i < MAX_GROUPS && groupOn[g.bit] !== false) bits[i] = g.bit; });
  uniforms.uGroupBit.value = bits;
  renderPanel(); drawHist();
}

document.querySelectorAll('.modes button[data-mode]').forEach(b => b.onclick = () => {
  uniforms.uMode.value = +b.dataset.mode;
  document.querySelectorAll('.modes button[data-mode]').forEach(x => x.setAttribute('aria-pressed', x === b));
  renderPanel(); drawHist();
});

// ---------- Timeline ----------
const hist = document.getElementById('hist');
const hctx = hist.getContext('2d');
const T0 = Math.floor(config.yearMin / 50) * 50, T1 = config.yearMax + 1;
const years = Object.entries(config.histogram).map(([y, v]) => [+y, v]);
const yMax = Math.max(...years.map(([, v]) => v.reduce((a, b) => a + b, 0)));
const xOf = y => (y - T0) / (T1 - T0) * hist.clientWidth;
const yearOf = x => Math.round(T0 + x / hist.clientWidth * (T1 - T0));

function layerGroupsShown() {
  if (uniforms.uMode.value !== MODE.layers || !activeLayer) return [];
  return activeLayer.groups.map((g, i) => ({ ...g, color: GROUP_COLORS[i] })).filter(g => groupOn[g.bit] !== false);
}

function visibleCount() {
  const Y = uniforms.uYear.value;
  const shown = layerGroupsShown();
  if (shown.length) return shown.reduce((n, g) => n + Object.entries(g.years).reduce((m, [y, c]) => m + (+y <= Y ? c : 0), 0), 0);
  let n = 0;
  for (const [y, v] of years) if (y <= Y) v.forEach((c, i) => { if (uniforms.uMode.value !== MODE.period || uniforms.uMask.value[i]) n += c; });
  // Buildings without a year join the count, as on the map, once the timeline reaches today.
  if (Y >= config.yearMax && (uniforms.uMode.value !== MODE.period || uniforms.uUnknown.value)) n += config.unknown.count;
  return n;
}

const plural = (n, one, few, many) => {
  const m10 = n % 10, m100 = n % 100;
  return m10 === 1 && m100 !== 11 ? one : m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14) ? few : many;
};

function drawHist() {
  const w = hist.clientWidth, h = hist.clientHeight, dpr = devicePixelRatio;
  hist.width = w * dpr; hist.height = h * dpr;
  hctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  hctx.clearRect(0, 0, w, h);
  const plotH = h - 20, bw = Math.max(1, w / (T1 - T0));
  const Y = uniforms.uYear.value, Yf = uniforms.uYearFrom.value;
  const shown = layerGroupsShown();
  const bar = (y, bh, top, color, on) => {
    hctx.fillStyle = color;
    hctx.globalAlpha = on ? (y <= Yf ? 0.3 : 1) : 0.18;
    hctx.fillRect(xOf(y), top - bh, bw, bh);
  };
  if (shown.length) {
    // Layer mode: the city in grey behind, the layer's own buildings in its colours.
    for (const [y, v] of years) {
      const bh = Math.sqrt(v.reduce((a, b) => a + b, 0) / yMax) * (plotH - 6);
      bar(y, bh, plotH, '#b9c0c4', false);
    }
    // Stack the groups per year; the stack's total height follows sqrt(total), split in proportion.
    const total = {};
    for (const g of shown) for (const [y, c] of Object.entries(g.years)) total[y] = (total[y] || 0) + c;
    const lMax = Math.max(1, ...Object.values(total));
    const stack = {};
    for (const g of shown) for (const [ys, c] of Object.entries(g.years)) {
      const y = +ys, full = Math.sqrt(total[ys] / lMax) * (plotH - 6) * 0.9, bh = full * c / total[ys];
      bar(y, bh, plotH - (stack[y] || 0), g.color, y <= Y);
      stack[y] = (stack[y] || 0) + bh;
    }
  } else {
    for (const [y, v] of years) {
      let top = plotH;
      v.forEach((c, i) => {
        if (!c) return;
        const bh = Math.sqrt(c / yMax) * (plotH - 6);
        const masked = uniforms.uMode.value === MODE.period && !uniforms.uMask.value[i];
        bar(y, bh, top, periods[i].color, !masked && y <= Y);
        top -= bh;
      });
    }
  }
  hctx.globalAlpha = 1;
  hctx.fillStyle = '#5d6266';
  hctx.font = '500 11px "Onest", sans-serif';
  for (let y = Math.ceil(T0 / 100) * 100; y <= T1; y += 100) hctx.fillText(y, Math.max(0, xOf(y) - 13), h - 4);
  hctx.fillStyle = '#000';
  hctx.fillRect(xOf(Y) - 1, 0, 2, plotH);
  if (Yf >= T0) { hctx.fillStyle = '#5d6266'; hctx.fillRect(xOf(Yf) - 0.5, 0, 1, plotH); }
  // at the end of the timeline the map shows the city as it stands, not a year that reads like a date
  document.getElementById('year').textContent = Y >= config.yearMax ? 'Сегодня' : Math.round(Y);
  const n = visibleCount();
  document.getElementById('count').textContent = fmt(n);
  document.getElementById('count-word').textContent = plural(n, 'здание', 'здания', 'зданий');
}

let handle = null;
hist.addEventListener('pointerdown', e => {
  hist.setPointerCapture(e.pointerId);
  const x = e.offsetX;
  handle = Math.abs(x - xOf(uniforms.uYearFrom.value)) < Math.abs(x - xOf(uniforms.uYear.value)) ? 'uYearFrom' : 'uYear';
  moveHandle(x);
  stopPlay();
});
hist.addEventListener('pointermove', e => handle && moveHandle(e.offsetX));
hist.addEventListener('pointerup', () => handle = null);
function moveHandle(x) {
  const y = Math.max(T0, Math.min(config.yearMax, yearOf(x)));
  if (handle === 'uYear') uniforms.uYear.value = Math.max(y, uniforms.uYearFrom.value + 1);
  else uniforms.uYearFrom.value = Math.min(y, uniforms.uYear.value - 1);
  drawHist();
}

// Play: quickly through the sparse centuries, then slowly through the dense ones.
let playing = false, playT0 = 0, playStart = 0;
const playBtn = document.getElementById('play');
const playIcon = document.getElementById('play-icon');
const DURATION = (+new URLSearchParams(location.search).get('film') || 30) * 1000; // ?film=6 for a short film
function playYear(t) {
  const k = 0.35; // share of time spent before 1850
  return t < k ? T0 + (1850 - T0) * (t / k) : 1850 + (config.yearMax - 1850) * ((t - k) / (1 - k));
}
function startPlay() {
  playing = true; playStart = performance.now();
  if (uniforms.uYear.value >= config.yearMax) uniforms.uYear.value = T0;
  playT0 = 0;
  while (playT0 < 1 && playYear(playT0) < uniforms.uYear.value) playT0 += 0.001;
  playIcon.setAttribute('d', 'M4 2.5h3v11H4zM9 2.5h3v11H9z');
  uniforms.uPlaying.value = 1;
  playBtn.setAttribute('aria-label', 'Пауза');
}
function stopPlay() {
  playing = false;
  uniforms.uPlaying.value = 0;
  uniforms.uRise.value = 0.01;
  uniforms.uYear.value = Math.round(uniforms.uYear.value);
  playIcon.setAttribute('d', 'M4 2.5v11l9-5.5z');
  playBtn.setAttribute('aria-label', 'Показать, как рос город');
}
playBtn.onclick = () => playing ? stopPlay() : startPlay();

// ---------- Search ----------
// The index (pipeline/s13_search.py) loads on the first click on the magnifier; house numbers come in shards,
// a few streets' worth at a time, when a street is asked for.
const STREET_TYPES = { 'улица': 'улица', 'ул': 'улица', 'проспект': 'проспект', 'пр': 'проспект', 'пр-т': 'проспект',
  'пр-кт': 'проспект', 'просп': 'проспект', 'набережная': 'набережная', 'наб': 'набережная', 'переулок': 'переулок',
  'пер': 'переулок', 'площадь': 'площадь', 'пл': 'площадь', 'бульвар': 'бульвар', 'б-р': 'бульвар', 'бул': 'бульвар',
  'шоссе': 'шоссе', 'ш': 'шоссе', 'проезд': 'проезд', 'пр-д': 'проезд', 'линия': 'линия', 'линии': 'линия', 'лин': 'линия',
  'аллея': 'аллея', 'дорога': 'дорога', 'дор': 'дорога', 'тупик': 'тупик', 'туп': 'тупик', 'мост': 'мост', 'спуск': 'спуск',
  'сквер': 'сквер', 'сад': 'сад' };
const STREET_FILLER = new Set(['реки', 'р', 'река', 'канала', 'кан', 'канал', 'острова', 'о', 'о-в']);
const normal = s => String(s).toLowerCase().replace(/ё/g, 'е').replace(/[–—]/g, '-')
  .replace(/в\.\s*о\.?/g, ' во ').replace(/п\.\s*с\.?/g, ' пс ')
  .replace(/васильевского острова/g, 'во').replace(/петроградской стороны/g, 'пс')
  .replace(/[^a-zа-я0-9/-]+/g, ' ').replace(/\s+/g, ' ').trim();
// 'мойка' and 'мойки', 'невский' and 'невская' meet at their stems
const stem = w => { let s = w; for (let i = 0; i < 2 && s.length > 4 && /[аяоеыийьуюэ]$/.test(s); i++) s = s.slice(0, -1); return s; };
function streetWords(name) {
  const core = [], types = [];
  for (const w of normal(name).split(' ')) {
    if (!w || STREET_FILLER.has(w)) continue;
    if (STREET_TYPES[w]) types.push(STREET_TYPES[w]); else core.push(w);
  }
  return { core, types };
}
// House numbers: '28', '28а', '12/14', '114-116', '25а к1 литБ', as the pipeline writes them and as people type them.
function parseNumber(s) {
  const t = normal(s).replace(/(\d)(корпус|корп|к|литера|лит|л|строение|стр|с)(?=\s*[\dа-я])/g, '$1 $2').split(' ');
  const m = t[0]?.match(/^(\d+(?:-\d+)*)([а-я])?(?:\/(\d+[а-я]?))?$/);
  if (!m) return null;
  const rest = ' ' + t.slice(1).join(' ');
  const lit = rest.match(/\s(?:литера|лит|л)\s*([а-я]\d*)/)?.[1] || '';
  return { nums: m[1].split('-').map(Number), letter: m[2] || rest.replace(/\s(?:литера|лит|л)\s*[а-я]\d*/, '').match(/\s([а-я])(?=\s|$)/)?.[1] || '',
    slash: m[3] || '', k: rest.match(/\s(?:корпус|корп|к)\s*(\d+)/)?.[1] || '', s: rest.match(/\s(?:строение|стр|с)\s*(\d+)/)?.[1] || '', lit };
}
const isNumber = w => /^\d+[а-я]?(?:\/\d+[а-я]?)?$/.test(w) || /^\d+(?:-\d+)+$/.test(w) ||
  /^\d+(корпус|корп|к|литера|лит|л|строение|стр|с)\d*[а-я]?$/.test(w);
const isSuffix = w => /^(корпус|корп|к|литера|лит|л|строение|стр|с)?\d*[а-я]?\d*$/.test(w) && w.length <= 9 ||
  /^(корпус|корп|литера|строение)$/.test(w);
// 'Невский 28', 'наб. Мойки, д. 12 лит. А', '8-я линия 25': the street, then the number with its parts
function splitQuery(q) {
  const w = normal(q).split(' ').filter(Boolean);
  for (let i = w.length - 1; i >= 1; i--) {
    if (!isNumber(w[i]) || !w.slice(i + 1).every(isSuffix)) continue;
    const street = w.slice(0, i).filter((x, j, a) => !(j === a.length - 1 && /^(д|дом)$/.test(x)));
    if (street.some(x => /[а-яa-z]/.test(x))) return { street: street.join(' '), num: parseNumber(w.slice(i).join(' ')) };
  }
  return null;
}

let index = null;
const shardCache = {};
function loadIndex() {
  index ??= fetch('data/search.json').then(r => r.json()).then(d => {
    const count = {};
    d.streets = d.streets.map(([n, shard, size, x, z, dist, split]) => {
      count[n] = (count[n] || 0) + 1;
      return { n, shard, size, x, z, dist, key: split ? `${n}\t${dist}` : n, ...streetWords(n) };
    });
    // namesakes in different districts say which district they are in
    d.streets.forEach(st => { st.namesake = count[st.n] > 1; });
    d.names.forEach(n => { n.key = normal(n[0]); n.words = n.key.split(' '); });
    return d;
  });
  return index;
}
function loadShard(k) {
  shardCache[k] ??= fetch(`data/search/${k}.json`).then(r => r.json()).then(sh => {
    for (const list of Object.values(sh)) list.forEach(e => { e.p = parseNumber(e[0]); });
    return sh;
  });
  return shardCache[k];
}
async function entriesOf(st) { return (await loadShard(st.shard))[st.key] || []; }

// How well the typed street fits a street: every typed word must start one of its words (or meet it at the stem).
function streetScore(st, q) {
  let score = 0;
  for (const w of q.core) {
    let best = 0;
    for (const c of st.core) {
      best = Math.max(best, c === w ? 3 : c.startsWith(w) ? 2 : stem(c).startsWith(stem(w)) && stem(w).length >= 3 ? 1.5 : 0);
    }
    if (!best) return 0;
    score += best;
  }
  for (const t of q.types) score += st.types.includes(t) ? 1 : -0.5;
  // 'Садовая' is Садовая улица before Малая Садовая; 'В.О.' and 'П.С.' only say which island
  const own = st.core.filter(w => w !== 'во' && w !== 'пс').length;
  if (q.core.filter(w => w !== 'во' && w !== 'пс').length === own) score += 1;
  return score;
}
function findStreets(d, text, strict) {
  const q = streetWords(text);
  if (!q.core.length) return [];
  return d.streets.map(st => [st, streetScore(st, q)]).filter(([, s]) => s > 0)
    .sort((a, b) => b[1] - a[1] || b[0].size - a[0].size)
    // a weaker fit only alongside fits as good: 'Невский' is Невский проспект, not also улица Александра Невского
    .filter(([, s], _, all) => !strict || s >= all[0][1] - 0.5).map(([st]) => st);
}
// The house among a street's numbers: the same number, as plain as the query allows; or the nearest on its side.
function bestHouse(entries, q) {
  const want = q.nums[0];
  let best = null, bestScore = Infinity;
  for (const e of entries) {
    const p = e.p;
    if (!p || !p.nums.includes(want)) continue;
    const part = (a, b, cost) => a ? (a === b ? 0 : 100) : (b ? cost : 0);
    const s = (p.nums[0] === want ? 0 : 1) + part(q.letter, p.letter, 4) + part(q.k, p.k, 3) + part(q.s, p.s, 2) +
      part(q.lit, p.lit, p.lit === 'а' ? 0.5 : 1) + (q.slash && q.slash !== p.slash ? 0.2 : 0);
    if (s < bestScore) { best = e; bestScore = s; }
  }
  if (best) return { e: best, exact: bestScore < 100, near: false };
  const same = entries.filter(e => e.p && e.p.nums[0] % 2 === want % 2);
  const near = same.sort((a, b) => Math.abs(a.p.nums[0] - want) - Math.abs(b.p.nums[0] - want))[0];
  return near ? { e: near, exact: false, near: true } : null;
}

const findInput = document.getElementById('find-input');
const findList = document.getElementById('find-results');
const findSel = document.getElementById('find-sel');
// The magnifier stands just right of the mode bar, whose width depends on the fonts.
const findBox = findInput.closest('.find'), modesBar = document.querySelector('.modes');
function placeFind() {
  if (phone.matches) { findBox.style.left = ''; return; }
  // while in use it widens, and must stay on screen
  const open = findBox.matches(':focus-within') || !findSel.hidden;
  const w = open ? 300 : findBox.offsetWidth;
  findBox.style.left = `${Math.min(modesBar.getBoundingClientRect().right + 8, innerWidth - w - 16)}px`;
}
addEventListener('resize', placeFind);
document.fonts?.ready.then(placeFind);
setTimeout(placeFind, 0);
findInput.addEventListener('focus', placeFind);
findInput.addEventListener('blur', () => setTimeout(placeFind, 200));
let results = [], active = -1, asked = 0;

async function search(text, d) {
  const k = normal(text);
  if (k.length < 2) return [];
  const out = [];
  const a = splitQuery(text);
  if (a?.num) {
    const houses = [];
    for (const st of findStreets(d, a.street, true).slice(0, 4)) {
      const h = bestHouse(await entriesOf(st), a.num);
      if (h) houses.push([st, h]);
    }
    // the nearest house on another street only when no street has the house itself
    const any = houses.some(([, h]) => h.exact);
    for (const [st, h] of houses) {
      if (any && !h.exact) continue;
      out.push({ kind: 'address', label: `${st.n}, ${h.e[0]}`, street: st, house: h.e,
        note: h.exact ? null : h.near ? `Дома ${a.num.nums[0]} в данных нет; ближайший на той же стороне улицы`
          : `Такого корпуса или литеры в данных нет; показан дом ${h.e[0]}` });
    }
  }
  const words = k.split(' ');
  const named = d.names.filter(n => n.key.includes(k) || words.every(w => n.words.some(x => x.startsWith(w))))
    .sort((p, q) => (q.key.startsWith(k) - p.key.startsWith(k)) || (q.key.includes(k) - p.key.includes(k)) ||
      p[0].length - q[0].length);
  const streets = a ? [] : findStreets(d, text).slice(0, 4).map(st => ({ kind: 'street', label: st.n, street: st }));
  // a street typed in full comes before the buildings named after it ('Каменноостровский', 'Садовая')
  const q = streetWords(text);
  const full = streets.filter(r => q.core.length && q.core.every(w => r.street.core.includes(w))).slice(0, 2);
  out.push(...full);
  for (const n of named.slice(0, a ? 3 : 5)) out.push({ kind: 'name', label: n[0], sub: d.kinds[n[1]] + (n[4] ? ` · ${n[4]}` : ''), name: n });
  out.push(...streets.filter(r => !full.includes(r)));
  return out.slice(0, 8);
}
const plural3 = (n, one, few, many) => { const m10 = n % 10, m100 = n % 100; return m10 === 1 && m100 !== 11 ? one : m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14) ? few : many; };
function subOf(r, d) {
  if (r.kind === 'name') return r.sub;
  const st = r.street, where = st.namesake && d.districts[st.dist] ? ` · ${d.districts[st.dist]}` : '';
  if (r.kind === 'address') return `Адрес${where}`;
  return `Улица${where} · ${fmt(st.size)} ${plural3(st.size, 'здание', 'здания', 'зданий')}`;
}
async function renderResults() {
  const d = await loadIndex();
  findList.innerHTML = results.map((r, i) => `<li role="option" data-i="${i}" aria-selected="${i === active}">
    <b>${esc(r.label)}</b><span>${esc(subOf(r, d))}</span>${r.note ? `<em>${esc(r.note)}</em>` : ''}</li>`).join('')
    || (normal(findInput.value).length > 1 ? '<li class="none">Ничего не нашлось</li>' : '');
  findList.hidden = !findList.innerHTML;
  findInput.setAttribute('aria-expanded', String(!findList.hidden));
  findList.querySelectorAll('[data-i]').forEach(li => li.onmousedown = e => { e.preventDefault(); choose(results[+li.dataset.i]); });
}
findInput.addEventListener('focus', loadIndex);
findInput.addEventListener('input', async () => {
  const n = ++asked, d = await loadIndex();
  const r = await search(findInput.value, d);
  if (n !== asked) return;  // a later keystroke has its own answer
  results = r; active = results.length ? 0 : -1;
  renderResults();
});
findInput.addEventListener('keydown', e => {
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault();
    if (results.length) active = (active + (e.key === 'ArrowDown' ? 1 : -1) + results.length) % results.length;
    renderResults();
  } else if (e.key === 'Enter' && results[active]) { choose(results[active]); }
  else if (e.key === 'Escape') { findList.hidden = true; findInput.blur(); }
  e.stopPropagation();
});
findInput.addEventListener('blur', () => setTimeout(() => { findList.hidden = true; }, 150));

// What the search found stays lit while the rest of the city dims.
let found = null;
function setLit(gids) {
  pickData.fill(0);
  for (const g of gids) pickData[g] = 255;
  pickTex.needsUpdate = true;
  uniforms.uPickOn.value = gids.length ? 1 : 0;
}
function clearFound() {
  if (found && pinnedGid >= 0) pinCard(-1);
  found = null; findSel.hidden = true; setLit([]); orbit = false; placeFind();
}
async function choose(r) {
  findList.hidden = true; findInput.blur();
  findInput.value = r.label;
  found = r;
  renderSel();
  if (r.kind === 'street') {
    const es = await entriesOf(r.street);
    if (found !== r || !es.length) return;
    setLit([...new Set(es.map(e => e[1]))]);
    pinCard(-1);
    const xs = es.map(e => e[2]), zs = es.map(e => e[3]);
    const span = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...zs) - Math.min(...zs), 150);
    flyTo((Math.max(...xs) + Math.min(...xs)) / 2, (Math.max(...zs) + Math.min(...zs)) / 2, null, Math.min(5000, span * 1.5));
    return;
  }
  let gids, x, z;
  if (r.kind === 'address') {
    // every building under this number: a house of several parts lights up whole
    const es = await entriesOf(r.street);
    gids = [...new Set(es.filter(e => e[0] === r.house[0]).map(e => e[1]))];
    [, , x, z] = r.house;
  } else {
    gids = r.name.slice(5); [x, z] = r.name.slice(2, 4);
  }
  if (found !== r) return;
  setLit(gids);
  const g = r.kind === 'address' ? r.house[1] : gids[0];
  flyTo(x, z, () => { if (found === r) { pinCard(g, innerWidth * 0.62, innerHeight * 0.2); orbit = true; } }, 420);
}
function renderSel() {
  if (!found) { findSel.hidden = true; return; }
  findSel.innerHTML = `<span>${esc(found.label)}</span><button class="sel-clear" aria-label="Сбросить поиск">×</button>`;
  findSel.hidden = false;
  placeFind();
  findSel.querySelector('.sel-clear').onclick = () => { clearFound(); findInput.value = ''; };
}

// The camera slowly circles what was found, until the viewer takes over.
let orbit = false;
canvas.addEventListener('pointerdown', () => { orbit = false; });
canvas.addEventListener('wheel', () => { orbit = false; }, { passive: true });
controls.autoRotateSpeed = 0.6;
const orbitTick = () => { controls.autoRotate = orbit && !flight; requestAnimationFrame(orbitTick); };
orbitTick();

// ---------- Loop ----------
function resize() {
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  drawHist();
}
addEventListener('resize', resize);
const about = document.getElementById('about');
document.querySelector('.about-open').onclick = () => about.showModal();
about.querySelector('.about-close').onclick = () => about.close();
about.addEventListener('click', e => { if (e.target === about) about.close(); });

// A shared link to a layer opens it: #layer=pushkin
const fromHash = location.hash.match(/layer=([\w-]+)/)?.[1];
const linked = fromHash && layers.find(L => L.id === fromHash);
if (linked) {
  uniforms.uMode.value = MODE.layers;
  document.querySelectorAll('.modes button[data-mode]').forEach(x => x.setAttribute('aria-pressed', String(+x.dataset.mode === MODE.layers)));
  setLayer(linked);
} else {
  renderPanel();
}
resize();
document.fonts?.ready.then(drawHist);

let frame = 0;
renderer.setAnimationLoop(now => {
  frame++;
  stepFlight(now);
  uniforms.uNow.value = now / 1000;
  controls.update();
  const dist = camera.position.distanceTo(controls.target);
  uniforms.uFog.value.set(dist * 1.6, dist * 4);
  if (frame % 6 === 0) updateLabels(dist);
  if (playing) {
    const t = Math.min(1, playT0 + (now - playStart) / DURATION);
    uniforms.uYear.value = playYear(t);
    // A flight lasts about 0.8 s on screen whatever the film's pace: as many years as the film covers in that time.
    uniforms.uRise.value = Math.max(2, (playYear(Math.min(1, t + 800 / DURATION)) - playYear(t)));
    if (t >= 1) stopPlay();
    drawHist();
  }
  if (pointer && !dragging && frame % 3 === 0) {
    const gid = pick(pointer[0], pointer[1]);
    uniforms.uHover.value = gid;
    showCard(gid, pointer[0], pointer[1]);
  }
  renderer.render(scene, camera);
});


window.__dbg = { pick, uniforms, camera, controls, setLayer, layers, pinCard, showCard, building, labelGroup, labels, flyTo, startPlay, gidOf };
