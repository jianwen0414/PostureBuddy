#!/usr/bin/env python3
"""
fatigue_state_node.py — PostureBuddy Module 3: Temporal Logic & Fatigue Engine

Subscribes : /posture_status   (posture_buddy/PostureStatus)
Publishes  : /fatigue_metrics  (posture_buddy/FatigueMetrics) @ 1 Hz
             /hri_triggers     (std_msgs/Int32) latched on change

Implements a professional Fatigue Engine with weighted multi-factor scoring
and hysteresis to prevent flickering levels.
"""

import rospy
from collections import deque
from std_msgs.msg import Int32
from posture_buddy.msg import PostureStatus, FatigueMetrics

# ── Tunable Constants ─────────────────────────────────────────────────────────
ROLLING_WINDOW_SEC       = 120.0  # 2 minutes rolling window for 'bad sec' calculation
HYSTERESIS_DELAY_SEC     = 10.0   # Require 10s of sustained score to flip fatigue level
MAX_ABSENCE_RESET_SEC    = 60.0   # Reset session if absent for 60 seconds

class FatigueStateNode:
    def __init__(self):
        rospy.init_node('fatigue_state_node', anonymous=False)

        # Basic States
        self.current_posture = "ABSENT"
        self.last_posture = "ABSENT"
        self.last_update_time = rospy.Time.now()

        # Core time tracking
        self.session_duration_sec = 0.0
        self.absence_duration_sec = 0.0

        # Posture tracking
        self.current_bad_streak_sec = 0.0
        self.max_bad_streak_sec = 0.0
        self.bad_posture_total_sec = 0.0
        self.good_posture_total_sec = 0.0
        self.posture_transition_count = 0

        # Fatigue model
        self.fatigue_score = 0.0
        self.target_fatigue_level = "LOW"
        self.current_fatigue_level = "LOW"
        self.level_sustain_timer = 0.0

        # History Window
        self.history_queue = deque()  # stores (timestamp, duration, state)

        # Triggers
        self.last_triggered_code = 0 
        self.trigger_cooldown = 0.0   

        # Publishers
        self.metrics_pub = rospy.Publisher('/fatigue_metrics', FatigueMetrics, queue_size=10)
        self.trigger_pub = rospy.Publisher('/hri_triggers', Int32, queue_size=10, latch=True)

        # Subscriber
        rospy.Subscriber('/posture_status', PostureStatus, self._posture_cb)

        # 1 Hz Timer loop
        rospy.Timer(rospy.Duration(1.0), self._tick_cb)

        rospy.loginfo('[fatigue_state_node] Advanced Fatigue Engine Ready.')

    def _posture_cb(self, msg):
        self.current_posture = msg.posture_state

    def _tick_cb(self, event):
        now = rospy.Time.now()
        dt = (now - self.last_update_time).to_sec()
        # Cap dt to avoid massive jumps if the node hangs briefly
        dt = min(dt, 2.0)
        self.last_update_time = now

        # 1. Update Core Time Tracking
        if self.current_posture == "ABSENT":
            self.absence_duration_sec += dt
            # If they leave for more than 1 minute, assume a new study session
            if self.absence_duration_sec >= MAX_ABSENCE_RESET_SEC:
                self._reset_session()
        else:
            self.absence_duration_sec = 0.0
            self.session_duration_sec += dt

            # 2. Update Posture & Transitions
            if self.current_posture != self.last_posture and self.last_posture != "ABSENT":
                self.posture_transition_count += 1
            
            if self.current_posture == "BAD":
                self.bad_posture_total_sec += dt
                self.current_bad_streak_sec += dt
                if self.current_bad_streak_sec > self.max_bad_streak_sec:
                    self.max_bad_streak_sec = self.current_bad_streak_sec
            elif self.current_posture == "GOOD":
                self.good_posture_total_sec += dt
                self.current_bad_streak_sec = 0.0
                
            self.history_queue.append((now.to_sec(), dt, self.current_posture))

        self.last_posture = self.current_posture

        # 3. Trim Rotating Window
        cutoff_time = now.to_sec() - ROLLING_WINDOW_SEC
        while self.history_queue and self.history_queue[0][0] < cutoff_time:
            self.history_queue.popleft()

        rolling_bad_sec = sum(dur for (t, dur, state) in self.history_queue if state == "BAD")

        # 4. Calculate Weighted Fatigue Score
        if self.session_duration_sec > 0:
            # Sitting duration pressure (max 100 at 10 mins = 600 sec)
            duration_score = min((self.session_duration_sec / 600.0) * 100.0, 100.0)
            
            # Bad posture exposure (ratio of bad time to session time cap)
            bad_ratio = rolling_bad_sec / min(self.session_duration_sec, ROLLING_WINDOW_SEC)
            bad_score = min(bad_ratio * 100.0, 100.0)
            
            # Continuous slouch severity (max 100 at 2 mins = 120 sec)
            streak_score = min((self.current_bad_streak_sec / 120.0) * 100.0, 100.0)
            
            # Instability factor
            transition_score = min(float(self.posture_transition_count) * 2.0, 100.0)
            
            # Final Formula
            self.fatigue_score = (0.4 * duration_score) + (0.4 * bad_score) + (0.15 * streak_score) + (0.05 * transition_score)
        else:
            self.fatigue_score = 0.0

        # 5. Convert Score to Target Level
        if self.fatigue_score >= 70.0:
            new_target_level = "HIGH"
        elif self.fatigue_score >= 40.0:
            new_target_level = "MEDIUM"
        else:
            new_target_level = "LOW"

        # 6. Apply Hysteresis
        if new_target_level == self.target_fatigue_level:
            self.level_sustain_timer += dt
            if self.level_sustain_timer >= HYSTERESIS_DELAY_SEC:
                self.current_fatigue_level = new_target_level
        else:
            self.target_fatigue_level = new_target_level
            self.level_sustain_timer = 0.0

        # 7. Trigger Logic
        trigger_code = 0  # Idle
        
        if self.trigger_cooldown > 0:
            self.trigger_cooldown -= dt
        else:
            if self.current_fatigue_level == "HIGH":
                trigger_code = 2  # Urgent Correction
                self.trigger_cooldown = 15.0
            elif self.current_fatigue_level == "MEDIUM":
                trigger_code = 1  # Stretch Reminder
                self.trigger_cooldown = 20.0
                
        # Only publish trigger if there's a state change or an active non-zero trigger is fired
        if trigger_code != 0 and trigger_code != self.last_triggered_code:
            self.trigger_pub.publish(Int32(trigger_code))
            self.last_triggered_code = trigger_code
            rospy.logwarn(f'[fatigue_state_node] FIRED TRIGGER {trigger_code} | Fatigue Score: {self.fatigue_score:.1f}')
        elif trigger_code == 0 and self.last_triggered_code != 0:
            self.trigger_pub.publish(Int32(0))
            self.last_triggered_code = 0

        # 8. Publish Metrics for Jiale's Dashboard
        metrics_msg = FatigueMetrics()
        metrics_msg.current_session_duration_sec = int(self.session_duration_sec)
        metrics_msg.rolling_bad_posture_sec = int(rolling_bad_sec)
        metrics_msg.fatigue_level = self.current_fatigue_level
        self.metrics_pub.publish(metrics_msg)

    def _reset_session(self):
        rospy.loginfo("[fatigue_state_node] User absent for a minute. Resetting session metrics.")
        self.session_duration_sec = 0.0
        self.current_bad_streak_sec = 0.0
        self.max_bad_streak_sec = 0.0
        self.bad_posture_total_sec = 0.0
        self.good_posture_total_sec = 0.0
        self.posture_transition_count = 0
        self.history_queue.clear()
        self.fatigue_score = 0.0

    def run(self):
        rospy.spin()

if __name__ == '__main__':
    try:
        FatigueStateNode().run()
    except rospy.ROSInterruptException:
        pass