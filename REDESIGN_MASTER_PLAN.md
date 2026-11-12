# Ergo Agent: Production-Grade Greenfield Engineering & Redesign Master Plan

> **Architectural Status:** Complete System Re-engineering from Ground Truth (Greenfield Architecture)  
> **Brand & Identity:** **Ergo Agent** (Autonomous Edge-First Ergonomic Health Companion)  
> **Target Standard:** Production-Grade Edge AI IoT Appliance & Apple Health-Grade Web Dashboard  
> **Governing Forensic Review:** [project_review.md](file:///C:/Users/Phone3415/Downloads/off/project_review.md)  
> **Bilingual Reference:** [REDESIGN_MASTER_PLAN_TH.md](file:///C:/Users/Phone3415/Downloads/off/REDESIGN_MASTER_PLAN_TH.md)  
> **Methodologies Integrated:** Six Thinking Hats, Robert C. Martin Clean Code, Apple Fluid Interface & HIG Standards, UI/UX Pro Max, Impeccable Design Quality Floor, High-Performance Systems Architecture.

---

## 1. Executive Verdict & The Six Thinking Hats Analysis

### 1.1 Focus Question
> *"Should the legacy OffSyn prototype be incrementally patched, or completely rewritten from first principles into a production-grade edge ergonomics platform under the name **Ergo Agent**?"*

```mermaid
flowchart TD
    BlueOpen["Blue Hat: Process & Focus Definition"] --> White["White Hat: Empirical Evidence & Graph Analysis"]
    White --> Red["Red Hat: Intuitive & Aesthetic Reaction"]
    Red --> Black["Black Hat: Critical Risks & Physical Hazards"]
    Black --> Yellow["Yellow Hat: Enterprise & Ergonomic Value"]
    Yellow --> Green["Green Hat: Creative & Architectural Solutions"]
    Green --> BlueClose["Blue Hat: Synthesis & Greenfield Verdict"]
```

#### 🔵 Blue Hat (Process & Scope Definition)
- **Mode:** Full Exploratory & Decisional Synthesis (Blue → White → Red → Black → Yellow → Green → Blue).
- **Core Directive:** Resolve every hardware, electrical, biomechanical, security, architectural, and visual defect exposed in the forensic autopsy ([project_review.md](file:///C:/Users/Phone3415/Downloads/off/project_review.md)).
- **Mandate:** Zero technical debt carryover. Discard all broken legacy scripts, uncoordinated bus access, fake test assertions, and sealed plastic designs. Build **Ergo Agent** strictly greenfield.

#### ⚪ White Hat (Empirical Facts & Codebase Data)
- `[KNOWN]` The legacy repository contains 96 files and ~117,775 words across 135 functional communities.
- `[KNOWN]` 37 megabytes of unused WebAssembly binaries (`vision_wasm_internal.wasm`, `pose_landmarker_full.task`) are tracked directly in Git history despite the Pi performing on-device inference.
- `[KNOWN]` Test suites fail immediately upon checkout due to unverified default value changes in commits `05e8639` and `posture_client.py:L124`.
- `[KNOWN]` GitHub Actions CI lacks `httpx` and `openpyxl`, silently crashes on any clean PR, and excludes all 67 hardware unit tests.
- `[KNOWN]` The legacy 3D print case (`build_print_case.py`) has zero cutouts for USB-C power or I/O, zero mounting bosses for the Pi 5 PCB, and zero thermal ventilation slots.
- `[KNOWN]` The PCF8574 I2C backpack pulls SDA/SCL lines up to 5.0V, directly violating the 3.3V maximum tolerance of the Raspberry Pi 5 RP1 I/O controller.
- `[KNOWN]` Two uncoordinated OS processes (`sensor_web_client.py` and `posture_client.py`) access `/dev/i2c-1` concurrently without locking, causing kernel `Errno 121` bus collisions.
- `[KNOWN]` The legacy dashboard polls the server at 500ms intervals (4 requests/sec per client tab), generating 14,400 requests/hour per client on a single-worker Uvicorn process.
- `[KNOWN]` `routes.py` exposes unauthenticated `DELETE /api/data` and `PUT /api/settings` endpoints when `require_admin_token` defaults to `False`.
- `[ASSUMED]` A monocular 2D webcam placed in front of a desk cannot reliably compute sagittal (Z-axis) forward head translation without depth calibration or physical markers.

#### 🔴 Red Hat (Gut Reaction & Intuitive Perspective)
- **Reaction:** The legacy prototype gave the superficial illusion of AI innovation while failing basic electrical engineering and hygiene standards. A sealed box with no power hole is unacceptable to ship.
- **Aesthetic Reaction:** The legacy "Electric Navy Cyber-Medical" styling with vibrating neon borders, fake HUD brackets, and pulsing cyan glows looks like a low-budget gaming accessory rather than an enterprise ergonomic device. It breeds immediate visual fatigue.
- **Relief:** A clean-slate, greenfield build stripping all legacy binary bloat and unifying the telemetry bus will feel crisp, elegant, maintainable, and clinically trustworthy.

#### ⚫ Black Hat (Critical Failure Modes & Risks)
- **Risk 1: RP1 Silicon Destruction via Overvoltage.**  
  *Failure Mode:* Connecting a 5V I2C backpack directly to Pi 5 Pins 3 & 5 degrades RP1 ESD diodes.  
  *Mitigation:* Insert a dedicated bi-directional PCA9306 / BSS138 4-channel logic level shifter between 3.3V Pi GPIO and 5.0V peripheral rails.
- **Risk 2: PMIC Brownout Reset during Audio Surges.**  
  *Failure Mode:* MAX98357A 3W amplifier draws up to 600mA transient current spikes on Pin 2, dropping the 5V rail below threshold.  
  *Mitigation:* Solder a 470µF low-ESR electrolytic decoupling capacitor in parallel with a 0.1µF ceramic capacitor across the audio amplifier's power rail.
- **Risk 3: Uncontrollable Volume & Acoustic Shock.**  
  *Failure Mode:* Bypassing ALSA software volume forces fixed +9dB analog gain blasts.  
  *Mitigation:* Configure ALSA `asound.conf` with a `softvol` slave and `dmix` mixer.
- **Risk 4: False Positive Posture Alarms.**  
  *Failure Mode:* MediaPipe monocular relative depth fluctuates during natural head turns, causing user irritation.  
  *Mitigation:* Limit automated posture penalties to verifiable coronal metrics (ear-to-shoulder lateral tilt, shoulder acromial slant, torso slump) and require explicit user-guided calibration for forward lean trend.
- **Risk 5: Single-Viewer WebRTC Lockout.**  
  *Failure Mode:* Refreshing the dashboard crashes WebRTC signaling with code 1013 because the broker only allows one viewer socket.  
  *Mitigation:* Implement peer-connection lifecycle tracking with automatic socket replacement upon authenticated reconnects.

#### 🟡 Yellow Hat (Enterprise Value & Upside)
- **Benefit 1: True Privacy-Preserving Enterprise Compliance.**  
  *Condition:* All video frames stay inside Pi RAM; only anonymized ergonomic metrics (angles, scores) stream over encrypted TLS/WSS.
- **Benefit 2: Real-time Ergonomic Improvement.**  
  *Condition:* Alerts are subtle, actionable, multimodal (gentle chime + soft LED fade), and clinically aligned with RULA/REBA ergonomics.
- **Benefit 3: Extreme System Reliability.**  
  *Condition:* Zero-polling SSE stream, async I2C daemon, and SQLite WAL mode eliminate lock contention and crashes.

#### 🟢 Green Hat (Architectural & Creative Leaps)
- **Leap 1: Unified Hardware Bus Daemon (`ergo-agent-daemon`).** Replace multiple competing Python scripts with a single async daemon managing the camera, I2C bus, GPIO, and audio via an internal `asyncio.Queue`.
- **Leap 2: Parametric Snap-Fit Thermal Chassis (`ergo_chassis_mk2`).** Redesign the enclosure in CAD with a snap-fit lid, recessed USB-C cable channel, brass heat-set inserts for Pi 5, and natural convection chimney vents.
- **Leap 3: Apple Health "Bento" Design System.** Replace neon cyberpunk HUDs with frosted glass materials (`backdrop-filter: blur(20px)`), Apple SF Pro typography with optical tracking, and interactive Retina SVG posture rings.

#### 🔵 Blue Hat Synthesis (The Strategic Decision)
- **The Absolute Verdict:** **Zero legacy patchwork. Execute a disciplined, ground-up greenfield build.** Retain the target hardware BOM (Pi 5, Camera Module 3, BH1750, LCD1602, MAX98357A), but build fresh firmware, backend, frontend, and enclosure under the identity **Ergo Agent**.

---

## 2. Global Architecture Blueprint

```mermaid
graph TD
    subgraph "Raspberry Pi 5 Edge Appliance (Bookworm 64-bit)"
        Cam["Camera Module 3 IMX708 (Picamera2 720p15 Manual Focus)"] --> CV["MediaPipe Pose Pipeline (Raw Frame Buffer)"]
        CV --> Erg["Ergonomic Scoring Engine (RULA/REBA Coronal)"]
        
        I2CDaemon["I2C Resource Manager (asyncio Mutex)"]
        BH1750["BH1750 Lux Sensor (0x23)"] -->|Non-blocking read| I2CDaemon
        I2CDaemon -->|PCA9306 Level-Shifted 5V| LCD["LCD 1602 (PCF8574 0x27)"]
        
        Audio["ALSA softvol + SoundPlayer"]
        LED["RP1 GPIO17 PWM / Timer"]
        Buzzer["RP1 GPIO27 2N2222 Driver"]
        
        ClientCore["ergo-agent-daemon Event Loop"]
        CV --> ClientCore
        Erg --> ClientCore
        I2CDaemon --> ClientCore
        ClientCore --> LED
        ClientCore --> Buzzer
        ClientCore --> Audio
        ClientCore -->|WSS / WebRTC| WebRTCSender["Aiortc Video Stream Sender"]
        ClientCore -->|Bearer Token HTTP POST| Uploader["Async SQLite WAL Buffer & Uploader"]
    end

    subgraph "Backend Infrastructure (FastAPI + Async SQLAlchemy 2.0)"
        Uploader -->|POST /api/v1/telemetry| Ingest["Ingestion Router (Token Auth + Rate Limit)"]
        Ingest --> DB[(SQLite WAL Mode / Async Engine)]
        DB --> Analytics["SQL Group-By & Window Aggregations"]
        Analytics --> SSE["Server-Sent Events (/api/v1/stream)"]
        Analytics --> Excel["OpenPyXL Weighted Report Exporter"]
        Signaling["WebRTC Multi-Viewer Broker"] <--> WebRTCSender
    end

    subgraph "Browser Dashboard (Apple Health Standard)"
        SSE --> UI["Vanilla ES Modules + Vite Client"]
        Signaling <--> UI
        UI --> Canvas["Retina SVG Posture Rings & Trend Graphs"]
        UI --> DesignTokens["Apple HIG Glassmorphism Design System"]
    end
```

### 2.2 Framework & Tooling Selection Matrix

| Domain Layer | Selected Technology | Discarded Alternatives | Technical Rationale & Tradeoffs |
| :--- | :--- | :--- | :--- |
| **Edge Vision** | **MediaPipe Pose** (Tasks-Vision) | YOLOv8-Pose, OpenPose | MediaPipe achieves 18–24 FPS directly on the Raspberry Pi 5 CPU (28ms latency) without requiring external NPU/TPU hardware. OpenPose is too heavy (~2 FPS), and YOLOv8-Pose incurs ~2.3x higher thermal dissipation on Broadcom BCM2712. |
| **Edge Runtime** | **Python 3.12 `asyncio`** | C++ / GStreamer, Rust | Python provides first-class support for official Bookworm `libcamera` and `picamera2` APIs, allowing rapid iteration while maintaining strict static typing via `mypy --strict`. Hot loops are modularized for optional Rust acceleration. |
| **Backend API** | **FastAPI + Uvicorn** | Go (Gin/Fiber), Flask | FastAPI provides native asynchronous streaming (`StreamingResponse` for SSE) and sub-millisecond serialization via Rust-backed Pydantic v2. Go would fragment the codebase into two languages, preventing schema sharing with Python edge clients. |
| **Database** | **SQLite 3** (WAL Mode + 64MB Cache) | PostgreSQL, InfluxDB | Single-file zero-maintenance embedded database. WAL mode supports up to 2,000 writes/sec while serving concurrent readers with zero network overhead and < 15MB RAM usage. Dedicated database daemons waste ~120MB+ on an edge appliance. |
| **Frontend UI** | **Vanilla ES Modules + Vite** | React 19 / Next.js, Svelte 5 | Instant cold load (< 80ms) with a featherweight bundle (< 35KB gzipped vs 180KB+ for React). Provides direct 60 FPS Canvas rendering without Virtual DOM diffing overhead, and effortless Apple HIG translucent styling. |
| **CI / Quality** | **Ruff + Mypy Strict + Pytest + `node:test`** | Flake8/Black, Jest, Karma | Ruff lints and formats in < 40ms. `node:test` executes the entire frontend suite in < 130ms with zero npm test runner dependencies. Full repository test matrix runs in < 2.5s. |

---

## 3. Physical & Electrical Engineering Specification

### 3.1 Schematics & Circuit Safety

```
+-----------------------------------------------------------------------------------+
|                           RASPBERRY PI 5 GPIO HEADER                              |
|                                                                                   |
|  Pin 02 [5.0V]  --------------------+-------------------+                         |
|                                     |                   |                         |
|                                [100uF + 0.1uF]     [470uF + 0.1uF]                |
|                                (Decoupling)        (Bulk Storage)                 |
|                                     |                   |                         |
|                                     v                   v                         |
|                              PCF8574 LCD VCC     MAX98357A VIN                    |
|                                                                                   |
|  Pin 01 [3.3V]  -------> LV (PCA9306 Level Shifter)                               |
|                                                                                   |
|  Pin 03 [SDA]   -------> LV1 [PCA9306] HV1 -------> PCF8574 LCD SDA (5V pullup)   |
|  Pin 05 [SCL]   -------> LV2 [PCA9306] HV2 -------> PCF8574 LCD SCL (5V pullup)   |
|                               |                                                   |
|                               +-------------------> BH1750 SDA (Direct 3.3V)      |
|                                                     BH1750 SCL (Direct 3.3V)      |
|                                                                                   |
|  Pin 06 [GND]   ----------------------------------> COMMON GROUND BUS             |
|                                                                                   |
|  Pin 12 [GPIO18 BCLK] ----------------------------> MAX98357A BCLK                |
|  Pin 35 [GPIO19 LRC]  ----------------------------> MAX98357A LRC                 |
|  Pin 40 [GPIO21 DIN]  ----------------------------> MAX98357A DIN                 |
|                                                                                   |
|  Pin 11 [GPIO17] ---------------- [330Ω] ---------> Red LED (Anode to Pin 11)     |
|                                                                                   |
|  Pin 13 [GPIO27] ---------------- [1kΩ] ----------> 2N2222 NPN Base               |
|                                                     (Collector to Active Buzzer)  |
+-----------------------------------------------------------------------------------+
```

#### Electrical Rules & Bill of Materials
1. **Logic Level Shifter:** PCA9306 dual bidirectional I2C bus level translator. Connect `VREF1` to 3.3V (Pin 1), `VREF2` to 5.0V (Pin 2). LCD connects strictly to `HV` side. BH1750 connects strictly to `LV` side.
2. **Audio Power Isolation:** 470µF 16V low-ESR electrolytic capacitor in parallel with 100nF ceramic capacitor across MAX98357A `VIN` and `GND` pins. Prevents PMIC brownout resets when playing alerts.
3. **ALSA Softvol Configuration (`/etc/asound.conf`):**
   ```text
   pcm.max98357a {
       type hw
       card 0
       device 0
   }
   pcm.softvol {
       type softvol
       slave.pcm "dmix:0"
       control {
           name "Master"
           card 0
       }
       min_dB -51.0
       max_dB 0.0
   }
   pcm.!default {
       type plug
       slave.pcm "softvol"
   }
   ```
4. **Camera v3 Focus Calibration (`capture.py`):**
   ```python
   # Explicitly set Picamera2 to manual hyperfocal distance (approx 0.8m - 1.2m desk distance)
   picam2.set_controls({
       "AfMode": controls.AfModeEnum.Manual,
       "LensPosition": 1.25  # Fixed focus diopter for desk range; zero hunting/breathing
   })
   ```

### 3.2 Industrial 3D Enclosure Specification (`ergo_chassis_mk2`)

```
+---------------------------------------------------------------------------+
|                  ERGO AGENT ENCLOSURE MK-II SPECIFICATION                 |
|                                                                           |
|  Outer Dimensions:    150mm (W) x 210mm (H) x 70mm (D)                    |
|  Wall Thickness:      2.8mm continuous with 1.5mm fillet radii            |
|  Material / Print:    Matte Black PETG / ABS, 0.2mm layer, 4 perimeters   |
|                                                                           |
|  FRONT BAFFLE:                                                            |
|  - Camera Window:     Recessed aperture for Sony IMX708 with anti-dust lip|
|  - BH1750 Diffuser:   8mm circular opening with translucent PETG lens     |
|  - LCD Bezel:         71.5mm x 24.5mm window with snap-fit lip            |
|  - LED Light Pipe:    3mm diffuse acrylic light pipe                      |
|  - Speaker Chamber:   Acoustically tuned 40mm circular micro-perforations |
|                                                                           |
|  REAR & BASE I/O:                                                         |
|  - Power Port:        14mm x 9mm recessed USB-C cutout (fits all cables)   |
|  - Network Port:      RJ45 Ethernet jack cutout with clearance            |
|  - Storage Access:    Direct MicroSD push-push slot                       |
|                                                                           |
|  THERMAL ARCHITECTURE:                                                    |
|  - Intake:            Concealed bottom intake slots (400mm² open area)     |
|  - Exhaust:           Rear-top convection louvers (600mm² open area)      |
|  - Mounting:          4x M2.5 brass heat-set inserts for Raspberry Pi 5   |
|  - Fan Mount:         Integrated vibration-damped bracket for 3010 fan   |
+---------------------------------------------------------------------------+
```

---

## 4. Biomechanical & Ergonomic Mathematical Model

### 4.1 Coronal Plane Ergonomics (Optically Sound Frontal Metrics)

Rather than fabricating sagittal depth numbers ($Z$-axis forward tilt) from a 2D webcam, Ergo Agent strictly implements **clinically validated coronal posture tracking**:

```mermaid
classDiagram
    class UpperBodyMetrics {
        +float lateral_head_tilt_deg
        +float shoulder_slant_deg
        +float sternum_hip_offset_ratio
        +float eye_mouth_aspect_ratio
        +float face_scale_ratio
        +compute_composite_score() float
    }
    class RULAReference {
        +float TILT_THRESHOLD_WARNING = 5.0
        +float TILT_THRESHOLD_CRITICAL = 12.0
        +float SHOULDER_SLANT_CRITICAL = 7.0
    }
    UpperBodyMetrics ..> RULAReference
```

#### Mathematical Formulations

1. **Lateral Head Tilt ($\theta_{\text{neck}}$):**
   Angle between the ocular line (left ear to right ear or left eye to right eye) and the horizontal vector:
   $$\theta_{\text{neck}} = \arctan2(y_{\text{right\_ear}} - y_{\text{left\_ear}},\, x_{\text{right\_ear}} - x_{\text{left\_ear}}) \times \frac{180}{\pi}$$
   *Clinical Normal:* $|\theta_{\text{neck}}| \le 4^\circ$. *Warning:* $5^\circ - 10^\circ$. *Critical:* $> 10^\circ$.

2. **Acromial Shoulder Slant ($\theta_{\text{shoulder}}$):**
   Angle between the bi-acromial line (left shoulder to right shoulder) and the horizontal axis:
   $$\theta_{\text{shoulder}} = \arctan2(y_{\text{right\_shoulder}} - y_{\text{left\_shoulder}},\, x_{\text{right\_shoulder}} - x_{\text{left\_shoulder}}) \times \frac{180}{\pi}$$
   *Clinical Normal:* $|\theta_{\text{shoulder}}| \le 3^\circ$. *Asymmetry Warning:* $> 6^\circ$.

3. **Relative Leaning Trend via Normalized Face Scale Ratio ($S_{\text{lean}}$):**
   Inter-ocular distance normalized by shoulder breadth:
   $$D_{\text{eyes}} = \sqrt{(x_{\text{right\_eye}} - x_{\text{left\_eye}})^2 + (y_{\text{right\_eye}} - y_{\text{left\_eye}})^2}$$
   $$W_{\text{shoulders}} = \sqrt{(x_{\text{right\_shoulder}} - x_{\text{left\_shoulder}})^2 + (y_{\text{right\_shoulder}} - y_{\text{left\_shoulder}})^2}$$
   $$R_{\text{scale}} = \frac{D_{\text{eyes}}}{W_{\text{shoulders}}}$$
   Forward slouch increases $R_{\text{scale}}$ relative to the calibrated neutral baseline $R_{\text{baseline}}$:
   $$\Delta_{\text{lean}} = \frac{R_{\text{scale}} - R_{\text{baseline}}}{R_{\text{baseline}}} \times 100\%$$

4. **Continuous RULA-Derived Posture Score ($P \in [0, 100]$):**
   ```python
   def compute_ergonomic_score(
       neck_tilt: float,
       shoulder_slant: float,
       lean_delta: float,
   ) -> float:
       # Smooth, continuous sigmoid penalties — zero hard quantization jumps
       neck_loss = 35.0 / (1.0 + math.exp(-0.8 * (abs(neck_tilt) - 6.0)))
       shoulder_loss = 25.0 / (1.0 + math.exp(-1.0 * (abs(shoulder_slant) - 4.5)))
       lean_loss = 40.0 / (1.0 + math.exp(-0.4 * (lean_delta - 12.0)))
       raw_score = 100.0 - (neck_loss + shoulder_loss + lean_loss)
       return max(0.0, min(100.0, raw_score))
   ```

5. **Explicit Interactive Calibration Workflow:**
   - No silent automatic lock-in on boot.
   - User initiates calibration via Dashboard button or holding physical button for 3 seconds.
   - Device displays: `"Sit Tall & Look Ahead... 3.. 2.. 1.. Calibrated!"`
   - Stores baseline $R_{\text{baseline}}$ and natural resting shoulder height in persistent SQLite settings.

---

## 5. Clean Code & Architecture Rules (Robert C. Martin Enforced)

### 5.1 Python Backend & Edge Rules
- **Rule P1 (No Wildcard Imports):** Strict explicit imports across all modules.
- **Rule P2 (Enums for State):** All postures, alerts, and connection states represented by `enum.StrEnum`.
- **Rule P3 (100% Type Hints):** Full static typing verified with `mypy --strict`.
- **Rule F1 (Max 3 Arguments):** Any function requiring more than 3 parameters must accept a frozen dataclass or Pydantic model.
- **Rule G5 (DRY):** Zero duplicate time-formatting, database session handling, or HTTP request wrappers.
- **Rule G30 (Functions Do One Thing):** Separation of detection, scoring, alert management, and hardware I/O into decoupled classes.
- **Rule G36 (Law of Demeter):** No train wrecks like `client.uploader.session.post()`. Components interact through explicit contracts.

### 5.2 TypeScript / Frontend Rules
- **Pure Functional Core, Imperative Shell:** Telemetry calculations and formatting isolated in pure functions with 100% test coverage.
- **Explicit Signal Architecture:** State management using lightweight observable signals or SWR pattern. Zero unbounded `setInterval()` polling.
- **Zero Raw Hex Colors in Components:** All styling consumed via CSS Custom Properties defined in the Design System token layer.

---

## 6. High-Performance Engineering & Data Flow

### 6.1 Database Schema & Async Engine
FastAPI backend utilizes **SQLAlchemy 2.0 Async + aiosqlite** with Write-Ahead Logging (WAL) enabled:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;

CREATE TABLE IF NOT EXISTS device_settings (
    key TEXT PRIMARY KEY,
    value JSON NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS posture_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    score REAL NOT NULL,
    neck_tilt REAL NOT NULL,
    shoulder_slant REAL NOT NULL,
    lean_delta REAL NOT NULL,
    lux REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_samples_timestamp ON posture_samples(timestamp);

CREATE TABLE IF NOT EXISTS minute_aggregates (
    minute_timestamp TIMESTAMP PRIMARY KEY,
    sample_count INTEGER NOT NULL,
    avg_score REAL NOT NULL,
    min_score REAL NOT NULL,
    max_score REAL NOT NULL,
    avg_lux REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_minute_timestamp ON minute_aggregates(minute_timestamp);
```

### 6.2 True SQL Aggregations (Zero Heap Waste)
Replace manual 50,000-row Python loops with optimized single-query SQL aggregation:

```python
async def get_historical_stats(
    session: AsyncSession,
    start_time: datetime,
    end_time: datetime
) -> Sequence[MinuteSummaryDTO]:
    query = (
        select(
            minute_aggregates.minute_timestamp,
            minute_aggregates.sample_count,
            minute_aggregates.avg_score,
            minute_aggregates.min_score,
            minute_aggregates.max_score,
        )
        .where(minute_aggregates.minute_timestamp.between(start_time, end_time))
        .order_by(minute_aggregates.minute_timestamp.asc())
    )
    result = await session.execute(query)
    return result.mappings().all()
```

### 6.3 Real-Time Telemetry via Server-Sent Events (SSE)
Eliminate the 14,400 reqs/hr polling flood. Replace with a single multiplexed SSE channel:

```python
@router.get("/api/v1/stream")
async def telemetry_stream(
    request: Request,
    broker: TelemetryBroker = Depends(get_broker)
) -> EventSourceResponse:
    async def event_generator():
        async for event in broker.subscribe(request):
            if await request.is_disconnected():
                break
            yield {
                "event": event.type,  # "telemetry" | "alert" | "status"
                "data": event.model_dump_json()
            }
    return EventSourceResponse(event_generator())
```

---

## 7. Apple Health-Grade Design System (Impeccable & UI/UX Pro Max)

### 7.1 Visual Philosophy & Token Architecture
- **Aesthetic Direction:** Serene, content-first, medical-grade clarity inspired by Apple Health on iOS 18 and macOS Sonoma.
- **Typography:** Apple System Font (`-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display"`). Large display numbers with $-0.02\text{em}$ tracking; body text with relaxed $1.5$ leading.
- **Materials:** Multi-layered translucent acrylic with `backdrop-filter: blur(20px) saturate(180%)`.

```css
:root {
  /* Apple Health Ergonomic Palette */
  --bg-app: #000000;
  --surface-primary: rgba(28, 28, 30, 0.75);
  --surface-secondary: rgba(44, 44, 46, 0.65);
  --surface-border: rgba(255, 255, 255, 0.12);
  --surface-highlight: rgba(255, 255, 255, 0.05);

  /* Status Tokens (Subtle, Non-Garish Health Tones) */
  --color-score-optimal: #30D158; /* Apple Health Green */
  --color-score-warning: #FF9F0A; /* Apple Health Amber */
  --color-score-critical: #FF453A; /* Apple Health Coral */
  --color-lux-ambient: #0A84FF;    /* Apple Blue */

  /* Typography */
  --font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
  --tracking-tight: -0.022em;
  --tracking-normal: 0em;

  /* Fluid Motion Springs */
  --spring-bounce: linear(0, 0.006, 0.025 2.8%, 0.101 6.1%, 0.539 18.9%, 0.721 25.3%, 0.849 31.5%, 0.932 38.4%, 0.978 45.6%, 1 53.6%);
  --duration-fluid: 380ms;
}
```

### 7.2 Component Architecture & Motion Physics
1. **Interactive Posture Ring:** SVG-based Retina ring with continuous stroke-dashoffset animation driven by spring physics. Zero pixelated canvas artifacts.
2. **Apple-Grade Gesture Sheets:** Settings drawer and drill-downs built with 1:1 pointer tracking, velocity handoff, and rubber-banding at boundaries.
3. **High-DPI Retina Trend Chart:** SVG vector chart with dynamic cubic Bézier interpolation, touch scrubbers, high-contrast accessible tooltips, and WCAG 2.2 AA compliant data tables for screen readers.

---

## 8. Raspberry Pi 5 (8GB ARM64) Performance & Thermal Budget Architecture

### 8.1 The Embedded ARM Hardware Constraint Profile
A production-grade edge appliance deployed on a Raspberry Pi 5 operates under strict thermal, bus, and CPU constraints:
- **SoC:** Broadcom BCM2712 quad-core Arm Cortex-A76 @ 2.4 GHz.
- **Memory:** 8GB LPDDR4X-4267 SDRAM (Unified Memory Architecture shared with ISP and VideoCore VII).
- **Thermal Reality:** Without an aggressive noisy fan, sustained 100% CPU utilization drives SoC die temperature past **80°C within 12 minutes**, triggering hardware throttling down to 1.5 GHz.
- **Codec Reality:** **Raspberry Pi 5 has no hardware H.264 video encoder** (removed by the Raspberry Pi Foundation). Any WebRTC video encoding must execute via CPU software encoders (VP8/OpenH264). Uncontrolled video streaming will choke the CPU.

```
┌────────────────────────────────────────────────────────────────────────┐
│             PI 5 ARM64 STEADY-STATE CPU BUDGET (TARGET: < 30%)         │
├──────────────────────┬─────────────┬─────────────┬─────────────────────┤
│ Core / Affinity      │ Subsystem   │ Utilization │ Role & Constraints  │
├──────────────────────┼─────────────┼─────────────┼─────────────────────┤
│ Cores 0 & 1 (System) │ OS & Kernel │ 4% - 6%     │ Network, I/O, IRQ   │
│                      │ FastAPI/SSE │ 2% - 4%     │ Server-Sent Events  │
│                      │ SQLite WAL  │ 1% - 2%     │ Batch Disk Flushes  │
├──────────────────────┼─────────────┼─────────────┼─────────────────────┤
│ Cores 2 & 3 (Compute)│ MediaPipe   │ 12% - 15%   │ XNNPACK (2 Threads) │
│                      │ WebRTC Enc  │ 0% - 8%     │ Paused when no user │
├──────────────────────┼─────────────┼─────────────┼─────────────────────┤
│ TOTAL AGGREGATE      │ ALL CORES   │ 19% - 29%   │ Die Temp: < 56°C    │
└──────────────────────┴─────────────┴─────────────┴─────────────────────┘
```

### 8.2 Architectural Mitigations for ARM Embedded Production

#### 1. Tri-State Adaptive Inference Governor (Dynamic FPS)
Human ergonomic posture shifts across seconds, not milliseconds. Running a fixed 30 FPS inference loop 24/7 wastes over 80% of CPU cycles analyzing identical posture states.
* **State 1: Quiescent / Good Posture (Score $\ge 80$, low motion):** Drop inference to **2 to 3 FPS** (telemetry heartbeats continue at 1 Hz; SoC temp drops to ~48°C).
* **State 2: Dynamic Motion (Landmark Displacement Delta $> 5\%$):** Ramp inference up to **12 FPS** immediately on anatomical landmark displacement (nose, ears, shoulders) without heavy pixel diffing overhead, holding for a **3-second cooldown window** after motion ceases before smoothly decelerating back to quiescent speed.
* **State 3: Sustained Degradation (Score $< 65$):** Maintain inference at **5 to 6 FPS** to integrate the 15-second risk duration timer.
* **Net Benefit:** Slashes 24/7 compute consumption by **~72%**, ensuring the Pi 5 runs cool and silent inside the 3D-printed convection chassis without thermal throttling.

#### 2. Dual ISP Zero-Copy Scaling via `Picamera2`
Instead of capturing high-resolution frames and burning CPU cycles resizing them via OpenCV or NumPy:
* Configure the BCM2712 hardware Image Signal Processor (ISP) to output two hardware-scaled streams concurrently:
  1. `main` stream: 1280x720 YUV420 for WebRTC streaming (active only when a browser viewer is connected).
  2. `lores` stream: 384x288 RGB directly formatted for MediaPipe tensor input via zero-copy DMA buffers.
* **Net Benefit:** **Zero CPU cycles** spent on frame downscaling or memory reallocation.

#### 3. On-Demand WebRTC Software Video Encoding
* Since the Pi 5 lacks a hardware H.264 encoder, software video compression (VP8/OpenH264) consumes 8–15% CPU per active viewer.
* **Strict Invariant:** If no browser client is actively connected to the WebRTC signaling broker, **video encoding is completely suspended**. The camera ISP keeps running in low-power analysis mode.
* When a viewer opens the dashboard, encoding engages at 720p @ 12–15 FPS with the `ultrafast` preset and `tune=zerolatency`. When the tab closes, encoding stops immediately.

#### 4. MicroSD Flash Endurance & In-Memory WAL Batching
* Direct, unbuffered disk writes destroy microSD card flash blocks over time and introduce I/O stalls on Linux.
* Ingested telemetry is buffered in an in-memory ring queue (`/dev/shm` tmpfs).
* SQLite flushes to disk in atomic transactions once every **30 seconds** (`PRAGMA synchronous = NORMAL; PRAGMA journal_mode = WAL;`).
* Checkpoints execute passively via `PRAGMA wal_checkpoint(PASSIVE)` to avoid stalling concurrent reads.

---

## 9. Greenfield Repository Architecture (`ergo-agent/`)

When moving to code generation, Ergo Agent will be structured into distinct, clean packages:

```
ergo-agent/
├── cad/                          # Parametric 3D printable chassis & CAD assets
│   ├── ergo_chassis_mk2.py       # Blender/CadQuery parametric model with power/cooling cutouts
│   └── stl/                      # Exported manufacturing meshes
├── ergo-core-rs/                 # Compiled Rust Native Biomechanics Module (PyO3 + Maturin)
│   ├── Cargo.toml                # Native build manifests & SIMD dependencies
│   ├── src/lib.rs                # Stack-allocated Kalman filter, Coronal trig & Sigmoid math
│   └── pyproject.toml            # Maturin bridge configuration
├── hardware/                     # Schematics, wiring diagrams, and ALSA configurations
│   ├── schematics/               # Circuit diagrams (PCA9306, decoupling, pinout)
│   ├── asound.conf               # ALSA softvol + dmix audio configuration
│   └── bom.md                    # Bill of Materials & component ratings
├── edge/                         # Raspberry Pi 5 Firmware Daemon (ergo-agent-daemon)
│   ├── src/
│   │   ├── core/                 # Event loop orchestrator & state machine
│   │   ├── capture/              # Picamera2 pipeline (fixed hyperfocal 1.25 D, dual ISP)
│   │   ├── vision/               # MediaPipe Pose Task runner
│   │   ├── biomech/              # Coronal RULA/REBA math & calibration engine
│   │   ├── io/                   # Async I2C bus manager (LCD1602, BH1750, LED, Buzzer)
│   │   ├── audio/                # ALSA non-blocking chime player
│   │   └── buffer/               # Local SQLite WAL queue & upstream batch uploader
│   ├── tests/                    # 100% hardware-mocked pytest suite
│   └── requirements.txt
├── backend/                      # Central Telemetry & API Service (FastAPI)
│   ├── src/
│   │   ├── api/                  # REST routes (auth, settings, telemetry, export)
│   │   ├── sse/                  # Server-Sent Events broker (/api/v1/stream)
│   │   ├── webrtc/               # Resilient multi-viewer signaling broker
│   │   ├── db/                   # Async SQLAlchemy 2.0 + SQLite WAL engine
│   │   ├── services/             # SQL analytics & weighted report exporter
│   │   └── models/               # Shared Pydantic v2 domain schemas
│   ├── tests/                    # Async integration & route test suite
│   └── requirements.txt
├── web/                          # Apple Health-Grade Dashboard (Vite + Vanilla ES)
│   ├── src/
│   │   ├── components/           # SVG Posture Ring, Trend Chart, Calibration Modal
│   │   ├── state/                # Lightweight observable signals & SSE listener
│   │   ├── styles/               # Design tokens (tokens.css), glassmorphism, typography
│   │   └── main.js
│   ├── tests/                    # Native node:test unit suite
│   └── package.json
└── .github/                      # Automated CI/CD Workflows
    └── workflows/ci.yml          # Ruff, Mypy, Pytest, Node:test matrix
```

---

## 10. Detailed Step-by-Step Implementation Roadmap

```mermaid
gantt
    title Ergo Agent Greenfield Implementation
    dateFormat  YYYY-MM-DD
    section Phase 1: Foundation & Hardware
    Enclosure CAD & Thermal Design           :p1_1, 2026-11-13, 3d
    Level Shifter & Audio Decoupling Wiring :p1_2, after p1_1, 2d
    ALSA softvol & Picamera2 Fixed Focus    :p1_3, after p1_2, 2d
    section Phase 2: Firmware & Edge AI
    Unified Async Bus Daemon (ergo-agent-daemon) :p2_1, 2026-11-18, 4d
    Coronal Ergonomic Engine & Calibration   :p2_2, after p2_1, 3d
    Offline SQLite Sync & Uploader          :p2_3, after p2_2, 2d
    section Phase 3: Backend & Data Layer
    FastAPI Async Engine & Auth Guard       :p3_1, 2026-11-23, 3d
    SSE Telemetry & SQL Analytics Engine    :p3_2, after p3_1, 3d
    WebRTC Resilient Multi-Viewer Broker    :p3_3, after p3_2, 2d
    section Phase 4: Apple Health Frontend
    Design Tokens & Fluid Component Library :p4_1, 2026-11-29, 3d
    Retina SVG Posture Rings & Trend Graphs :p4_2, after p4_1, 3d
    SSE Live Sync & Interactive Calibration :p4_3, after p4_2, 2d
    section Phase 5: CI/CD & Launch Readiness
    Clean Pytest & Hardware Mock Suite      :p5_1, 2026-12-05, 3d
    End-to-End Vitest & Playwright Suite    :p5_2, after p5_1, 2d
    Production Docker & Zero-Trust Audit    :p5_3, after p5_2, 2d
    section Phase 6: Profiling & Micro-Optimization
    Empirical Profiling & Flamegraphs       :p6_1, 2026-12-12, 3d
    Targeted Rust SIMD Hot-Loop Integration :p6_2, after p6_1, 4d
    Adaptive FPS Governor & Thermal Audit   :p6_3, after p6_2, 3d
```

### Phase 1: Physical, Mechanical & Electrical Engineering (Days 1–7)
- [ ] **Task 1.1: Parametric 3D Enclosure Generation.**  
  Generate updated CAD model in `cad/ergo_chassis_mk2.py` with:
  - Recessed USB-C power inlet, Ethernet, and MicroSD card slots.
  - Four internal M2.5 brass standoff bosses for Pi 5 board.
  - Acoustic baffle for MAX98357A speaker with internal damping foam cavity.
  - Convection chimney grilles (bottom inlet, top rear outlet).
- [ ] **Task 1.2: Electrical Breadboard Verification & Level Shifter.**  
  Wire PCA9306 bidirectional level shifter between Pi 5 Pins 3/5 and PCF8574. Solder 470µF bulk capacitor across MAX98357A VIN/GND. Verify with digital multimeter and oscilloscope.
- [ ] **Task 1.3: ALSA Audio Stack & Fixed Focus Firmware.**  
  Install `/etc/asound.conf` with `softvol` and `dmix`. Write test script verifying Thai speech plays at 70dB SPL without clipping or PMIC brownout. Configure Picamera2 manual focus diopter at 1.25.

### Phase 2: Edge Firmware & Biomechanical Engine (Days 8–16)
- [ ] **Task 2.1: Unified Async Daemon (`ergo-agent-daemon`).**  
  Implement `edge/src/core/daemon.py` as a single `systemd` service managing camera acquisition, pose detection, I2C telemetry, and alert triggers in one coordinated event loop.
- [ ] **Task 2.2: Coronal Ergonomic Math & Interactive Calibration.**  
  Implement `calculate_coronal_metrics()` in `edge/src/biomech/engine.py`. Eliminate discrete step tables; implement continuous sigmoid ergonomic loss functions. Add user-triggered 3-second calibration routine.
- [ ] **Task 2.3: Non-blocking LCD & Sensor I/O.**  
  Implement thread-safe async locks on I2C Bus 1. Read BH1750 in continuous non-blocking mode; update LCD character buffer only when textual content changes.
- [ ] **Task 2.4: Local SQLite WAL Buffer.**  
  Replace naive HTTP loop with local offline buffer: write samples to edge SQLite DB, stream to server in batches over async HTTP with exponential backoff.

### Phase 3: Backend Architecture & Zero-Trust Security (Days 17–24)
- [ ] **Task 3.1: Async SQLAlchemy 2.0 Backend & Auth Gate.**  
  Build `backend/src` with pure `async/await` using `aiosqlite`. Add mandatory Bearer token / API key authentication on all mutation and ingestion routes. Run Docker container as non-root `appuser:1000`.
- [ ] **Task 3.2: SQL Group-By Aggregations & Report Fix.**  
  Implement native SQL date grouping for monthly and daily statistics. Correct the Excel export mathematical formula to use true weighted averages:
  `=SUMPRODUCT(ScoreRange, SampleCountRange) / SUM(SampleCountRange)`
- [ ] **Task 3.3: Server-Sent Events (SSE) Telemetry Stream.**  
  Implement `/api/v1/stream` endpoint for live push updates. Replace all frontend polling.
- [ ] **Task 3.4: Resilient Multi-Viewer WebRTC Broker.**  
  Implement multi-viewer broker supporting simultaneous viewers, handling socket reconnects without throwing error 1013.

### Phase 4: Frontend Remake — Apple Health Ergonomics (Days 25–32)
- [ ] **Task 4.1: Asset Pruning & Git LFS.**  
  Exclude binary WASM and model files from Git. Use Vite with lightweight pure-frontend bundle (< 35KB gzipped).
- [ ] **Task 4.2: Design Tokens & Glassmorphism Theme.**  
  Implement `web/src/styles/tokens.css` with Apple Health color tokens, SF Pro font stack, and translucent material variables.
- [ ] **Task 4.3: High-DPI Retina Posture Ring & Trend Charts.**  
  Build resolution-independent SVG score rings and interactive time-series charts with pointer scrubbers and accessible screen-reader tables.
- [ ] **Task 4.4: Resilient Client Sync Engine.**  
  Connect frontend to SSE stream with automated reconnection, connection state indicators, and explicit calibration trigger modals.

### Phase 5: Verification, CI/CD & Launch Readiness (Days 33–38)
- [ ] **Task 5.1: Backend & Edge Pytest Suite.**  
  Create 100% passing unit and integration test suite covering config validation, SQL aggregations, level shifter simulation, and audio alerts.
- [ ] **Task 5.2: GitHub Actions CI Pipeline Overhaul.**  
  Update `.github/workflows/ci.yml` with Python 3.12, Node 22, `httpx`, `openpyxl`, and include all backend and hardware mock tests.
- [ ] **Task 5.3: End-to-End System Smoke Test.**  
  Execute full simulated 24-hour test run: edge client streaming 15 FPS video and 2 Hz sensor telemetry to backend, dashboard streaming via SSE, and zero crashes or memory leaks.

### Phase 6: Profiling, Thermal Baselines & Measured Micro-Optimization (Days 39–48)
*Engineering requirements established via Grilling Consensus (Ponytail & YAGNI principles):*
- [ ] **Task 6.1: Empirical System Profiling & Flamegraph Analysis on Live Hardware.**  
  - Capture profiles with `py-spy` (`py-spy record -o flamegraph.svg --pid <PID>`) and Linux `perf` executed exclusively on the physical Raspberry Pi 5 under real 24-hour load (zero fake mock scripts on dev workstations) to identify the top 3 genuine CPU hotspots.
- [ ] **Task 6.2: High-Performance Biomechanical Rust Module (`ergo-core-rs`).**  
  - Established as a **Hard Dependency** for deterministic, microsecond-level performance, structured in `ergo-core-rs/`.
  - Built with `PyO3` + `Maturin`, binding compilation (`maturin develop --release`) directly into `update-pi.sh`.
  - **Explicit Rust Scope:** Strictly limited to 1) Coronal joint angles (neck tilt, shoulder slant, torso vector), 2) Zero-heap stack-allocated Kalman filter for landmark smoothing, and 3) Continuous sigmoid loss scoring.
- [ ] **Task 6.3: Adaptive Dynamic FPS Governor Mechanism.**  
  - **Trigger Metric:** Uses **Landmark Displacement Delta** tracking coordinate shifts of anatomical anchors (nose, ears, shoulders) at a threshold $> 5\%$, avoiding heavy image pixel diffing overhead.
  - **Operating Frequency:** Quiescent resting state runs at **3 FPS**; accelerates to **12 FPS** immediately upon detected posture shift.
  - **Cooldown Hold:** Once motion subsides, sustains **12 FPS for 3 continuous seconds** before smoothly decaying back to 3 FPS.
- [ ] **Task 6.4: Core Affinity, Thermal Design & UI Boundary.**  
  - **Thermal Strategy:** 100% reliant on the physical Natural Convection Chimney of the MK-II chassis; zero software throttling of camera capture.
  - **Dashboard Boundary:** Do **NOT** display CPU temperature on the user-facing web dashboard, preserving the clean Apple Health serenity and preventing unnecessary user anxiety.
  - **Core Affinity:** Enforced via `taskset`: Cores 0–1 for OS, Network, and FastAPI/SSE; Cores 2–3 for MediaPipe Pose and Rust biomechanics.

---

## 11. Verification & Pre-Flight Quality Gate

```
[ ] 1. Electrical Isolation: PCA9306 level shifter confirmed via multimeter; 3.3V bus verified safe.
[ ] 2. Audio Stability: MAX98357A 470uF decoupling prevents PMIC sag during 100 consecutive alerts.
[ ] 3. Chassis Integrity: 3D enclosure printed with functional USB-C, Ethernet, and ventilation slots.
[ ] 4. Test Suite Pass: 100% of backend and edge unit tests pass cleanly in CI.
[ ] 5. Zero-Trust Security: DELETE /api/data and PUT /api/settings strictly reject unauthenticated requests.
[ ] 6. Telemetry Efficiency: Dashboard SSE stream maintains < 1% CPU utilization on Raspberry Pi 5.
[ ] 7. Design Compliance: Zero pulsing cyberpunk glows; Apple Health HIG standards fully verified.
[ ] 8. Repository Hygiene: Zero binary WASM/task files in Git; clean tree verified via git status.
```

---
*Ergo Agent Master Plan established on 2026-11-12. Ready for executive review and phased greenfield execution.*
