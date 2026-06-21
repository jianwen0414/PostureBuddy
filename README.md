# PostureBuddy

An autonomous workspace wellness monitor built on ROS Noetic. Continuously analyses sitting posture via a side-view camera, calculates a fatigue score over time, and delivers audio reminders when the user slouches or sits too long. A live Next.js dashboard displays real-time posture state, session stats, and alert history.

---

## Architecture

```
Camera (usb_cam)
  └─► /usb_cam/image_raw
        └─► [M1] pose_estimation_node      → /user_kinematics        (10 Hz)
              │                            → /usb_cam/image_annotated/compressed
              └─► [M2] posture_eval_node   → /posture_status         (10 Hz)
                    └─► [M3] fatigue_state_node → /fatigue_metrics   (1 Hz)
                    │                           → /hri_triggers       (latched)
                    │         └─► [M4] feedback_controller_node → /hri_execution_status
                    └─────────────────────────────────────────────────────────────┐
  /usb_cam/image_annotated/compressed ────────────────────────────────────────────┤
  /posture_status ────────────────────────────────────────────────────────────────┤─► rosbridge → [M5] Dashboard
  /fatigue_metrics ───────────────────────────────────────────────────────────────┤
  /hri_execution_status ──────────────────────────────────────────────────────────┘
```

| Module | Node | Role |
|--------|------|------|
| M1 | `pose_estimation_node` | MediaPipe pose → neck & spine angles |
| M2 | `posture_eval_node` | Angles → GOOD / BAD / ABSENT |
| M3 | `fatigue_state_node` | Fatigue score, rolling window, trigger logic |
| M4 | `feedback_controller_node` | Two-way voice conversation: TTS (pyttsx3) + STT (Google) + LLM (DeepSeek via OpenRouter) |
| M5 | Next.js dashboard | Live WebSocket UI via rosbridge |

---

## Custom Message Types

All custom messages are defined in the `posture_buddy` package:

| Message | Fields |
|---------|--------|
| `Kinematics.msg` | `bool is_person_detected`, `float32 neck_angle_degrees`, `float32 spine_angle_degrees` |
| `PostureStatus.msg` | `string posture_state` — `"GOOD"` / `"BAD"` / `"ABSENT"` |
| `FatigueMetrics.msg` | `int32 current_session_duration_sec`, `int32 rolling_bad_posture_sec`, `string fatigue_level` |
| `HriStatus.msg` | `bool is_speaking`, `int32 last_executed_trigger`, `string robot_message`, `string user_message`, `string[] conversation` |

---

## Prerequisites

### Robot / ROS Machine

- Ubuntu 20.04
- ROS Noetic (full desktop install)
- Python 3.8+

```bash
# ROS packages
sudo apt install ros-noetic-usb-cam
sudo apt install ros-noetic-rosbridge-suite
sudo apt install ros-noetic-cv-bridge

# Mic backend for Module 4 STT (needed before PyAudio installs cleanly)
sudo apt install portaudio19-dev python3-pyaudio

# Python packages (all modules)
pip3 install -r requirements.txt
```

> See [`requirements.txt`](requirements.txt) for the full pinned list
> (mediapipe, opencv-python, numpy, pyttsx3, SpeechRecognition, PyAudio,
> openai, python-dotenv).

### Dashboard Machine (can be same machine)

- Node.js 18+
- npm 9+

---

## Installation

### 1. Clone into your catkin workspace

```bash
cd ~/catkin_ws/src
git clone <repo-url> posture_buddy
```

### 2. Build the package

```bash
cd ~/catkin_ws
catkin_make
source devel/setup.bash
```

Verify custom messages compiled:

```bash
rosmsg show posture_buddy/Kinematics
rosmsg show posture_buddy/PostureStatus
rosmsg show posture_buddy/FatigueMetrics
rosmsg show posture_buddy/HriStatus
```

### 3. Make node scripts executable

```bash
chmod +x ~/catkin_ws/src/PostureBuddy/posture_buddy/src/*.py
```

### 4. Configure the OpenRouter API key (Module 4)

The conversation LLM (DeepSeek V4 Flash) is reached through OpenRouter. The key
is read from a `.env` file that must sit **inside `posture_buddy/src/`** — the
node resolves it relative to its own location, not your shell's directory.

```bash
cd ~/catkin_ws/src/PostureBuddy/posture_buddy/src
cp .env.example .env
# edit .env and set OPENROUTER_API_KEY=sk-or-...   (get one at https://openrouter.ai/keys)
```

> Skipping this is non-fatal: M4 still speaks, but with fixed fallback lines
> instead of LLM-generated replies, and logs `DeepSeek disabled`.

---

## Running the Full Pipeline

### Start ROS core + all modules

```bash
roslaunch posture_buddy posture_buddy.launch
```

This single command starts:
- `usb_cam_node` (camera driver on `/dev/video2`)
- `pose_estimation_node` (M1)
- `posture_eval_node` (M2)
- `fatigue_state_node` (M3)
- `feedback_controller_node` (M4)
- `rosbridge_websocket` on port 9090

> **Camera not on `/dev/video2`?** Edit `launch/pose_estimation.launch` and change the `video_device` param.

### Verify topics are live

```bash
rostopic list
```

Expected topics:

```
/usb_cam/image_raw
/usb_cam/image_raw/compressed
/usb_cam/image_annotated/compressed
/user_kinematics
/posture_status
/fatigue_metrics
/hri_triggers
/hri_execution_status
```

### Monitor live data

```bash
rostopic echo /posture_status
rostopic echo /fatigue_metrics
rostopic echo /hri_execution_status
```

### Manually fire a trigger (for testing)

```bash
# Trigger 1 — Stretch Reminder
rostopic pub -1 /hri_triggers std_msgs/Int32 "data: 1"

# Trigger 2 — Posture Correction Alert
rostopic pub -1 /hri_triggers std_msgs/Int32 "data: 2"
```

---

## Running the Dashboard (Module 5)

### 1. Configure environment

```bash
cd posture_buddy/dashboard
cp .env.example .env.local
```

Edit `.env.local`:

```env
# Replace <robot-ip> with the actual IP of the robot running rosbridge
NEXT_PUBLIC_WS_URL=ws://<robot-ip>:9090

# Set to false when connecting to real robot
NEXT_PUBLIC_MOCK_WS=false

# Skeleton-annotated stream from M1 (same frame the classifier sees).
# Use /usb_cam/image_raw/compressed for the raw feed instead.
NEXT_PUBLIC_CAMERA_TOPIC=/usb_cam/image_annotated/compressed
```

> Set `NEXT_PUBLIC_MOCK_WS=true` to run the dashboard in offline demo mode without the robot.

### 2. Install dependencies

```bash
npm install
```

### 3. Start the dashboard

```bash
npm run dev
```

Open `http://localhost:3000` in a browser.

### Dashboard panels

| Panel | Description |
|-------|-------------|
| Camera Feed | Live compressed camera stream with MediaPipe skeleton overlay |
| Posture Status | Current state (GOOD / BAD / ABSENT) with colour coding |
| Fatigue Level | Gauge ring showing current fatigue level (LOW / MEDIUM / HIGH) |
| Degradation | Rolling bad-posture score for the current 2-minute window |
| Wellness Stats | Session totals — good time, bad time, good-posture percentage |
| Session Timeline | Per-second fatigue history chart |
| Alert Feed | Timestamped log of every stretch and correction alert fired |
| Conversation | Live transcript of the current robot↔user voice conversation (M4) |

The **Session Report** is an on-demand modal separate from the panels. It shows a posture grade (A–F), key stats, alert breakdown by type, a fatigue distribution bar across the session, and a personalised recommendation. Trigger it via the **Report** button in the header.

---

## Running Individual Modules (Development)

Each module has its own launch file for isolated testing:

```bash
# M1 only (+ camera driver)
roslaunch posture_buddy pose_estimation.launch

# M2 only (requires M1 running)
roslaunch posture_buddy posture_eval.launch

# M3 only (requires M2 running)
roslaunch posture_buddy fatigue_state.launch

# M4 only (requires M3 running)
roslaunch posture_buddy feedback_controller.launch
```

---

## Tunable Parameters

**`pose_estimation_node.py`**

| Constant | Default | Effect |
|----------|---------|--------|
| `MIN_VISIBILITY` | `0.35` | MediaPipe landmark visibility gate — lower values tolerate partially occluded landmarks |
| `ANGLE_EMA_ALPHA` | `0.55` | EMA smoothing factor for per-frame angle jitter (`1.0` = no smoothing) |
| `SIDE_SWITCH_MARGIN` | `0.30` | Aggregate visibility margin the non-active side must exceed before a left/right switch is allowed |

**`posture_eval_node.py`**

| Constant | Default | Effect |
|----------|---------|--------|
| `NECK_ANGLE_BAD_DEG` | `20.0°` | Max acceptable forward head tilt |
| `SPINE_ANGLE_BAD_DEG` | `15.0°` | Max acceptable spine lean |
| `DEBOUNCE_FRAMES` | `3` | Consecutive frames a candidate state must hold before publishing (~0.3 s at 10 Hz) |

**`fatigue_state_node.py`**

| Constant | Default | Effect |
|----------|---------|--------|
| `ROLLING_WINDOW_SEC` | `120` | Rolling bad-posture window (seconds) |
| `HYSTERESIS_DELAY_SEC` | `10` | Seconds a new fatigue score must be sustained before the fatigue level flips |
| `MAX_ABSENCE_RESET_SEC` | `60` | Absence duration before session resets |
| `BAD_STREAK_ALERT_SEC` | `30` | Continuous slouch streak (seconds) that fires an urgent correction alert regardless of cumulative fatigue score |

---

## Team

| Module | Owner |
|--------|-------|
| M1 — Vision & Kinematics | Jianwen |
| M2 — Posture Classification | Shihan |
| M3 — Temporal Logic & Fatigue Engine | Rexton |
| M4 — HRI & Actuation | Ruizhe |
| M5 — Telemetry & Dashboard | Jiale |
