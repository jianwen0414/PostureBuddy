#!/usr/bin/env python3
"""
feedback_controller_node.py  —  PostureBuddy Module 4: HRI & Actuation

Subscribes : /hri_triggers          (std_msgs/Int32)          latched
Publishes  : /hri_execution_status  (posture_buddy/HriStatus) @ 1 Hz + on change

STUB: This node fulfils the topic contract so the full pipeline and dashboard
run immediately. Replace the marked TODO sections with real pyttsx3 TTS logic.
Owner: Ruizhe
"""

import rospy
from std_msgs.msg import Int32
from posture_buddy.msg import HriStatus

# ── Trigger code definitions (must match fatigue_state_node) ──────────────────
TRIGGER_IDLE              = 0
TRIGGER_STRETCH_REMINDER  = 1
TRIGGER_POSTURE_ALERT     = 2

# Human-readable labels used in log output
TRIGGER_LABELS = {
    TRIGGER_STRETCH_REMINDER: 'Gentle Stretch Reminder',
    TRIGGER_POSTURE_ALERT:    'Strong Posture Correction Alert',
}


class FeedbackControllerNode:

    def __init__(self):
        rospy.init_node('feedback_controller_node', anonymous=False)

        self._last_executed_trigger = 0
        self._is_speaking           = False   # TODO (Ruizhe): set True while pyttsx3 is active

        self._pub = rospy.Publisher(
            '/hri_execution_status', HriStatus, queue_size=10
        )

        # Heartbeat so the dashboard always has fresh data
        rospy.Timer(rospy.Duration(1.0), self._heartbeat_cb)

        # Subscriber last — all state is initialised before any callback fires
        rospy.Subscriber('/hri_triggers', Int32, self._trigger_cb)

        rospy.loginfo('[feedback_controller_node] Stub ready. Waiting for /hri_triggers ...')

    # ── Trigger callback ──────────────────────────────────────────────────────
    def _trigger_cb(self, msg):
        code = msg.data

        if code == TRIGGER_IDLE:
            return

        label = TRIGGER_LABELS.get(code, f'Unknown trigger {code}')
        rospy.logwarn('[feedback_controller_node] Received trigger %d (%s)', code, label)

        self._last_executed_trigger = code

        # TODO (Ruizhe): push (code, text) to TTS queue here.
        #   Example texts:
        #     TRIGGER_STRETCH_REMINDER → "Please take a stretch break. You have been sitting for a while."
        #     TRIGGER_POSTURE_ALERT    → "Posture alert. Please sit up straight and correct your posture."

        self._publish_status()

    # ── Heartbeat ─────────────────────────────────────────────────────────────
    def _heartbeat_cb(self, _event):
        self._publish_status()

    # ── Publish helper ────────────────────────────────────────────────────────
    def _publish_status(self):
        out = HriStatus()
        out.is_speaking           = self._is_speaking
        out.last_executed_trigger = self._last_executed_trigger
        self._pub.publish(out)

    # ── Spin ──────────────────────────────────────────────────────────────────
    def run(self):
        rospy.spin()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    try:
        FeedbackControllerNode().run()
    except rospy.ROSInterruptException:
        pass
