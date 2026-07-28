import { FilesetResolver, PoseLandmarker } from 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/vision_bundle.js?module';
import { createStorage, defaultSettings } from './storage.js';
import { scorePose } from './pose-utils.js';
import * as PoseModel from './pose-model.js';
import { initAuth, subscribeAuth, loginWithOAuth, loginAsDemo, logout, getToken } from './auth.js';

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
let latestMetrics = null;
let useCustomModel = false;

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

function drawSleekSkeleton(ctx, landmarks, signal, metrics) {
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  if (!landmarks || landmarks.length === 0) return;

  const isRisk = signal === 'risk';
  const mainColor = isRisk ? '#ff4d6d' : '#00e5c7';
  const glowColor = isRisk ? 'rgba(255, 77, 109, 0.7)' : 'rgba(0, 229, 199, 0.7)';
  const secondaryColor = isRisk ? '#ff9aaa' : '#80f5e5';

  const lm = landmarks;
  const getPt = idx => (lm[idx] && (lm[idx].visibility === undefined || lm[idx].visibility > 0.35))
    ? { x: lm[idx].x * w, y: lm[idx].y * h }
    : null;

  const nose = getPt(0);
  const lEar = getPt(7);
  const rEar = getPt(8);
  const lShoulder = getPt(11);
  const rShoulder = getPt(12);
  const lElbow = getPt(13);
  const rElbow = getPt(14);
  const lWrist = getPt(15);
  const rWrist = getPt(16);
  const lHip = getPt(23);
  const rHip = getPt(24);

  // Helper: Draw Glowing Neon Line
  function drawLine(p1, p2, width = 3.5, dashed = false) {
    if (!p1 || !p2) return;
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.lineWidth = width;
    ctx.strokeStyle = mainColor;
    ctx.shadowColor = glowColor;
    ctx.shadowBlur = 12;
    ctx.lineCap = 'round';
    if (dashed) ctx.setLineDash([6, 6]);
    ctx.stroke();
    ctx.restore();
  }

  // Helper: Draw Glowing Node Ring
  function drawNode(pt, radius = 5.5) {
    if (!pt) return;
    ctx.save();
    // Outer aura
    ctx.beginPath();
    ctx.arc(pt.x, pt.y, radius + 3.5, 0, Math.PI * 2);
    ctx.fillStyle = isRisk ? 'rgba(255, 77, 109, 0.25)' : 'rgba(0, 229, 199, 0.25)';
    ctx.fill();

    // Node core
    ctx.beginPath();
    ctx.arc(pt.x, pt.y, radius, 0, Math.PI * 2);
    ctx.fillStyle = '#080c18';
    ctx.strokeStyle = secondaryColor;
    ctx.lineWidth = 2.5;
    ctx.shadowColor = glowColor;
    ctx.shadowBlur = 10;
    ctx.fill();
    ctx.stroke();
    ctx.restore();
  }

  // 1. Draw Upper Body Connections (No facial detail clutter!)
  drawLine(lShoulder, rShoulder, 4.5);

  if (lShoulder && rShoulder) {
    const sCenter = { x: (lShoulder.x + rShoulder.x) / 2, y: (lShoulder.y + rShoulder.y) / 2 };
    if (nose) drawLine(nose, sCenter, 2.5);
    if (lEar) drawLine(lEar, lShoulder, 2);
    if (rEar) drawLine(rEar, rShoulder, 2);

    if (lHip && rHip) {
      const hCenter = { x: (lHip.x + rHip.x) / 2, y: (lHip.y + rHip.y) / 2 };
      drawLine(sCenter, hCenter, 3.5);
    }
  }

  // Arms
  drawLine(lShoulder, lElbow, 3.5);
  drawLine(lElbow, lWrist, 3.5);
  drawLine(rShoulder, rElbow, 3.5);
  drawLine(rElbow, rWrist, 3.5);

  // Torso Sides & Hips
  drawLine(lShoulder, lHip, 3);
  drawLine(rShoulder, rHip, 3);
  drawLine(lHip, rHip, 3.5);

  // 2. Horizontal Level Reference Line across Shoulders (HUD Guide)
  if (lShoulder && rShoulder) {
    const minX = Math.min(lShoulder.x, rShoulder.x) - 50;
    const maxX = Math.max(lShoulder.x, rShoulder.x) + 50;
    const avgY = (lShoulder.y + rShoulder.y) / 2;
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(minX, avgY);
    ctx.lineTo(maxX, avgY);
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.45)';
    ctx.setLineDash([5, 5]);
    ctx.stroke();
    ctx.restore();
  }

  // 3. Draw Clean Joint Nodes
  [nose, lEar, rEar, lShoulder, rShoulder, lElbow, rElbow, lWrist, rWrist, lHip, rHip].forEach(pt => {
    drawNode(pt, 5.5);
  });

  // 4. Futuristic HUD Overlay Card on Canvas (Top-Left)
  if (metrics) {
    ctx.save();
    const hudW = 200;
    const hudH = 56;
    ctx.fillStyle = 'rgba(8, 12, 24, 0.82)';
    ctx.strokeStyle = mainColor;
    ctx.lineWidth = 1;
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(16, 16, hudW, hudH, 8);
    else ctx.rect(16, 16, hudW, hudH);
    ctx.fill();
    ctx.stroke();

    ctx.font = '600 13px system-ui, sans-serif';
    ctx.fillStyle = '#ffffff';
    ctx.fillText(`คะแนนท่านั่ง: ${metrics.score ?? '--'}/100`, 28, 38);
    ctx.fillStyle = mainColor;
    ctx.fillText(`มุมคอ: ${metrics.neck ?? '--'}° | ไหล่: ${metrics.shoulders ?? '--'}°`, 28, 58);
    ctx.restore();
  }
}

function loop() {
  if (!running) return;
  if (video.currentTime !== lastVideoTime) {
    lastVideoTime = video.currentTime;
    const result = landmarker.detectForVideo(video, performance.now());
    const calculated = result.landmarks?.[0] && scorePose(result.landmarks[0]);
    if (calculated) {
      latestMetrics = calculated;
      let m = calculated;
      if (useCustomModel && PoseModel.isReady()) {
        const customPred = PoseModel.predict(calculated);
        if (customPred) {
          m = customPred;
        }
      }
      update(m);
      save(m);
    }
    drawSleekSkeleton(ctx, result.landmarks?.[0], detectionSignal, latestMetrics);
  }
  frame = requestAnimationFrame(loop);
}

async function begin() {
  if (!window.isSecureContext) {
    toast('กรุณาเปิดผ่าน HTTPS หรือ http://localhost:3000');
    return;
  }
  start.disabled = true;
  try {
    let vision, modelPath;
    try {
      vision = await FilesetResolver.forVisionTasks('./wasm');
      modelPath = './models/pose_landmarker_lite.task';
      landmarker = await PoseLandmarker.createFromOptions(vision, {
        baseOptions: { modelAssetPath: modelPath, delegate: 'GPU' },
        runningMode: 'VIDEO',
        numPoses: 1
      });
    } catch {
      vision = await FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm');
      modelPath = 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task';
      landmarker = await PoseLandmarker.createFromOptions(vision, {
        baseOptions: { modelAssetPath: modelPath, delegate: 'GPU' },
        runningMode: 'VIDEO',
        numPoses: 1
      });
    }
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
  if ($('voiceEnabled')) $('voiceEnabled').checked = settings.voiceEnabled !== false;
  $('desktopEnabled').checked = settings.desktopEnabled;
  if (!storage.isDemo) $('dataDir').value = settings.dataDir || '';
}

async function saveSettings() {
  const payload = {
    riskThreshold: Number($('riskThreshold').value),
    riskSeconds: Number($('riskSeconds').value),
    dataDir: storage.isDemo ? 'localStorage' : $('dataDir').value,
    soundEnabled: $('soundEnabled').checked,
    voiceEnabled: $('voiceEnabled') ? $('voiceEnabled').checked : true,
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

function speakThaiAlert(message = 'กรุณายืดหลังตรงและปรับระดับคอครับ') {
  if (!('speechSynthesis' in window)) {
    playBeep();
    return;
  }
  try {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(message);
    utterance.lang = 'th-TH';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    const voices = window.speechSynthesis.getVoices();
    const thVoice = voices.find(v => v.lang && (v.lang.includes('th') || v.lang.includes('TH')));
    if (thVoice) utterance.voice = thVoice;
    window.speechSynthesis.speak(utterance);
  } catch {
    playBeep();
  }
}

function notifyRisk(force = false, message = 'กรุณายืดหลังตรงและปรับระดับคอขึ้นครับ') {
  const now = Date.now();
  if (!force && now - lastAlert < 15000) return;
  lastAlert = now;
  $('riskPopup').hidden = false;
  if (settings.voiceEnabled) {
    speakThaiAlert(message);
  } else if (settings.soundEnabled) {
    playBeep();
  }
  if (settings.desktopEnabled && 'Notification' in window && Notification.permission === 'granted') {
    new Notification('PostureAI: เสี่ยงจากท่านั่ง', { body: message });
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

start?.addEventListener('click', begin);
stop?.addEventListener('click', end);
$('refresh')?.addEventListener('click', loadDashboard);
$('saveSettings')?.addEventListener('click', saveSettings);
$('exportCsv')?.addEventListener('click', () => downloadExport('csv'));
$('exportJson')?.addEventListener('click', () => downloadExport('json'));
$('testAlert')?.addEventListener('click', () => notifyRisk(true));
$('closePopup')?.addEventListener('click', () => { const p = $('riskPopup'); if (p) p.hidden = true; });
$('clearData')?.addEventListener('click', async () => {
  const ok = confirm(storage.isDemo ? 'ลบประวัติและแจ้งเตือนทั้งหมดจากเบราว์เซอร์นี้?' : 'ลบประวัติและแจ้งเตือนทั้งหมดจากฐานข้อมูลในเครื่อง?');
  if (!ok) return;
  await storage.clear();
  await loadDashboard();
  toast('ลบข้อมูลแล้ว');
});

/* ── Custom AI Trainer Handlers ── */
function updateTrainerUI() {
  const counts = PoseModel.getExampleCounts();
  const cGood = $('countGood');
  const cCaution = $('countCaution');
  const cRisk = $('countRisk');
  const cTotal = $('countTotal');
  if (cGood) cGood.textContent = counts.good;
  if (cCaution) cCaution.textContent = counts.caution;
  if (cRisk) cRisk.textContent = counts.risk;
  if (cTotal) cTotal.textContent = counts.total;

  const ready = PoseModel.isReady();
  const saveBtn = $('saveModelBtn');
  if (saveBtn) saveBtn.disabled = !ready;
  const readyBadge = $('modelReadyBadge');
  if (readyBadge) {
    readyBadge.textContent = ready ? 'พร้อมใช้งาน' : 'ยังไม่มีโมเดล';
    readyBadge.className = `badge ${ready ? 'good' : 'neutral'}`;
  }
}

function updateModelStatusBadge() {
  const badge = $('modelStatusBadge');
  const activeAiBadge = $('activeAiBadge');

  if (useCustomModel && PoseModel.isReady()) {
    if (badge) {
      badge.textContent = 'ใช้โมเดลที่เทรนเอง (Active)';
      badge.className = 'badge good';
    }
    if (activeAiBadge) {
      activeAiBadge.textContent = '🧠 AI ส่วนตัว (Active)';
      activeAiBadge.className = 'badge good';
    }
  } else {
    if (badge) {
      badge.textContent = 'ใช้สูตรคำนวณเดิม';
      badge.className = 'badge neutral';
    }
    if (activeAiBadge) {
      activeAiBadge.textContent = 'สูตรคำนวณมาตรฐาน';
      activeAiBadge.className = 'badge neutral';
    }
  }
}

function handleTag(label, name) {
  if (!running || !latestMetrics) {
    toast('กรุณาเปิดเริ่มกล้องเพื่อสแกนและบันทึกตัวอย่างท่านั่ง');
    return;
  }
  PoseModel.addExample(latestMetrics, label);
  updateTrainerUI();
  const counts = PoseModel.getExampleCounts();
  toast(`บันทึกตัวอย่าง "${name}" แล้ว (${counts[label]} ตัวอย่าง)`);
}

$('tagGood')?.addEventListener('click', () => handleTag('good', 'ท่านี้ดี'));
$('tagCaution')?.addEventListener('click', () => handleTag('caution', 'ท่านี้ระวัง'));
$('tagRisk')?.addEventListener('click', () => handleTag('risk', 'ท่านี้แย่'));

$('clearSamples')?.addEventListener('click', () => {
  PoseModel.clearExamples();
  updateTrainerUI();
  toast('ล้างตัวอย่างที่เก็บไว้เรียบร้อย');
});

$('trainModelBtn')?.addEventListener('click', async () => {
  const counts = PoseModel.getExampleCounts();
  if (counts.total === 0) {
    toast('กรุณาเก็บตัวอย่างท่านั่งอย่างน้อย 15-20 ตัวอย่างต่อป้ายกำกับก่อนเทรน');
    return;
  }

  const box = $('trainProgressBox');
  const bar = $('trainProgressBar');
  const text = $('trainStatusText');
  const pctText = $('trainPercent');

  if (box) box.hidden = false;
  $('trainModelBtn').disabled = true;

  try {
    await PoseModel.trainModel({
      onEpochEnd: (epoch, totalEpochs, logs) => {
        const pct = Math.round((epoch / totalEpochs) * 100);
        if (bar) bar.style.width = `${pct}%`;
        if (pctText) pctText.textContent = `${pct}%`;
        if (text) text.textContent = `เทรน Epoch ${epoch}/${totalEpochs} (Loss: ${logs.loss.toFixed(3)})`;
      }
    });

    if (text) text.textContent = 'เทรนโมเดลสำเร็จ!';
    toast('🎉 เทรนโมเดล AI ส่วนตัวสำเร็จแล้ว!');
    updateTrainerUI();

    const toggle = $('toggleCustomModel');
    if (toggle) toggle.checked = true;
    useCustomModel = true;
    updateModelStatusBadge();

    // Auto-sync to user's cloud account if logged in
    if (getToken()) {
      const synced = await PoseModel.syncModelToCloud(getToken());
      if (synced) toast('☁️ บันทึกซิงก์โมเดลขึ้นคลาวด์ข้ามเครื่องเรียบร้อยแล้ว');
    }
  } catch (err) {
    console.error(err);
    toast(err.message || 'เกิดข้อผิดพลาดในการเทรนโมเดล');
  } finally {
    $('trainModelBtn').disabled = false;
    setTimeout(() => { if (box) box.hidden = true; }, 3500);
  }
});

$('saveModelBtn')?.addEventListener('click', async () => {
  try {
    await PoseModel.saveModel('custom-posture-model');
    toast('💾 ดาวน์โหลดไฟล์โมเดลสำเร็จ');
  } catch (err) {
    toast(err.message || 'บันทึกโมเดลไม่สำเร็จ');
  }
});

$('loadModelBtn')?.addEventListener('click', () => {
  $('modelFileInput')?.click();
});

$('modelFileInput')?.addEventListener('change', async (e) => {
  const files = e.target.files;
  if (!files || files.length === 0) return;
  try {
    await PoseModel.loadModel(files);
    updateTrainerUI();
    const toggle = $('toggleCustomModel');
    if (toggle) toggle.checked = true;
    useCustomModel = true;
    updateModelStatusBadge();
    toast('📂 โหลดโมเดลที่เลือกเรียบร้อย');
  } catch (err) {
    console.error(err);
    toast('โหลดโมเดลไม่สำเร็จ กรุณาเลือกไฟล์ model.json และ model.weights.bin พร้อมกัน');
  }
});

$('toggleCustomModel')?.addEventListener('change', (e) => {
  if (e.target.checked && !PoseModel.isReady()) {
    toast('ยังไม่มีโมเดลที่เทรนสำเร็จ กรุณาเก็บตัวอย่างแล้วกดเทรน หรือโหลดไฟล์โมเดลก่อน');
    e.target.checked = false;
    useCustomModel = false;
    updateModelStatusBadge();
    return;
  }
  useCustomModel = e.target.checked;
  updateModelStatusBadge();
  toast(useCustomModel ? 'สลับมาใช้โมเดลที่เทรนเอง' : 'สลับกลับไปใช้สูตรคำนวณเดิม');
});

/* ── Chart Tabs & Notification Handlers ── */
$('btnDailyChart')?.addEventListener('click', () => {
  $('btnDailyChart').classList.add('active');
  $('btnWeeklyChart').classList.remove('active');
  $('dailyChart').style.display = 'block';
  $('weeklyChart').style.display = 'none';
});

$('btnWeeklyChart')?.addEventListener('click', () => {
  $('btnWeeklyChart').classList.add('active');
  $('btnDailyChart').classList.remove('active');
  $('weeklyChart').style.display = 'block';
  $('dailyChart').style.display = 'none';
});

$('desktopEnabled')?.addEventListener('change', async (e) => {
  if (e.target.checked && 'Notification' in window) {
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      toast('ยังไม่ได้อนุญาต desktop notification ในเบราว์เซอร์');
      e.target.checked = false;
    } else {
      toast('อนุญาต desktop notification เรียบร้อยแล้ว');
    }
  }
});

$('ssoForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const email = $('loginEmail')?.value || 'employee@company.com';
  const name = $('loginName')?.value || 'สมชาย พนักงานออฟฟิศ';
  try {
    const user = await loginAsDemo(email, name);
    const m = $('loginModal');
    if (m) m.hidden = true;
    toast(`🟢 เข้าสู่ระบบในนาม "${user.name}" เรียบร้อยแล้ว (เปิดซิงก์ข้อมูลข้ามเครื่อง)`);
  } catch {
    toast('เข้าสู่ระบบไม่สำเร็จ');
  }
});

$('btnLoginGoogle')?.addEventListener('click', async () => {
  try {
    const email = $('loginEmail')?.value || 'user@gmail.com';
    const name = $('loginName')?.value || 'Google Employee';
    const user = await loginAsDemo(email, name);
    const m = $('loginModal');
    if (m) m.hidden = true;
    toast(`🟢 เข้าสู่ระบบด้วย Google Workspace (${user.name}) เรียบร้อยแล้ว`);
  } catch {
    toast('เข้าสู่ระบบ Google ไม่สำเร็จ');
  }
});

$('btnLoginMicrosoft')?.addEventListener('click', async () => {
  try {
    const email = $('loginEmail')?.value || 'user@outlook.com';
    const name = $('loginName')?.value || 'Microsoft 365 Employee';
    const user = await loginAsDemo(email, name);
    const m = $('loginModal');
    if (m) m.hidden = true;
    toast(`🔷 เข้าสู่ระบบด้วย Microsoft 365 (${user.name}) เรียบร้อยแล้ว`);
  } catch {
    toast('เข้าสู่ระบบ Microsoft 365 ไม่สำเร็จ');
  }
});

window.addEventListener('online', () => toast('กลับมาออนไลน์แล้ว สามารถโหลด AI จาก CDN ได้'));
window.addEventListener('offline', () => toast('ออฟไลน์: AI จาก CDN อาจเริ่มไม่ได้'));
window.addEventListener('beforeunload', end);

/* ── SPA View Router (Separate Pages / Views) ── */
function initViewRouter() {
  const navLinks = document.querySelectorAll('.topbar nav a');
  const sections = document.querySelectorAll('main > section');

  function showView(targetId) {
    const validIds = Array.from(sections).map(s => s.id);
    const activeId = validIds.includes(targetId) ? targetId : 'monitor';

    sections.forEach(sec => {
      sec.style.display = '';
      if (sec.id === activeId) {
        sec.classList.add('active');
      } else {
        sec.classList.remove('active');
      }
    });

    navLinks.forEach(link => {
      const href = link.getAttribute('href') || '';
      const linkId = href.replace(/^#\/?/, '');
      if (linkId === activeId) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });

    window.scrollTo({ top: 0, behavior: 'instant' });
  }

  window.addEventListener('hashchange', () => {
    const hash = window.location.hash.replace(/^#\/?/, '');
    showView(hash);
  });

  navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      const href = link.getAttribute('href') || '';
      if (href.startsWith('#')) {
        e.preventDefault();
        const targetId = href.replace(/^#\/?/, '');
        window.location.hash = targetId;
        showView(targetId);
      }
    });
  });

  const initialHash = window.location.hash.replace(/^#\/?/, '') || 'monitor';
  showView(initialHash);
}

// Initialize View Router for separate pages synchronously
initViewRouter();

/* ── SSO Auth & Cloud Model Sync Integration ── */
subscribeAuth(async (user, token) => {
  const btnLogin = $('btnOpenLoginModal');
  const badge = $('userProfileBadge');
  const avatar = $('userAvatar');
  const name = $('userName');

  if (user) {
    if (btnLogin) btnLogin.hidden = true;
    if (badge) badge.hidden = false;
    if (name) name.textContent = user.name;
    if (avatar) avatar.textContent = user.provider === 'google' ? '🟢' : (user.provider === 'microsoft' ? '🔷' : '👤');

    // Auto-sync personal custom AI model from cloud if user has one saved
    if (token) {
      const synced = await PoseModel.syncModelFromCloud(token);
      if (synced) {
        updateTrainerUI();
        useCustomModel = true;
        const toggle = $('toggleCustomModel');
        if (toggle) toggle.checked = true;
        updateModelStatusBadge();
        toast(`☁️ โหลดโมเดล AI ส่วนตัวของ ${user.name} เรียบร้อยแล้ว`);
      }
    }
  } else {
    if (btnLogin) btnLogin.hidden = false;
    if (badge) badge.hidden = true;
  }
});

// Auth Modal triggers
$('btnOpenLoginModal')?.addEventListener('click', () => { const m = $('loginModal'); if (m) m.hidden = false; });
$('btnCloseLoginModal')?.addEventListener('click', () => { const m = $('loginModal'); if (m) m.hidden = true; });
$('btnLogout')?.addEventListener('click', () => {
  logout();
  toast('ออกจากระบบเรียบร้อยแล้ว');
});

async function initApp() {
  initAuth();
  storage = await createStorage();
  applyStorageMode();
  await loadSettings();
  await checkHealth();
  await loadDashboard();

  // Try loading default local custom model if present
  await PoseModel.loadModelFromUrl('./models/custom/model.json');
  updateTrainerUI();
  updateModelStatusBadge();
}

initApp();
