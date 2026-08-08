import { createStorage, defaultSettings } from './storage.js';
import { scorePose } from './pose-utils.js';

const $ = id => document.getElementById(id);
const video = $('video');
const canvas = $('overlay');
const ctx = canvas.getContext('2d');
const start = $('start');
const stop = $('stop');

// This file is copied to public/ during npm install. Keep it as a runtime
// import so Vite serves the local MediaPipe runtime without bundling it.
const visionTasksUrl = '/vision_bundle.js';
const loadVisionTasks = () => import(/* @vite-ignore */ visionTasksUrl);

let storage;
let landmarker;
let stream;
let running = false;
let frame;
let lastVideoTime = -1;
let analysisVideo = video;
let saveAnalysisResults = true;
let lastSave = 0;
let lastAlert = 0;
let lastVoiceAlert = 0;
let lastMetricAt = 0;
let poorPostureMs = 0;
let detectionSignal = 'neutral';
let settings = { ...defaultSettings };
let latestMetrics = null;
let piPeer;
let piSignal;
let piReconnectTimer;
let piManualStop = false;
let piLandmarks = [];
let piMetrics = null;
let piRoboflowResult = null;

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
  $('adminTokenField').hidden = demo;
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
  const cls = s >= 70 ? 'good' : s >= 40 ? 'caution' : 'risk';
  $('score').value = s;
  $('score').textContent = s;
  $('score').style.color = `var(--status-${cls})`;
  $('status').textContent = s >= 70 ? 'ท่านั่งดี' : s >= 40 ? 'ปรับพฤติกรรม' : 'ท่านั่งแย่';
  $('advice').textContent = s >= 70 ? 'รักษาระดับสายตาและไหล่ให้ผ่อนคลาย' : s >= 40 ? 'ลองยืดหลังและดึงคางเข้าเล็กน้อย' : 'พักสั้น ๆ แล้วจัดหลังให้ตรง';
  $('neck').textContent = `${m.neck.toFixed(0)}°`;
  $('shoulders').textContent = `${m.shoulders.toFixed(1)}%`;
  $('torso').textContent = `${m.torso.toFixed(0)}°`;
  updateLcdPreview(s);
  state(s >= 70 ? 'กำลังติดตาม' : s >= 40 ? 'ปรับพฤติกรรม' : 'ท่านั่งแย่', cls);
  updateRisk(m);
}

function updateLcdPreview(score) {
  const safeScore = Math.max(0, Math.min(100, Math.round(score)));
  $('lcdLine1').textContent = `SCORE: ${String(safeScore).padStart(3, ' ')}/100`;
  $('lcdLine2').textContent = safeScore >= 70
    ? 'GOOD POSTURE'
    : safeScore >= 40
      ? 'CHECK POSTURE'
      : 'ADJUST POSTURE';
}

function updateRoboflowResult(result) {
  const el = $('roboflowResult');
  const label = String(result?.label || '');
  const confidence = Number(result?.confidence);
  if (!label || !Number.isFinite(confidence)) return;
  const labels = {
    good_posture: 'AI เสริม: ท่านั่งดี',
    slouch: 'AI เสริม: หลังงอ',
    leaning_forward: 'AI เสริม: โน้มตัวไปข้างหน้า',
    leaning_backward: 'AI เสริม: เอนตัวไปข้างหลัง'
  };
  piRoboflowResult = result;
  el.hidden = false;
  el.textContent = `${labels[label] || `AI เสริม: ${label}`} (${Math.round(confidence * 100)}%)`;
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
  if (!running || !landmarker || !analysisVideo) return;
  if (analysisVideo.currentTime !== lastVideoTime) {
    lastVideoTime = analysisVideo.currentTime;
    const result = landmarker.detectForVideo(analysisVideo, performance.now());
    const calculated = result.landmarks?.[0] && scorePose(result.landmarks[0]);
    if (calculated) {
      latestMetrics = calculated;
      update(calculated);
      if (saveAnalysisResults) save(calculated);
    }
    drawSleekSkeleton(ctx, result.landmarks?.[0], detectionSignal, latestMetrics);
  }
  frame = requestAnimationFrame(loop);
}

async function loadPoseLandmarker() {
  if (landmarker) return;
  try {
    const { FilesetResolver, PoseLandmarker } = await loadVisionTasks();
    const vision = await FilesetResolver.forVisionTasks('./wasm');
    const modelPath = './models/pose_landmarker_full.task';
    try {
      landmarker = await PoseLandmarker.createFromOptions(vision, {
        baseOptions: { modelAssetPath: modelPath, delegate: 'GPU' },
        runningMode: 'VIDEO',
        numPoses: 1,
        minPoseDetectionConfidence: 0.5,
        minPosePresenceConfidence: 0.5,
        minTrackingConfidence: 0.5
      });
    } catch {
      // GPU delegates are not available in every browser. CPU keeps the
      // application usable without sending camera frames to a remote service.
      landmarker = await PoseLandmarker.createFromOptions(vision, {
        baseOptions: { modelAssetPath: modelPath, delegate: 'CPU' },
        runningMode: 'VIDEO',
        numPoses: 1,
        minPoseDetectionConfidence: 0.5,
        minPosePresenceConfidence: 0.5,
        minTrackingConfidence: 0.5
      });
    }
  } catch (error) {
    landmarker?.close();
    landmarker = null;
    throw error;
  }
}

function startPoseTracking(source, { saveResults = false } = {}) {
  analysisVideo = source;
  saveAnalysisResults = saveResults;
  lastVideoTime = -1;
  canvas.width = source.videoWidth;
  canvas.height = source.videoHeight;
  canvas.hidden = false;
  running = true;
  cancelAnimationFrame(frame);
  loop();
}

async function begin() {
  if (!window.isSecureContext) {
    toast('กรุณาเปิดผ่าน HTTPS หรือ http://localhost:3000');
    return;
  }
  start.disabled = true;
  try {
    await loadPoseLandmarker();
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
    video.srcObject = stream;
    await video.play();
    startPoseTracking(video, { saveResults: true });
    $('cameraHelp').hidden = true;
    start.disabled = true;
    stop.disabled = false;
    state('กำลังติดตาม', 'good');
  } catch (e) {
    console.error(e);
    state('เริ่มไม่ได้', 'risk');
    start.disabled = false;
    toast('เปิดกล้องหรือ AI ไม่สำเร็จ โปรดอนุญาตกล้องแล้วลองใหม่');
    $('cameraHelp').textContent = 'ตรวจสอบว่าไฟล์ AI ในเครื่องถูกติดตั้งครบ แล้วอนุญาตการใช้กล้อง';
  }
}

function end() {
  running = false;
  cancelAnimationFrame(frame);
  stream?.getTracks().forEach(t => t.stop());
  stream = null;
  landmarker?.close();
  landmarker = null;
  video.srcObject = null;
  analysisVideo = video;
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

function beginPiCamera() {
  piManualStop = false;
  clearTimeout(piReconnectTimer);
  connectPiCamera();
  $('cameraHelp').hidden = true;
  $('cameraSignal').className = 'camera-signal neutral';
  $('cameraSignal').textContent = 'กำลังเชื่อมต่อสตรีม Pi Camera';
  state('กำลังเชื่อมต่อ', 'neutral');
  start.disabled = true;
  stop.disabled = false;
}

function endPiCamera() {
  piManualStop = true;
  clearTimeout(piReconnectTimer);
  piSignal?.send(JSON.stringify({ type: 'stop' }));
  piSignal?.close();
  piSignal = undefined;
  piPeer?.close();
  piPeer = undefined;
  const piVideo = $('piCamera');
  running = false;
  cancelAnimationFrame(frame);
  landmarker?.close();
  landmarker = null;
  analysisVideo = video;
  lastVideoTime = -1;
  if (piVideo) piVideo.srcObject = null;
  piLandmarks = [];
  piMetrics = null;
  piRoboflowResult = null;
  $('roboflowResult').hidden = true;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  canvas.hidden = true;
  $('cameraHelp').hidden = false;
  $('cameraSignal').className = 'camera-signal neutral';
  $('cameraSignal').textContent = 'หยุดแสดงภาพ';
  state('หยุดแล้ว');
  start.disabled = false;
  stop.disabled = true;
}

function webrtcUrl() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${location.host}/api/camera/webrtc?role=viewer`;
}

function waitForIceComplete(peer) {
  if (peer.iceGatheringState === 'complete') return Promise.resolve();
  return new Promise(resolve => {
    const timeout = setTimeout(resolve, 5000);
    peer.addEventListener('icegatheringstatechange', function done() {
      if (peer.iceGatheringState === 'complete') {
        clearTimeout(timeout);
        peer.removeEventListener('icegatheringstatechange', done);
        resolve();
      }
    });
  });
}

function reconnectPiCamera() {
  if (piManualStop) return;
  clearTimeout(piReconnectTimer);
  piReconnectTimer = setTimeout(connectPiCamera, 2000);
  $('cameraSignal').className = 'camera-signal neutral';
  $('cameraSignal').textContent = 'สตรีมขาด กำลังเชื่อมต่อใหม่';
  state('กำลังเชื่อมต่อใหม่', 'neutral');
}

function piOverlayLandmarks(points) {
  const landmarks = Array(33).fill(null);
  if (!Array.isArray(points)) return landmarks;
  for (const point of points) {
    const index = Number(point?.index);
    if (!Number.isInteger(index) || index < 0 || index >= landmarks.length) continue;
    if (!Number.isFinite(point?.x) || !Number.isFinite(point?.y)) continue;
    landmarks[index] = {
      x: point.x,
      y: point.y,
      visibility: Number.isFinite(point.visibility) ? point.visibility : 1
    };
  }
  return landmarks;
}

function drawPiOverlay() {
  // The Pi already burns the current MediaPipe skeleton into its WebRTC
  // frame. Drawing the same landmarks in the browser creates a second,
  // misaligned cyan skeleton, so keep the dashboard canvas off for Pi video.
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  canvas.hidden = true;
}

function connectPiCamera() {
  if (piManualStop || piSignal?.readyState === WebSocket.OPEN) return;
  piPeer?.close();
  piPeer = new RTCPeerConnection({ iceServers: [] });
  piPeer.addTransceiver('video', { direction: 'recvonly' });
  piPeer.addEventListener('track', event => {
    const preview = $('piCamera');
    preview.srcObject = event.streams[0];
    preview.onloadedmetadata = () => {
      drawPiOverlay();
    };
    console.log('[PostureAI] WebRTC stream color mode: RGB', {
      track: event.track.getSettings?.(),
      streamId: event.streams[0]?.id
    });
    $('cameraSignal').className = 'camera-signal good';
    $('cameraSignal').textContent = 'กำลังรับสตรีมสดจาก Pi Camera';
    state('กำลังติดตาม', 'good');
  });
  piPeer.addEventListener('connectionstatechange', () => {
    if (['failed', 'disconnected', 'closed'].includes(piPeer?.connectionState)) reconnectPiCamera();
  });

  piSignal = new WebSocket(webrtcUrl());
  piSignal.addEventListener('message', async event => {
    const message = JSON.parse(event.data);
    if (message.type === 'ready') {
      const offer = await piPeer.createOffer();
      await piPeer.setLocalDescription(offer);
      await waitForIceComplete(piPeer);
      piSignal.send(JSON.stringify({ type: 'offer', sdp: piPeer.localDescription.sdp }));
    } else if (message.type === 'answer') {
      await piPeer.setRemoteDescription({ type: 'answer', sdp: message.sdp });
    } else if (message.type === 'stream_info') {
      const colorMode = message.displayColorMode || message.cameraFormat || 'unknown';
      $('streamColorMode').textContent = `รูปแบบภาพ: ${colorMode} · RGB`;
      $('streamColorMode').className = 'badge good';
      console.log('[PostureAI] actual Pi Camera stream format:', message.cameraFormat, {
        displayColorMode: colorMode,
        normalizedOutput: message.outputColorSpace
      });
    } else if (message.type === 'pose_update') {
      piLandmarks = piOverlayLandmarks(message.landmarks);
      const metrics = message.metrics;
      if (['score', 'neck', 'shoulders', 'torso'].every(key => Number.isFinite(metrics?.[key]))) {
        piMetrics = metrics;
        latestMetrics = metrics;
        update(metrics);
      }
      if (!running || analysisVideo !== $('piCamera')) drawPiOverlay();
    } else if (message.type === 'roboflow_update') {
      updateRoboflowResult(message.result);
    } else if (message.type === 'error') {
      toast(message.message || 'ไม่สามารถเชื่อมต่อ Pi Camera ได้');
      if (message.code === 'unavailable') {
        piManualStop = true;
        $('cameraSignal').className = 'camera-signal risk';
        $('cameraSignal').textContent = message.message;
        state('กล้องถูกใช้งานอยู่', 'risk');
      }
    }
  });
  piSignal.addEventListener('close', reconnectPiCamera);
  piSignal.addEventListener('error', () => piSignal.close());
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

function unlockAdminActions() {
  if (storage.isDemo) return true;
  const field = $('adminToken');
  const token = field?.value.trim();
  if (!token) {
    toast('กรอกรหัสผ่านผู้ดูแลก่อนบันทึกหรือลบข้อมูล');
    field?.focus();
    return false;
  }
  storage.setAdminToken(token);
  return true;
}

async function loadPiStatus() {
  const target = $('piSyncState');
  if (!target) return;
  if (storage.isDemo) {
    target.textContent = 'โหมดตัวอย่าง: ไม่มี Raspberry Pi เชื่อมต่อ';
    return;
  }
  try {
    const status = await storage.clientStatus();
    const sync = status.lastSyncAt ? new Date(status.lastSyncAt).toLocaleTimeString('th-TH') : 'ยังไม่เคย sync';
    target.textContent = status.online
      ? `Pi ออนไลน์ · sync ตั้งค่าล่าสุด ${sync} · เก็บข้อมูล ${status.retentionDays} วัน`
      : `Pi ยังไม่รายงานตัว · ${status.message || 'กำลังรอ sensor client'}`;
  } catch {
    target.textContent = 'ไม่สามารถอ่านสถานะ Raspberry Pi ได้';
  }
}

async function saveSettings() {
  if (!unlockAdminActions()) return;
  const payload = {
    riskThreshold: Number($('riskThreshold').value),
    riskSeconds: Number($('riskSeconds').value),
    dataDir: storage.isDemo ? 'localStorage' : $('dataDir').value,
    soundEnabled: $('soundEnabled').checked,
    voiceEnabled: $('voiceEnabled') ? $('voiceEnabled').checked : true,
    desktopEnabled: $('desktopEnabled').checked
  };
  try {
    settings = { ...settings, ...await storage.saveSettings(payload) };
    toast(storage.isDemo ? 'บันทึกตั้งค่าแล้วในเบราว์เซอร์' : 'บันทึกตั้งค่าแล้ว; Pi จะ sync ภายใน 30 วินาที');
    await loadPiStatus();
  } catch (error) {
    toast(error.message.includes('401') ? 'รหัสผ่านผู้ดูแลไม่ถูกต้อง' : 'บันทึกตั้งค่าไม่สำเร็จ');
  }
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

async function loadSensorReadings() {
  const lux = $('sensorLux');
  const distance = $('sensorDistance');
  const status = $('sensorDataState');
  const updatedAt = $('sensorUpdatedAt');
  if (!lux || !distance || !status || !updatedAt) return;

  try {
    const response = await fetch('/api/sensors/latest', { cache: 'no-store' });
    if (!response.ok) throw new Error('sensor API returned ' + response.status);
    const data = await response.json();
    const updated = data.updatedAt ? new Date(data.updatedAt) : null;
    const stale = !updated || Date.now() - updated.getTime() > 10_000;
    const online = data.bh1750Ok && data.tof200cOk;
    lux.textContent = data.bh1750Ok && Number.isFinite(data.lux) ? Number(data.lux).toFixed(1) : '--';
    distance.textContent = data.tof200cOk && Number.isFinite(data.distanceCm)
      ? Number(data.distanceCm).toFixed(1)
      : '--';
    status.textContent = stale ? 'กำลังรอข้อมูลใหม่' : online ? 'ออนไลน์' : 'Sensor error';
    status.className = 'badge ' + (stale ? 'neutral' : online ? 'good' : 'risk');
    updatedAt.textContent = updated
      ? 'อัปเดตล่าสุด ' + updated.toLocaleTimeString('th-TH')
      : 'รอ Raspberry Pi sensor client ส่งข้อมูล';
  } catch {
    lux.textContent = '--';
    distance.textContent = '--';
    status.textContent = 'ไม่พบข้อมูล';
    status.className = 'badge neutral';
    updatedAt.textContent = 'ยังเชื่อมต่อกับ sensor API ไม่ได้';
  }
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
  await loadPiStatus();
  await loadSensorReadings();
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
  
  if (force || now - lastVoiceAlert >= 30000) {
    lastVoiceAlert = now;
    if (settings.voiceEnabled) {
      speakThaiAlert(message);
    } else if (settings.soundEnabled) {
      playBeep();
    }
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

start?.addEventListener('click', beginPiCamera);
stop?.addEventListener('click', endPiCamera);
$('refresh')?.addEventListener('click', loadDashboard);
$('saveSettings')?.addEventListener('click', saveSettings);
$('exportCsv')?.addEventListener('click', () => downloadExport('csv'));
$('exportJson')?.addEventListener('click', () => downloadExport('json'));
$('testAlert')?.addEventListener('click', () => notifyRisk(true));
$('closePopup')?.addEventListener('click', () => { const p = $('riskPopup'); if (p) p.hidden = true; });
$('clearData')?.addEventListener('click', async () => {
  if (!unlockAdminActions()) return;
  const ok = confirm(storage.isDemo ? 'ลบประวัติและแจ้งเตือนทั้งหมดจากเบราว์เซอร์นี้?' : 'ลบประวัติและแจ้งเตือนทั้งหมดจากฐานข้อมูลในเครื่อง?');
  if (!ok) return;
  try {
    await storage.clear();
    await loadDashboard();
    toast('ลบข้อมูลแล้ว');
  } catch (error) {
    toast(error.message.includes('401') ? 'รหัสผ่านผู้ดูแลไม่ถูกต้อง' : 'ลบข้อมูลไม่สำเร็จ');
  }
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

window.addEventListener('online', () => toast('กลับมาออนไลน์แล้ว สามารถโหลด AI จาก CDN ได้'));
window.addEventListener('offline', () => toast('ออฟไลน์: AI จาก CDN อาจเริ่มไม่ได้'));
window.addEventListener('beforeunload', () => {
  end();
  endPiCamera();
});

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

async function initApp() {
  storage = await createStorage();
  applyStorageMode();
  await loadSettings();
  await checkHealth();
  await loadDashboard();
  beginPiCamera();
  setInterval(loadSensorReadings, 1_000);

}

initApp();
