# ============================================================
#  action_engine.py  — Integrated Version
#  Merges MyAI-v14 command engine + new JARVIS modular system
# ============================================================


import os
import time
import datetime
import webbrowser
import threading
import re
import subprocess
import urllib.parse
import sys
import pytesseract
import pyautogui  # used for keyboard/mouse automation

# ---------- SAFE IMPORTS ----------
try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

try:
    import yt_dlp
except Exception:
    yt_dlp = None

# optional libraries
try:
    import requests
except Exception:
    requests = None

try:
    import psutil
except Exception:
    psutil = None

try:
    import wikipedia
except Exception:
    wikipedia = None

# pycaw for Windows precise volume control
_pycaw_available = False
try:
    from ctypes import POINTER, cast
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    _pycaw_available = True
except Exception:
    _pycaw_available = False

# keyboard lib for fallback send of media keys and other combos
_keyboard_lib = False
try:
    import keyboard as kb
    _keyboard_lib = True
except Exception:
    _keyboard_lib = False

# pygetwindow for window focusing
_pygetwindow_available = False
try:
    import pygetwindow as gw
    _pygetwindow_available = True
except Exception:
    gw = None
    _pygetwindow_available = False

from voice import speak  # for speaking responses

# ----------------- GLOBAL SETTINGS -----------------
TEST_MODE = False
_pygetwindow_available = False
try:
    import pygetwindow as gw
    _pygetwindow_available = True
except ImportError:
    pass

# ----------------- APP PATHS -----------------

# ============================================================
#           🔹 BASIC HELPER FUNCTIONS
# ============================================================


# ============================================================
#           🔹 YOUR OLD HELPER FUNCTIONS
# ============================================================
# You can paste your helper functions here (close_tab, focus_window,
# switch_to_tab_number, parse_key_combo, press_keys_from_list, etc.)
# These stay unchanged from MyAI-v14.
import pyautogui
import re
import time

#instant yt play libs
import webbrowser
import requests
from bs4 import BeautifulSoup
import time
import pyautogui
# === CLICK HELPERS ===
def perform_click(x, y, click_type="left"):
    """Perform a mouse click of the given type at the given coordinates."""
    pyautogui.moveTo(x, y, duration=0.2)
    if click_type == "double":
        pyautogui.doubleClick()
    elif click_type == "right":
        pyautogui.rightClick()
    else:
        pyautogui.click()
def open_start_menu():
    pyautogui.press('win')
    speak("Start menu opened.")

def search_in_start(query):
    pyautogui.press('win')
    time.sleep(0.4)
    pyautogui.typewrite(query, interval=0.5)
    speak(f"Searching for {query} in Start.")

def toggle_wifi():
    speak("Toggling Wi-Fi.")
    pyautogui.hotkey("win", "a")
    time.sleep(1.5)     # move focus to quick toggles section
    pyautogui.press("enter")   # toggle Wi-Fi
    pyautogui.hotkey("win", "a")

def toggle_bluetooth():
    speak("Toggling Bluetooth.")
    pyautogui.hotkey("win", "a")
    time.sleep(1.2)
    pyautogui.press("right")   # move to Bluetooth icon (usually right of Wi-Fi)
    time.sleep(0.5)
    pyautogui.press("enter")   # toggle
    pyautogui.hotkey("win", "a")

from win11toast import toast
toast = toast
# -------------------------------------------------------------------------------
# ---------- UTILITIES ----------
def show_popup(message):
    """Show popup message like Telegram bubble."""
    toast.show_toast("MyAI", message, duration=3, threaded=True)

import ctypes

# Try import python-vlc for app-specific control
try:
    import vlc
except Exception:
    vlc = None

# Virtual-Key codes for multimedia keys (Windows)
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

# keybd_event constants
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

def _send_vk(vk):
    """Send a single multimedia virtual-key (press & release)."""
    ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)

# System-wide controls (call these to control system media players)
def system_play_pause():
    _send_vk(VK_MEDIA_PLAY_PAUSE)

def system_next_track():
    _send_vk(VK_MEDIA_NEXT_TRACK)

def system_prev_track():
    _send_vk(VK_MEDIA_PREV_TRACK)

def system_stop():
    _send_vk(VK_MEDIA_STOP)

# ---------------- VLCManager ----------------
# Manage a VLC player launched/owned by MyAI. Supports play/pause, stop, next/prev (playlist),
# seek +/- seconds, jump to second N, load file/playlist.
class VLCManager:
    def __init__(self):
        self.instance = None
        self.player = None
        self.playlist = []   # list of media paths
        self.current_index = -1
        self.lock = threading.Lock()

    def _ensure_instance(self):
        if vlc is None:
            return False
        if self.instance is None:
            self.instance = vlc.Instance()
        if self.player is None:
            self.player = self.instance.media_player_new()
        return True

    def load_and_play(self, path_or_url, start_immediately=True):
        """Load a single media (file path or URL) and play it."""
        if not self._ensure_instance():
            return False, "VLC not available"
        try:
            media = self.instance.media_new(path_or_url)
            self.player.set_media(media)
            if start_immediately:
                self.player.play()
                time.sleep(0.2)  # let playback begin
            return True, "Loaded"
        except Exception as e:
            return False, str(e)

    def add_to_playlist(self, path_or_url):
        self.playlist.append(path_or_url)
        if self.current_index == -1:
            self.current_index = 0
        return True

    def play_playlist_index(self, idx):
        if not self._ensure_instance(): return False
        if idx < 0 or idx >= len(self.playlist): return False
        self.current_index = idx
        return self.load_and_play(self.playlist[idx], start_immediately=True)

    def play_pause(self):
        if not self._ensure_instance():
            return False
        state = self.player.get_state()
        # states: Playing(3), Paused(4), Stopped(6)
        if state == vlc.State.Playing:
            self.player.pause()
        else:
            self.player.play()
        return True

    def stop(self):
        if not self._ensure_instance(): return False
        self.player.stop()
        return True

    def next(self):
        if not self._ensure_instance(): return False
        if self.playlist and self.current_index + 1 < len(self.playlist):
            self.current_index += 1
            self.load_and_play(self.playlist[self.current_index], start_immediately=True)
            return True
        # fallback: send system media next
        system_next_track()
        return True

    def previous(self):
        if not self._ensure_instance(): return False
        if self.playlist and self.current_index - 1 >= 0:
            self.current_index -= 1
            self.load_and_play(self.playlist[self.current_index], start_immediately=True)
            return True
        # fallback: system prev
        system_prev_track()
        return True

    def seek_seconds(self, seconds_offset):
        """
        Seek forward (positive) or backward (negative) by seconds_offset.
        Uses player.get_time()/set_time() (milliseconds).
        """
        if not self._ensure_instance(): return False
        try:
            cur = self.player.get_time()  # milliseconds
            if cur == -1:
                return False
            new = int(cur + seconds_offset * 1000)
            length = self.player.get_length()
            if length > 0:
                new = max(0, min(new, length - 1000))
            self.player.set_time(new)
            return True
        except Exception:
            return False

    def jump_to_second(self, second):
        if not self._ensure_instance(): return False
        try:
            msec = int(second * 1000)
            self.player.set_time(msec)
            return True
        except Exception:
            return False

    def is_playing(self):
        if not self._ensure_instance(): return False
        return self.player.is_playing()


def open_site(url, name="website"):
    speak(f"Opening {name}.")
    if TEST_MODE:
        print("[TEST_MODE] webbrowser.open", url)
        return
    webbrowser.open(url)

def open_app(app_path):
    """
    Open an application by name.
    Automatically handles names with spaces (e.g., 'voice access' → 'voiceaccess.exe').
    """
    try:
        name = app_path.strip().lower()

        # ✅ Remove spaces for EXE names like "voice access" → "voiceaccess.exe"
        exe_name = name.replace(" ", "") + ".exe"

        speak(f"Opening {name}.")

        if TEST_MODE:
            print("[TEST_MODE] open_app:", exe_name)
            return

        # Try opening by exact name first
        try:
            os.startfile(name)
            return
        except Exception:
            pass

        # Try with .exe suffix (handles “voice access” → “voiceaccess.exe”)
        try:
            os.startfile(exe_name)
            return
        except Exception:
            pass

        # Try Windows Search (if not found)
        pyautogui.hotkey("win", "s")
        time.sleep(0.5)
        pyautogui.typewrite(name)
        pyautogui.press("enter")

    except Exception as e:
        speak(f"Failed to open {app_path}: {e}")
    try:
        if os.path.exists(app_path):
            os.startfile(app_path)
        else:
            # try to open as given or append .exe
            try:
                os.startfile(app_path)
            except Exception:
                os.startfile(f"{app_path}.exe")
    except Exception as e:
        speak(f"Failed to open {app_path}: {e}")

def play_instant_youtube(query):
    """
    Instantly opens the first matching YouTube video for a given search query.
    Fast — uses simple HTML regex scraping (no API, no ytdlp delay).
    """
    try:
        # Construct the search URL
        search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"

        # Get YouTube search HTML
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers, timeout=5)

        if response.status_code != 200:
            print("[YouTube] Error: Invalid HTTP response.")
            return False

        # Search for the first video ID using regex (fastest way)
        video_ids = re.findall(r"watch\?v=(.{11})", response.text)

        if not video_ids:
            print("[YouTube] No video IDs found.")
            return False

        # Pick the first unique video ID
        video_id = video_ids[0]
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Open in browser
        webbrowser.open(video_url)
        print(f"[YouTube] Now playing: {video_url}")
        return True

    except Exception as e:
        print(f"[YouTube Error]: {e}")
        return False

def close_app(process):
    name = process.strip().lower()
        # ✅ Remove spaces for EXE names like "voice access" → "voiceaccess.exe"
    exe_name = name.replace(" ", "")
    if TEST_MODE:
        print("[TEST_MODE] close_app:", process)
        return
    try:
        os.system(f"taskkill /f /im {exe_name}")
    except Exception as e:
        speak(f"Failed to close {process}: {e}")

def tell_time():
    now = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"The time is {now}")

def tell_date():
    today = datetime.datetime.now().strftime("%A, %d %B %Y")
    now = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"Today is {today} and it’s {now}")

def take_screenshot():
    speak("Taking screenshot.")
    if TEST_MODE:
        speak("TEST_MODE: screenshot skipped.")
        return
    try:
        pyautogui.hotkey('win', 'shift', 's')
        speak("Screenshot command sent (Win+Shift+S). Use the snipping tool to capture/save.")
    except Exception as e:
        speak(f"Screenshot failed: {e}")
def lock_screen():
    pyautogui.hotkey("win","l")
    speak("Screen Locked")

def sleep_system():
    speak("System going to sleep")
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

def hibernate_system():
    speak("System hibernating")
    os.system("shutdown /h")
def shutdown():
    speak("Shutting down in 5 seconds.")
    if not TEST_MODE:
        os.system("shutdown /s /t 5")
def minimize_window():
    try:
        window = gw.getActiveWindow()
        if window:
            window.minimize()
            speak("Window minimized")
    except:
        speak("Unable to minimize")

def maximize_window():
    try:
        window = gw.getActiveWindow()
        if window:
            window.maximize()
            speak("Window maximized")
    except:
        speak("Unable to maximize")

# ---------- YOUTUBE ----------
def play_youtube_first_result(query):
    speak(f"Playing {query} on YouTube.")
    if TEST_MODE:
        return
    try:
        if yt_dlp is not None:
            search_query = f"ytsearch1:{query}"
            ydl_opts = {"quiet": True, "skip_download": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(search_query, download=False)
                video_url = result["entries"][0]["webpage_url"]
                webbrowser.open(video_url)
        else:
            webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
    except Exception as e:
        speak(f"Failed to play video: {e}")

def youtube_download(query):
    if yt_dlp is None:
        speak("yt_dlp not installed. Run 'pip install yt-dlp'")
        return
    speak(f"Downloading {query} from YouTube.")
    downloads_folder = os.path.join(os.getcwd(), "downloads")
    os.makedirs(downloads_folder, exist_ok=True)
    try:
        search_query = f"ytsearch1:{query}"
        ydl_opts = {
            "outtmpl": os.path.join(downloads_folder, "%(title)s.%(ext)s"),
            "quiet": False,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([search_query])
        speak("Download completed successfully.")
    except Exception as e:
        speak(f"Download failed: {e}")

# ---------- WEATHER ----------
def get_weather(location=""):
    if requests is None:
        speak("Weather feature requires the 'requests' library. Opening web results instead.")
        if location:
            open_site(f"https://www.google.com/search?q=weather+{urllib.parse.quote(location)}", f"weather for {location}")
        else:
            open_site("https://wttr.in", "wttr.in")
        return
    try:
        target = location.strip() or ""
        url = f"http://wttr.in/{urllib.parse.quote(target)}?format=3"
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            speak(r.text)
        else:
            speak("Couldn't fetch weather. Opening web result.")
            if location:
                open_site(f"https://www.google.com/search?q=weather+{urllib.parse.quote(location)}", f"weather for {location}")
            else:
                open_site("https://wttr.in", "wttr.in")
    except Exception as e:
        speak(f"Weather lookup failed: {e}")


NOTES_FILE = "assistant_notes.txt"# ---------- NOTES ----------
def make_note(text):
    try:
        with open(NOTES_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} - {text}\n")
        speak("Note saved.")
    except Exception as e:
        speak(f"Failed to save note: {e}")

def show_notes():
    try:
        if not os.path.exists(NOTES_FILE):
            speak("No notes yet.")
            return
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            lines = f.read().strip().splitlines()
        if not lines:
            speak("No notes yet.")
            return
        speak("Here are your recent notes:")
        for ln in lines[-10:]:
            speak(ln)
    except Exception as e:
        speak(f"Failed to read notes: {e}")

def clear_notes():
    try:
        open(NOTES_FILE, "w", encoding="utf-8").close()
        speak("Cleared all notes.")
    except Exception as e:
        speak(f"Failed to clear notes: {e}")

# ---------- WIKIPEDIA ----------
def wiki_summary(query):
    if wikipedia is None:
        speak("Wikipedia package not installed. Opening web search instead.")
        open_site(f"https://en.wikipedia.org/wiki/{urllib.parse.quote(query.replace(' ', '_'))}", f"Wikipedia: {query}")
        return
    try:
        summary = wikipedia.summary(query, sentences=2) 
        speak(summary)
    except Exception as e:
        speak(f"Wikipedia lookup failed: Opening web search.")
        print("error code read for fix:",e)
        open_site(f"https://en.wikipedia.org/wiki/{urllib.parse.quote(query.replace(' ', '_'))}", f"Wikipedia: {query}")

# ---------- SYSTEM INFO ----------
def get_system_info():
    if psutil is None:
        speak("System info requires 'psutil'. Please install it to use this feature.")
        return
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        speak(f"CPU usage is {cpu} percent. Memory usage is {int(mem.percent)} percent.")
        try:
            batt = psutil.sensors_battery()
            if batt:
                if batt.power_plugged==False:
                    pg="not charging"
                else:
                    pg="charging"
            time.sleep(4)
            speak(f"Battery at {int(batt.percent)} percent. battery is {pg}")
        except Exception:
            pass
    except Exception as e:
        speak(f"Failed to get system info: {e}")

# ---------- VOLUME CONTROL ----------
def _get_volume_interface():
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return volume
    except Exception:
        return None

def volume_up(step=0.05):
    if _pycaw_available:
        vol = _get_volume_interface()
        if vol:
            try:
                current = vol.GetMasterVolumeLevelScalar()
                vol.SetMasterVolumeLevelScalar(min(1.0, current + float(step)), None)
                speak("Volume increased.")
                return
            except Exception:
                pass
    if _keyboard_lib:
        try:
            kb.send('volume up')
            speak("Volume increased (fallback).")
            return
        except Exception:
            pass
    speak("Volume control unavailable. Install pycaw or keyboard library for fallback.")

def volume_down(step=0.05):
    if _pycaw_available:
        vol = _get_volume_interface()
        if vol:
            try:
                current = vol.GetMasterVolumeLevelScalar()
                vol.SetMasterVolumeLevelScalar(max(0.0, current - float(step)), None)
                speak("Volume decreased.")
                return
            except Exception:
                pass
    if _keyboard_lib:
        try:
            kb.send('volume down')
            speak("Volume decreased (fallback).")
            return
        except Exception:
            pass
    speak("Volume control unavailable. Install pycaw or keyboard library for fallback.")

def volume_mute():
    if _pycaw_available:
        vol = _get_volume_interface()
        if vol:
            try:
                vol.SetMute(1, None)
                speak("Muted.")
                return
            except Exception:
                pass
    if _keyboard_lib:
        try:
            kb.send('volume mute')
            speak("Muted (fallback).")
            return
        except Exception:
            pass
    speak("Mute unavailable.")

def volume_unmute():
    if _pycaw_available:
        vol = _get_volume_interface()
        if vol:
            try:
                vol.SetMute(0, None)
                speak("Unmuted.")
                return
            except Exception:
                pass
    if _keyboard_lib:
        try:
            kb.send('volume unmute')
            speak("Unmuted (fallback).")
            return
        except Exception:
            pass
    speak("Unmute unavailable.")

def volume_set(percentage):
    try:
        p = float(percentage)
        if p < 0 or p > 100:
            speak("Please specify a value between 0 and 100.")
            return
    except Exception:
        speak("Invalid volume value.")
        return
    if _pycaw_available:
        vol = _get_volume_interface()
        if vol:
            try:
                vol.SetMasterVolumeLevelScalar(max(0.0, min(1.0, p / 100.0)), None)
                speak(f"Volume set to {int(p)} percent.")
                return
            except Exception:
                pass
    speak("Precise volume set requires 'pycaw' on Windows. Install it for exact control.")

# ---------- CALCULATOR (safe AST) ----------
import ast, operator as op
_allowed_operators = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.Mod: op.mod,
    ast.FloorDiv: op.floordiv
}

def _eval_expr(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Unsupported constant")
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.BinOp):
        left = _eval_expr(node.left)
        right = _eval_expr(node.right)
        oper = _allowed_operators.get(type(node.op))
        if oper is None:
            raise ValueError("Unsupported operator")
        return oper(left, right)
    if isinstance(node, ast.UnaryOp):
        oper = _allowed_operators.get(type(node.op))
        if oper is None:
            raise ValueError("Unsupported unary operator")
        return oper(_eval_expr(node.operand))
    raise ValueError("Unsupported expression")

def calculate_expression(expr_text):
    trans = {
        'plus': '+', 'minus': '-', 'times': '*', 'multiplied by': '*', 'multiply': '*',
        'x': '*', 'into': '*', 'divide': '/', 'divided by': '/', 'over': '/',
        'power': '**', 'to the power of': '**'
    }
    expr = expr_text.lower()
    for k, v in trans.items():
        expr = re.sub(r'\b' + re.escape(k) + r'\b', v, expr)
    expr = expr.replace(',', '')
    expr = expr.replace('^', '**')
    cleaned = re.sub(r'[^0-9\.\+\-\*\/\%\(\)\s\*]', '', expr)
    cleaned = cleaned.strip()
    if not re.search(r'[0-9]', cleaned):
        raise ValueError("No numbers to calculate")
    node = ast.parse(cleaned, mode='eval').body
    return _eval_expr(node)

# ---------- MOUSE & SCROLL ----------
def left_click():
    try:
        if TEST_MODE:
            print("[TEST_MODE] left_click")
            speak("Clicked (test).")
            return
        pyautogui.click()
        speak("Clicked.")
    except Exception as e:
        speak(f"Click failed: {e}")

def double_click():
    try:
        if TEST_MODE:
            print("[TEST_MODE] double_click")
            speak("Double clicked (test).")
            return
        pyautogui.doubleClick()
        speak("Double clicked.")
    except Exception as e:
        speak(f"Double click failed: {e}")

def right_click():
    try:
        if TEST_MODE:
            print("[TEST_MODE] right_click")
            speak("Right clicked (test).")
            return
        pyautogui.click(button='right')
        speak("Right clicked.")
    except Exception as e:
        speak(f"Right click failed: {e}")

def move_mouse_to(x, y, duration=0.2):
    try:
        if TEST_MODE:
            print(f"[TEST_MODE] move_mouse_to {x},{y}")
            speak(f"Moved mouse to {x},{y} (test).")
            return
        pyautogui.moveTo(int(x), int(y), duration=duration)
        speak(f"Moved mouse to {x},{y}.")
    except Exception as e:
        speak(f"Move mouse failed: {e}")

def scroll_direction(amount):
    try:
        if TEST_MODE:
            print(f"[TEST_MODE] scroll {amount}")
            return
        pyautogui.scroll(int(amount))
        print(f"[AI]: scrolled {amount}")
    except Exception as e:
        speak(f"Scroll failed: {e}")

# ---------- TAB & WINDOW HELPERS ----------
def next_tab():
    try:
        if TEST_MODE:
            print("[TEST_MODE] next_tab")
            speak("Switched to next tab (test).")
            return
        pyautogui.hotkey('ctrl', 'tab')
        speak("Switched to next tab.")
    except Exception as e:
        speak(f"Switching tab failed: {e}")

def previous_tab():
    try:
        if TEST_MODE:
            print("[TEST_MODE] previous_tab")
            speak("Switched to previous tab (test).")
            return
        pyautogui.hotkey('ctrl', 'shift', 'tab')
        speak("Switched to previous tab.")
    except Exception as e:
        speak(f"Switching tab failed: {e}")

def new_tab():
    try:
        if TEST_MODE:
            print("[TEST_MODE] new_tab")
            speak("Opened new tab (test).")
            return
        pyautogui.hotkey('ctrl', 't')
        speak("Opened new tab.")
    except Exception as e:
        speak(f"Open new tab failed: {e}")

def close_tab():
    try:
        if TEST_MODE:
            print("[TEST_MODE] close_tab")
            speak("Closed current tab (test).")
            return
        pyautogui.hotkey('ctrl', 'w')
        speak("Closed current tab.")
    except Exception as e:
        speak(f"Close tab failed: {e}")

def switch_to_tab_number(n):
    try:
        if TEST_MODE:
            print(f"[TEST_MODE] switch_to_tab_number {n}")
            speak(f"Switched to tab {n} (test).")
            return
        if 1 <= n <= 8:
            pyautogui.hotkey('ctrl', str(n))
            speak(f"Switched to tab {n}.")
        else:
            speak("Tab number out of quick range (1-8).")
    except Exception as e:
        speak(f"Switch to tab failed: {e}")

# ---------- WINDOW & APP SWITCHING ----------
def focus_window(title_substring):
    if TEST_MODE:
        print("[TEST_MODE] focus_window", title_substring)
        speak("Focus window (test).")
        return
    if not _pygetwindow_available:
        speak("Window focus requires 'pygetwindow'. Using Alt+Tab fallback.")
        try:
            pyautogui.hotkey('alt', 'tab')
        except Exception:
            pass
        return
    try:
        titles = [t for t in gw.getAllTitles() if t and title_substring.lower() in t.lower()]
        if not titles:
            speak(f"No window with title containing {title_substring} found.")
            return
        win = gw.getWindowsWithTitle(titles[0])[0]
        win.activate()
        speak(f"Activated window: {win.title}")
    except Exception as e:
        speak(f"Failed to focus window: {e}")

def alt_tab_once():
    try:
        if TEST_MODE:
            print("[TEST_MODE] alt_tab_once")
            speak("Switched to next app (test).")
            return
        pyautogui.hotkey('alt', 'tab')
        speak("Switched to next app.")
    except Exception as e:
        speak(f"Alt+Tab failed: {e}")

def alt_shift_tab_once():
    try:
        if TEST_MODE:
            print("[TEST_MODE] alt_shift_tab_once")
            speak("Switched to previous app (test).")
            return
        pyautogui.hotkey('shift', 'alt', 'tab')
        speak("Switched to previous app.")
    except Exception as e:
        speak(f"Alt+Shift+Tab failed: {e}")

def win_tab():
    try:
        if TEST_MODE:
            print("[TEST_MODE] win_tab")
            speak("Opened task view (test).")
            return
        pyautogui.hotkey('win', 'tab')
        speak("Opened task view.")
    except Exception as e:
        speak(f"Win+Tab failed: {e}")

# ---------- KEY / HOTKEY PARSING ----------
_key_alias = {
    'control': 'ctrl', 'ctrl': 'ctrl', 'alt': 'alt', 'shift': 'shift',
    'windows': 'win', 'win': 'win', 'command': 'command', 'cmd': 'command',
    'enter': 'enter', 'return': 'enter', 'esc': 'esc', 'escape': 'esc',
    'space': 'space', 'tab': 'tab', 'backspace': 'backspace', 'delete': 'delete',
    'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right',
}

def parse_key_combo(text):
    t = text.lower().strip()
    t = t.replace('press the ', '').replace('press ', '')
    t = t.replace(' plus ', ' + ').replace(' and ', ' ')
    t = t.replace('windows', 'win')
    t = re.sub(r'\s*\+\s*', '+', t)
    parts = re.split(r'\s+|,|\+|and', t)
    keys = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p in ['paste']:
            return ['ctrl', 'v']
        if p in ['copy']:
            return ['ctrl', 'c']
        if p in ['cut']:
            return ['ctrl', 'x']
        if p in ['undo']:
            return ['ctrl', 'z']
        if p in ['redo']:
            return ['ctrl', 'y']
        if p in ['selectall', 'select all', 'select']:
            return ['ctrl', 'a']
        if re.match(r'^f\d{1,2}$', p):
            keys.append(p)
            continue
        if len(p) == 1:
            keys.append(p)
            continue
        if p in _key_alias:
            keys.append(_key_alias[p])
            continue
        if re.match(r'^\d+$', p):
            keys.append(p)
            continue
        keys.append(p)
    return keys

def press_keys_from_list(key_list):
    if not key_list:
        speak("No keys to press.")
        return
    try:
        if TEST_MODE:
            print("[TEST_MODE] press keys:", key_list)
            speak("Shortcut executed (test).")
            return
        if len(key_list) == 1:
            pyautogui.press(key_list[0])
        else:
            pyautogui.hotkey(*key_list)
        speak("pressed")
    except Exception as e:
        speak(f"Key press failed: {e}")

# ---------- MAIN COMMAND PROCESSOR ----------

def execute_chained(command):
    """
    Split compound commands (like 'open youtube and search arijit singh')
    and run each individually with a short pause between them.
    """
    # Split using 'and', 'then', or commas
    parts = re.split(r"\band\b|\bthen\b|,", command, flags=re.IGNORECASE)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        execute(part)
        time.sleep(2)  # 2-sec delay between tasks
# ---------- MAIN COMMAND PROCESSOR ----------
stopwatch_running = False
stopwatch_start = None
'''command=input("enter query: ")'''
def execute(command):
    global stopwatch_running, stopwatch_start
    if not command:
        return

    lc = command.lower().strip()
    print(f"[ACTION_ENGINE EXECUTE] {lc}")

    # your full existing logic continues here...
    global stopwatch_running, stopwatch_start

    if not command:
        return
    lc = command.lower().strip()
    media_keywords = ["play", "pause", "next", "previous", "prev", "song", "track", "vlc", "seek", "jump", "forward", "rewind", "stop music"]

    
    #conver with bot
    if "how are you" in lc or "how r u" in lc:
        speak("i am fine. say jarvis when you need me to help?")
        return
    elif ("what can you do") in lc:
        speak('''I can manage your all windows snap them left and right, write and chat for you
              open or close any application
              set timer, stopwatch and reminder,
              search on wikipedia and play songs on youtube even download them on windows and many you just by your words,
              people say bolne se kya hota hai! yaha bolo sb hoga''')

    # ---- Timer / Stopwatch / Reminder ----
    if "timer" in lc:
        match = re.search(r"(\d+)\s*(second|seconds|minute|minutes|hour|hours)?", lc)
        if match:
            value = int(match.group(1))
            unit = match.group(2) or "seconds"
            if "minute" in unit:
                delay = value * 60
            elif "hour" in unit:
                delay = value * 3600
            else:
                delay = value
            speak(f"Timer set for {value} {unit}")
            def timer_done():
                time.sleep(delay)
                speak("Time's up!")
            threading.Thread(target=timer_done).start()
        else:
            speak("Please specify the duration for the timer.")
        return

    if "start stopwatch" in lc:
        if not stopwatch_running:
            stopwatch_running = True
            stopwatch_start = time.time()
            speak("Stopwatch started.")
        else:
            speak("Stopwatch already running.")
        return
    if "stop stopwatch" in lc:
        if stopwatch_running:
            elapsed = time.time() - stopwatch_start
            stopwatch_running = False
            speak(f"Stopped. Time elapsed {int(elapsed)} seconds.")
        else:
            speak("Stopwatch is not running.")
        return
    if "reset stopwatch" in lc:
        stopwatch_running = False
        stopwatch_start = None
        speak("Stopwatch reset.")
        return

    elif lc.startswith("search on start"):
        q = lc.replace("search on start", "").strip()
        if q:
            search_in_start(q)
        else:
            speak("Say the text to search.")
        return
    if "remind" in lc or "reminder" in lc:
        try:
            if "after" in lc:
                match = re.search(r"after (\d+)\s*(second|seconds|minute|minutes|hour|hours)?", lc)
                if not match:
                    speak("Please say it like remind me after 10 minutes.")
                    return
                value = int(match.group(1))
                unit = match.group(2) or "seconds"
                if "minute" in unit:
                    delay = value * 60
                elif "hour" in unit:
                    delay = value * 3600
                else:
                    delay = value
                parts = lc.split("after", 1)[1].split("as")
                message = parts[1].strip() if len(parts) > 1 else "Reminder!"
                speak(f"Reminder set after {value} {unit} as {message}")
                def remind_later():
                    time.sleep(delay)
                    speak(message)
                threading.Thread(target=remind_later).start()
                return
            elif "at" in lc:
                match = re.search(r"at\s*(\d{1,2})[:\s](\d{1,2})", lc)
                if not match:
                    speak("Please say it like remind me at 13:23 as message.")
                    return
                hour, minute = int(match.group(1)), int(match.group(2))
                now = datetime.datetime.now()
                target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if target < now:
                    target += datetime.timedelta(days=1)
                delay = (target - now).total_seconds()
                parts = lc.split("as")
                message = parts[1].strip() if len(parts) > 1 else lc.split(match.group(0))[-1].strip() or "Reminder!"
                speak(f"Reminder set for {hour}:{minute:02d} as {message}")
                def remind_later():
                    time.sleep(delay)
                    speak(message)
                threading.Thread(target=remind_later).start()
                return
            else:
                speak("Please say remind me after or remind me at.")
        except Exception as e:
            speak(f"Sorry, I couldn’t set the reminder. Error: {e}")
        return
        # ---------- ADVANCED WHATSAPP LOGIC ----------
    if "open whatsapp" in lc and "send" in lc:
        try:
            # Step 1: Open WhatsApp (Win + 3)
            speak("Opening WhatsApp and preparing to send your message.")
            pyautogui.hotkey("win", "3")
            time.sleep(5)

            # Step 2: Extract receiver name and message
            # Example: "open whatsapp send hello to ayush"
            match = re.search(r"send\s+(.*?)\s+to\s+(\w+)", lc)
            if match:
                message = match.group(1).strip()
                receiver = match.group(2).strip()
            else:
                # fallback if user says "send to ayush hello"
                match2 = re.search(r"send\s+to\s+(\w+)\s+(.*)", lc)
                if match2:
                    receiver = match2.group(1).strip()
                    message = match2.group(2).strip()
                else:
                    speak("I couldn't detect the contact or message clearly.")
                    return

            # Step 3: Search for contact
            pyautogui.typewrite(receiver, interval=0.05)
            time.sleep(2)
            pyautogui.press("down")
            pyautogui.press("enter")
            time.sleep(2)

            # Step 4: Send message
            pyautogui.typewrite(message, interval=0.05)
            pyautogui.press("enter")

            speak(f"Message '{message}' sent to {receiver}.")
        except Exception as e:
            speak(f"Failed to send message: {e}")
        return
        # ---------- ADVANCED YOUTUBE LOGIC ----------
    if "open youtube" in lc and "search" in lc:
        try:
            speak("Opening YouTube and searching your query.")
            
            # Step 1: Open YouTube app (Win + 4)
            pyautogui.hotkey("win", "4")
            time.sleep(8)

            # Step 2: Extract the search query
            # Example: "open youtube search arijit singh"
            match = re.search(r"search\s+(.*)", lc)
            if match:
                query = match.group(1).strip()
            else:
                speak("Please specify what to search on YouTube.")
                return

            # Step 3: Focus search bar (press '/')
            pyautogui.press("/")
            time.sleep(0.5)

            # Step 4: Type the query and search
            pyautogui.typewrite(query, interval=0.05)
            pyautogui.press("enter")

            speak(f"Searching YouTube for {query}.")
        except Exception as e:
            speak(f"Failed to search on YouTube: {e}")
        return

    # ---------- ORIGINAL HANDLERS (kept intact) ----------
    if lc in ["open youtube","youtube khol"]:
        open_site("https://youtube.com", "YouTube"); return
    if lc in ["open google", "google", "google khol"]:
        open_site("https://google.com", "Google"); return
    if "chrome" in lc and "open" in lc:
        open_app("chrome"); return
    if "pw" in lc or "physics wallah" in lc:
        open_site("https://www.pw.live/study-v2/batches/654b31fd3d24f600180fe031/batch-overview#Subjects_2", "Physics Wallah"); return
    if "explorer" in lc and "open" in lc:
        speak("Opening File Explorer.")
        if not TEST_MODE:
            os.system("explorer")
        return
    
    if "open whatsapp" in lc:
        pyautogui.hotkey('win','3'); speak("whatsapp launched sucessfully")
        return
    if lc.startswith("download "):
        query = lc.replace("download", "", 1).strip()
        if query:
            youtube_download(query)
        else:
            speak("What should I download?")
        return
    if lc.startswith("play "):
        query = lc.replace("play", "", 1).strip()
        if query:
            play_instant_youtube(query)
        else:
            speak("What should I play on YouTube?")
        return

    if "search" in lc and "youtube" in lc:
        q = re.sub(r'.*search\s+', '', lc).replace("on youtube","").strip()
        open_site(f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}", f"results for {q} on YouTube")
        return
    if "search" in lc:
        q = re.sub(r'.*search\s+', '', lc).replace("on google","").strip()
        open_site(f"https://www.google.com/search?q={urllib.parse.quote(q)}", f"search results for {q} on Google")
        return

    # ---------- NEW FEATURES: high priority complex phrases ----------

    # Task view / Win+Tab
    if any(kw in lc for kw in ["window plus tab", "windows plus tab", "press windows and tab", "open task view", "show all windows", "win tab", "window tab"]):
        win_tab(); return

    # App switching: alt+tab / next app
    if any(kw in lc for kw in ["alt tab", "alt plus tab", "switch app", "next app", "switch application", "next application"]):
        alt_tab_once(); return
    if any(kw in lc for kw in ["previous app", "previous application", "reverse alt tab", "alt shift tab", "shift alt tab"]):
        alt_shift_tab_once(); return

    # Focus window
    if lc.startswith("focus ") or lc.startswith("switch to "):
        tgt = lc.replace("focus", "").replace("switch to", "").strip()
        if tgt:
            focus_window(tgt)
        else:
            speak("Which window should I focus?")
        return

    elif ("toggle wi-fi" in lc) or ("wi-fi" in lc):
        toggle_wifi()
        return

    elif ("toggle bluetooth" in lc) or ("bluetooth" in lc):
        toggle_bluetooth()
        return

    # Start/search/run/settings/explorer
    if any(kw in lc for kw in ["open start", "open start menu", "start menu"]):
        try:
            if TEST_MODE:
                print("[TEST_MODE] open start menu")
                speak("Opened Start menu (test).")
            else:
                pyautogui.hotkey('win')
                speak("Opened Start menu.")
        except Exception as e:
            speak(f"Open Start failed: {e}")
        return
    if any(kw in lc for kw in ["open search", "windows search", "open search window"]) or lc.strip() == "search":
        try:
            if TEST_MODE:
                print("[TEST_MODE] win+s")
                speak("Opened Windows search (test).")
            else:
                pyautogui.hotkey('win','s')
                speak("Opened Windows search.")
        except Exception as e:
            speak(f"Open search failed: {e}")
        return
    if any(kw in lc for kw in ["open run", "run window", "windows run"]):
        try:
            if TEST_MODE:
                print("[TEST_MODE] win+r")
                speak("Opened Run dialog (test).")
            else:
                pyautogui.hotkey('win','r')
                speak("Opened Run dialog.")
        except Exception as e:
            speak(f"Open Run failed: {e}")
        return
    if any(kw in lc for kw in ["open settings", "settings"]):
        try:
            if TEST_MODE:
                print("[TEST_MODE] win+i")
                speak("Opened Settings (test).")
            else:
                pyautogui.hotkey('win','i')
                speak("Opened Settings.")
        except Exception as e:
            speak(f"Open Settings failed: {e}")
        return
    if any(kw in lc for kw in ["open file explorer", "open explorer", "open files"]):
        try:
            if TEST_MODE:
                print("[TEST_MODE] win+e")
                speak("Opened File Explorer (test).")
            else:
                pyautogui.hotkey('win','e')
                speak("Opened File Explorer.")
        except Exception as e:
            speak(f"Open File Explorer failed: {e}")
        return
    #quick tiles
    if any(k in lc for k in media_keywords):
        result_text = handle_media_command(lc)
        speak(result_text)
        return
    if any(kw in lc for kw in ["open quick tiles"]):
        pyautogui.hotkey("win","a")
        return

    # Snap windows
    if any(kw in lc for kw in ["snap left", "move window left", "snap window to left"]):
        try:
            if TEST_MODE:
                print("[TEST_MODE] snap left (win+left)")
                speak("Window snapped left (test).")
            else:
                pyautogui.hotkey('win','left'); speak("Window snapped left.")
        except Exception as e:
            speak(f"Snap left failed: {e}")
        return
    if any(kw in lc for kw in ["snap right", "move window right", "snap window to right"]):
        try:
            if TEST_MODE:
                print("[TEST_MODE] snap right (win+right)")
                speak("Window snapped right (test).")
            else:
                pyautogui.hotkey('win','right'); speak("Window snapped right.")
        except Exception as e:
            speak(f"Snap right failed: {e}")
        return
    if any(kw in lc for kw in ["snap up", "snap maximize", "snap window to top"]):
        try:
            if TEST_MODE:
                print("[TEST_MODE] snap up (win+up)")
                speak("Window snapped up/maximized (test).")
            else:
                pyautogui.hotkey('win','up'); speak("Window snapped up/maximized.")
        except Exception as e:
            speak(f"Snap up failed: {e}")
        return
    if any(kw in lc for kw in ["snap down", "snap to bottom"]):
        try:
            if TEST_MODE:
                print("[TEST_MODE] snap down (win+down)")
                speak("Window snapped down (test).")
            else:
                pyautogui.hotkey('win','down'); speak("Window snapped down.")
        except Exception as e:
            speak(f"Snap down failed: {e}")
        return
    if "minimize" in lc or "minimise" in lc:
        minimize_window()
        return

    if "maximize" in lc or "maximise" in lc:
        maximize_window()
        return

    # Show desktop / lock screen / task manager
    if any(kw in lc for kw in ["show desktop", "show my desktop"]):
        try:
            if TEST_MODE:
                print("[TEST_MODE] win+d")
                speak("Showing desktop (test).")
            else:
                pyautogui.hotkey('win','d'); speak("Showing desktop.")
        except Exception as e:
            speak(f"Show desktop failed: {e}")
        return
    if any(kw in lc for kw in ["lock screen", "lock pc", "lock computer"]):
        try:
            if TEST_MODE:
                print("[TEST_MODE] win+l")
                speak("Locked screen (test).")
            else:
                pyautogui.hotkey('win','l'); speak("Locked screen.")
        except Exception as e:
            speak(f"Lock screen failed: {e}")
        return
    if any(kw in lc for kw in ["task manager", "open task manager"]):
        try:
            if TEST_MODE:
                print("[TEST_MODE] ctrl+shift+esc")
                speak("Opened Task Manager (test).")
            else:
                pyautogui.hotkey('ctrl','shift','esc'); speak("Opened Task Manager.")
        except Exception as e:
            speak(f"Task Manager failed: {e}")
        return
    # Zoom controls
    if any(kw in lc for kw in ["zoom in", "zoom +", "zoom plus"]):
        try:
            if TEST_MODE:
                print("[TEST_MODE] ctrl++")
                speak("Zoomed in (test).")
            else:
                pyautogui.hotkey('ctrl','+'); speak("Zoomed in.")
        except Exception as e:
            speak(f"Zoom in failed: {e}")
        return
    if any(kw in lc for kw in ["zoom out", "zoom -", "zoom minus"]):
        try:
            if TEST_MODE:
                print("[TEST_MODE] ctrl+-")
                speak("Zoomed out (test).")
            else:
                pyautogui.hotkey('ctrl','-'); speak("Zoomed out.")
        except Exception as e:
            speak(f"Zoom out failed: {e}")
        return
    if any(kw in lc for kw in ["reset zoom", "zoom reset", "zoom 0", "zoom zero"]):
        try:
            if TEST_MODE:
                print("[TEST_MODE] ctrl+0")
                speak("Zoom reset (test).")
            else:
                pyautogui.hotkey('ctrl','0'); speak("Zoom reset.")
        except Exception as e:
            speak(f"Zoom reset failed: {e}")
        return

    # Volume controls
    if "volume up" in lc or "increase volume" in lc:
        volume_up(); return
    if "volume down" in lc or "decrease volume" in lc:
        volume_down(); return
    vm = re.search(r"set volume to (\d{1,3})", lc)
    if vm:
        volume_set(vm.group(1)); return
    vm2 = re.search(r"volume (?:to )?(\d{1,3})\s*%?", lc)
    if vm2 and ("set volume" in lc or lc.startswith("volume to") or lc.startswith("set volume")):
        volume_set(vm2.group(1)); return
    if lc.strip() == "mute" or ("mute" in lc and "unmute" not in lc):
        volume_mute(); return
    if lc.strip() == "unmute" or "unmute" in lc:
        volume_unmute(); return

    # Notes
    if lc.startswith("make a note") or lc.startswith("note "):
        if "make a note" in lc:
            content = command.split("make a note",1)[1].strip()
        else:
            content = command.split("note",1)[1].strip()
        if content:
            make_note(content)
        else:
            speak("What should I note?")
        return
    if "show notes" in lc or "read notes" in lc:
        show_notes(); return
    if "clear notes" in lc or "delete notes" in lc:
        clear_notes(); return

    if lc.startswith("open "):
        q = lc.replace("open", "").strip()
        open_app(q); return
    # Wikipedia
    if lc.startswith("wikipedia ") or lc.startswith("search wikipedia") or lc.strip() == "wikipedia":
        q = lc.replace("wikipedia", "").replace("search", "").strip()
        if q:
            wiki_summary(q)
        else:
            speak("What should I search on Wikipedia?")
        return

    # System info
    if ("cpu" in lc and "usage" in lc) or lc == "cpu usage":
        get_system_info(); return
    if "ram" in lc or "memory" in lc:
        get_system_info(); return
    if "battery" in lc:
        get_system_info(); return

    # Calculations
    calc_trigger = False
    if lc.startswith("what is ") or lc.startswith("calculate ") or lc.startswith("solve "):
        q = re.sub(r'^(what is|calculate|solve)\s+', '', lc)
        calc_trigger = True
    else:
        if re.search(r'[0-9]', lc) and re.search(r'[\+\-\*\/%]', lc):
            q = lc
            calc_trigger = True
    if calc_trigger:
        try:
            result = calculate_expression(q)
            speak(f"The result is {result}")
        except Exception as e:
            speak(f"Could not calculate: {e}. Opening web search.")
            open_site(f"https://www.google.com/search?q={urllib.parse.quote(q)}", f"calculate {q}")
        return

    # Mouse and scroll commands
    if "double click" in lc:
        double_click(); return
    if lc.strip() in ["click","left click"]:
        left_click(); return
    if lc.strip() in ["right click"]:
        right_click(); return
    m = re.search(r'move mouse to\s*(\d+)\s*(\d+)', lc)
    if m:
        move_mouse_to(m.group(1), m.group(2)); return
    mrel = re.search(r'move mouse (up|down|left|right)\s*(\d+)?', lc)
    if mrel:
        dirn = mrel.group(1); amt = int(mrel.group(2) or 100)
        try:
            if TEST_MODE:
                print(f"[TEST_MODE] move mouse {dirn} by {amt}")
                speak(f"Moved mouse {dirn} by {amt} pixels (test).")
            else:
                if dirn == 'up': pyautogui.moveRel(0, -amt)
                if dirn == 'down': pyautogui.moveRel(0, amt)
                if dirn == 'left': pyautogui.moveRel(-amt, 0)
                if dirn == 'right': pyautogui.moveRel(amt, 0)
                speak(f"Moved mouse {dirn} by {amt} pixels.")
        except Exception as e:
            speak(f"Move mouse relative failed: {e}")
        return
        # Generic hotkey / shortcuts (undo/redo/copy/paste etc.)
    if lc.strip() in ['paste','copy','cut','undo','redo','select all','select all','select']:
        keys = parse_key_combo(lc.strip()); press_keys_from_list(keys); return
    if "scroll" in lc:
        tm = re.search(r'scroll(?:\s+(-?\d+))?', lc)
        if tm and tm.group(1):
            amt = int(tm.group(1)); scroll_direction(amt); return
        times = 1
        tmatch = re.search(r'(\d+)\s*(times|x)', lc)
        if tmatch:
            times = int(tmatch.group(1))
        if "down" in lc:
            for _ in range(times):
                scroll_direction(-500)
            return
        if "up" in lc:
            for _ in range(times):
                scroll_direction(500)
            return
        speak("Please say scroll up, scroll down, or scroll <number>.")
        return
    # Tabs & browser shortcuts (checked before generic "tab")
    if any(kw in lc for kw in ["new tab", "open new tab"]):
        new_tab(); return
    if any(kw in lc for kw in ["reopen closed tab", "reopen closed", "restore tab"]):
        try:
            if TEST_MODE:
                print("[TEST_MODE] reopen closed tab (ctrl+shift+t)")
                speak("Reopened last closed tab (test).")
            else:
                pyautogui.hotkey('ctrl','shift','t'); speak("Reopened last closed tab.")
        except Exception as e:
            speak(f"Reopen tab failed: {e}")
        return
    if ("next tab" in lc) or ("switch tab" in lc):
        next_tab(); return
    if ("previous tab" in lc) or ("switch to previous tab" in lc and "previous" in lc):
        previous_tab(); return
    if "close tab" in lc:
        close_tab(); return
    if "close app" in lc:
        pyautogui.hotkey('alt','f4'); speak("current app closed")
        return
        
    m = re.search(r"switch to tab (\d+)", lc)
    if m:
        try:
            switch_to_tab_number(int(m.group(1))); return
        except Exception:
            speak("Invalid tab number."); return



    if lc.startswith("press ") or lc.startswith("press the "):
        keys = parse_key_combo(lc)
        if keys:
            press_keys_from_list(keys)
            return

    # ---------- NEW: Send message feature ----------
    # syntax: "send <message>", "send message <message>", "type and send <message>", "write and send <message>"
    send_match = re.match(r'^(send|send message|type and send|write and send)\s+(.*)', lc)
    if send_match:
        msg = send_match.group(2).strip()
        if msg:
            try:
                if TEST_MODE:
                    print("[TEST_MODE] send message:", msg)
                    speak("sent")
                else:
                    # type the message and press enter
                    pyautogui.typewrite(msg, interval=0.02)
                    pyautogui.press('enter')
                    speak("sent")
            except Exception as e:
                speak(f"Send failed: {e}")
        else:
            speak("What should I send?")
        return

    # Also support "send <singleword>" where earlier regex may not catch variants:
    if lc.startswith("send "):
        msg = lc[len("send "):].strip()
        if msg:
            try:
                if TEST_MODE:
                    print("[TEST_MODE] send message:", msg)
                    speak("sent")
                else:
                    pyautogui.typewrite(msg, interval=0.02)
                    pyautogui.press('enter')
                    speak("sent")
            except Exception as e:
                speak(f"Send failed: {e}")
            return
    if any(qw in lc for qw in ["who is", "what is", "when is", "where is", "tell me about", "define"]):
        q = re.sub(r'^(who is|what is|when is|where is|tell me about|define)\s*', '', lc).strip()
        if q:
            try:
                wiki_summary(q)
            except Exception:
                open_site(f"https://www.google.com/search?q={urllib.parse.quote(q)}", f"search for {q}")
        else:
            speak("What would you like to know?")
        return
    elif command.startswith(("write ", "right ", "type ")):
        text_to_write = command.split(" ", 1)[1]
        try:
            pyautogui.typewrite(text_to_write, interval=0.05)
            speak(f"writing {text_to_write}")
        except Exception as e:
            speak(f"Typing failed: {e}")
        return

    elif command.startswith("say "):
        text_to_say = command.replace("say ", "")
        speak(text_to_say)
        return
    

    # --- Info ---
    elif "time" in lc:
        tell_time()
    elif "date" in lc:
        tell_date()

    # --- System ---
    elif "screenshot" in lc:
        take_screenshot()
    elif "shutdown" in lc:
        shutdown()
    elif "close chrome" in lc:
        close_app("chrome.exe")
    elif lc.startswith("close"):
        q = lc.replace("close", "").strip()
        close_app(f"{q}.exe")

vlc_manager = VLCManager()
def handle_media_command(command):
    """
    command: normalized lower-case string.
    Returns a string status for TTS.
    """
    c = command.lower().strip()

# ---------------- Integration helpers ----------------

    # VLC-specific control (if user asks for vlc)
    if c.startswith("vlc "):
        # commands: vlc play <path>, vlc add <path>, vlc next, vlc prev, vlc seek +10, vlc jump 30
        parts = c.split()
        if len(parts) >= 2:
            op = parts[1]
            if op == "play" and len(parts) >= 3:
                path = " ".join(parts[2:])
                ok, msg = vlc_manager.load_and_play(path, start_immediately=True)
                return "Playing in VLC" if ok else f"VLC error {msg}"
            if op == "add" and len(parts) >= 3:
                path = " ".join(parts[2:])
                vlc_manager.add_to_playlist(path)
                return "Added to VLC playlist"
            if op == "next":
                vlc_manager.next()
                return "VLC next"
            if op == "previous" or op == "prev":
                vlc_manager.previous()
                return "VLC previous"
            if op == "stop":
                vlc_manager.stop()
                return "VLC stopped"
            if op == "pause" or op == "playpause":
                vlc_manager.play_pause()
                return "VLC toggled play/pause"
            if op == "seek" and len(parts) >= 3:
                # e.g., "vlc seek +10" or "vlc seek -10"
                try:
                    sec = int(parts[2])
                    vlc_manager.seek_seconds(sec)
                    return f"VLC seeked {sec} seconds"
                except:
                    return "Invalid seek value"
            if op == "jump" and len(parts) >= 3:
                try:
                    sec = int(parts[2])
                    vlc_manager.jump_to_second(sec)
                    return f"VLC jumped to {sec} seconds"
                except:
                    return "Invalid jump value"
        return "VLC command not understood"

    # Generic media controls (system-wide)
    # play / pause
    if any(x in c for x in ["play", "pause", "play pause", "playpause", "toggle"]):
        system_play_pause()
        return "Toggled play/pause"

    # next / prev
    if "next" in c and "song" in c or "next track" in c:
        system_next_track()
        return "Next track"
    if "previous" in c or "prev" in c or "last song" in c:
        system_prev_track()
        return "Previous track"

    # stop
    if "stop" in c and ("music" in c or "song" in c or "stop music" in c):
        system_stop()
        return "Stop media"

    # seek commands - for generic players we attempt media keys + reject if unsupported
    # Note: system-wide seeking is unreliable; recommend VLC for precise seeking.
    if "seek" in c or "forward" in c or "back" in c or "rewind" in c:
        # interpret patterns like "seek 10 seconds" "forward 10 seconds" "rewind 22 seconds"
        import re
        m = re.search(r'([+-]?\d+)\s*second', c)
        if m:
            sec = int(m.group(1))
            # try VLC if active
            if vlc is not None and vlc_manager.is_playing():
                ok = vlc_manager.seek_seconds(sec)
                return f"Seeked {sec} seconds in VLC" if ok else "VLC seek failed"
            else:
                return "Precise seeking only supported in VLC. Use VLC commands or use next/prev for system players."
        # commands like "forward 10 seconds"
        m2 = re.search(r'(forward|after|ahead)\s+(\d+)', c)
        if m2:
            sec = int(m2.group(2))
            if vlc is not None and vlc_manager.is_playing():
                vlc_manager.seek_seconds(sec)
                return f"VLC seeked forward {sec}s"
            else:
                return "Use VLC for seeking; system players do not support precise seeks."
        # fallback
        return "Seek command needs seconds; say 'seek 10 seconds' or control VLC directly."

    # jump to second X: "jump to 30 second"
    if "jump" in c or ("go to" in c and "second" in c):
        import re
        m = re.search(r'(\d+)\s*second', c)
        if m and vlc is not None:
            sec = int(m.group(1))
            ok = vlc_manager.jump_to_second(sec)
            return f"Jumped to {sec}s in VLC" if ok else "VLC jump failed"
        return "Jump command requires VLC playback."

    return "Media command not recognized"


# ============================================================
# ✅ Final Integration Ready
# ============================================================
# Usage Example:
#   from action_engine import execute_chained
#   execute_chained("open youtube and search arijit singh")
# ============================================================

