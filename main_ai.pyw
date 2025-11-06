# ==========================================================
# main_ai.pyw — MyAI v25 (Final Stable Build)
# Full Dock + Tray + Dictation + Smart Execution Logic
# ==========================================================
import time, re, datetime, threading, os, sys, traceback
import sys
ALEXA_MODE = "--alexa" in sys.argv
from voice import listen, speak, play_sound
from action_engine import execute_chained
from utils import log_event
from win11toast import toast
from ui_dock import JarvisDock

dock = JarvisDock()

# ----------------------------------------------------------
# CONFIG
# ----------------------------------------------------------
WAKE_WORDS = ["jarvis", "jar", "alexa", "hello", "konnichiwa", "welcome", "good", "arise", "wake"]
ACTIVE = False
ALWAYS_ACTIVE = False
DICTATE_MODE = False

SOUND_PATHS = {
    "start": "sounds/start.wav",
    "activated": "sounds/activated.wav",
    "success": "sounds/success.wav",
    "fail": "sounds/fail.wav"
}

# ----------------------------------------------------------
# HELPERS
# ----------------------------------------------------------
def greet_user():
    now = datetime.datetime.now()
    hour = now.hour
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    elif 17 <= hour < 23:
        return "Good evening"
    else:
        return "Good night"

def split_commands(text):
    text = text.lower().strip()
    if ("open youtube" in text and "search" in text) or \
       ("open whatsapp" in text and ("send" in text or "message" in text)):
        return [text]
    return [p.strip() for p in re.split(r'\band\b|\bthen\b|,', text) if p.strip()]

def show_popup(message):
    try:
        toast("MyAI", message, duration="short")
    except Exception:
        pass

# ----------------------------------------------------------
# TRAY INTEGRATION
# ----------------------------------------------------------
try:
    import pystray
    from PIL import Image, ImageDraw
    import pyautogui
    HAS_TRAY = True
except Exception:
    HAS_TRAY = False

tray_icon = None

def setup_tray():
    """System tray control center for Jarvis."""
    global tray_icon
    if not HAS_TRAY:
        return

    def create_icon(color="#ffaa00"):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((16, 16, 48, 48), fill=color)
        return img

    # ---------------- MENU ACTIONS ----------------
    def on_showhide(icon, item):
        dock.toggle_visibility()

    def on_toggle_active(icon, item):
        global ALWAYS_ACTIVE
        ALWAYS_ACTIVE = not ALWAYS_ACTIVE
        msg = "Always Active Mode Enabled" if ALWAYS_ACTIVE else "Always Active Mode Disabled"
        dock.log(msg, "AI")
        speak(msg)
        dock.set_mode("active" if ALWAYS_ACTIVE else "normal")

    def on_toggle_mic(icon, item):
        dock.toggle_mic()

    def on_dictate(icon, item):
        global DICTATE_MODE, ACTIVE
        DICTATE_MODE = not DICTATE_MODE
        if DICTATE_MODE:
            speak("Dictation mode activated.")
            dock.set_mode("active")
            dock.log("🗣️ Dictation mode ON", "AI")
            ACTIVE = True
        else:
            speak("Dictation mode deactivated.")
            dock.set_mode("normal")
            dock.log("Dictation mode OFF", "AI")

    def activate_voice_access(icon, item):
        try:
            speak("Activating voice access.")
            os.startfile("voiceaccess.exe")
        except Exception:
            dock.log("Voice access not found.", "AI")

    def on_exit(icon, item):
        """Full exit — kills Python and closes UI."""
        speak("Shutting down MyAI completely.")
        dock.set_mode("shutdown")
        time.sleep(1)
        dock.shutdown()
        os.system("taskkill /F /IM pythonw.exe")
        os.system("taskkill /F /IM python.exe")
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Show / Hide Dock", on_showhide),
        pystray.MenuItem("Always Active Mode", on_toggle_active),
        pystray.MenuItem("Toggle Microphone", on_toggle_mic),
        pystray.MenuItem("Dictation Mode", on_dictate),
        pystray.MenuItem("Activate Voice Access", activate_voice_access),
        pystray.MenuItem("Exit Jarvis", on_exit)
    )

    tray_icon = pystray.Icon("Jarvis", create_icon(), "Anshu-AI Assistant", menu)

    # ---------------- LEFT CLICK: ACTIVATE ----------------
    def on_click(icon, item):
        global ACTIVE
        ACTIVE = True
        dock.set_mode("active")
        play_sound(SOUND_PATHS["activated"])
        speak("Yes, I’m listening.")
        dock.log("Activated by click.", "AI")

    tray_icon.run_detached()
    try:
        tray_icon.visible = True
        tray_icon._menu_handle_click = on_click
    except Exception:
        pass

# ----------------------------------------------------------
# MAIN LOGIC
# ----------------------------------------------------------

def main_loop():
    global ACTIVE, ALWAYS_ACTIVE, DICTATE_MODE
    play_sound(SOUND_PATHS["start"])
    time.sleep(1)
    greet = greet_user()
    dock.set_mode("normal")
    dock.log(f"{greet}, how can I help you?", "AI")
    speak(f"{greet}, how can I help you?")
    if ALEXA_MODE:
    # Skip greeting & continuous listening; just run the command from sys.argv
        if len(sys.argv) > 1:
            user_command = " ".join(sys.argv[1:])
            dock.log(f"[Alexa trigger] {user_command}", "AI")
            from action_engine import execute_chained
            execute_chained(user_command)
            speak("Task complete.")
        return

    while True:
        try:
            # Mic muted
            if not dock.mic_state:
                time.sleep(0.4)
                continue

            user = listen()
            if not user:
                continue

            dock.log(user, "You")
            u = user.lower().strip()

            # ========== MODES ==========
            if u in ("remain active", "always active"):
                ALWAYS_ACTIVE = True
                dock.log("Remaining active mode enabled.", "AI")
                speak("Remaining active mode enabled.")
                dock.set_mode("active")
                continue

            if "stop remaining active" in u or "disable always active" in u:
                ALWAYS_ACTIVE = False
                dock.log("Returning to normal mode.", "AI")
                speak("Returning to normal mode.")
                dock.set_mode("normal")
                continue

            if "shutdown jarvis" in u or "exit" in u or "terminate" in u:
                dock.log("Shutting down. Goodbye.", "AI")
                speak("Shutting down. Goodbye.")
                dock.set_mode("shutdown")
                time.sleep(1)
                dock.shutdown()
                os.system("taskkill /F /IM pythonw.exe")
                os.system("taskkill /F /IM python.exe")
                break

            # ========== WAKE ACTIVATION ==========
            if not ACTIVE and any(w in u for w in WAKE_WORDS):
                ACTIVE = True
                dock.set_mode("active")
                play_sound(SOUND_PATHS["activated"])
                continue

            # ========== DICTATION ==========
            if DICTATE_MODE:
                try:
                    import pyautogui
                    pyautogui.typewrite(user + " ")
                    dock.log(f"🗣️ {user}", "AI")
                except Exception as e:
                    print("[Dictation Error]:", e)
                    dock.log("Dictation error occurred.", "AI")
                continue

            # ========== EXECUTION ==========
            if ACTIVE or ALWAYS_ACTIVE:
                log_event({"user": user, "stage": "received"})
                print(f"[Jarvis] Command received: {user}")
                commands = split_commands(user)
                dock.set_mode("active")
                dock.speaking(True)

                all_success = True
                had_response = False

                for cmd in commands:
                    try:
                        result = execute_chained(cmd)
                        if isinstance(result, str) and result.strip():
                            dock.log(result.strip(), "AI")
                            speak(result.strip())
                            had_response = True
                        time.sleep(1)
                    except Exception as e:
                        print(f"[Exec Error]: {e}")
                        dock.log(f"Error in: {cmd}", "AI")
                        play_sound(SOUND_PATHS["fail"])
                        all_success = False

                dock.speaking(False)
                log_event({"user": user, "status": "executed"})

                if all_success and not had_response:
                    play_sound(SOUND_PATHS["success"])
                    speak("Task complete.")
                    dock.log("Task complete.", "AI")
                elif not all_success:
                    speak("Some tasks failed.")
                    dock.log("Execution error occurred.", "AI")

                if not ALWAYS_ACTIVE:
                    ACTIVE = False
                    dock.set_mode("normal")
                    print("[Jarvis] Returning to sleep.")
                    time.sleep(1)

        except KeyboardInterrupt:
            speak("Goodbye master.")
            break

        except Exception as e:
            print(f"[Jarvis Error]: {e}")
            traceback.print_exc()
            play_sound(SOUND_PATHS["fail"])
            dock.log("Error occurred.", "AI")
            ACTIVE = False
            time.sleep(1)

# ----------------------------------------------------------
# ENTRY POINT
# ----------------------------------------------------------
# --- Alexa Integration Flag ---
import sys
ALEXA_MODE = "--alexa" in sys.argv

if __name__ == "__main__":
    threading.Thread(target=main_loop, daemon=True).start()
    setup_tray()
    try:
        dock.start()  # GUI loop must be main thread
    except KeyboardInterrupt:
        speak("Exiting gracefully.")
        os.system("taskkill /F /IM pythonw.exe")
    except Exception as e:
        print("[Fatal Error]:", e)
        os.system("taskkill /F /IM pythonw.exe")
        sys.exit(1)

# ==========================================================
# END OF MyAI v25 — Final Polished Stable Build
# ==========================================================
