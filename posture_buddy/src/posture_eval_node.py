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

# Debounce: number of consecutive frames a new candidate state must hold
# before we commit. At 10 Hz this is a ~0.3 s delay — invisible to the user
# but stops single-frame outliers from flipping the published state.
DEBOUNCE_FRAMES     = 3


# ── Node ──────────────────────────────────────────────────────────────────────
class PostureEvalNode:

    def __init__(self):
        rospy.init_node('posture_eval_node', anonymous=False)

        self._pub = rospy.Publisher('/posture_status', PostureStatus, queue_size=10)
        self._last_state = None        # track state changes for log output only
        self._committed_state = None   # what we actually publish
        self._candidate_state = None   # what we *might* switch to
        self._candidate_count = 0      # consecutive frames seeing the candidate

        # Subscriber last — publisher is ready before any callback fires
        rospy.Subscriber('/user_kinematics', Kinematics, self._kinematics_cb)

        rospy.loginfo('[posture_eval_node] Ready. Waiting for /user_kinematics ...')

    # ── Callback ──────────────────────────────────────────────────────────────
    def _kinematics_cb(self, msg):
        if not msg.is_person_detected:
            raw = 'ABSENT'
        elif (msg.neck_angle_degrees  > NECK_ANGLE_BAD_DEG or
              msg.spine_angle_degrees > SPINE_ANGLE_BAD_DEG):
            raw = 'BAD'
        else:
            raw = 'GOOD'

        # Debounce: a candidate state must be observed DEBOUNCE_FRAMES times
        # in a row before it replaces the committed state. Until then the
        # committed state is what we publish. First-ever frame initialises
        # immediately so the system isn't silent at startup.
        if self._committed_state is None:
            self._committed_state = raw
            self._candidate_state = raw
            self._candidate_count = 0
        elif raw == self._committed_state:
            self._candidate_state = raw
            self._candidate_count = 0
        else:
            if raw == self._candidate_state:
                self._candidate_count += 1
            else:
                self._candidate_state = raw
                self._candidate_count = 1
            if self._candidate_count >= DEBOUNCE_FRAMES:
                self._committed_state = raw
                self._candidate_count = 0

        state = self._committed_state

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
