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
from sensor_msgs.msg import Image, CompressedImage
from posture_buddy.msg import Kinematics

import numpy as np

# ── Tunable constants ─────────────────────────────────────────────────────────
PUBLISH_INTERVAL_SEC  = 0.1   # 10 Hz output gate
MIN_VISIBILITY        = 0.35  # MediaPipe landmark visibility threshold (lowered: 0.5 was too aggressive at edges)
SIDE_SWITCH_MARGIN    = 0.30  # the other side must beat the sticky side by this in aggregate visibility
ANGLE_EMA_ALPHA       = 0.55  # smoothing factor for per-frame angle outliers (1.0 = no smoothing)
MP_MODEL_COMPLEXITY   = 1     # 0=fast, 1=balanced, 2=accurate
MP_MIN_DETECT_CONF    = 0.5
MP_MIN_TRACK_CONF     = 0.5

# Overlay thresholds — must match posture_eval_node.py for visual/classifier parity
OVERLAY_NECK_BAD_DEG  = 20.0
OVERLAY_SPINE_BAD_DEG = 15.0
JPEG_QUALITY          = 80

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
        self._sticky_side = None              # 'L' or 'R' — carry across frames to suppress flicker
        self._ema_neck = None
        self._ema_spine = None

        self._pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=MP_MODEL_COMPLEXITY,
            min_detection_confidence=MP_MIN_DETECT_CONF,
            min_tracking_confidence=MP_MIN_TRACK_CONF,
        )
        rospy.on_shutdown(self._pose.close)

        self._pub = rospy.Publisher('/user_kinematics', Kinematics, queue_size=10)
        self._annotated_pub = rospy.Publisher(
            '/usb_cam/image_annotated/compressed', CompressedImage, queue_size=1)

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
        chosen_px = None
        if results.pose_landmarks:
            out, chosen_px = self._compute_kinematics(
                results.pose_landmarks.landmark, img_w, img_h)
        # else: out already has is_person_detected=False and angles=0.0

        self._pub.publish(out)
        self._publish_annotated(bgr, out, chosen_px, msg.header)

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

        # Side stickiness: once a side is chosen, only flip when the other side
        # decisively wins. Prevents one-frame visibility blips from yanking
        # the skeleton across the body and corrupting the angle.
        if self._sticky_side == 'L':
            pick_left = left_score + SIDE_SWITCH_MARGIN >= right_score
        elif self._sticky_side == 'R':
            pick_left = left_score >= right_score + SIDE_SWITCH_MARGIN
        else:
            pick_left = left_score >= right_score

        if pick_left:
            ear, shoulder, hip = lm[L_EAR], lm[L_SHOULDER], lm[L_HIP]
            self._sticky_side = 'L'
        else:
            ear, shoulder, hip = lm[R_EAR], lm[R_SHOULDER], lm[R_HIP]
            self._sticky_side = 'R'

        # All three landmarks must exceed the visibility gate
        if (ear.visibility      < MIN_VISIBILITY
                or shoulder.visibility < MIN_VISIBILITY
                or hip.visibility      < MIN_VISIBILITY):
            out.is_person_detected  = False
            out.neck_angle_degrees  = 0.0
            out.spine_angle_degrees = 0.0
            # Drop EMA on extended dropout so we don't bias the next reading
            self._ema_neck = None
            self._ema_spine = None
            return out, None

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
            return out, None

        # EMA on angles to suppress single-frame jitter when the user is
        # sitting right on the threshold (e.g. neck oscillating 19°↔21°).
        if self._ema_neck is None:
            self._ema_neck, self._ema_spine = neck_angle, spine_angle
        else:
            self._ema_neck  = (ANGLE_EMA_ALPHA * neck_angle
                               + (1.0 - ANGLE_EMA_ALPHA) * self._ema_neck)
            self._ema_spine = (ANGLE_EMA_ALPHA * spine_angle
                               + (1.0 - ANGLE_EMA_ALPHA) * self._ema_spine)

        out.is_person_detected  = True
        out.neck_angle_degrees  = float(self._ema_neck)
        out.spine_angle_degrees = float(self._ema_spine)
        return out, (ear_px, sh_px, hip_px)

    @staticmethod
    def _label(canvas, text, origin, color):
        """Draw text with a dark filled background so it's legible on any feed."""
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        x, y = origin
        cv2.rectangle(canvas, (x - 4, y - th - 4), (x + tw + 4, y + 4),
                      (15, 15, 15), -1)
        cv2.putText(canvas, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, color, 2, cv2.LINE_AA)

    # ── Skeleton overlay & compressed republish ───────────────────────────────
    def _publish_annotated(self, bgr, kin, chosen_px, header):
        """
        Burn the neck/spine skeleton onto the frame and publish as
        sensor_msgs/CompressedImage so the dashboard can show the same
        evidence the classifier is using.
        """
        canvas = bgr  # in-place is fine: we don't reuse bgr afterwards

        if kin.is_person_detected and chosen_px is not None:
            ear_px, sh_px, hip_px = chosen_px
            ear_pt = (int(ear_px[0]), int(ear_px[1]))
            sh_pt  = (int(sh_px[0]),  int(sh_px[1]))
            hip_pt = (int(hip_px[0]), int(hip_px[1]))

            neck_bad  = kin.neck_angle_degrees  > OVERLAY_NECK_BAD_DEG
            spine_bad = kin.spine_angle_degrees > OVERLAY_SPINE_BAD_DEG
            neck_color  = (40, 60, 255)  if neck_bad  else (60, 230, 120)
            spine_color = (40, 60, 255)  if spine_bad else (60, 230, 120)

            # Dark outline under each line so the skeleton stays visible against
            # bright clothing / busy backgrounds.
            cv2.line(canvas, sh_pt, ear_pt, (15, 15, 15), 8, cv2.LINE_AA)
            cv2.line(canvas, hip_pt, sh_pt, (15, 15, 15), 8, cv2.LINE_AA)
            cv2.line(canvas, sh_pt, ear_pt, neck_color, 4, cv2.LINE_AA)
            cv2.line(canvas, hip_pt, sh_pt, spine_color, 4, cv2.LINE_AA)
            for pt in (ear_pt, sh_pt, hip_pt):
                cv2.circle(canvas, pt, 9, (15, 15, 15), -1, cv2.LINE_AA)
                cv2.circle(canvas, pt, 6, (255, 255, 255), -1, cv2.LINE_AA)

            # Joint labels — make it explicit which MediaPipe landmark each
            # dot represents, so the user reads the lines (not the dots) as
            # the neck/spine vectors.
            joint_color = (235, 235, 235)
            self._label(canvas, 'EAR',      (ear_pt[0] + 12, ear_pt[1] - 6), joint_color)
            self._label(canvas, 'SHOULDER', (sh_pt[0]  + 12, sh_pt[1]  + 4), joint_color)
            self._label(canvas, 'HIP',      (hip_pt[0] + 12, hip_pt[1] + 4), joint_color)

            # Angles still need to be visible — pin them to a HUD in the
            # top-left corner where they can't be misread as dot labels.
            self._label(canvas, f'neck  {kin.neck_angle_degrees:5.1f} deg',
                        (14, 28), neck_color)
            self._label(canvas, f'spine {kin.spine_angle_degrees:5.1f} deg',
                        (14, 56), spine_color)
        else:
            cv2.putText(canvas, 'NO PERSON DETECTED',
                        (16, canvas.shape[0] - 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180),
                        2, cv2.LINE_AA)

        ok, buf = cv2.imencode('.jpg', canvas,
                               [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        if not ok:
            return
        out = CompressedImage()
        out.header = header
        out.format = 'jpeg'
        out.data = np.asarray(buf).tobytes()
        self._annotated_pub.publish(out)

    # ── Spin ──────────────────────────────────────────────────────────────────
    def run(self):
        rospy.spin()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    try:
        PoseEstimationNode().run()
    except rospy.ROSInterruptException:
        pass
