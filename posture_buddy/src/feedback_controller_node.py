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

# Optional motion
from geometry_msgs.msg import Twist

# Standard library
import threading
import time 
import queue

# Try to import pyttsx3, but if it's not available, we'll just log a warning and skip TTS functionality.
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    rospy.logwarn('[feedback_controller_node] pyttsx3 not available. TTS functionality is disabled.')
    TTS_AVAILABLE = False

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

        # State
        self._last_executed_trigger = 0
        self._is_speaking           = False

        # Publishers
        self._pub = rospy.Publisher('/hri_execution_status', HriStatus, queue_size=10)

        # Optional robot base command publisher (disabled by default)
        self._enable_cmd_vel = rospy.get_param('~enable_cmd_vel', False)
        if self._enable_cmd_vel:
            self._cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
        else:
            self._cmd_vel_pub = None

        # TTS queue & worker
        # pyttsx3 is intentionally NOT initialised here — it must be created on
        # the same thread that calls runAndWait() (Linux/espeak GLib loop is
        # not thread-safe). Initialisation happens inside _tts_worker instead.
        self._tts_queue = queue.Queue()

        self._tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self._tts_thread.start()

        # Heartbeat so the dashboard always has fresh data
        rospy.Timer(rospy.Duration(1.0), self._heartbeat_cb)

        # Subscriber last — all state is initialised before any callback fires
        rospy.Subscriber('/hri_triggers', Int32, self._trigger_cb)

        rospy.loginfo('[feedback_controller_node] Ready. Waiting for /hri_triggers ... (enable_cmd_vel=%s, tts_ok=%s)',
                    self._enable_cmd_vel, TTS_AVAILABLE)

    # ── Trigger callback ──────────────────────────────────────────────────────
    def _trigger_cb(self, msg):
        code = msg.data

        if code == TRIGGER_IDLE:
            # Optionally push an idle event to stop speaking, but keep simple.
            return

        label = TRIGGER_LABELS.get(code, f'Unknown trigger {code}')
        rospy.logwarn('[feedback_controller_node] Received trigger %d (%s)', code, label)

        self._last_executed_trigger = code

        # Map code → spoken text
        if code == TRIGGER_STRETCH_REMINDER:
            text = "Please take a short stretch break. You've been sitting for a while."
        elif code == TRIGGER_POSTURE_ALERT:
            text = "Posture alert. Please sit up straight and correct your posture now."
        else:
            text = f"Notification {code}"

        # Push to TTS queue (non-blocking)
        try:
            self._tts_queue.put_nowait((code, text))
        except queue.Full:
            rospy.logwarn('[feedback_controller_node] TTS queue full; dropping message.')

        # Update dashboard immediately
        self._publish_status()

    # ── TTS worker ────────────────────────────────────────────────────────────
    def _tts_worker(self):
        # Initialise pyttsx3 here so engine lives on this thread.
        # On Linux the espeak driver uses a GLib event loop that must be driven
        # by the same thread that created it — cross-thread use hangs/crashes.
        tts_engine = None
        if TTS_AVAILABLE:
            try:
                tts_engine = pyttsx3.init()
            except Exception as e:
                rospy.logerr('[feedback_controller_node] pyttsx3 init failed: %s', e)

        if not tts_engine:
            rospy.logwarn('[feedback_controller_node] pyttsx3 not available; falling back to logs.')

        while not rospy.is_shutdown():
            try:
                code, text = self._tts_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            self._is_speaking = True
            self._publish_status()

            # Optional attention wiggle before speaking
            if self._enable_cmd_vel and self._cmd_vel_pub is not None:
                try:
                    self._do_attention_wiggle()
                except Exception as e:
                    rospy.logwarn('[feedback_controller_node] attention wiggle failed: %s', e)

            # Speak (or log fallback)
            if tts_engine:
                try:
                    tts_engine.say(text)
                    tts_engine.runAndWait()
                except Exception as e:
                    rospy.logerr('[feedback_controller_node] TTS error: %s', e)
            else:
                rospy.loginfo('[feedback_controller_node] TTS (log fallback): %s', text)
                time.sleep(min(max(len(text) * 0.03, 0.5), 3.0))

            self._is_speaking = False
            self._publish_status()
            self._tts_queue.task_done()

    # ── Simple left-right wiggle (kiri-kanan) ─────────────────────────────────
    def _do_attention_wiggle(self): 
        if not self._cmd_vel_pub:
            return
        # Publish a quick left-right angular wiggle (tune durations/velocities as needed)
        twist = Twist()
        # left turn
        twist.angular.z = 0.8
        self._cmd_vel_pub.publish(twist)
        rospy.sleep(0.18)
        # right turn
        twist.angular.z = -0.8
        self._cmd_vel_pub.publish(twist)
        rospy.sleep(0.18)
        # center
        twist.angular.z = 0.0
        self._cmd_vel_pub.publish(twist)
        rospy.sleep(0.06)

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
