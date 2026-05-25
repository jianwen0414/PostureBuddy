#!/usr/bin/env python3
"""
pose_estimation_node.py  —  PostureBuddy Module 1: Vision & Kinematics

Subscribes : /camera/image_raw   (sensor_msgs/Image)
Publishes  : /user_kinematics    (posture_buddy/Kinematics)  @ 10 Hz

Angles are measured against the vertical axis (0° = perfectly upright).
Both neck_angle_degrees and spine_angle_degrees rise above 0° when the
user slouches or develops forward-head posture.
"""

import math
import rospy
import cv2
import mediapipe as mp
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image
from posture_buddy.msg import Kinematics

# ── Tunable constants ─────────────────────────────────────────────────────────
PUBLISH_INTERVAL_SEC  = 0.1   # 10 Hz output gate
MIN_VISIBILITY        = 0.5   # MediaPipe landmark visibility threshold
MP_MODEL_COMPLEXITY   = 1     # 0=fast, 1=balanced, 2=accurate
MP_MIN_DETECT_CONF    = 0.5
MP_MIN_TRACK_CONF     = 0.5

# ── MediaPipe landmark aliases ────────────────────────────────────────────────
PL         = mp.solutions.pose.PoseLandmark
L_EAR      = PL.LEFT_EAR
R_EAR      = PL.RIGHT_EAR
L_SHOULDER = PL.LEFT_SHOULDER
R_SHOULDER = PL.RIGHT_SHOULDER
L_HIP      = PL.LEFT_HIP
R_HIP      = PL.RIGHT_HIP


# ── Angle helper ──────────────────────────────────────────────────────────────
def _angle_from_vertical(top_x, top_y, bot_x, bot_y):
    """
    Angle in degrees between the vector (bottom→top) and vertical-up (0,-1).

    Coordinates must be in pixels (or any consistent unit) so that the
    aspect ratio is already baked in — pass lm.x*width, lm.y*height.

    Returns (degrees: float, valid: bool).
    valid=False when landmarks are coincident (degenerate MediaPipe output).
    """
    dx = top_x - bot_x
    dy = top_y - bot_y
    magnitude = math.sqrt(dx * dx + dy * dy)
    if magnitude < 1e-6:
        return 0.0, False
    # dot product with (0, -1): projects onto the upward direction in image space
    dot = -dy / magnitude
    dot = max(-1.0, min(1.0, dot))   # guard against float rounding past ±1
    return math.degrees(math.acos(dot)), True


# ── Node ──────────────────────────────────────────────────────────────────────
class PoseEstimationNode:

    def __init__(self):
        rospy.init_node('pose_estimation_node', anonymous=False)

        self._bridge = CvBridge()
        self._last_pub_time = rospy.Time(0)   # ensures first frame always runs

        self._pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=MP_MODEL_COMPLEXITY,
            min_detection_confidence=MP_MIN_DETECT_CONF,
            min_tracking_confidence=MP_MIN_TRACK_CONF,
        )
        rospy.on_shutdown(self._pose.close)

        self._pub = rospy.Publisher('/user_kinematics', Kinematics, queue_size=10)

        # Subscriber last — all state is initialised before any callback fires
        rospy.Subscriber('/usb_cam/image_raw', Image, self._image_cb)

        rospy.loginfo('[pose_estimation_node] Ready. Waiting for /usb_cam/image_raw ...')

    # ── Image callback ────────────────────────────────────────────────────────
    def _image_cb(self, msg):
        now = rospy.Time.now()
        if (now - self._last_pub_time).to_sec() < PUBLISH_INTERVAL_SEC:
            return
        self._last_pub_time = now

        try:
            bgr = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except CvBridgeError as exc:
            rospy.logwarn('[pose_estimation_node] CvBridgeError: %s', exc)
            return

        img_h, img_w = bgr.shape[:2]
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        results = self._pose.process(rgb)

        out = Kinematics()
        if results.pose_landmarks:
            out = self._compute_kinematics(results.pose_landmarks.landmark,
                                           img_w, img_h)
        # else: out already has is_person_detected=False and angles=0.0

        self._pub.publish(out)

    # ── Kinematics computation ────────────────────────────────────────────────
    def _compute_kinematics(self, lm, img_w, img_h):
        out = Kinematics()

        # Pick the side whose three keypoints are most visible in aggregate.
        # This makes the node camera-agnostic (left-side or right-side view).
        left_score  = (lm[L_EAR].visibility
                       + lm[L_SHOULDER].visibility
                       + lm[L_HIP].visibility)
        right_score = (lm[R_EAR].visibility
                       + lm[R_SHOULDER].visibility
                       + lm[R_HIP].visibility)

        if left_score >= right_score:
            ear, shoulder, hip = lm[L_EAR], lm[L_SHOULDER], lm[L_HIP]
        else:
            ear, shoulder, hip = lm[R_EAR], lm[R_SHOULDER], lm[R_HIP]

        # All three landmarks must exceed the visibility gate
        if (ear.visibility      < MIN_VISIBILITY
                or shoulder.visibility < MIN_VISIBILITY
                or hip.visibility      < MIN_VISIBILITY):
            out.is_person_detected  = False
            out.neck_angle_degrees  = 0.0
            out.spine_angle_degrees = 0.0
            return out

        # Convert normalised coords → pixels for aspect-ratio-correct angles
        ear_px  = (ear.x  * img_w, ear.y  * img_h)
        sh_px   = (shoulder.x * img_w, shoulder.y * img_h)
        hip_px  = (hip.x  * img_w, hip.y  * img_h)

        neck_angle,  neck_ok  = _angle_from_vertical(
            ear_px[0],  ear_px[1],
            sh_px[0],   sh_px[1])

        spine_angle, spine_ok = _angle_from_vertical(
            sh_px[0],   sh_px[1],
            hip_px[0],  hip_px[1])

        if not (neck_ok and spine_ok):
            out.is_person_detected  = False
            out.neck_angle_degrees  = 0.0
            out.spine_angle_degrees = 0.0
            return out

        out.is_person_detected  = True
        out.neck_angle_degrees  = float(neck_angle)
        out.spine_angle_degrees = float(spine_angle)
        return out

    # ── Spin ──────────────────────────────────────────────────────────────────
    def run(self):
        rospy.spin()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    try:
        PoseEstimationNode().run()
    except rospy.ROSInterruptException:
        pass
