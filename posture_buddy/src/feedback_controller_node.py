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
from posture_buddy.msg import HriStatus, PostureStatus

# Optional motion
from geometry_msgs.msg import Twist

# Standard library
import threading
import time
import queue
from collections import deque
from typing import Optional

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
    # Resolve .env relative to THIS file, not the process cwd — roslaunch/rosrun
    # often start the node from a different working directory, which otherwise
    # causes load_dotenv() to silently find nothing and leave the API key unset.
    _env_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '.env')
    _load_dotenv(dotenv_path=_env_path)
    _api_key = _os.getenv("OPENROUTER_API_KEY")
    if not _api_key:
        raise RuntimeError(
            f"OPENROUTER_API_KEY not set (looked for .env at {_env_path}). "
            "Check the file exists there and contains OPENROUTER_API_KEY=..."
        )
    _openrouter_client = _OpenAIClient(
        base_url="https://openrouter.ai/api/v1",
        api_key=_api_key,
    )
    DEEPSEEK_AVAILABLE = True   # keeping the flag name so rest of code is unchanged
except ImportError as _imp_exc:
    _openrouter_client = None
    DEEPSEEK_AVAILABLE = False
    print(f'[feedback_controller_node] DeepSeek disabled — missing package: {_imp_exc}')
except Exception as _setup_exc:
    _openrouter_client = None
    DEEPSEEK_AVAILABLE = False
    print(f'[feedback_controller_node] DeepSeek disabled — setup error: {_setup_exc}')

# Model slug on OpenRouter
_DEEPSEEK_MODEL = "deepseek/deepseek-v4-flash"

# ── Conversation tuning ───────────────────────────────────────────────────────
# Maximum back-and-forth turns before the robot ends the conversation.
MAX_TURNS = 5
# Seconds to wait for the user to speak before giving up.
LISTEN_TIMEOUT_SEC = 8

# Seconds to keep the just-finished conversation visible on the dashboard
# after a posture-recovered praise line, before clearing it for the next
# session. A new real trigger (stretch/posture alert) cancels this hold
# immediately rather than waiting it out.
POST_PRAISE_HOLD_SEC = 30.0

# ── Wake-word (user-initiated) conversation tuning ────────────────────────────
# Phrases that start a user-initiated conversation when heard while idle.
# Simple substring match on the STT transcript — no extra wake-word engine needed.
WAKE_PHRASES = {"hey posture buddy", "posture buddy", "hey posturebuddy"}
# Short listen window used while idly polling for the wake phrase, so the loop
# stays responsive and doesn't hog the mic lock for long stretches.
WAKE_LISTEN_TIMEOUT_SEC = 4
# A virtual "trigger code" used only to pick a system prompt for user-initiated
# conversations — does not correspond to a real /hri_triggers value.
TRIGGER_USER_INITIATED = -1

# ── Trigger code definitions (must match fatigue_state_node) ──────────────────
TRIGGER_IDLE              = 0
TRIGGER_STRETCH_REMINDER  = 1
TRIGGER_POSTURE_ALERT     = 2
# Internal-only trigger (never published by fatigue_state_node) — fired locally
# by _posture_cb when posture flips to GOOD while a stretch check was active,
# so the robot can react/praise instead of silently resetting.
TRIGGER_POSTURE_RECOVERED = 3

# Human-readable labels used in log output
TRIGGER_LABELS = {
    TRIGGER_STRETCH_REMINDER:  'Gentle Stretch Reminder',
    TRIGGER_POSTURE_ALERT:     'Strong Posture Correction Alert',
    TRIGGER_POSTURE_RECOVERED: 'Posture Recovered Praise',
}


class FeedbackControllerNode:

    def __init__(self):
        rospy.init_node('feedback_controller_node', anonymous=False)

        # State
        self._last_executed_trigger = 0
        self._is_speaking           = False
        self._last_robot_message    = ''
        self._last_user_message     = ''
        self._conversation_history  = []
        self._current_posture       = 'ABSENT'
        self._stretch_check_active   = False
        self._stretch_check_started  = None
        self._stretch_retry_count    = 0

        # Post-praise dashboard hold: after TRIGGER_POSTURE_RECOVERED speaks,
        # the conversation stays visible for POST_PRAISE_HOLD_SEC instead of
        # being wiped immediately. None = no hold pending. A new real trigger
        # (stretch/posture alert) cancels the hold and clears it early.
        self._praise_hold_until = None
        self._praise_hold_lock  = threading.Lock()

        # Rolling record of the 10 most recently COMPLETED conversations
        # (kept separate from the live _conversation_history, which only
        # reflects whatever conversation is currently in progress). Each
        # entry is {'source': 'trigger'|'wakeword', 'trigger_code': int,
        # 'lines': [...], 'ended_at': rospy time}. Oldest is dropped once
        # the 10th new one is added — this never gets wiped wholesale.
        self._conversation_log = deque(maxlen=10)

        # Coordination for folding a trigger into an ongoing wake-word
        # conversation instead of starting a competing one. (Both conversation
        # types now run on the SAME worker thread/mic/TTS engine — see
        # _conversation_worker — so no cross-thread mic lock is needed.)
        self._conversation_active = False          # True while a conversation is in progress
        self._conversation_source = None            # 'trigger' or 'wakeword'
        self._state_lock = threading.Lock()          # guards the two fields above
        self._pending_trigger_note = None            # text to fold into the wake-word chat

        # Publishers
        self._pub = rospy.Publisher('/hri_execution_status', HriStatus, queue_size=10)

        # Optional robot base command publisher (disabled by default)
        self._enable_cmd_vel = rospy.get_param('~enable_cmd_vel', False)
        if self._enable_cmd_vel:
            self._cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
        else:
            self._cmd_vel_pub = None

        # TTS queue & single worker thread.
        # IMPORTANT: pyttsx3 and the speech_recognition Microphone/PortAudio
        # backend are NOT safe to initialise twice (two engine/PyAudio
        # instances in the same process can segfault). Both trigger-driven
        # AND wake-word conversations therefore run on this ONE thread,
        # sharing a single pyttsx3 engine and a single Microphone/Recognizer.
        # pyttsx3 is intentionally NOT initialised here — it must be created on
        # the same thread that calls runAndWait() (Linux/espeak GLib loop is
        # not thread-safe). Initialisation happens inside _conversation_worker.
        self._tts_queue = queue.Queue()

        self._worker_thread = threading.Thread(target=self._conversation_worker, daemon=True)
        self._worker_thread.start()

        # Heartbeat so the dashboard always has fresh data
        rospy.Timer(rospy.Duration(1.0), self._heartbeat_cb)

        # Subscribers last — all state is initialised before any callback fires
        rospy.Subscriber('/hri_triggers', Int32, self._trigger_cb)
        rospy.Subscriber('/posture_status', PostureStatus, self._posture_cb)

        # Extra state for two-way conversation
        self._is_listening = False

        rospy.loginfo(
            '[feedback_controller_node] Ready. Waiting for /hri_triggers ...'
            ' (enable_cmd_vel=%s, tts=%s, stt=%s, deepseek=%s)',
            self._enable_cmd_vel, TTS_AVAILABLE, STT_AVAILABLE, DEEPSEEK_AVAILABLE,
        )

    # ── Shared conversation-state helpers ─────────────────────────────────────
    def _archive_current_conversation(self, source: str, trigger_code: int):
        """
        Save a snapshot of the just-finished conversation into the rolling
        10-entry log. Skips empty conversations (e.g. a trigger fired but the
        worker never got a chance to say anything before shutdown).
        """
        if not self._conversation_history:
            return
        self._conversation_log.append({
            'source': source,
            'trigger_code': trigger_code,
            'lines': list(self._conversation_history),
            'ended_at': rospy.Time.now().to_sec(),
        })

    def _try_claim_conversation(self, source: str) -> bool:
        """
        Attempt to mark a conversation as active for `source` ('trigger' or
        'wakeword'). Returns False if one is already running from either
        source — callers must not proceed with a new conversation in that case.
        """
        with self._state_lock:
            if self._conversation_active:
                return False
            self._conversation_active = True
            self._conversation_source = source
            return True

    def _release_conversation(self):
        with self._state_lock:
            self._conversation_active = False
            self._conversation_source = None

    def _conversation_source_is(self, source: str) -> bool:
        with self._state_lock:
            return self._conversation_active and self._conversation_source == source

    # ── Trigger callback ──────────────────────────────────────────────────────
    def _trigger_cb(self, msg):
        code = msg.data

        if code == TRIGGER_IDLE:
            # Optionally push an idle event to stop speaking, but keep simple.
            return

        label = TRIGGER_LABELS.get(code, f'Unknown trigger {code}')
        rospy.logwarn('[feedback_controller_node] Received trigger %d (%s)', code, label)

        if code == TRIGGER_STRETCH_REMINDER:
            self._stretch_check_active = True
            self._stretch_check_started = rospy.Time.now()
            self._stretch_retry_count = 0

        # If the user is already mid-conversation (because they started it
        # themselves with the wake phrase), don't barge in with a separate
        # conversation — just fold a short reminder note into the ongoing one.
        # The wake-word loop picks this up on its next DeepSeek call.
        if self._conversation_source_is('wakeword'):
            note = {
                TRIGGER_STRETCH_REMINDER: (
                    "[System note: the user has been sitting too long — "
                    "gently work in a suggestion that they stand and stretch soon.]"
                ),
                TRIGGER_POSTURE_ALERT: (
                    "[System note: the user's posture has become poor — "
                    "gently remind them to sit up straight.]"
                ),
            }.get(code)
            if note:
                self._pending_trigger_note = note
                self._cancel_praise_hold()
                rospy.loginfo(
                    '[feedback_controller_node] Folding trigger %d into ongoing '
                    'wake-word conversation instead of starting a new one.', code,
                )
            return

        # If a trigger-driven conversation is already in progress, just queue
        # this new trigger for whenever the current one finishes — do NOT
        # touch _conversation_history / _last_robot_message / publish here.
        # Wiping mid-conversation was causing the dashboard to blank out
        # while the bot was still actively speaking/listening. The actual
        # reset for a fresh conversation happens inside
        # _run_trigger_conversation, right as that conversation begins.
        if self._conversation_source_is('trigger'):
            try:
                self._tts_queue.put_nowait(code)
                self._cancel_praise_hold()
                rospy.loginfo(
                    '[feedback_controller_node] Trigger %d queued — a conversation '
                    'is already in progress, will run after it finishes.', code,
                )
            except queue.Full:
                rospy.logwarn('[feedback_controller_node] TTS queue full; dropping trigger.')
            return

        self._cancel_praise_hold()
        self._last_executed_trigger = code
        self._last_robot_message = ''
        self._last_user_message = ''
        self._conversation_history = []

        # Push trigger to TTS/conversation worker (non-blocking).
        # The worker itself calls DeepSeek for the opening line and then
        # drives the full back-and-forth loop.
        try:
            self._tts_queue.put_nowait(code)
        except queue.Full:
            rospy.logwarn('[feedback_controller_node] TTS queue full; dropping trigger.')

        # Update dashboard immediately
        self._publish_status()

    # ── Posture monitoring ───────────────────────────────────────────────────
    def _posture_cb(self, msg):
        self._current_posture = msg.posture_state

        if self._stretch_check_active and self._current_posture == 'GOOD':
            # User has improved enough; stop the stretch re-check loop and
            # let the robot react/praise instead of resetting silently.
            self._stretch_check_active = False
            self._stretch_check_started = None
            self._stretch_retry_count = 0
            if not self._conversation_source_is('wakeword'):
                # Queues behind any in-progress trigger conversation rather
                # than interrupting it (same queue/worker as every other
                # trigger — see _trigger_cb / _conversation_worker).
                try:
                    self._tts_queue.put_nowait(TRIGGER_POSTURE_RECOVERED)
                except queue.Full:
                    rospy.logwarn(
                        '[feedback_controller_node] TTS queue full; '
                        'skipping posture-recovered praise.'
                    )
            return

        if (
            self._stretch_check_active
            and self._stretch_check_started is not None
            and (rospy.Time.now() - self._stretch_check_started).to_sec() >= 30.0
            and self._stretch_retry_count < 2
        ):
            # If the user still has not improved after a short window, prompt again.
            self._stretch_retry_count += 1
            self._stretch_check_started = rospy.Time.now()
            try:
                self._tts_queue.put_nowait(TRIGGER_STRETCH_REMINDER)
            except queue.Full:
                rospy.logwarn('[feedback_controller_node] Stretch re-check queue full; skipping reminder.')

    # ── Conversation worker (single thread — owns the ONE pyttsx3 engine and
    # ONE microphone/recogniser for the whole node) ───────────────────────────
    def _conversation_worker(self):
        """
        Runs on its own thread for the lifetime of the node. Owns the single
        pyttsx3 engine and the single speech_recognition Microphone/Recognizer
        used by BOTH trigger-driven and wake-word-initiated conversations.

        IMPORTANT: pyttsx3 (espeak/GLib backend) and PortAudio (used by
        speech_recognition's Microphone) are not safe to initialise more than
        once in a process — doing so from two threads previously caused a
        hard segfault. So there is exactly one of each, created here, and
        every conversation (trigger or wake-word) goes through this loop.

        Each pass:
          1. Checks the trigger queue (non-blocking). If a trigger is
             waiting, run a full trigger-driven conversation.
          2. Otherwise, if idle, do one short listen for the wake phrase.
             If heard, run a full user-initiated conversation.
          3. Either way, loop back and repeat.
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

        if recogniser is not None and microphone is not None:
            rospy.loginfo(
                '[feedback_controller_node] Wake-word listening active (phrases: %s).',
                ', '.join(sorted(WAKE_PHRASES)),
            )
        else:
            rospy.logwarn(
                '[feedback_controller_node] STT unavailable — wake-word listening disabled '
                '(trigger-driven conversations still work via TTS-only fallback).'
            )

        # ── main loop ─────────────────────────────────────────────────────────
        while not rospy.is_shutdown():
            # -- 1. Trigger-driven conversation takes priority -------------------
            code = None
            try:
                code = self._tts_queue.get_nowait()
                self._tts_queue.task_done()
                # Drain any further queued triggers and keep only the most
                # recent one — fatigue_state_node may have re-published the
                # same (or a newer) trigger multiple times while we were busy
                # with a previous conversation; we don't want to run a
                # separate full conversation for each stale copy.
                while True:
                    try:
                        code = self._tts_queue.get_nowait()
                        self._tts_queue.task_done()
                    except queue.Empty:
                        break
            except queue.Empty:
                pass

            if code is not None:
                self._try_claim_conversation('trigger')  # always succeeds: single thread
                try:
                    self._run_trigger_conversation(code, tts_engine, recogniser, microphone)
                finally:
                    self._release_conversation()
                continue

            # -- 2. Otherwise, idle-poll for the wake phrase ----------------------
            if recogniser is None or microphone is None:
                rospy.sleep(0.5)
                continue

            heard = self._listen_short(recogniser, microphone, WAKE_LISTEN_TIMEOUT_SEC)
            if not heard:
                continue

            if not any(phrase in heard.lower() for phrase in WAKE_PHRASES):
                continue  # not the wake phrase — ignore and keep polling

            rospy.loginfo('[feedback_controller_node] Wake phrase detected: "%s"', heard)
            self._try_claim_conversation('wakeword')  # always succeeds: single thread
            try:
                self._run_wakeword_conversation(tts_engine, recogniser, microphone)
            finally:
                self._release_conversation()

    def _run_trigger_conversation(self, code, tts_engine, recogniser, microphone):
        """Full back-and-forth conversation for a fatigue/posture trigger."""
        self._last_executed_trigger = code

        # ── Optional attention wiggle ─────────────────────────────────────────
        if self._enable_cmd_vel and self._cmd_vel_pub is not None:
            try:
                self._do_attention_wiggle()
            except Exception as exc:
                rospy.logwarn('[feedback_controller_node] wiggle failed: %s', exc)

        # ── Single reactive line, no back-and-forth ───────────────────────────
        # Posture-recovered praise is a momentary reaction, not the start of a
        # new conversation. It APPENDS to whatever conversation is already on
        # the dashboard (e.g. the stretch-reminder chat that led here) instead
        # of wiping it, then holds the dashboard as-is for POST_PRAISE_HOLD_SEC
        # so the praise visibly lands in that same session before clearing.
        if code == TRIGGER_POSTURE_RECOVERED:
            chat = self._open_deepseek_chat(code)
            robot_text = self._deepseek_next(chat, code, None, 0)
            self._last_robot_message = robot_text
            self._conversation_history.append(f'Robot: {robot_text}')
            self._publish_status()

            self._is_speaking = True
            self._publish_status()
            self._speak(tts_engine, robot_text)
            self._is_speaking = False
            self._publish_status()

            self._archive_current_conversation('trigger', code)

            with self._praise_hold_lock:
                self._praise_hold_until = rospy.Time.now().to_sec() + POST_PRAISE_HOLD_SEC
            return

        # ── Real trigger (stretch reminder / posture alert) ──────────────────
        # A genuine new trigger always wins over a pending praise hold — clear
        # it immediately rather than waiting out the 30s.
        self._cancel_praise_hold()

        # ── Open a DeepSeek chat session for this trigger ───────────────────────
        chat = self._open_deepseek_chat(code)
        self._conversation_history = []
        self._last_robot_message = ''
        self._last_user_message = ''

        # ── Conversation loop ─────────────────────────────────────────────────
        user_reply = None          # None on the very first turn
        for turn in range(MAX_TURNS):
            if rospy.is_shutdown():
                break

            # -- 1. Get robot's next utterance from DeepSeek ---------------------
            robot_text = self._deepseek_next(chat, code, user_reply, turn)
            self._last_robot_message = robot_text
            self._conversation_history.append(f'Robot: {robot_text}')
            self._publish_status()

            # -- 2. Speak ----------------------------------------------------
            self._is_speaking = True
            self._publish_status()
            self._speak(tts_engine, robot_text)
            self._is_speaking = False
            self._publish_status()

            # -- 3. Listen for user reply -------------------------------------
            user_reply = self._listen(recogniser, microphone)
            if user_reply is None:
                # No speech detected — end the conversation gracefully.
                rospy.loginfo('[feedback_controller_node] No reply heard; ending conversation.')
                break

            rospy.loginfo('[feedback_controller_node] User said: "%s"', user_reply)
            self._last_user_message = user_reply
            self._conversation_history.append(f'User: {user_reply}')
            self._publish_status()

        self._archive_current_conversation('trigger', code)

    def _run_wakeword_conversation(self, tts_engine, recogniser, microphone):
        """The actual back-and-forth loop once the wake phrase has been heard."""
        code = TRIGGER_USER_INITIATED
        chat = self._open_deepseek_chat(code)
        self._conversation_history = []
        self._last_robot_message = ''
        self._last_user_message = ''
        self._last_executed_trigger = code
        self._publish_status()

        user_reply = None
        for turn in range(MAX_TURNS):
            if rospy.is_shutdown():
                break

            # Fold in any reminder a trigger queued up while we were talking.
            note = self._pending_trigger_note
            self._pending_trigger_note = None

            # -- 1. Get robot's next utterance from DeepSeek ---------------------
            robot_text = self._deepseek_next(chat, code, user_reply, turn, note=note)
            self._last_robot_message = robot_text
            self._conversation_history.append(f'Robot: {robot_text}')
            self._publish_status()

            # -- 2. Speak ----------------------------------------------------
            self._is_speaking = True
            self._publish_status()
            self._speak(tts_engine, robot_text)
            self._is_speaking = False
            self._publish_status()

            # -- 3. Listen for user reply -------------------------------------
            user_reply = self._listen(recogniser, microphone)
            if user_reply is None:
                rospy.loginfo('[feedback_controller_node] No reply heard; ending wake-word conversation.')
                break

            rospy.loginfo('[feedback_controller_node] User said: "%s"', user_reply)
            self._last_user_message = user_reply
            self._conversation_history.append(f'User: {user_reply}')
            self._publish_status()

        self._archive_current_conversation('wakeword', code)

    def _listen_short(self, recogniser, microphone, timeout_sec: float) -> Optional[str]:
        """
        Like _listen, but quiet (no is_listening/status-publish churn) and
        with a short, configurable timeout — used for idle wake-phrase
        polling so it doesn't block trigger handling for long stretches.
        """
        try:
            with microphone as source:
                audio = recogniser.listen(source, timeout=timeout_sec, phrase_time_limit=6)
            return recogniser.recognize_google(audio)
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as exc:
            rospy.logerr('[feedback_controller_node] Wake-word STT service error: %s', exc)
            return None
        except Exception as exc:
            rospy.logerr('[feedback_controller_node] Wake-word listen error: %s', exc)
            return None

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
        TRIGGER_POSTURE_RECOVERED: (
            "You are PostureBuddy, a friendly desk-companion robot. "
            "The user just fixed their posture on their own — no alert is active "
            "anymore, you're simply noticing and reacting in the moment. "
            "Say one short, warm, varied line of genuine praise or encouragement "
            "(e.g. acknowledging they're sitting up straight now). "
            "Do NOT ask a question and do NOT expect a reply — "
            "this is a single reactive line, not the start of a conversation."
        ),
        TRIGGER_USER_INITIATED: (
            "You are PostureBuddy, a friendly desk-companion robot. "
            "The user just spoke to you on their own — they were not prompted by a "
            "fatigue or posture alert. Chat naturally and help with whatever posture, "
            "stretching, or general wellbeing question they bring up. "
            "Keep every reply to 1-2 sentences. Be warm and conversational. "
            "If the user seems finished, wish them well and end the conversation naturally. "
            "You may occasionally receive a bracketed [System note: ...] in a user message — "
            "that is not something the user said; weave its suggestion naturally into your "
            "reply without quoting the note itself."
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

    def _deepseek_next(self, chat, code: int, user_reply, turn: int, note: Optional[str] = None) -> str:
        """
        Ask DeepSeek V4 Flash (via OpenRouter) what the robot should say next.
        On turn 0 `user_reply` is None — robot speaks first.
        If `note` is given, it's prepended to the user-role message as a
        bracketed system note (used to fold a pending trigger reminder into
        an ongoing wake-word conversation without starting a new one).
        Appends the new user message and assistant reply to `chat` history.
        Returns a plain string to be spoken.
        """
        _FALLBACKS = {
            TRIGGER_STRETCH_REMINDER:  "Time for a quick stretch — stand up and move around a little!",
            TRIGGER_POSTURE_ALERT:     "Please sit up straight and check your posture right now.",
            TRIGGER_POSTURE_RECOVERED: "Great job, your posture looks much better now!",
        }

        if chat is None or _openrouter_client is None:
            return _FALLBACKS.get(code, f"Notification {code}.")

        try:
            user_msg = "Start the conversation." if turn == 0 else user_reply
            if note:
                user_msg = f"{note}\n{user_msg}"
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
            rospy.logerr(
                '[feedback_controller_node] OpenRouter request failed (%s): %s',
                type(exc).__name__, exc,
            )
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
    def _listen(self, recogniser, microphone) -> Optional[str]:
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
        self._check_praise_hold_expired()
        self._publish_status()

    def _check_praise_hold_expired(self):
        """
        If a post-praise dashboard hold is active and POST_PRAISE_HOLD_SEC has
        elapsed, clear the conversation so the dashboard is ready for a fresh
        session. No-op if no hold is pending (the common case).
        """
        with self._praise_hold_lock:
            if self._praise_hold_until is None:
                return
            if rospy.Time.now().to_sec() < self._praise_hold_until:
                return
            self._praise_hold_until = None

        # Only clear if nothing new has started speaking/listening in the
        # meantime (a fresh trigger cancels the hold itself before this could
        # fire, but this guard is cheap insurance against a race).
        if not self._conversation_active:
            self._conversation_history = []
            self._last_robot_message = ''
            self._last_user_message = ''
            rospy.loginfo(
                '[feedback_controller_node] Post-praise hold expired — '
                'dashboard cleared, ready for next session.'
            )

    def _cancel_praise_hold(self):
        """Cancel any pending post-praise hold (called when a new real
        trigger needs the dashboard immediately instead of waiting it out)."""
        with self._praise_hold_lock:
            self._praise_hold_until = None

    # ── Publish helper ────────────────────────────────────────────────────────
    def _publish_status(self):
        out = HriStatus()
        out.is_speaking           = self._is_speaking
        out.last_executed_trigger = self._last_executed_trigger
        out.robot_message         = self._last_robot_message
        out.user_message          = self._last_user_message
        out.conversation          = self._conversation_history
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