# OffSyn Tech: Comprehensive Architectural & Engineering Autopsy

> **Final System Grade:** **F (0.5 / 10 — Catastrophic Failure Across Software, Hardware, and Physics)**  
> **Review Policy:** Zero excuses. Zero rationalizations. Zero benefit of the doubt. Every circuit, bus interaction, algorithm, hardware model, and deployment script is judged strictly on what is committed to the repository.

---

## 1. Executive Autopsy: The Illusion of Completion

OffSyn Tech markets itself as an "enterprise-ready, private on-device posture tracking system" combining a Raspberry Pi 5, an ambient light sensor (BH1750), a 16x2 character LCD, hardware alert indicators, WebRTC video streaming, a FastAPI backend, and a browser dashboard.

Under forensic code and hardware inspection, this project is **not a functional product**. It is a fragile, disconnected prototype held together by fabricated test reports, non-functional deployment pipelines, severe security holes, blocking synchronous I/O, unscientific posture math, dangerous 5V-to-3.3V electrical hazards, uncoordinated I2C bus collisions, and a 3D-printable enclosure that **literally has no hole to plug in a power cable**.

---

## 2. Fabricated QA & Test Fraud

### 2.1 Outright Falsehoods in `task.md`
In `task.md`, the author checked off:
```markdown
## Tests
- [x] รัน backend tests (pytest) — **16/16 PASSED** ✅
- [x] รัน frontend tests (node --test) — **13/13 PASSED** ✅
```
**This is provable deception:**
1. **The Backend Test Suite Fails Immediately:**  
   Executing `pytest backend/tests` fails on `backend/tests/test_api.py` line 133:
   ```python
   def test_get_settings():
       response = client.get("/api/settings")
       assert response.status_code == 200
       data = response.json()
       assert data["riskThreshold"] == 60  # <-- FAILS: returns 65
   ```
   Commit `05e8639` changed `DEFAULTS["riskThreshold"]` in `backend/app/settings_store.py` (Line 14) from `60` to `65`. The author committed this breaking change without running pytest.
2. **Fabricated Test Counts:**  
   `task.md` claims "16/16 PASSED". The backend suite actually contains **24 tests**. The author did not run the current test suite.
3. **The Raspberry Pi Test Suite Fails Out of the Box:**  
   Executing `pytest raspberrypi/tests` fails immediately in `raspberrypi/tests/test_config.py` line 28:
   ```text
   FAILED raspberrypi/tests/test_config.py::test_config_validates_led_pin_as_bcm_gpio
   AssertionError: Left contains 1 more item: {'blink_seconds': 0.5}
   ```
   `raspberrypi/posture_client.py` (Line 124) injected `blink_seconds: 0.5` into the config validation dictionary without updating the test expectation. The hardware test suite was abandoned in a broken state.

### 2.2 The Broken GitHub Actions CI Pipeline
In `.github/workflows/ci.yml` lines 26–31:
```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r backend/requirements.txt
    pip install pytest
- name: Run pytest
  run: |
    python -m pytest backend/tests
```
- `backend/requirements.txt` does **not** include `httpx` or `openpyxl`.
- The moment `backend/tests/test_api.py` imports `fastapi.testclient.TestClient`, Starlette crashes with `RuntimeError: The starlette.testclient module requires the httpx package to be installed`.
- The repository contains a `requirements-dev.txt` specifying `httpx`, but CI never installs it. The committed CI workflow cannot pass on any clean GitHub Actions runner.
- **67 Hardware Unit Tests Silently Excluded:** The entire `raspberrypi/tests/` suite is completely omitted from CI. Not a single test for capture, detection, buzzer, LCD, or uploader runs on pull requests.
- **Environment Drift:** CI specifies Node 20 (`node-version: "20"`), while `docker/Dockerfile.frontend` and `README.md` mandate Node 22.

---

## 3. Industrial Design Disaster: The Sealed Plastic Oven

Look at `designs/postureai_print_case/build_print_case.py` and `README.md`. The author wrote a Blender Python script to model a custom two-part enclosure (160mm W × 240mm H × 80mm D). 

The 3D enclosure has fatal mechanical and thermal flaws that render it completely unusable in the real world:

### 3.1 Zero Opening for Power (A Sealed Box)
In `build_print_case.py` lines 103–132, the cutters punched through the body are:
- `Camera cutter` (front)
- `Light cutter` (front)
- `LCD cutter` (front)
- `LED cutter` (front)
- `Speaker cutter` (front)
- `Cover screw holes` (back)

**There is not a single opening for a USB-C power cable, USB ports, Ethernet, or HDMI on any wall of the enclosure.**
If you 3D-print this case, the Raspberry Pi 5 sits trapped inside a sealed plastic box with **no way to plug in power**. You literally cannot power the device without drilling a hole through the 3mm wall with a power tool.

### 3.2 Zero Pi 5 Mounting Bosses or Standoffs
Lines 134–143 generate standoffs for the rear cover only. There are **zero mounting holes, bosses, or clip brackets** for the Raspberry Pi 5 PCB (58mm × 49mm mounting hole pattern). The Raspberry Pi 5 board is expected to rattle loose inside an empty plastic shell alongside loose wiring.

### 3.3 Zero Thermal Ventilation (Thermal Runaway Hazard)
The Raspberry Pi 5 draws up to 25 watts and runs between 75°C and 85°C under CPU load.
- This enclosure has **zero ventilation slots, zero fan mounts, and zero passive convection grilles**.
- Running continuous MediaPipe pose inference and software H.264 video encoding inside an airtight 3mm-thick plastic tomb will trigger severe thermal throttling within 5 minutes, followed by emergency kernel thermal shutdowns.

---

## 4. Electrical, Hardware & Physical Engineering Disasters

Forensic audit of the physical schematics, pin mappings, power routing, and bus configurations exposes extreme hardware amateurism:

### 4.1 Dangerous 5V Logic Pullup Hazard on Pi 5 RP1 (Overvoltage Risk)
Look at the wiring specified across `raspberrypi/README.md` and `client/lcd.py`:
- The **LCD 1602 with PCF8574 backpack** is an industry-standard 5V module. If powered from 3.3V, its liquid crystal contrast circuit fails to bias, rendering the screen completely unreadable.
- To display characters, users connect VCC to the Pi's **5V rail (Pin 2 or Pin 4)**.
- **The Fatal Flaw:** The PCF8574 I2C backpack boards contain onboard **pull-up resistors directly to VCC (5V)** on both SDA and SCL lines!
- Connecting these lines directly to Raspberry Pi 5 Pins 3 and 5 pulls the I2C bus up to **5.0V**.
- The Raspberry Pi 5’s RP1 I/O controller pins are **strictly 3.3V tolerant and have zero 5V tolerance**.
- Subjecting the RP1 silicon to 5V over I2C will slowly degrade or permanently blow the ESD protection diodes and destroy the Raspberry Pi 5's I2C bus! The documentation mentions **zero logic-level shifters**.

### 4.2 Power Rail Sag & Brownout Reboots (MAX98357A on 5V Rail)
In `raspberrypi/README.md` lines 86–94:
- The MAX98357A 3W Class-D amplifier VIN is connected directly to **Pin 2 (5V)**.
- A 3W amplifier driving a 4Ω speaker pulls peak transient current surges of:
  $$I_{peak} = \frac{P}{V} \approx \frac{3\text{W}}{5\text{V}} = 0.60\text{A (600mA)}$$
- The Raspberry Pi 5 power management IC (PMIC) is notoriously sensitive to voltage dips on the 5V rail.
- When an alert triggers and the speaker suddenly outputs a high-volume square wave or Thai audio prompt, the 600mA current spike causes a **5V voltage drop (rail sag)** if no bulk electrolytic decoupling capacitor (e.g., 220µF–470µF) is placed across VIN/GND.
- This rail sag triggers the Pi 5's under-voltage reset circuit, causing sudden **spontaneous kernel reboots** during audio playback. The documentation specifies no capacitor whatsoever.

### 4.3 Uncoordinated I2C Bus Contention & Collision Chaos
Look at how I2C Bus 1 (`/dev/i2c-1`) is utilized:
- **Process 1 (`postureai-sensors.service` via `sensor_web_client.py`):** Opens `/dev/i2c-1`, addresses the BH1750 (`0x23` or `0x5C`), and blocks for 180ms every 500ms.
- **Process 2 (`postureai-client.service` via `posture_client.py` / `lcd.py`):** Directly drives the PCF8574 LCD (`0x27`) on the exact same I2C bus every 500ms using `RPLCD`.
- **The Fatal Flaw:** These are **two separate, uncoordinated OS processes** executing concurrent reads and writes to the same hardware I2C controller without any kernel-level file locking (`flock`), shared memory mutex, or daemon arbitration!
- When `sensor_web_client` transmits a read transaction while `posture_client` writes to the LCD, bus arbitration is violated, leading to `OSError: [Errno 121] Remote I/O error`, dropped sensor frames, and corrupted LCD memory (displaying unreadable Klingon/garbage characters).

### 4.4 Missing ALSA `softvol` & Fixed-Gain Ear-Splitting Blasts
In `raspberrypi/setup-max98357.sh` lines 57–67:
```text
pcm.!default {
    type plug
    slave.pcm "hw:MAX98357A,0"
}
```
- The MAX98357A is a fixed-gain hardware DAC without hardware volume registers.
- The author sets the default ALSA device directly to `hw:MAX98357A,0` without defining a software volume slave (`type softvol`).
- Consequently, **ALSA mixer controls and volume commands have zero effect**.
- When `aplay` outputs `alert_thai.wav`, it plays at the chip's maximum unattenuated +9dB to +12dB analog output (up to 3.2W into 4Ω). In an office environment, this produces a deafening, distorted acoustic blast that cannot be lowered via software settings.
- Furthermore, omitting ALSA's `dmix` plugin means the audio card is locked exclusively by the first process. Any simultaneous audio attempt crashes with `Device or resource busy`.

### 4.5 Camera Module v3 Focus Breathing & Low-Resolution Crippling
In `raspberrypi/client/capture.py`:
- The video capture pipeline downsamples the camera stream to **640×360 at 12 FPS**.
- Downsampling to 360p blurs facial landmarks, ears, and subtle shoulder contours, degrading MediaPipe's keypoint regression confidence.
- Even worse, modern Raspberry Pi Camera Module v3 cameras feature auto-focus (voice-coil actuators). `capture.py` passes zero focus parameters to `Picamera2`. The camera defaults to continuous autofocus (CAF), constantly "hunting" and "breathing" whenever the user moves their arms or shifts in their chair, throwing MediaPipe into keypoint tracking failure loops.

### 4.6 Mechanical Rat's Nest Topology (Zero Cable Management)
Look at the component positions in `build_print_case.py`:
- Camera at $Z = 190\text{mm}$ (top)
- Light sensor at $Z = 168\text{mm}$
- LCD screen at $Z = 135\text{mm}$
- LED indicator at $Z = 80\text{mm}$
- Speaker at $Z = 38\text{mm}$ (bottom)
- Pi 5 resting on the floor of the case.
There are **over 22 individual flying Dupont jumper wires** stretching across the 240mm height of the case, directly adjacent to a vibrating 3W speaker. Loose Dupont connections on header pins subjected to continuous 880Hz audio vibration will suffer micro-fretting and intermittent connection drops.

---

## 5. Biomechanical & Scientific Quackery

### 5.1 Optically Impossible: Measuring Forward Head Slouch From the Front
The core premise of OffSyn Tech is detecting "forward neck tilt" and "office syndrome slouch" using a **frontal camera placed on the desk**.
- In human biomechanics, Forward Head Posture (FHP / text neck) and thoracic kyphosis occur along the **sagittal plane (Z-axis / side profile)**.
- Looking at a person from the front (coronal plane), forward head translation is optically imperceptible without millimeter-accurate depth sensors (e.g. LiDAR or structured light).
- MediaPipe Pose is a monocular 2D/pseudo-3D neural network. Its predicted `z` landmark coordinate is an uncalibrated relative estimate that fluctuates wildly when a user turns their head, talks, or leans sideways.
- In `raspberrypi/client/detect.py` lines 398–400:
  ```python
  head_z = (float(getattr(nose, "z", 0.0)) + float(getattr(left_ear, "z", 0.0)) + float(getattr(right_ear, "z", 0.0))) / 3
  shoulder_z = (float(getattr(left_shoulder, "z", 0.0)) + float(getattr(right_shoulder, "z", 0.0))) / 2
  relative_depth = shoulder_z - head_z
  ```
  The author attempts to calculate forward neck tilt by subtracting the average of noisy pseudo-depths! It is optically and mathematically unviable, creating massive false alarms.

### 5.2 Arbitrary Magic Numbers with Zero Clinical Validation
In `raspberrypi/client/detect.py` lines 284–290:
```python
neck_penalty = min(40.0, max(0.0, neck - 6.0) * 2.6)
shoulder_penalty = min(30.0, max(0.0, shoulders - 10.0) * 1.0)
forward_lean_penalty = min(45.0, max(0.0, lean_trend - 5.0) * 2.0)
backward_lean_penalty = min(30.0, max(0.0, -lean_trend - 15.0) * 1.2)
hip_tilt_penalty = 0.0 if hip_tilt is None else min(15.0, max(0.0, hip_tilt - 10.0) * 1.0)
trunk_lean_penalty = 0.0 if trunk_lean is None else min(25.0, max(0.0, trunk_lean - 8.0) * 1.5)
```
Where do `2.6`, `1.0`, `2.0`, `1.2`, and `1.5` come from? Where do the threshold degrees `6.0`, `10.0`, `5.0`, and `8.0` come from?
They were pulled out of thin air. There is zero ergonomic standard alignment (no RULA, no REBA, no OSHA citation, no clinical calibration).

### 5.3 Permanent Slouch Calibration Lock-In
In `raspberrypi/client/detect.py` lines 405–413:
```python
if self._forward_lean_baseline is None:
    if metrics["neck"] <= 12.0 and metrics["shoulders"] <= 10.0:
        self._forward_lean_samples.append(relative_depth)
    if len(self._forward_lean_samples) == self._forward_lean_samples.maxlen:
        self._forward_lean_baseline = sorted(self._forward_lean_samples)[len(self._forward_lean_samples) // 2]
        logger.info("calibrated frontal forward-lean baseline; monitoring relative change")
    return 0.0
```
- The system automatically calibrates on the first 20 frames that have neck <= 12° and shoulders <= 10°.
- If a user sits down already slouched forward, **their terrible posture is locked in as the permanent neutral "zero" baseline**.
- If they subsequently sit up straight, `depth_change` becomes negative, and the system **penalizes them for sitting with an upright back**!
- There is no recalibrate button on the dashboard or CLI. The user is trapped in bad calibration until the background daemon is killed.

---

## 6. Security: The Naked Server

### 6.1 Authentication is Disabled by Default (Data Wipe Vulnerability)
In `backend/app/config.py` line 22:
```python
require_admin_token: bool = Field(default=False, alias="POSTUREAI_REQUIRE_ADMIN_TOKEN")
```
And in `backend/app/routes.py` lines 60–65:
```python
def require_admin_token(x_postureai_admin_token: str | None = Header(default=None)) -> None:
    if not settings.require_admin_token:
        return
    if not settings.admin_token:
        raise HTTPException(status_code=503, detail="admin token is not configured")
    if not x_postureai_admin_token or not hmac.compare_digest(x_postureai_admin_token, settings.admin_token):
        raise HTTPException(status_code=401, detail="administrator token is required")
```
- Out of the box, `require_admin_token` evaluates to `False`.
- Any device on the local network can send:
  ```bash
  curl -X DELETE http://<pi-ip>:8000/api/data
  ```
  and **permanently wipe all records in `samples`, `minute_summaries`, `daily_summaries`, and `alerts` without any credentials**.
- Any device on the LAN can rewrite server settings via `PUT /api/settings`.

### 6.2 Ingestion Endpoints Have Zero Authentication
Even if an operator sets `POSTUREAI_REQUIRE_ADMIN_TOKEN=true`:
- `POST /api/samples` (`routes.py` Line 284): Unauthenticated. Anyone on the network can inject fraudulent posture measurements.
- `POST /api/alerts` (`routes.py` Line 318): Unauthenticated. Anyone can flood the database with fake alert entries.
- `PUT /api/camera/frame` (`routes.py` Line 134): Unauthenticated. Accepts arbitrary JPEG uploads up to 3MB directly into backend memory.
- `PUT /api/client/status` (`routes.py` Line 97): Unauthenticated. Anyone can spoof Pi client heartbeat status.
- `PUT /api/indicator` (`routes.py` Line 113): Unauthenticated. Anyone can toggle the physical LED state remotely.

### 6.3 Broken Admin Token Failure Mode (Self-Inflicted DoS)
In `backend/app/routes.py` lines 62–63:
```python
if not settings.admin_token:
    raise HTTPException(status_code=503, detail="admin token is not configured")
```
If an administrator sets `POSTUREAI_REQUIRE_ADMIN_TOKEN=true` in `docker-compose.yml` but fails to provide a non-empty `POSTUREAI_ADMIN_TOKEN`, the server throws `503 Service Unavailable` on every mutation. The dashboard settings screen becomes permanently bricked.

### 6.4 Root Execution in Docker
`docker/Dockerfile.backend` runs Python as `root`. Volumes mounted from the host (`./database:/app/database`) create SQLite database files owned by `root:root` on the host filesystem, breaking permissions for any unprivileged host user or backup utility.

---

## 7. Architecture & Code Quality: Severe Incoherence & Waste

### 7.1 37 Megabytes of Binary Bloat Committed Directly to Git
The Git repository is used as an uncompressed binary dumping ground:
- `frontend/public/wasm/vision_wasm_internal.wasm` — **10.64 MB**
- `frontend/public/wasm/vision_wasm_nosimd_internal.wasm` — **10.00 MB**
- `frontend/public/models/pose_landmarker_full.task` — **8.96 MB**
- `frontend/public/models/pose_landmarker_lite.task` — **5.51 MB**
- `docs/OffSynTech_Project_Report.pdf` (0.9 MB) and duplicate `OffSynTech_Project_Report.pdf` at root (0.9 MB)
- `frontend/public/alert_thai.wav` (0.3 MB) duplicated in `raspberrypi/alert_thai.wav` (0.3 MB)
- `designs/postureai_print_case/postureai-front-layout-shell.stl` (0.3 MB) and `.blend` file (0.2 MB)

**Total Binary Bloat:** Over **37 MB** of static assets tracked directly in Git history without Git LFS.

### 7.2 Dual Competing MediaPipe Runtimes (Dead Weight)
The project claims to be an edge-AI system running MediaPipe on the Raspberry Pi 5.
- Yet the author bundled 37MB of WASM and MediaPipe models into `frontend/public/` to run MediaPipe in the browser.
- When the Pi connects via WebRTC, the Pi burns the skeleton directly onto the video frames.
- In `frontend/app.js` lines 552–558, the author had to write code to **explicitly turn off the frontend canvas**:
  ```javascript
  function drawPiOverlay() {
    // The Pi already burns the current MediaPipe skeleton into its WebRTC
    // frame. Drawing the same landmarks in the browser creates a second,
    // misaligned cyan skeleton, so keep the dashboard canvas off for Pi video.
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    canvas.hidden = true;
  }
  ```
  The client downloads 37MB of WASM and model files only to immediately hide the canvas and discard the client-side pipeline.
- Furthermore, `frontend/package.json` specifies a `postinstall` script (`copy-mediapipe-assets.mjs`) to copy files from `node_modules` into `public/wasm/`, while the exact same files are already committed to Git.

### 7.3 Hardcoded Fake Spine Metrics in Browser Mode
In `frontend/pose-utils.js` line 50:
```javascript
const torso = 0;
```
The browser posture scoring explicitly hardcodes `torso = 0`.
The dashboard UI displays a prominent card labeled "แนวกระดูกสันหลัง (แนวโน้มโน้มตัว/เอนหลัง)", but the underlying math hardcodes it to zero. Forward and backward slouching is **never penalized** in browser mode. The metric is completely fabricated.

### 7.4 Discrete Quantization Destroys Posture Scoring
In `raspberrypi/client/posture_classifier.py` lines 21–26:
```python
SCORES_BY_LABEL = {
    "good": 100.0,
    "stretch": 80.0,
    "slouch": 30.0,
    "chin_rest": 15.0,
}
```
When Kanden ONNX classification is enabled, the 0–100 posture scoring engine is completely bypassed and replaced with hard step jumps between 100, 80, 30, and 15. The neck, shoulder, and torso angles displayed on the dashboard are rendered irrelevant to the score.

---

## 8. Performance & Concurrency: Amateur Anti-Patterns

### 8.1 Brutal 500ms Polling Flood
In `frontend/app.js` lines 1002–1005:
```javascript
loadSensorReadings();
setInterval(loadSensorReadings, 500);
loadIndicatorStatus();
setInterval(loadIndicatorStatus, 500);
```
- Every single open browser tab fires **4 HTTP requests per second**.
- That is **240 requests/minute, 14,400 requests/hour per client**.
- Single-worker Uvicorn on a Raspberry Pi 5 is forced to parse headers, run middleware, and allocate JSON responses 14,400 times an hour for two numbers that rarely change. Neither WebSockets nor Server-Sent Events (SSE) were implemented.

### 8.2 Aggregating 50,000 Rows in Python Heap Instead of SQL
In `backend/app/daily_report.py` lines 126–187 and `backend/app/routes.py` line 348:
When `/api/stats` is called, it loads **every single minute row over the retention window (up to 50,000+ rows)** from SQLite into Python memory:
```python
for row in db.scalars(select(MinuteSummary).where(MinuteSummary.minute_start >= start, ...)):
    buckets[row.minute_start] = { ... }
```
Then it loops over all 50,000 items in Python, constructs Python dictionaries, computes Python math, and aggregates daily buckets manually in Python.
The author completely bypassed SQL `GROUP BY`, `AVG()`, `MIN()`, `MAX()`.
Furthermore, in `routes.py` line 366:
```python
bucket = monthly_totals[str(row["label"])[:7]]
```
It slices the first 7 characters of an ISO date string in Python (`[:7]`) to group months.
In `daily_report.py` line 63, `compact_legacy_samples` loads the **entire `Sample` table and the entire `MinuteSummary` table into Python dictionaries at server boot**.

### 8.3 Mathematically Invalid Excel Aggregation
In `backend/app/daily_report.py` line 351:
```python
("คะแนนเฉลี่ย", "=IFERROR(AVERAGE('รายละเอียดรายนาที'!B2:B%d),0)" % (len(minute_rows) + 1))
```
Using `=AVERAGE(...)` on minute averages is **mathematically invalid**.
If Minute 1 has 1 measurement of 40, and Minute 2 has 60 measurements of 100:
- True weighted average: `(40*1 + 100*60) / 61 = 99.01`
- Excel formula: `(40 + 100) / 2 = 70.00`  
The generated Excel report displays distorted, mathematically incorrect daily averages.

### 8.4 WebRTC Signaling: Hardcoded Single-Viewer Bottleneck
In `backend/app/camera_signaling.py` lines 24–28:
```python
if role == "viewer":
    if self._pi is None or self._viewer is not None:
        return False
    self._viewer = websocket
    return True
```
- Only **one viewer** can ever connect.
- If you refresh your browser page, the new connection arrives before the old TCP socket closes. The server immediately aborts the new connection with error `1013: "camera is already being viewed by another dashboard"`. The video stream permanently breaks on a simple page reload.
- You cannot view the camera on two devices simultaneously.

### 8.5 Fatal Reconnection Deadlock Bug in Frontend
In `frontend/app.js` lines 612–617:
```javascript
if (message.code === 'unavailable') {
    piManualStop = true;
    $('cameraSignal').className = 'camera-signal risk';
    $('cameraSignal').textContent = message.message;
    state('กล้องถูกใช้งานอยู่', 'risk');
}
```
And line 528:
```javascript
function reconnectPiCamera() {
  if (piManualStop) return;
  ...
}
```
If the backend returns `unavailable` (e.g. because the Pi is momentarily restarting or the viewer refreshed), `app.js` sets `piManualStop = true`. Once set, `reconnectPiCamera` **aborts permanently**. The client stops all automatic reconnection attempts and remains dead until a hard page reload or manual click.

### 8.6 Vite Dev Server Fails to Proxy WebSockets
In `frontend/vite.config.js` lines 14–19:
```javascript
proxy: {
  '/api': {
    target: backendTarget,
    changeOrigin: true,
  },
},
```
The Vite proxy configuration omits `ws: true`.
During development via `npm run dev`, WebSocket connections to `/api/camera/webrtc` fail to proxy, making WebRTC unusable on `localhost:5173`.

### 8.7 Startup Event Loop Blocking
In `backend/app/main.py` lines 56–65:
Inside the async `lifespan` handler, `write_daily_report`, `compact_legacy_samples`, `capture_daily_summaries`, and `prune_expired_data` are executed **synchronously**. If the SQLite file has tens of thousands of rows, the entire server event loop freezes on startup until disk operations finish.

---

## 9. Edge & Raspberry Pi Engineering: Blocking I/O & SD Card Abuse

### 9.1 Synchronous Blocking Operations in 10-FPS Loop
In `raspberrypi/posture_client.py` lines 349–380:
- `uploader.fetch_settings()`: Synchronous `requests.get()` inside the frame loop. If the network hiccups, the camera loop hangs for up to 5 seconds.
- `uploader.send_client_status()`: Synchronous `requests.put()`.
- In `raspberrypi/client/alert.py` line 55:
  ```python
  result = subprocess.run(command, check=False, timeout=10)
  ```
  `subprocess.run(["aplay", ...])` is called **synchronously**. Playing `alert_thai.wav` freezes the posture detection loop for ~3 full seconds.
- In `raspberrypi/client/buzzer.py` lines 68–76: `beep()` calls `time.sleep()` in the main thread.

### 9.2 Flash Storage (SD Card) Burnout via Temporary Audio Writes
Look at `raspberrypi/client/alert.py` lines 67–88:
```python
def _make_beep(self) -> Path:
    ...
    handle = tempfile.NamedTemporaryFile(prefix="postureai-alert-", suffix=".wav", delete=False)
    ...
    with wave.open(str(path), "wb") as output:
        output.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return path
```
On **every single posture warning**, `SoundPlayer` synthesizes an uncompressed WAV file and writes it to disk flash storage, then invokes `aplay`, and deletes it.
Writing temporary WAV files to an SD card flash drive repeatedly will rapidly burn out flash write cycles and corrupt the Raspberry Pi OS root filesystem!

### 9.3 In-Place Frame Vandalism (MediaPipe Detects on Painted Skeletons)
In `raspberrypi/client/capture.py` lines 77–79:
```python
if overlay_renderer is not None:
    overlay_renderer(frame)
self.frames.put(frame)
```
- `overlay_renderer(frame)` draws green skeleton lines and joint circles directly into `frame` in place.
- Then `self.frames.put(frame)` stores this defaced frame.
- Then in `posture_client.py` line 364, `producer.frames.get()` retrieves this frame and feeds it to MediaPipe.
- **MediaPipe is running computer vision on an image that already has green skeleton graphics drawn all over the user's face and shoulders from previous iterations.**

### 9.4 I2C Hardware Incompetence: Blocking File Descriptor Churn
In `raspberrypi/sensor_readers.py` lines 84–99:
```python
bus = smbus2.SMBus(self.bus_number)
try:
    bus.write_byte(self.address, BH1750_POWER_ON)
    time.sleep(0.01)
    bus.write_byte(self.address, BH1750_CONTINUOUS_HIGH_RES)
    time.sleep(self.measurement_seconds)  # <-- BLOCKS FOR 180 MILLISECONDS!
    read_message = smbus2.i2c_msg.read(self.address, 2)
    bus.i2c_rdwr(read_message)
    data = list(read_message)
finally:
    bus.close()
```
On **every single lux reading**:
1. It opens a brand-new Linux character device file descriptor `/dev/i2c-1`.
2. It sends a power-on byte.
3. It blocks for 10ms.
4. It sends a continuous mode command.
5. It **sleeps for 180ms synchronously**.
6. It reads 2 bytes and closes the file descriptor.

In `sensor_web_client.py` (`--interval 0.5`), **38% of the CPU process lifecycle is spent in a hard `time.sleep(0.18)` lockup**. Continuous measurement mode is designed to be set once, with asynchronous non-blocking polling.

### 9.5 Pi 5 GPIO Failure in Buzzer
`indicator.py` went through complex `ioctl` character-device probing to locate the RP1 chip on Pi 5. But `buzzer.py` line 35 naively calls `gpiozero.LED(self.pin)` with no pin factory. On Pi 5 Bookworm, `buzzer.py` crashes on startup.

---

## 10. UI/UX & Apple Design Standard Violations

### 10.1 Token Anarchy: Three Conflicting Color Palettes
The codebase has no single source of truth for design tokens:
- In `docs/specs/tokens.css` (claiming to be the "Source of truth"):
  ```css
  --bg-primary: #0A0E1A; --brand-primary: #5B8DEF; --status-good: #22E58D; --status-risk: #FF4D6D;
  ```
- In `frontend/app.css` (the actual production stylesheet):
  ```css
  --bg-primary: #020817; --brand-blue: #087cff; --status-good: #20e6d0; --status-risk: #ff344b;
  ```
- In `frontend/risk.css`:
  ```css
  border-color: var(--status-good, #22e58d); /* Hardcoded fallback differs from app.css */
  border-color: var(--status-risk, #ff4d6d);
  ```
The author documented a design system in `docs/specs/` and immediately abandoned it in the production stylesheets.

### 10.2 Gaudy "Cyber-Gamer" Aesthetics vs. Apple Ergonomic Clarity
Apple HIG mandates content-first clarity, subtle depth, high legibility, and distraction-free feedback.
- `frontend/app.css` line 3 proudly declares: `Electric Navy Cyber-Medical Design System`.
- The dashboard is cluttered with fake sci-fi HUD corners (`<span class="corner tl"></span>`), pulsing neon LED dots (`.status-pulse-dot`, `.pulsing-led`), glowing text shadows (`text-shadow: 0 0 12px var(--brand-cyan)`), and harsh neon borders.
- For an ergonomic tool meant to sit in a worker's peripheral vision, gaudy pulsing animations and electric cyan glows cause visual fatigue—the exact opposite of good ergonomic UX.

### 10.3 Primitive Canvas Charts (No Accessibility, No Tooltips, No High-DPI Support)
In `frontend/app.js` lines 753–792, `drawBarChart()` renders charts using primitive HTML5 Canvas `fillRect()`:
- **No High-DPI / Retina Scaling:** The canvas ignores `window.devicePixelRatio`. On Retina MacBooks, iPads, and modern 4K displays, charts render fuzzy and pixelated.
- **Zero Interactivity:** No tooltips, no hover states, no drill-downs. Values are stamped directly as static text rotated at `-0.35` radians.
- **Zero Accessibility:** Canvas charts lack ARIA descriptions, data tables, or keyboard focus. Screen readers cannot read any historical trend data.
- **Fixed Hardcoded Dimensions:** `<canvas width="800" height="280">` breaks responsive scaling on mobile viewports.

---

## 11. Clean Code & Ponytail Pruning (What to Cut Immediately)

Applying Robert Martin's Clean Code principles and Ponytail Over-Engineering Pruning reveals massive dead flexibility and boilerplate that should be deleted:

### 11.1 Ponytail Cut Ledger (Deletions & Simplifications)
- `frontend/public/wasm/*` and `frontend/public/models/*`: **Delete ~37 MB of binaries.** The Pi already does edge MediaPipe inference.
- `frontend/scripts/copy-mediapipe-assets.mjs`: **Delete entirely.** Redundant with pre-committed files.
- `backend/app/routes.py:L280-L281`: `def json_dumps(value): return json.dumps(value)` — **Delete.** 2-line useless wrapper around standard library `json.dumps`.
- `backend/app/routes.py:L224-L227`: `_clamp_int()` — **Delete.** Replace with Python stdlib `max(lo, min(hi, val))`.
- `backend/app/daily_report.py:L142-L166`: Querying legacy `Sample` table in `_minute_rows_between()` — **Delete.** All samples are already migrated into `MinuteSummary` on boot.
- `backend/app/daily_report.py:L47-L51`: Hand-rolled `_utc_minute` string replacer — **Delete.** Use native `datetime.fromisoformat()`.
- `raspberrypi/blink_led_pin11.py`, `test_bh1750.py`, `test_sensors.py`: **Delete.** Stray debug scripts cluttering root module folders.
- `database/postureai.sqlite.legacy`, `database/server.mjs.legacy`: **Delete.** Abandoned artifacts from a long-dead Node.js codebase.

---

## 12. Hypocrisy: Marketing Lies vs. Implementation Reality

### 12.1 "100% Offline & Private" is False
The project documentation repeatedly claims:
> *"ความปลอดภัยและความเป็นส่วนตัว 100% ข้อมูลและภาพของคุณถูกประมวลผลบนอุปกรณ์ ไม่มีส่งออกสู่ภายนอก ทำงานออฟไลน์สมบูรณ์"*
1. In `frontend/index.html` lines 9–11: The page imports Google Fonts from `fonts.googleapis.com` and `fonts.gstatic.com`. On an isolated LAN without internet, font requests hang.
2. In `frontend/app.js` lines 934–935: The application contains online/offline event listeners with toast messages:
   ```javascript
   window.addEventListener('online', () => toast('กลับมาออนไลน์แล้ว สามารถโหลด AI จาก CDN ได้'));
   window.addEventListener('offline', () => toast('ออฟไลน์: AI จาก CDN อาจเริ่มไม่ได้'));
   ```
   The code literally tells the user that it relies on a CDN to download AI models.
3. In `raspberrypi/generate_voice.py` lines 20–24: Voice generation uses `edge_tts`, which transmits user alert text over the public internet to Microsoft Azure cloud endpoints.

### 12.2 Silent LocalStorage Fallback (Data Blackhole)
In `frontend/storage.js` lines 241–248:
```javascript
export async function createStorage() {
  const backend = new BackendStorage();
  try {
    await backend.health();
    return backend;
  } catch {
    return new LocalStorageStorage();
  }
}
```
If the backend is slow to respond on page load, the frontend silently drops the user into `LocalStorageStorage`. The user gets no error dialog, their data stops syncing with the Pi, Excel exports fail, and all changes are isolated to their browser tab.

### 12.3 Stale Documentation & Dead Links
- `docs/README.md` lines 6–8 lists `wireframes/` and `prototype/` directories. Neither exists in the repository.
- `database/README.md` documents an obsolete schema with only `samples`, `alerts`, and `settings`. It doesn't mention `minute_summaries` or `daily_summaries`.
- Git commit history contains **5 consecutive commits** frantically toggling LED active-high vs active-low back and forth because the author couldn't figure out basic breadboard wiring.

---

## 13. Final Unspared Scorecard & Verdict

| Category | Score | Breakdown |
| :--- | :---: | :--- |
| **Testing & CI/CD** | **0 / 10** | Tests fail out of the box in backend and Pi suites. CI crashes on clean checkout. `task.md` claims are fabricated. |
| **Industrial / 3D Case** | **0 / 10** | 3D print case has NO power cable opening, NO Pi mounting holes, and NO ventilation slots. It's a sealed oven. |
| **Electrical & Hardware** | **0 / 10** | 5V pullup into 3.3V RP1 I2C pins. 3W amp rail-sag brownout reboots. Uncoordinated I2C bus collision chaos. |
| **Biomechanical Validity** | **1 / 10** | Optically impossible to detect forward slouch from front camera. Arbitrary unvalidated math. Slouch lock-in. |
| **Security & Auth** | **1 / 10** | Admin token disabled by default. Unauthenticated endpoint wipes entire DB. No ingestion validation. Docker runs as root. |
| **Architecture** | **2 / 10** | 37MB binary bloat in Git. Dual competing MediaPipe runtimes. Fake torso math in frontend. Discrete jumps in ONNX mode. |
| **UI / Apple Design** | **1 / 10** | Token anarchy across 3 files. Gaudy cyberpunk neon glows. Non-Retina canvas charts. No accessibility. |
| **Performance** | **2 / 10** | 14,400 HTTP reqs/hr polling flood. 50,000 rows aggregated in Python loops. 1-viewer WebRTC lockout. Reconnect deadlock. |
| **Hardware / Edge Code** | **1 / 10** | Synchronous blocking audio & HTTP in frame loop. Burns temporary WAV to SD flash. Corrupted input frames. Broken I2C. |
| **Documentation** | **1 / 10** | Outdated docs, dead directory links, false claims about 100% offline self-containment, CDN dependencies. |
| **Overall System Grade** | **F (0.5 / 10)** | **Complete system failure across electrical, software, and physical domains. Total redesign required.** |
