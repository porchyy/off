# Graph Report - off  (2026-11-12)

## Corpus Check
- 96 files · ~117,775 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 17 file(s) not represented in the graph (top: (none) 4, .stl 2, .css 2)

## Summary
- 1660 nodes · 2582 edges · 135 communities (70 shown, 65 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 139 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- MediaPipe WASM Runtime
- MediaPipe WASM (No-SIMD) Runtime
- Frontend Storage & Backend Sync
- FastAPI API Endpoints
- Database Schema & SQLite Persistence
- Hardware Alert Controller
- Docker Deployment & Containers
- Frontend Storage & Backend Sync (2)
- Daily & Monthly Report Generation
- Edge HTTP Uploader & Buffer
- RP1 GPIO LED Indicator
- Upper Body Posture Scoring
- I2C PCF8574 LCD Driver
- Upper Body Posture Scoring (2)
- FastAPI API Endpoints (2)
- Sensor Web Client & Reporting
- CI/CD Pipeline & GitHub Actions
- WebRTC Streaming Sender
- BH1750 Ambient Light Sensor
- Frontend Build Dependencies
- Raspberry Pi Client Main Loop
- FastAPI API Endpoints (3)
- FastAPI API Endpoints (4)
- WebRTC Streaming Sender (2)
- Database Schema & SQLite Persistence (2)
- WebRTC Camera Signaling
- 3D Enclosure Design & Modeling
- MediaPipe WASM Runtime (2)
- MediaPipe WASM (No-SIMD) Runtime (2)
- GPIO Buzzer Control
- BH1750 Ambient Light Sensor (2)
- MediaPipe WASM Runtime (3)
- MediaPipe WASM (No-SIMD) Runtime (3)
- PiCamera2 Video Capture Pipeline
- Hardware Alert Controller (2)
- Application Configuration & Settings
- Runtime State Module
- Upper Body Posture Scoring (3)
- Requirements Module
- Copy-Mediapipe-Assets Module
- Config.Example Module
- Readme Module
- WebRTC Streaming Sender (3)
- Upper Body Posture Scoring (4)
- ONNX Posture Classifier
- Config.Example Module (2)
- FastAPI API Endpoints (5)
- MediaPipe WASM Runtime (4)
- MediaPipe WASM (No-SIMD) Runtime (4)
- ONNX Posture Classifier (2)
- Config.Example Module (3)
- Camera Store Module
- Upper Body Posture Scoring (5)
- Config.Example Module (4)
- Config.Example Module (5)
- PiCamera2 Video Capture Pipeline (2)
- Sensor Store Module
- Readme Module (2)
- MediaPipe WASM Runtime (5)
- MediaPipe WASM (No-SIMD) Runtime (5)
- Upper Body Posture Scoring (6)
- BH1750 Ambient Light Sensor (3)
- Update-Pi Module
- Forensic Architectural Autopsy
- Forensic Architectural Autopsy (2)
- MediaPipe WASM Runtime (6)
- MediaPipe WASM Runtime (7)
- MediaPipe WASM Runtime (8)
- MediaPipe WASM Runtime (9)
- MediaPipe WASM (No-SIMD) Runtime (6)
- MediaPipe WASM (No-SIMD) Runtime (7)
- MediaPipe WASM (No-SIMD) Runtime (8)
- MediaPipe WASM (No-SIMD) Runtime (9)
- BH1750 Ambient Light Sensor (4)
- Config.Example Module (6)
- Config.Example Module (7)
- Config.Example Module (8)
- Config.Example Module (9)
- Readme Module (3)
- Forensic Architectural Autopsy (3)
- Design Tokens & Stylesheets
- MediaPipe WASM Runtime (10)
- MediaPipe WASM Runtime (11)
- MediaPipe WASM (No-SIMD) Runtime (10)
- MediaPipe WASM (No-SIMD) Runtime (11)
- Forensic Architectural Autopsy (4)
- Config.Example Module (10)
- Setup-Pi5 Module
- Upper Body Posture Scoring (7)
- Offsyntech Quickguide Module
- Pi5-Setup-Guide Module
- Forensic Architectural Autopsy (5)
- MediaPipe WASM Runtime (12)
- MediaPipe WASM (No-SIMD) Runtime (12)
- Forensic Architectural Autopsy (6)
- Install-Sensor-Service Module
- ALSA Audio & Speech Configuration
- Agents Module
- Forensic Architectural Autopsy (7)
- Forensic Architectural Autopsy (8)
- MediaPipe WASM Runtime (13)
- MediaPipe WASM Runtime (14)
- MediaPipe WASM Runtime (15)
- MediaPipe WASM Runtime (16)
- MediaPipe WASM Runtime (17)
- MediaPipe WASM Runtime (18)
- MediaPipe WASM Runtime (19)
- MediaPipe WASM (No-SIMD) Runtime (13)
- MediaPipe WASM (No-SIMD) Runtime (14)
- MediaPipe WASM (No-SIMD) Runtime (15)
- MediaPipe WASM (No-SIMD) Runtime (16)
- MediaPipe WASM (No-SIMD) Runtime (17)
- MediaPipe WASM (No-SIMD) Runtime (18)
- MediaPipe WASM (No-SIMD) Runtime (19)
- Forensic Architectural Autopsy (9)
- Forensic Architectural Autopsy (10)
- Forensic Architectural Autopsy (11)
- Forensic Architectural Autopsy (12)
- Setup-Sensor-Pi5 Module
- Start Module
- Stop Module
- Offsyntech Project Report Module
- MediaPipe WASM Runtime (20)
- MediaPipe WASM (No-SIMD) Runtime (20)
- Forensic Architectural Autopsy (13)
- Forensic Architectural Autopsy (14)
- Forensic Architectural Autopsy (15)
- Forensic Architectural Autopsy (16)
- Forensic Architectural Autopsy (17)
- Forensic Architectural Autopsy (18)
- Requirements Module (2)
- Project Tasks & QA Tracking

## God Nodes (most connected - your core abstractions)
1. `main()` - 24 edges
2. `CharacterLcd` - 21 edges
3. `Uploader` - 20 edges
4. `AlertController` - 18 edges
5. `get_all()` - 17 edges
6. `process_live_frame()` - 17 edges
7. `validate_config()` - 17 edges
8. `Bh1750Reader` - 16 edges
9. `FakeUploader` - 16 edges
10. `lifespan()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Master Project Report PDF (Root)` --semantically_similar_to--> `Master Technical Documentation (OffSyn Tech)`  [EXTRACTED] [semantically similar]
  OffSynTech_Project_Report.pdf → docs/OffSynTech_Project_Report.html
- `Backend Service Container` --conceptually_related_to--> `FastAPI Backend Server`  [INFERRED]
  docker/README.md → backend/README.md
- `Persistent Database Volume Mount` --conceptually_related_to--> `SQLite Database File (postureai.sqlite)`  [INFERRED]
  docker/README.md → database/README.md
- `RPLCD HD44780 LCD Library` --semantically_similar_to--> `BH1750 Lux & LCD1602 Display Telemetry`  [INFERRED] [semantically similar]
  raspberrypi/requirements.txt → frontend/index.html
- `History Analytics & Excel Export View` --conceptually_related_to--> `Backend HTTP API Endpoints`  [INFERRED]
  frontend/index.html → backend/README.md

## Import Cycles
- None detected.

## Communities (135 total, 65 thin omitted)

### Community 2 - "Frontend Storage & Backend Sync"
Cohesion: 0.05
Nodes (57): applyStorageMode(), bangkokDate(), bangkokMonth(), begin(), beginPiCamera(), canvas, checkHealth(), connectPiCamera() (+49 more)

### Community 3 - "FastAPI API Endpoints"
Cohesion: 0.09
Nodes (34): camera_status(), _clamp_int(), client_status(), get_camera_frame(), get_indicator_status(), get_latest_sensor_readings(), health(), put_camera_frame() (+26 more)

### Community 5 - "Hardware Alert Controller"
Cohesion: 0.11
Nodes (15): AlertController, SoundPlayer, FakeIndicator, FakeSound, FakeUploader, test_alert_waits_for_risk_duration_and_respects_cooldown(), test_dashboard_settings_apply_without_restarting_client(), test_good_posture_resets_low_score_timer() (+7 more)

### Community 6 - "Docker Deployment & Containers"
Cohesion: 0.06
Nodes (37): build, condition, container_name, deploy, environment, healthcheck, ports, restart (+29 more)

### Community 7 - "Frontend Storage & Backend Sync (2)"
Cohesion: 0.09
Nodes (10): adminHeaders(), BackendStorage, createStorage(), dayKey(), KEYS, LocalStorageStorage, readJson(), requestJson() (+2 more)

### Community 8 - "Daily & Monthly Report Generation"
Cohesion: 0.13
Nodes (15): _alert_rows(), _alert_rows_between(), build_daily_report(), build_monthly_report(), daily_history(), _history_bounds(), local_day_bounds(), local_day_label() (+7 more)

### Community 9 - "Edge HTTP Uploader & Buffer"
Cohesion: 0.12
Nodes (3): Uploader, test_uploader_averages_detector_samples_before_posting(), test_uploader_sends_live_indicator_state_only_when_it_changes()

### Community 10 - "RP1 GPIO LED Indicator"
Cohesion: 0.11
Nodes (8): _detect_lgpio_chip(), _gpiochip_label(), GpioLed, test_blink_flashes_twice_and_leaves_the_led_off(), test_detect_lgpio_chip_falls_back_to_the_sysfs_index_without_a_dev_entry(), test_detect_lgpio_chip_finds_pi5_rp1_controller(), test_detect_lgpio_chip_maps_pi5_sysfs_index_to_the_character_device(), test_direct_lgpio_fallback_controls_an_active_high_led()

### Community 11 - "Upper Body Posture Scoring"
Cohesion: 0.10
Nodes (14): calculate_upper_body_metrics(), score_frontal_desk_metrics(), Point, test_calibrated_lean_trend_lowers_the_frontal_desk_score_only_when_extreme(), test_detector_initialization_fails_loudly_instead_of_using_fake_metrics(), test_forward_lean_proxy_uses_a_personal_neutral_depth_baseline(), test_frontal_desk_metrics_ignore_unstable_relative_depth(), test_head_drift_from_shoulders_is_penalized_at_the_visible_14_degree_range() (+6 more)

### Community 12 - "I2C PCF8574 LCD Driver"
Cohesion: 0.15
Nodes (7): CharacterLcd, test_lcd_1602_does_not_rewrite_an_unchanged_screen(), test_lcd_1602_lines_fit_the_display_and_show_posture_state(), test_lcd_1602_marks_scores_from_60_to_79_as_check_posture(), test_lcd_1602_prompts_for_a_complete_pose_and_clears_stale_scores(), test_lcd_1602_shows_the_trained_classifier_label_when_it_was_used(), test_lcd_1602_uses_risk_message_for_low_score()

### Community 13 - "Upper Body Posture Scoring (2)"
Cohesion: 0.16
Nodes (11): close_detector(), draw_pose_overlay(), get_detector(), get_posture_classifier(), _overlay_settings(), process_live_frame(), _publish_indicator_status(), run_detection_cycle() (+3 more)

### Community 14 - "FastAPI API Endpoints (2)"
Cohesion: 0.14
Nodes (10): capture_daily_summaries(), local_today(), prune_daily_summaries(), prune_expired_reports(), lifespan(), _retention_loop(), _root_index(), DailySummary (+2 more)

### Community 15 - "Sensor Web Client & Reporting"
Cohesion: 0.12
Nodes (8): main(), parse_lux_scale(), publish_sensor_payload(), read_sensor_payload(), Reader, test_publish_sensor_payload_closes_failed_response(), test_publish_sensor_payload_uses_latest_endpoint_and_timeout(), test_read_sensor_payload_handles_bh1750_error()

### Community 16 - "CI/CD Pipeline & GitHub Actions"
Cohesion: 0.10
Nodes (22): name, runs-on, steps, name, runs-on, steps, jobs, backend-tests (+14 more)

### Community 18 - "BH1750 Ambient Light Sensor"
Cohesion: 0.23
Nodes (6): main(), parse_args(), parse_i2c_address(), main(), parse_lux_scale(), main()

### Community 19 - "Frontend Build Dependencies"
Cohesion: 0.12
Nodes (16): dependencies, @mediapipe/tasks-vision@^0.10.35, devDependencies, vite@^5.4.10, name, private, scripts, build (+8 more)

### Community 20 - "Raspberry Pi Client Main Loop"
Cohesion: 0.22
Nodes (13): load_config(), validate_config(), test_config_accepts_a_non_negative_led_gpiochip(), test_config_accepts_only_supported_score_sources(), test_config_can_disable_mediapipe(), test_config_clamps_metric_smoothing_option(), test_config_clamps_overlay_smoothing_options(), test_config_rejects_unimplemented_remote_detection_mode() (+5 more)

### Community 21 - "FastAPI API Endpoints (3)"
Cohesion: 0.14
Nodes (6): Base, Setting, camera_webrtc(), json_dumps(), ensure_defaults(), setup_test_db()

### Community 22 - "FastAPI API Endpoints (4)"
Cohesion: 0.19
Nodes (9): _daily_report_loop(), add_alert(), add_sample(), download_daily_excel(), download_monthly_excel(), prune_old_data(), stats(), OkResponse (+1 more)

### Community 23 - "WebRTC Streaming Sender (2)"
Cohesion: 0.16
Nodes (3): CameraProducer, LatestFrameBuffer, test_latest_frame_buffer_keeps_only_the_latest_frame()

### Community 24 - "Database Schema & SQLite Persistence (2)"
Cohesion: 0.15
Nodes (16): Alerts Table Schema, Backend Environment Configuration, FastAPI Backend Server, Data Retention Policy, Samples Table Schema, Settings Table Schema, HTTPX Test Client, Pytest Test Framework (+8 more)

### Community 25 - "WebRTC Camera Signaling"
Cohesion: 0.23
Nodes (3): CameraSignalingBroker, test_broker_allows_one_pi_and_one_viewer_only(), check()

### Community 26 - "3D Enclosure Design & Modeling"
Cohesion: 0.14
Nodes (15): Blender 3D Case Model Asset, Case Hardware Cutouts & Openings, Front-Layout Case Dimensions & Specs, System Settings & Admin Controls, Raspberry Pi Client Main Loop (posture_client.py), eSpeak-NG Thai Speech Alert System, BCM GPIO17 Red LED Warning Indicator, MAX98357A I2S 3W Audio Amplifier Output (+7 more)

### Community 27 - "MediaPipe WASM Runtime (2)"
Cohesion: 0.14
Nodes (12): abort(), assert(), createLazyFile(), stream_ops, forceLoadFile(), getBinarySync(), getMouseWheelDelta(), getWasmBinary() (+4 more)

### Community 28 - "MediaPipe WASM (No-SIMD) Runtime (2)"
Cohesion: 0.14
Nodes (12): abort(), assert(), createLazyFile(), stream_ops, forceLoadFile(), getBinarySync(), getMouseWheelDelta(), getWasmBinary() (+4 more)

### Community 30 - "BH1750 Ambient Light Sensor (2)"
Cohesion: 0.25
Nodes (5): Bh1750Reader, SensorReadError, test_bh1750_applies_the_configured_lux_scale(), test_bh1750_read_error_clears_cached_address(), test_bh1750_uses_second_supported_address()

### Community 33 - "PiCamera2 Video Capture Pipeline"
Cohesion: 0.28
Nodes (7): Camera, _camera_indices(), open_camera(), _open_opencv(), _open_picamera2(), test_camera_indices_accepts_explicit_number(), test_camera_indices_accepts_list_and_csv()

### Community 37 - "Upper Body Posture Scoring (3)"
Cohesion: 0.20
Nodes (3): calculate_hip_metrics(), MediaPipePoseDetector, test_hip_metrics_measure_level_pelvis_and_vertical_trunk_when_aligned()

### Community 39 - "Requirements Module"
Cohesion: 0.20
Nodes (10): BH1750 Lux & LCD1602 Display Telemetry, RPLCD HD44780 LCD Library, requests HTTP Sensor Dependency, smbus2 Sensor Dependency, smbus2 Linux I2C Python Library, BH1750 Ambient Light Lux Sensor, Raspberry Pi 5 I2C Bus 1 Wiring, BH1750 Lux Scale Ratio Calibration (+2 more)

### Community 40 - "Copy-Mediapipe-Assets Module"
Cohesion: 0.20
Nodes (5): here, pkgDir, publicDir, root, targetWasmDir

### Community 41 - "Config.Example Module"
Cohesion: 0.20
Nodes (10): detection, enabled, interval, metric_smoothing_alpha, mode, model, overlay_hold_seconds, overlay_min_visibility (+2 more)

### Community 42 - "Readme Module"
Cohesion: 0.22
Nodes (9): Backend HTTP API Endpoints, History Analytics & Excel Export View, On-Device Edge AI Privacy Guarantee, Offline Static Asset Model Serving, MediaPipe Pose Landmarker Full Task File, Browser MediaPipe Pose Inference, Node Native Test Runner Suite, Frontend Storage & Backend Abstraction (+1 more)

### Community 44 - "Upper Body Posture Scoring (4)"
Cohesion: 0.31
Nodes (4): PoseOverlaySmoother, test_overlay_smoother_holds_then_discards_missing_landmarks(), test_overlay_smoother_ignores_low_confidence_landmarks(), test_overlay_smoother_interpolates_landmarks_and_preserves_raw_score_path()

### Community 46 - "Config.Example Module (2)"
Cohesion: 0.22
Nodes (8): backend, settings_sync_seconds, timeout, url, buffer, path, recording, sample_interval_seconds

### Community 47 - "FastAPI API Endpoints (5)"
Cohesion: 0.36
Nodes (5): compact_legacy_samples(), MinuteSummary, Sample, clear_data(), test_compact_legacy_samples_moves_high_frequency_data_to_one_minute()

### Community 48 - "MediaPipe WASM Runtime (4)"
Cohesion: 0.29
Nodes (8): assignWasmExports(), createWasm(), receiveInstance(), receiveInstantiationResult(), findWasmBinary(), getWasmImports(), locateFile(), updateMemoryViews()

### Community 49 - "MediaPipe WASM (No-SIMD) Runtime (4)"
Cohesion: 0.29
Nodes (8): assignWasmExports(), createWasm(), receiveInstance(), receiveInstantiationResult(), findWasmBinary(), getWasmImports(), locateFile(), updateMemoryViews()

### Community 51 - "Config.Example Module (3)"
Cohesion: 0.25
Nodes (8): indicator, active_high, blink_seconds, chip, delay_seconds, enabled, pin, threshold

### Community 53 - "Upper Body Posture Scoring (5)"
Cohesion: 0.43
Nodes (3): PoseMetricSmoother, test_metric_smoother_rejects_a_single_score_spike(), test_metric_smoother_resets_between_people_or_lost_poses()

### Community 54 - "Config.Example Module (4)"
Cohesion: 0.29
Nodes (7): camera, backend, flip, height, index, retries, width

### Community 55 - "Config.Example Module (5)"
Cohesion: 0.29
Nodes (7): lcd, columns, enabled, i2c_address, i2c_port, rows, update_seconds

### Community 58 - "Readme Module (2)"
Cohesion: 0.33
Nodes (6): Pi Camera Viewport & Overlay Canvas, Live Pose Monitor Interface Section, Office Syndrome Risk Evaluation Card, Posture Score Display & Ergonomic Advice Card, Biomechanical Angle Telemetry Bar, Pi WebRTC Low-Latency Live Video Pipeline

### Community 59 - "MediaPipe WASM Runtime (5)"
Cohesion: 0.33
Nodes (6): makeBufferEntry(), makeEntries(), makeEntry(), makeSamplerEntry(), makeStorageTextureEntry(), makeTextureEntry()

### Community 60 - "MediaPipe WASM (No-SIMD) Runtime (5)"
Cohesion: 0.33
Nodes (6): makeBufferEntry(), makeEntries(), makeEntry(), makeSamplerEntry(), makeStorageTextureEntry(), makeTextureEntry()

### Community 63 - "Update-Pi Module"
Cohesion: 0.50
Nodes (3): build.sh script, fail(), update-pi.sh script

### Community 64 - "Forensic Architectural Autopsy"
Cohesion: 0.40
Nodes (4): Balanced Focus Mode Alert Logic, Upper-Body Pose Scoring Geometry, Biomechanical Forward Head Posture Quackery, Hardcoded Fake Spine Metrics in Browser Mode

### Community 65 - "Forensic Architectural Autopsy (2)"
Cohesion: 0.40
Nodes (5): 40-Pin GPIO Hardware Mapping Specification, Hardware Pin Wiring Reference, Uncoordinated I2C Bus Contention, Power Rail Sag & Brownout Reboots, 5V Logic Pullup Hazard on Pi 5 RP1 Controller

### Community 67 - "MediaPipe WASM Runtime (7)"
Cohesion: 0.40
Nodes (5): initRuntime(), postRun(), preRun(), run(), doRun()

### Community 68 - "MediaPipe WASM Runtime (8)"
Cohesion: 0.40
Nodes (5): makeBlendComponent(), makeBlendState(), makeColorState(), makeColorStates(), makeFragmentState()

### Community 69 - "MediaPipe WASM Runtime (9)"
Cohesion: 0.40
Nodes (5): makeVertexAttribute(), makeVertexAttributes(), makeVertexBuffer(), makeVertexBuffers(), makeVertexState()

### Community 71 - "MediaPipe WASM (No-SIMD) Runtime (7)"
Cohesion: 0.40
Nodes (5): initRuntime(), postRun(), preRun(), run(), doRun()

### Community 72 - "MediaPipe WASM (No-SIMD) Runtime (8)"
Cohesion: 0.40
Nodes (5): makeBlendComponent(), makeBlendState(), makeColorState(), makeColorStates(), makeFragmentState()

### Community 73 - "MediaPipe WASM (No-SIMD) Runtime (9)"
Cohesion: 0.40
Nodes (5): makeVertexAttribute(), makeVertexAttributes(), makeVertexBuffer(), makeVertexBuffers(), makeVertexState()

### Community 75 - "Config.Example Module (6)"
Cohesion: 0.40
Nodes (5): buzzer, active_high, enabled, pin, threshold

### Community 76 - "Config.Example Module (7)"
Cohesion: 0.40
Nodes (5): posture_classifier, enabled, interval, min_confidence, model

### Community 77 - "Config.Example Module (8)"
Cohesion: 0.40
Nodes (5): sound, device, enabled, file, volume

### Community 78 - "Config.Example Module (9)"
Cohesion: 0.40
Nodes (5): video, enabled, fps, height, width

### Community 79 - "Readme Module (3)"
Cohesion: 0.50
Nodes (4): Backend Service Container, Persistent Database Volume Mount, OffSyn Docker Deployment Setup, Frontend Nginx Alpine Container

### Community 80 - "Forensic Architectural Autopsy (3)"
Cohesion: 0.50
Nodes (4): Master Technical Documentation (OffSyn Tech), Master Project Report PDF (Docs), Master Project Report PDF (Root), False Offline Marketing & Cloud TTS Dependencies

### Community 81 - "Design Tokens & Stylesheets"
Cohesion: 0.50
Nodes (4): Documentation Directory Index, OffSyn Tech Design System & Style Guide, Privacy-Preserving Posture Silhouette Icons, OffSyn Tech Project Overview

### Community 82 - "MediaPipe WASM Runtime (10)"
Cohesion: 0.50
Nodes (4): getFullscreenElement(), requestFullscreen(), fullscreenChange(), updateCanvasDimensions()

### Community 83 - "MediaPipe WASM Runtime (11)"
Cohesion: 0.50
Nodes (4): makeColorAttachment(), makeColorAttachments(), makeDepthStencilAttachment(), makeRenderPassDescriptor()

### Community 84 - "MediaPipe WASM (No-SIMD) Runtime (10)"
Cohesion: 0.50
Nodes (4): getFullscreenElement(), requestFullscreen(), fullscreenChange(), updateCanvasDimensions()

### Community 85 - "MediaPipe WASM (No-SIMD) Runtime (11)"
Cohesion: 0.50
Nodes (4): makeColorAttachment(), makeColorAttachments(), makeDepthStencilAttachment(), makeRenderPassDescriptor()

### Community 86 - "Forensic Architectural Autopsy (4)"
Cohesion: 0.50
Nodes (4): Camera Module v3 Focus Breathing & Low-Res Crippling, Dual Competing MediaPipe Runtimes, WebRTC Single-Viewer Lockout & Reconnect Deadlock, Edge AI & WebRTC Architecture

### Community 87 - "Config.Example Module (10)"
Cohesion: 0.50
Nodes (4): risk, cooldown, seconds, threshold

### Community 88 - "Setup-Pi5 Module"
Cohesion: 0.83
Nodes (3): compose_cmd(), fail(), setup-pi5.sh script

### Community 90 - "Offsyntech Quickguide Module"
Cohesion: 0.67
Nodes (3): OffSyn Tech Quick Guide HTML Edition, OffSyn Tech Quick Guide & Overview (Markdown), OffSyn Tech Quick Guide PDF Edition

### Community 93 - "MediaPipe WASM Runtime (12)"
Cohesion: 1.00
Nodes (3): syncfs(), doCallback(), done()

### Community 94 - "MediaPipe WASM (No-SIMD) Runtime (12)"
Cohesion: 1.00
Nodes (3): syncfs(), doCallback(), done()

## Knowledge Gaps
- **76 isolated node(s):** `RFC-2279`, `RFC-3629`, `RFC-2279`, `RFC-3629`, `Executive Autopsy: The Illusion of Completion` (+71 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 937 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **65 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `Upper Body Posture Scoring (2)` to `PiCamera2 Video Capture Pipeline`, `Hardware Alert Controller`, `Edge HTTP Uploader & Buffer`, `RP1 GPIO LED Indicator`, `I2C PCF8574 LCD Driver`, `WebRTC Streaming Sender`, `BH1750 Ambient Light Sensor`, `Raspberry Pi Client Main Loop`, `WebRTC Streaming Sender (2)`, `GPIO Buzzer Control`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `main()` (e.g. with `.apply_runtime_settings()` and `.clear_posture()`) actually correct?**
  _`main()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RFC-2279`, `RFC-3629`, `RFC-2279` to the rest of the system?**
  _76 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `MediaPipe WASM Runtime` be split into smaller, more focused modules?**
  _Cohesion score 0.009478672985781991 - nodes in this community are weakly interconnected._
- **Why does `PiWebRtcSender` connect `WebRTC Streaming Sender` to `WebRTC Streaming Sender (3)`, `Upper Body Posture Scoring (2)`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `CharacterLcd` (e.g. with `test_lcd_1602_does_not_rewrite_an_unchanged_screen()` and `test_lcd_1602_lines_fit_the_display_and_show_posture_state()`) actually correct?**
  _`CharacterLcd` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Should `MediaPipe WASM (No-SIMD) Runtime` be split into smaller, more focused modules?**
  _Cohesion score 0.009478672985781991 - nodes in this community are weakly interconnected._