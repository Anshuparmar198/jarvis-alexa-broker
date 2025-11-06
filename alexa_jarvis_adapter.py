#!/usr/bin/env python3
# alexa_jarvis_adapter.py
"""
Adapter run by poller or bridge to execute Jarvis commands without GUI.
It imports and runs your action_engine.execute_chained(command).
If your Jarvis has side-effectful modules (voice, GUI), ensure this adapter runs locally.
"""

import sys, time, traceback, os

# Try to import your Jarvis runtime pieces; if missing, fail gracefully but return an error string.
try:
    from action_engine import execute_chained
except Exception as e:
    execute_chained = None
    _import_err = e

# Optional voice helpers; if not present we still continue.
try:
    from voice import speak, play_sound
except Exception:
    def speak(msg): pass
    def play_sound(path): pass

from utils import log_event if 'utils' in sys.modules or True else None  # safe guard removed; keep log_event only if present

def run_text_command(command: str) -> str:
    command = (command or "").strip()
    if not command:
        return "No command given."

    try:
        # best-effort logging
        try:
            from utils import log_event
            log_event({"user": command, "stage": "alexa"})
        except Exception:
            pass

        print(f"[AlexaBridge] Executing: {command}")

        if execute_chained is None:
            return f"Adapter error: execute_chained not importable. Module import error."

        result = execute_chained(command)

        if isinstance(result, str) and result.strip():
            try:
                speak(result)
            except Exception:
                pass
            try:
                from utils import log_event
                log_event({"user": command, "reply": result})
            except Exception:
                pass
            return result
        else:
            try:
                play_sound("sounds/success.wav")
            except Exception:
                pass
            try:
                speak("Task complete.")
            except Exception:
                pass
            return "Task complete."
    except Exception as e:
        traceback.print_exc()
        try:
            play_sound("sounds/fail.wav")
        except Exception:
            pass
        msg = f"Error executing command: {e}"
        try:
            speak(msg)
        except Exception:
            pass
        return msg

if __name__ == "__main__":
    cmd = " ".join(sys.argv[1:]).strip()
    if not cmd:
        print("Usage: python alexa_jarvis_adapter.py \"your command here\"")
        sys.exit(1)
    try:
        with open("alexa_adapter.log", "a", encoding="utf-8") as _f:
            _f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] adapter START cmd={cmd}\n")
            _f.flush()
    except Exception:
        pass
    reply = run_text_command(cmd)
    try:
        with open("alexa_adapter.log", "a", encoding="utf-8") as _f:
            _f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] adapter REPLY: {reply}\n")
            _f.flush()
    except Exception:
        pass
    print(reply)
