#!/usr/bin/env python3
"""
feedback_controller_node.py  —  PostureBuddy Module 4: HRI & Actuation

Subscribes : /hri_triggers          (std_msgs/Int32)          latched
Publishes  : /hri_execution_status  (posture_buddy/HriStatus) @ 1 Hz + on change

Two-way conversation flow (per trigger):
  1. DeepSeek generates an opening message based on trigger code.
  2. pyttsx3 speaks the message.
  3. SpeechRecognition listens for a user reply (mic).
  4. Reply is sent back to DeepSeek (with chat history preserved).
  5. Repeat from step 2 until DeepSeek signals the conversation is done
     OR the user says a closing phrase OR MAX_TURNS is reached.

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

# ── TTS ───────────────────────────────────────────────────────────────────────
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# ── Speech-to-text ────────────────────────────────────────────────────────────
try:
    import speech_recognition as sr
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False

# ── OpenRouter (DeepSeek V4 Flash) ───────────────────────────────────────────
try:
    from openai import OpenAI as _OpenAIClient
    import os as _os
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv()
    _openrouter_client = _OpenAIClient(
        base_url="https://openrouter.ai/api/v1",
        api_key=_os.getenv("OPENROUTER_API_KEY"),
    )
    DEEPSEEK_AVAILABLE = True   # keeping the flag name so rest of code is unchanged
except ImportError:
    _openrouter_client = None
    DEEPSEEK_AVAILABLE = False

# Model slug on OpenRouter
_DEEPSEEK_MODEL = "deepseek/deepseek-v4-flash"

# ── Conversation tuning ───────────────────────────────────────────────────────
# Maximum back-and-forth turns before the robot ends the conversation.
MAX_TURNS = 5
# Seconds to wait for the user to speak before giving up.
LISTEN_TIMEOUT_SEC = 8
# Phrases that end the conversation immediately when the user says them.
CLOSING_PHRASES = {"ok", "okay", "thanks", "thank you", "bye", "done", "got it", "alright"}

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

        # Extra state for two-way conversation
        self._is_listening = False

        rospy.loginfo(
            '[feedback_controller_node] Ready. Waiting for /hri_triggers ...'
            ' (enable_cmd_vel=%s, tts=%s, stt=%s, deepseek=%s)',
            self._enable_cmd_vel, TTS_AVAILABLE, STT_AVAILABLE, DEEPSEEK_AVAILABLE,
        )

    # ── Trigger callback ──────────────────────────────────────────────────────
    def _trigger_cb(self, msg):
        code = msg.data

        if code == TRIGGER_IDLE:
            # Optionally push an idle event to stop speaking, but keep simple.
            return

        label = TRIGGER_LABELS.get(code, f'Unknown trigger {code}')
        rospy.logwarn('[feedback_controller_node] Received trigger %d (%s)', code, label)

        self._last_executed_trigger = code

        # Push trigger to TTS/conversation worker (non-blocking).
        # The worker itself calls DeepSeek for the opening line and then
        # drives the full back-and-forth loop.
        try:
            self._tts_queue.put_nowait(code)
        except queue.Full:
            rospy.logwarn('[feedback_controller_node] TTS queue full; dropping trigger.')

        # Update dashboard immediately
        self._publish_status()

    # ── TTS / conversation worker ─────────────────────────────────────────────
    def _tts_worker(self):
        """
        Runs on its own thread. Owns the pyttsx3 engine and the microphone
        recogniser. For each trigger code it receives:

          1. Opens a fresh DeepSeek chat session with a role-defining system prompt.
          2. Loops up to MAX_TURNS:
               a. Asks DeepSeek for the next thing to say.
               b. Speaks it via pyttsx3 (or logs it as fallback).
               c. Listens for the user's reply via the microphone.
               d. Feeds the reply back into the DeepSeek chat history.
               e. Checks whether the conversation should end.
          3. Resets state and waits for the next trigger.

        pyttsx3 MUST be initialised here — the GLib event loop it uses on
        Linux is NOT thread-safe across threads.
        """
        # ── pyttsx3 init ──────────────────────────────────────────────────────
        tts_engine = None
        if TTS_AVAILABLE:
            try:
                tts_engine = pyttsx3.init()
            except Exception as exc:
                rospy.logerr('[feedback_controller_node] pyttsx3 init failed: %s', exc)
        if not tts_engine:
            rospy.logwarn('[feedback_controller_node] pyttsx3 unavailable — using log fallback.')

        # ── speech_recognition init ───────────────────────────────────────────
        recogniser = None
        microphone = None
        if STT_AVAILABLE:
            try:
                recogniser = sr.Recognizer()
                microphone = sr.Microphone()
                # Calibrate once for ambient noise at startup.
                with microphone as source:
                    recogniser.adjust_for_ambient_noise(source, duration=1)
                rospy.loginfo('[feedback_controller_node] Microphone calibrated.')
            except Exception as exc:
                rospy.logerr('[feedback_controller_node] Microphone init failed: %s', exc)
                recogniser = microphone = None

        # ── main loop ─────────────────────────────────────────────────────────
        while not rospy.is_shutdown():
            # Block until a trigger code arrives.
            try:
                code = self._tts_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            # ── Optional attention wiggle ─────────────────────────────────────
            if self._enable_cmd_vel and self._cmd_vel_pub is not None:
                try:
                    self._do_attention_wiggle()
                except Exception as exc:
                    rospy.logwarn('[feedback_controller_node] wiggle failed: %s', exc)

            # ── Open a DeepSeek chat session for this trigger ───────────────────
            chat = self._open_deepseek_chat(code)

            # ── Conversation loop ─────────────────────────────────────────────
            user_reply = None          # None on the very first turn
            for turn in range(MAX_TURNS):
                if rospy.is_shutdown():
                    break

                # -- 1. Get robot's next utterance from DeepSeek -----------------
                robot_text = self._deepseek_next(chat, code, user_reply, turn)

                # -- 2. Speak --------------------------------------------------
                self._is_speaking = True
                self._publish_status()
                self._speak(tts_engine, robot_text)
                self._is_speaking = False
                self._publish_status()

                # -- 3. Listen for user reply ----------------------------------
                user_reply = self._listen(recogniser, microphone)
                if user_reply is None:
                    # No speech detected — end the conversation gracefully.
                    rospy.loginfo('[feedback_controller_node] No reply heard; ending conversation.')
                    break

                rospy.loginfo('[feedback_controller_node] User said: "%s"', user_reply)

                # -- 4. Check closing phrases ----------------------------------
                if any(phrase in user_reply.lower() for phrase in CLOSING_PHRASES):
                    # Say a brief goodbye then stop.
                    goodbye = self._deepseek_goodbye(chat)
                    self._is_speaking = True
                    self._publish_status()
                    self._speak(tts_engine, goodbye)
                    self._is_speaking = False
                    self._publish_status()
                    break

            # Reset and wait for next trigger.
            self._tts_queue.task_done()

    # ── DeepSeek helpers ────────────────────────────────────────────────────────

    # System prompts that define the robot's persona for each trigger.
    _SYSTEM_PROMPTS = {
        TRIGGER_STRETCH_REMINDER: (
            "You are PostureBuddy, a friendly desk-companion robot. "
            "Your goal right now is to encourage the user to take a short stretch break "
            "because they have been sitting for too long. "
            "Keep every reply to 1-2 sentences. Be warm, varied, and supportive. "
            "When the user has acknowledged and is ready to stretch, "
            "wish them well and end the conversation naturally."
        ),
        TRIGGER_POSTURE_ALERT: (
            "You are PostureBuddy, a friendly desk-companion robot. "
            "Your goal right now is to help the user correct their posture immediately. "
            "Keep every reply to 1-2 sentences. Be direct but kind. "
            "Give brief, actionable posture tips if the user asks. "
            "When the user has confirmed they have fixed their posture, "
            "praise them and end the conversation naturally."
        ),
    }

    _DEFAULT_SYSTEM_PROMPT = (
        "You are PostureBuddy, a friendly desk-companion robot giving health reminders. "
        "Keep replies to 1-2 sentences."
    )

    def _open_deepseek_chat(self, code: int):
        """
        Return a fresh conversation history list (system prompt included).
        'chat' is now just a list of message dicts — we manage history manually
        because OpenRouter uses a stateless REST API, unlike a stateful SDK.
        Returns None if OpenRouter is unavailable.
        """
        if not DEEPSEEK_AVAILABLE:
            return None
        system = self._SYSTEM_PROMPTS.get(code, self._DEFAULT_SYSTEM_PROMPT)
        # The history list is [{"role": ..., "content": ...}, ...]
        # System prompt goes in as the first message with role "system".
        return [{"role": "system", "content": system}]

    def _deepseek_next(self, chat, code: int, user_reply, turn: int) -> str:
        """
        Ask DeepSeek V4 Flash (via OpenRouter) what the robot should say next.
        On turn 0 `user_reply` is None — robot speaks first.
        Appends the new user message and assistant reply to `chat` history.
        Returns a plain string to be spoken.
        """
        _FALLBACKS = {
            TRIGGER_STRETCH_REMINDER: "Time for a quick stretch — stand up and move around a little!",
            TRIGGER_POSTURE_ALERT:    "Please sit up straight and check your posture right now.",
        }

        if chat is None or _openrouter_client is None:
            return _FALLBACKS.get(code, f"Notification {code}.")

        try:
            user_msg = "Start the conversation." if turn == 0 else user_reply
            chat.append({"role": "user", "content": user_msg})

            response = _openrouter_client.chat.completions.create(
                model=_DEEPSEEK_MODEL,
                messages=chat,
                max_tokens=120,
            )
            reply = response.choices[0].message.content.strip()
            # Append assistant reply so next turn has full context.
            chat.append({"role": "assistant", "content": reply})
            return reply
        except Exception as exc:
            rospy.logerr('[feedback_controller_node] OpenRouter request failed: %s', exc)
            return _FALLBACKS.get(code, "I have a reminder for you.")

    def _deepseek_goodbye(self, chat) -> str:
        """Ask DeepSeek for a short closing line."""
        if chat is None or _openrouter_client is None:
            return "Great, take care!"
        try:
            chat.append({"role": "user", "content": "The user is done. Say a short, friendly goodbye in one sentence."})
            response = _openrouter_client.chat.completions.create(
                model=_DEEPSEEK_MODEL,
                messages=chat,
                max_tokens=60,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            rospy.logerr('[feedback_controller_node] OpenRouter goodbye failed: %s', exc)
            return "Great, take care!"

    # ── Speak helper ──────────────────────────────────────────────────────────

    def _speak(self, tts_engine, text: str):
        """Speak `text` via pyttsx3, or log it as a fallback."""
        rospy.loginfo('[feedback_controller_node] Robot says: "%s"', text)
        if tts_engine:
            try:
                tts_engine.say(text)
                tts_engine.runAndWait()
                return
            except Exception as exc:
                rospy.logerr('[feedback_controller_node] TTS error: %s', exc)
        # Fallback: simulate speaking duration so the rest of the loop is realistic.
        time.sleep(min(max(len(text) * 0.05, 0.5), 4.0))

    # ── Listen helper ─────────────────────────────────────────────────────────

    def _listen(self, recogniser, microphone) -> str | None:
        """
        Listen for a user utterance and return its transcript, or None on
        timeout / error / STT unavailable.
        """
        if recogniser is None or microphone is None:
            rospy.logwarn('[feedback_controller_node] STT unavailable — skipping listen.')
            return None

        self._is_listening = True
        self._publish_status()
        rospy.loginfo('[feedback_controller_node] Listening for user reply ...')

        transcript = None
        try:
            with microphone as source:
                audio = recogniser.listen(source, timeout=LISTEN_TIMEOUT_SEC, phrase_time_limit=10)
            transcript = recogniser.recognize_google(audio)
        except sr.WaitTimeoutError:
            rospy.loginfo('[feedback_controller_node] Listen timed out (no speech).')
        except sr.UnknownValueError:
            rospy.loginfo('[feedback_controller_node] Speech not understood.')
        except sr.RequestError as exc:
            rospy.logerr('[feedback_controller_node] STT service error: %s', exc)
        except Exception as exc:
            rospy.logerr('[feedback_controller_node] Listen error: %s', exc)
        finally:
            self._is_listening = False
            self._publish_status()

        return transcript

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