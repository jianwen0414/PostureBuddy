# Overview

### **The Interactive Workspace "Posture" Buddy**

This robot acts as an autonomous wellness monitor for a study lounge, lab, or library. It proactively checks on users rather than waiting for commands.

#### **Core Features**

* **Non-moving/static monitoring**   
* **Ergonomic Analysis:** It uses its camera to assess a user's sitting posture (e.g., measuring the angle of their neck and shoulders, spine curvature etc).  
* Detecting posture degradation over time  
* Calculate fatigue level based on behavioral patterns  
* **Context-Aware Reminders:**   
  * If a user has been sitting for over 2 minutes or is visibly slouching, the robot delivers a friendly audio to ask the user to stretch.  
  * High-score of fatigueness calculated, ask user if he/she feeling okay/experiencing any fatigueness, delivers urgent audio to give posture recovery instruction.  
* **Companion Analytics Dashboard:** A live web interface that displays the robot’s current location, camera feed, and aggregated workspace wellness stats (e.g., "70% of users had great posture today\!").

# Modules

**1\. Vision & Kinematics Module (`pose_estimation_node`) Jianwen**

* **Function:** Captures the side-view camera feed and extracts human skeletal keypoints.  
* **Core Tasks:** Identifies the Ear, Shoulder, and Hip coordinates using a lightweight framework (like MediaPipe Pose).  
* **Output Topic:** Publishes raw coordinate data and calculated angles (Neck Angle, Back/Spine Angle).

**2\. Posture Classification Module (`posture_eval_node`) Shihan**

* **Function:** Ingests the angles and determines the immediate posture state.  
* **Core Tasks:** Compares the calculated angles against calibrated "good posture" thresholds.  
* **Output Topic:** Publishes a simple boolean or string state: `Good` or `Bad`.

**3\. Temporal Logic & Fatigue Engine (`fatigue_state_node`) Rexton**

* **Function:** The "brain" of the operation. It maintains the time windows and rule-based logic.  
* **Core Tasks:**  
  * Tracks continuous sitting time (Target: 2 mins).  
  * Maintains a rolling 2-minute window to track the 1-minute degradation threshold.  
  * Applies the rule-based logic to output a Fatigue Level (Low, Medium, High).  
* **Output Topic:** Publishes `AlertTriggers` (e.g., `Trigger_1_Stretch`, `Trigger_2_CorrectPosture`) and current `FatigueLevel`.

**4\. HRI & Actuation Module (`feedback_controller_node`) Ruizhe**

* **Function:** Executes the physical and auditory interaction with the user.  
* **Core Tasks:** Subscribes to `AlertTriggers`. Uses a text-to-speech engine (like `pyttsx3`) to deliver the specific audio prompts.  
* **Optional Task:** If the 3-week milestone is met early, this module will handle the simple base commands (`/cmd_vel`) to execute the subtle left-right (kiri-kanan) movement to grab the user's attention before speaking.

**5\. Telemetry & Dashboard Module (`ui_bridge_node` \+ Web Server) Jiale**

* **Function:** The visual interface for the user to monitor their stats.  
* **Core Tasks:** Uses `rosbridge_suite` to pass ROS data over WebSockets to a local web server running Node.js and Next.js. Displays real-time timers, posture status, and fatigue levels.

# Contract

### **1\. Vision & Kinematics Module (`pose_estimation_node`)**

**Role:** Extracts raw geometry from the camera feed.

* **Inputs (Subscribes to):**  
  * **Topic:** `/camera/image_raw`  
  * **Type:** `sensor_msgs/Image`  
  * **Source:** USB/Webcam Driver Node  
* **Outputs (Publishes to):**  
  * **Topic:** `/user_kinematics`  
  * **Type:** Custom Message (`Kinematics.msg`)  
  * **Target Frequency:** 10 Hz  
  * **Payload Variables:**  
    * `is_person_detected` (Boolean) \- *True if ear, shoulder, and hip keypoints are visible.*  
    * `neck_angle_degrees` (Float32) \- *Calculated angle between ear, shoulder, and vertical axis.*  
    * `spine_angle_degrees` (Float32) \- *Calculated angle between shoulder, hip, and vertical axis.*

### **2\. Posture Classification Module (`posture_eval_node`)**

**Role:** Evaluates kinematics against geometric thresholds.

* **Inputs (Subscribes to):**  
  * **Topic:** `/user_kinematics`  
  * **Type:** Custom Message (`Kinematics.msg`)  
  * **Source:** Module 1  
* **Outputs (Publishes to):**  
  * **Topic:** `/posture_status`  
  * **Type:** Custom Message (`PostureStatus.msg`)  
  * **Target Frequency:** 10 Hz  
  * **Payload Variables:**  
    * `posture_state` (String) \- *Strictly limited to 3 values: "GOOD", "BAD", or "ABSENT".*

### **3\. Temporal Logic & Fatigue Engine (`fatigue_state_node`)**

**Role:** The state machine handling timers and triggering logic.

* **Inputs (Subscribes to):**  
  * **Topic:** `/posture_status`  
  * **Type:** Custom Message (`PostureStatus.msg`)  
  * **Source:** Module 2  
* **Outputs (Publishes to):**  
  * **Topic A: `/fatigue_metrics`** (For the Dashboard)  
    * **Type:** Custom Message (`FatigueMetrics.msg`)  
    * **Target Frequency:** 1 Hz  
    * **Payload Variables:**  
      * `current_session_duration_sec` (Int32)  
      * `rolling_bad_posture_sec` (Int32) \- *Time accumulated in the current 20-min window.*  
      * `fatigue_level` (String) \- *Strictly limited to: "LOW", "MEDIUM", "HIGH".*  
  * **Topic B: `/hri_triggers`** (For the Feedback Module)  
    * **Type:** `std_msgs/Int32`  
    * **Target Frequency:** Published ONLY when a state changes (Latched)  
    * **Payload Variables:**  
      * `trigger_code` (Int32) \- *0 \= Idle, 1 \= Gentle Stretch Reminder, 2 \= Strong Posture Correction Alert.*

### **4\. HRI & Actuation Module (`feedback_controller_node`)**

**Role:** Executes physical and auditory feedback.

* **Inputs (Subscribes to):**  
  * **Topic:** `/hri_triggers`  
  * **Type:** `std_msgs/Int32`  
  * **Source:** Module 3  
* **Outputs (Publishes to):**  
  * **Topic:** `/hri_execution_status`  
  * **Type:** Custom Message (`HriStatus.msg`)  
  * **Target Frequency:** Published on state change  
  * **Payload Variables:**  
    * `is_speaking` (Boolean) \- *True while TTS is actively playing audio.*  
    * `last_executed_trigger` (Int32) \- *Echos the trigger\_code just completed.*

### **5\. Telemetry & Dashboard Module (`ui_bridge_node`)**

**Role:** Packages ROS data for the front-end web client.

* **Inputs (Subscribes to via `rosbridge_websocket`):**  
  * **Topic 1:** `/posture_status` (From Module 2\)  
  * **Topic 2:** `/fatigue_metrics` (From Module 3\)  
  * **Topic 3:** `/hri_execution_status` (From Module 4\)  
* **Outputs (Emits to Frontend Client):**  
  * **Protocol:** WebSockets (JSON payload)  
  * **Target Frequency:** 1 Hz updates to UI  
  * **JSON Data Contract Example:**  
  * JSON:

{  
  "posture": "GOOD",  
  "session\_time\_seconds": 1240,  
  "degradation\_time\_seconds": 320,  
  "fatigue\_level": "LOW",  
  "system\_status": "Idle" 

}

