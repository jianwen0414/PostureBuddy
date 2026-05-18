#!/usr/bin/env python3
"""
posture_eval_node.py  —  PostureBuddy Module 2: Posture Classification

Subscribes : /user_kinematics   (posture_buddy/Kinematics)
Publishes  : /posture_status    (posture_buddy/PostureStatus)  @ 10 Hz

Classifies each incoming kinematics frame as GOOD, BAD, or ABSENT:
  ABSENT — no person detected by Module 1
  BAD    — neck or spine angle exceeds the threshold for forward slouch
  GOOD   — person detected and all angles within acceptable range
"""

import rospy
from posture_buddy.msg import Kinematics, PostureStatus

# ── Tunable thresholds ────────────────────────────────────────────────────────
# Angles are measured from vertical (0° = perfectly upright).
# Both values represent the maximum acceptable forward deviation.
NECK_ANGLE_BAD_DEG  = 20.0   # forward head tilt beyond this → BAD
SPINE_ANGLE_BAD_DEG = 15.0   # spine lean beyond this → BAD


# ── Node ──────────────────────────────────────────────────────────────────────
class PostureEvalNode:

    def __init__(self):
        rospy.init_node('posture_eval_node', anonymous=False)

        self._pub = rospy.Publisher('/posture_status', PostureStatus, queue_size=10)
        self._last_state = None   # track state changes for log output only

        # Subscriber last — publisher is ready before any callback fires
        rospy.Subscriber('/user_kinematics', Kinematics, self._kinematics_cb)

        rospy.loginfo('[posture_eval_node] Ready. Waiting for /user_kinematics ...')

    # ── Callback ──────────────────────────────────────────────────────────────
    def _kinematics_cb(self, msg):
        if not msg.is_person_detected:
            state = 'ABSENT'
        elif (msg.neck_angle_degrees  > NECK_ANGLE_BAD_DEG or
              msg.spine_angle_degrees > SPINE_ANGLE_BAD_DEG):
            state = 'BAD'
        else:
            state = 'GOOD'

        if state != self._last_state:
            rospy.loginfo('[posture_eval_node] State → %s  (neck=%.1f°, spine=%.1f°)',
                          state,
                          msg.neck_angle_degrees,
                          msg.spine_angle_degrees)
            self._last_state = state

        out = PostureStatus()
        out.posture_state = state
        self._pub.publish(out)

    # ── Spin ──────────────────────────────────────────────────────────────────
    def run(self):
        rospy.spin()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    try:
        PostureEvalNode().run()
    except rospy.ROSInterruptException:
        pass
