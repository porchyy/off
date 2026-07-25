import { FilesetResolver, PoseLandmarker, DrawingUtils } from 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/vision_bundle.js?module';
import { createStorage, defaultSettings } from './storage.js';

const $ = id => document.getElementById(id);
const video = $('video');
const canvas = $('overlay');
const ctx = canvas.getContext('2d');
const start = $('start');
const stop = $('stop');

let storage;
let landmarker;
let stream;
let running = false;
let frame;
let lastVideoTime = -1;
let lastSave = 0;
let lastAlert = 0;
let lastMetricAt = 0;
let poorPostureMs = 0;
let detectionSignal = 'neutral';
let settings = { ...defaultSettings };

const toast = msg => {
  const el = $('toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3500);
};

const state = (name, cls = 'neutral') => {
  const el = $('cameraState');
  el.textContent = name;
  el.className = `badge ${cls}`;
};

function applyStorageMode() {
  const demo = storage.isDemo;
  $('demoBanner').hidden = !demo;
  $('dataDirField').hidden = demo;
  $('historyEyebrow').textContent = demo ? 'DEMO · LOCALSTORAGE' : 'LOCAL SQLITE DATABASE';
  $('settingsNote').textContent = demo
    ? 'โหมดตัวอย่างจะเก็บข้อมูลไว้ในเบราว์เซอร์นี้เท่านั้น ถ้าล้างข้อมูลเว็บหรือเปลี่ยนเบราว์เซอร์ ประวัติจะหาย'
    : 'การเปลี่ยน path ฐานข้อมูลจะมีผลหลังรีสตาร์ท server เพื่อย้ายไฟล์ SQLite ไปตำแหน่งใหม่';
}

function scorePose(l) {
  const nose = l[0], ls = l[11], rs = l[12], lh = l[23], rh = l[24];
  if (![nose, ls, rs, lh, rh].every(x => x?.visibility > 0.45)) return null;
  const sh = { x: (ls.x + rs.x) / 2, y: (ls.y + rs.y) / 2 };
  const hip = { x: (lh.x + rh.x) / 2, y: (lh.y + rh.y) / 2 };
  const neck = Math.abs(Math.atan2(nose.x - sh.x, nose.y - sh.y) * 180 / Math.PI);
  const shoulders = Math.abs(ls.y - rs.y) * 100;
  const torso = Math.abs(Math.atan2(sh.x - hip.x, sh.y - hip.y) * 180 / Math.PI);
  const score = Math.max(0, Math.min(100, 100 - Math.max(0, neck - 12) * 2.3 - shoulders * 1.4 - Math.max(0, torso - 7) * 2));
  return { neck, shoulders, torso, score };
}

function updateRisk(m) {
  const now = performance.now();
  const delta = lastMetricAt ? Math.min(now - lastMetricAt, 1000) : 0;
  lastMetricAt = now;
  if (m.score < settings.riskThreshold) poorPostureMs += delta;
  else poorPostureMs = Math.max(0, poorPostureMs - delta * 0.35);

  const high = m.score < settings.riskThreshold - 10 || poorPostureMs >= settings.riskSeconds * 1000;
  detectionSignal = high ? 'risk' : 'good';

  $('officeRiskCard').className = `risk-card card ${high ? 'risk' : 'good'}`;
  $('cameraSignal').className = `camera-signal ${high ? 'risk' : 'good'}`;
  $('cameraSignal').textContent = high ? 'สีแดง: เสี่ยงจากท่านั่ง' : 'สีเขียว: ท่านั่งอยู่ในเกณฑ์ดี';
  $('officeRisk').textContent = high ? 'สีแดง · เสี่ยงจากท่านั่ง' : 'สีเขียว · ความเสี่ยงจากท่านั่งต่ำ';
  $('riskReason').textContent = high
    ? `ตรวจพบท่าค้างหรือโน้มตัวต่อเนื่อง ${Math.round(poorPostureMs / 1000)} วินาที ควรลุกพักและปรับเก้าอี้/จอภาพ`
    : 'ท่าที่เห็นตอนนี้ใกล้กลางลำตัว และยังไม่พบการค้างในระดับเตือน';
  if (high) notifyRisk();
}

function update(m) {
  const s = Math.round(m.score);
  const cls = s >= 80 ? 'good' : s >= settings.riskThreshold ? 'caution' : 'risk';
  $('score').value = s;
  $('score').textContent = s;
  $('score').style.color = `var(--status-${cls})`;
  $('status').textContent = s >= 80 ? 'ท่านั่งดี' : s >= settings.riskThreshold ? 'เริ่มโน้มตัว' : 'ควรปรับท่า';
  $('advice').textContent = s >= 80 ? 'รักษาระดับสายตาและไหล่ให้ผ่อนคลาย' : s >= settings.riskThreshold ? 'ลองยืดหลังและดึงคางเข้าเล็กน้อย' : 'พักสั้น ๆ แล้วจัดหลังให้ตรง';
  $('neck').textContent = `${m.neck.toFixed(0)}°`;
  $('shoulders').textContent = `${m.shoulders.toFixed(1)}%`;
  $('torso').textContent = `${m.torso.toFixed(0)}°`;
  state(s >= 80 ? 'กำลังติดตาม' : s >= settings.riskThreshold ? 'ควรระวัง' : 'ควรปรับท่า', cls);
  updateRisk(m);
}

async function save(m) {
  const now = Date.now();
  if (now - lastSave > 30000) {
    lastSave = now;
    try {
      await storage.addSample(m);
      loadDashboard();
    } catch {
      toast('บันทึกข้อมูลไม่สำเร็จ');
    }
  }

  if (m.score < settings.riskThreshold && now - lastAlert > 120000) {
    lastAlert = now;
    try {
      await storage.addAlert({ severity: 'risk', message: 'ตรวจพบท่านั่งที่ควรปรับ' });
      loadDashboard();
    } catch {}
  }
}

function draw(result) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!result.landmarks?.length) return;
  const colors = detectionSignal === 'risk'
    ? { line: '#ff4d6d', dot: '#ff9aaa', glow: 'rgba(255,77,109,.28)' }
    : { line: '#22e58d', dot: '#00e5c7', glow: 'rgba(34,229,141,.22)' };
  ctx.save();
  ctx.fillStyle = colors.glow;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.restore();
  const d = new DrawingUtils(ctx);
  d.drawConnectors(result.landmarks[0], PoseLandmarker.POSE_CONNECTIONS, { color: colors.line, lineWidth: 5 });
  d.drawLandmarks(result.landmarks[0], { color: colors.dot, radius: 5 });
}

function loop() {
  if (!running) return;
  if (video.currentTime !== lastVideoTime) {
    lastVideoTime = video.currentTime;
    const result = landmarker.detectForVideo(video, performance.now());
    draw(result);
    const m = result.landmarks?.[0] && scorePose(result.landmarks[0]);
    if (m) {
      update(m);
      save(m);
    }
  }
  frame = requestAnimationFrame(loop);
}

async function begin() {
  if (!window.isSecureContext) {
    toast('กรุณาเปิดผ่าน HTTPS หรือ http://localhost:3000');
    return;
  }
  start.disabled = true;
  state('กำลังโหลด AI');
  try {
    const vision = await FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm');
    landmarker = await PoseLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
        delegate: 'GPU'
      },
      runningMode: 'VIDEO',
      numPoses: 1
    });
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
    video.srcObject = stream;
    await video.play();
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    running = true;
    $('cameraHelp').hidden = true;
    start.disabled = true;
    stop.disabled = false;
    state('กำลังติดตาม', 'good');
    loop();
  } catch (e) {
    console.error(e);
    state('เริ่มไม่ได้', 'risk');
    start.disabled = false;
    toast(navigator.onLine ? 'เปิดกล้องหรือ AI ไม่สำเร็จ โปรดอนุญาตกล้องแล้วลองใหม่' : 'ไม่มีอินเทอร์เน็ต จึงโหลด AI จาก CDN ไม่ได้');
    $('cameraHelp').textContent = 'ถ้าต้องใช้งานออฟไลน์เต็มรูปแบบ ให้ดาวน์โหลด MediaPipe model มาเสิร์ฟในเครื่องแทน CDN';
  }
}

function end() {
  running = false;
  cancelAnimationFrame(frame);
  stream?.getTracks().forEach(t => t.stop());
  stream = null;
  video.srcObject = null;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  detectionSignal = 'neutral';
  $('cameraSignal').className = 'camera-signal neutral';
  $('cameraSignal').textContent = 'รอเริ่มตรวจจับ';
  start.disabled = false;
  stop.disabled = true;
  $('cameraHelp').hidden = false;
  lastMetricAt = 0;
  state('หยุดแล้ว');
}

async function loadSummary() {
  const d = await storage.summary();
  $('average').textContent = d.average ?? '--';
  $('samples').textContent = d.samples ?? 0;
  $('alerts').textContent = d.alerts.length;
  $('events').innerHTML = d.alerts.length
    ? d.alerts.map(a => `<li class="event-${a.severity}">${new Date(a.created_at).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })} — ${escapeHtml(a.message)}</li>`).join('')
    : '<li>ยังไม่มีการแจ้งเตือนในวันนี้</li>';
}

async function loadSettings() {
  settings = { ...defaultSettings, ...await storage.getSettings() };
  $('riskThreshold').value = settings.riskThreshold;
  $('riskSeconds').value = settings.riskSeconds;
  $('soundEnabled').checked = settings.soundEnabled;
  $('desktopEnabled').checked = settings.desktopEnabled;
  if (!storage.isDemo) $('dataDir').value = settings.dataDir || '';
}

async function saveSettings() {
  const payload = {
    riskThreshold: Number($('riskThreshold').value),
    riskSeconds: Number($('riskSeconds').value),
    dataDir: storage.isDemo ? 'localStorage' : $('dataDir').value,
    soundEnabled: $('soundEnabled').checked,
    desktopEnabled: $('desktopEnabled').checked
  };
  settings = { ...settings, ...await storage.saveSettings(payload) };
  toast(storage.isDemo ? 'บันทึกตั้งค่าแล้วในเบราว์เซอร์' : 'บันทึกตั้งค่าแล้ว');
}

async function checkHealth() {
  const h = await storage.health();
  const el = $('healthState');
  if (storage.isDemo) {
    el.textContent = 'โหมดตัวอย่าง';
    el.className = 'badge caution';
    return;
  }
  el.textContent = h.dbOk ? 'ระบบพร้อมใช้งาน' : 'ฐานข้อมูลมีปัญหา';
  el.className = `badge ${h.dbOk ? 'good' : 'risk'}`;
}

async function loadDashboard() {
  try {
    await loadSummary();
    const stats = await storage.stats();
    drawBarChart($('dailyChart'), stats.daily, 'average', 100, '#00e5c7');
    drawBarChart($('weeklyChart'), stats.weeklyAlerts, 'alerts', Math.max(5, ...stats.weeklyAlerts.map(x => x.alerts || 0)), '#ff4d6d');
  } catch {
    toast('โหลดข้อมูลไม่สำเร็จ');
  }
}

function drawBarChart(target, rows, field, maxValue, color) {
  const c = target.getContext('2d');
  const { width, height } = target;
  c.clearRect(0, 0, width, height);
  c.fillStyle = '#0a0e1a';
  c.fillRect(0, 0, width, height);
  c.strokeStyle = '#1f2942';
  for (let i = 1; i <= 4; i++) {
    const y = 24 + (height - 64) * i / 4;
    c.beginPath();
    c.moveTo(34, y);
    c.lineTo(width - 16, y);
    c.stroke();
  }
  if (!rows.length) {
    c.fillStyle = '#a8b3cf';
    c.font = '16px sans-serif';
    c.fillText('ยังไม่มีข้อมูล', 34, height / 2);
    return;
  }
  const gap = 10;
  const chartW = width - 56;
  const barW = Math.max(12, (chartW - gap * (rows.length - 1)) / rows.length);
  rows.forEach((row, i) => {
    const value = Number(row[field] || 0);
    const x = 34 + i * (barW + gap);
    const h = Math.max(2, (height - 78) * value / maxValue);
    const y = height - 38 - h;
    c.fillStyle = color;
    c.fillRect(x, y, barW, h);
    c.fillStyle = '#a8b3cf';
    c.font = '12px sans-serif';
    c.fillText(String(value), x, y - 6);
    c.save();
    c.translate(x + 2, height - 18);
    c.rotate(-0.35);
    c.fillText(row.label.slice(5), 0, 0);
    c.restore();
  });
}

function notifyRisk(force = false) {
  const now = Date.now();
  if (!force && now - lastAlert < 15000) return;
  $('riskPopup').hidden = false;
  if (settings.soundEnabled) playBeep();
  if (settings.desktopEnabled && 'Notification' in window && Notification.permission === 'granted') {
    new Notification('PostureAI: เสี่ยงจากท่านั่ง', { body: 'ลุกพักหรือปรับเก้าอี้/จอภาพสักครู่' });
  }
}

function playBeep() {
  const Audio = window.AudioContext || window.webkitAudioContext;
  if (!Audio) return;
  const audio = new Audio();
  const osc = audio.createOscillator();
  const gain = audio.createGain();
  osc.frequency.value = 880;
  gain.gain.setValueAtTime(0.0001, audio.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.18, audio.currentTime + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + 0.22);
  osc.connect(gain).connect(audio.destination);
  osc.start();
  osc.stop(audio.currentTime + 0.24);
}

async function downloadExport(format) {
  const content = await storage.export(format);
  const blob = new Blob([content], { type: format === 'json' ? 'application/json;charset=utf-8' : 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = format === 'json' ? 'postureai-export.json' : 'postureai-export.csv';
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}

start.addEventListener('click', begin);
stop.addEventListener('click', end);
$('refresh').addEventListener('click', loadDashboard);
$('saveSettings').addEventListener('click', saveSettings);
$('exportCsv').addEventListener('click', () => downloadExport('csv'));
$('exportJson').addEventListener('click', () => downloadExport('json'));
$('testAlert').addEventListener('click', () => notifyRisk(true));
$('closePopup').addEventListener('click', () => $('riskPopup').hidden = true);
$('requestNotify').addEventListener('click', async () => {
  if (!('Notification' in window)) return toast('เบราว์เซอร์นี้ไม่รองรับ desktop notification');
  const permission = await Notification.requestPermission();
  toast(permission === 'granted' ? 'อนุญาต desktop notification แล้ว' : 'ยังไม่ได้อนุญาต desktop notification');
});
$('clearData').addEventListener('click', async () => {
  const ok = confirm(storage.isDemo ? 'ลบประวัติและแจ้งเตือนทั้งหมดจากเบราว์เซอร์นี้?' : 'ลบประวัติและแจ้งเตือนทั้งหมดจากฐานข้อมูลในเครื่อง?');
  if (!ok) return;
  await storage.clear();
  await loadDashboard();
  toast('ลบข้อมูลแล้ว');
});

window.addEventListener('online', () => toast('กลับมาออนไลน์แล้ว สามารถโหลด AI จาก CDN ได้'));
window.addEventListener('offline', () => toast('ออฟไลน์: AI จาก CDN อาจเริ่มไม่ได้'));
window.addEventListener('beforeunload', end);

storage = await createStorage();
applyStorageMode();
await loadSettings();
await checkHealth();
await loadDashboard();
