# PostureBuddy

An autonomous workspace wellness monitor built on ROS Noetic. Continuously analyses sitting posture via a side-view camera, calculates a fatigue score over time, and delivers audio reminders when the user slouches or sits too long. A live Next.js dashboard displays real-time posture state, session stats, and alert history.

---

## Architecture

```
Camera (usb_cam)
  └─► /camera/image_raw
        └─► [M1] pose_estimation_node      → /user_kinematics        (10 Hz)
              └─► [M2] posture_eval_node   → /posture_status         (10 Hz)
                    └─► [M3] fatigue_state_node → /fatigue_metrics   (1 Hz)
                    │                           → /hri_triggers       (latched)
                    │         └─► [M4] feedback_controller_node → /hri_execution_status
                    └─────────────────────────────────────────────────────────────┐
  /camera/image_raw/compressed ──────────────────────────────────────────────────┤
  /posture_status ────────────────────────────────────────────────────────────────┤─► rosbridge → [M5] Dashboard
  /fatigue_metrics ───────────────────────────────────────────────────────────────┤
  /hri_execution_status ──────────────────────────────────────────────────────────┘
```

| Module | Node | Role |
|--------|------|------|
| M1 | `pose_estimation_node` | MediaPipe pose → neck & spine angles |
| M2 | `posture_eval_node` | Angles → GOOD / BAD / ABSENT |
| M3 | `fatigue_state_node` | Fatigue score, rolling window, trigger logic |
| M4 | `feedback_controller_node` | TTS audio prompts (pyttsx3) |
| M5 | Next.js dashboard | Live WebSocket UI via rosbridge |

---

## Custom Message Types

All custom messages are defined in the `posture_buddy` package:

| Message | Fields |
|---------|--------|
| `Kinematics.msg` | `bool is_person_detected`, `float32 neck_angle_degrees`, `float32 spine_angle_degrees` |
| `PostureStatus.msg` | `string posture_state` — `"GOOD"` / `"BAD"` / `"ABSENT"` |
| `FatigueMetrics.msg` | `int32 current_session_duration_sec`, `int32 rolling_bad_posture_sec`, `string fatigue_level` |
| `HriStatus.msg` | `bool is_speaking`, `int32 last_executed_trigger` |

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

# Python packages
pip3 install mediapipe opencv-python pyttsx3
```

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

---

## Running the Full Pipeline

### Start ROS core + all modules

```bash
roslaunch posture_buddy posture_buddy.launch
```

This single command starts:
- `usb_cam_node` (camera driver on `/dev/video0`)
- `pose_estimation_node` (M1)
- `posture_eval_node` (M2)
- `fatigue_state_node` (M3)
- `feedback_controller_node` (M4)
- `rosbridge_websocket` on port 9090

> **Camera not on `/dev/video0`?** Edit `launch/pose_estimation.launch` and change the `video_device` param.

### Verify topics are live

```bash
rostopic list
```

Expected topics:

```
/camera/image_raw
/camera/image_raw/compressed
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

# Must match the topic published by usb_cam (compressed)
NEXT_PUBLIC_CAMERA_TOPIC=/camera/image_raw/compressed
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

| File | Constant | Default | Effect |
|------|----------|---------|--------|
| `pose_estimation_node.py` | `MIN_VISIBILITY` | `0.5` | MediaPipe landmark confidence gate |
| `posture_eval_node.py` | `NECK_ANGLE_BAD_DEG` | `20.0°` | Max acceptable forward head tilt |
| `posture_eval_node.py` | `SPINE_ANGLE_BAD_DEG` | `15.0°` | Max acceptable spine lean |
| `fatigue_state_node.py` | `ROLLING_WINDOW_SEC` | `120` | Rolling bad-posture window (seconds) |
| `fatigue_state_node.py` | `MAX_ABSENCE_RESET_SEC` | `60` | Absence duration before session resets |

---

## Team

| Module | Owner |
|--------|-------|
| M1 — Vision & Kinematics | Jianwen |
| M2 — Posture Classification | Shihan |
| M3 — Temporal Logic & Fatigue Engine | Rexton |
| M4 — HRI & Actuation | Ruizhe |
| M5 — Telemetry & Dashboard | Jiale |
