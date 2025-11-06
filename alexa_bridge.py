# alexa_bridge.py
"""
Universal bridge:
- Accepts simple POST {"command":"..."} (handy for curl/tests)
- Accepts Alexa IntentRequest JSON and extracts the command slot
- Tries to run Jarvis via CLI (main_ai.pyw) by default.
- If your main_ai.pyw DOES NOT accept CLI text args, set USE_CLI_ARGS = False
  and create a small jarvis_cli.py that imports action_engine and calls a run_text_command(cmd) function.
"""

from flask import Flask, request, jsonify
import subprocess, shlex, threading, json, sys, os, time

app = Flask(__name__)

# ------ CONFIG ------
USE_CLI_ARGS = False   # True if `python main_ai.pyw "open chrome"` works
JARVIS_CMD_PY = "python"   # command to run python (adjust if needed)
MAIN_JARVIS_FILE = "main_ai.pyw"
# --------------------

def run_jarvis_cli_arg(command_text: str) -> str:
    """Call main_ai.pyw with a text argument and return short output (or error)."""
    try:
        cmd = f'{JARVIS_CMD_PY} {shlex.quote(MAIN_JARVIS_FILE)} --alexa {shlex.quote(command_text)}'
        proc = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=15)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if out:
            return out[:400]
        if proc.returncode != 0:
            return f"Jarvis error: {err[:300] or 'non-zero exit'}"
        return "Command executed."
    except Exception as e:
        return f"Jarvis call failed: {e}"
def run_jarvis_via_helper(command_text: str) -> str:
    """
    Start alexa_jarvis_adapter.py in the background (non-blocking),
    setting cwd to the Jarvis folder and writing logs to alexa_adapter.log.
    Added robust logging + Windows-friendly creationflags to avoid first-run silent exits.
    """
    try:
        jarvis_folder = r"C:\Users\gamin\Desktop\MYAi\jarvis"
        python_exe = sys.executable or "python"

        # Build command list safely (pass command_text as one arg)
        cmd_list = [python_exe, "alexa_jarvis_adapter.py", command_text]

        # Debug: write launch attempt to bridge_debug.log
        dbg_path = os.path.join(jarvis_folder, "bridge_debug.log")
        with open(dbg_path, "a", encoding="utf-8") as dbg:
            dbg.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] About to Popen: {cmd_list}\n")
            dbg.flush()

        # Open adapter log append (child will write into this)
        log_path = os.path.join(jarvis_folder, "alexa_adapter.log")
        logfile = open(log_path, "a", encoding="utf-8", buffering=1)  # line-buffered

        # On Windows, use CREATE_NEW_CONSOLE to detach child reliably.
        creation_flags = 0
        try:
            creation_flags = subprocess.CREATE_NEW_CONSOLE
        except Exception:
            creation_flags = 0

        proc = subprocess.Popen(
            cmd_list,
            cwd=jarvis_folder,
            stdout=logfile,
            stderr=logfile,
            stdin=subprocess.DEVNULL,
            creationflags=creation_flags,
            close_fds=False
        )

        # Log actual pid and flush right away
        with open(dbg_path, "a", encoding="utf-8") as dbg:
            dbg.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Popen returned pid={proc.pid}\n")
            dbg.flush()

        # do not close logfile here (child inherits it), but flush parent side
        logfile.flush()

        return f"Adapter launched (pid {proc.pid})."
    except Exception as e:
        # Write exception to debug so we can see why launch failed
        try:
            with open(os.path.join(r"C:\Users\gamin\Desktop\MYAi\jarvis", "bridge_debug.log"), "a", encoding="utf-8") as dbg:
                dbg.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Adapter launch EXCEPTION: {e}\n")
        except Exception:
            pass
        return f"Adapter launch failed: {e}"
def invoke_jarvis(command_text: str) -> str:
    """Choose method based on config. Keep quick and safe for Alexa's timeout."""
    if USE_CLI_ARGS:
        return run_jarvis_cli_arg(command_text)
    else:
        return run_jarvis_via_helper(command_text)

def alexa_response_text(text: str, end_session: bool = True):
    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {"type": "PlainText", "text": text},
            "shouldEndSession": end_session
        }
    }

@app.route("/alexa", methods=["POST"])
def alexa_endpoint():
    data = request.get_json(force=True, silent=True) or {}
    # Debug log (short)
    try:
        print("[bridge] received payload keys:", list(data.keys()))
    except Exception:
        pass

    # 1) Support simple test format: { "command": "..." }
    if isinstance(data, dict) and "command" in data:
        cmd_text = str(data["command"]).strip()
        if not cmd_text:
            return jsonify({"response":"No command received"}), 400
        # run jarvis in background to keep response snappy
        threading.Thread(target=invoke_jarvis, args=(cmd_text,), daemon=True).start()
        return jsonify({"response": f"{cmd_text}"}), 200

    # 2) Alexa format handling
    req = data.get("request") or {}
    req_type = req.get("type")
    if req_type == "LaunchRequest":
    # Alexa opens Jarvis; keep the mic open and ask directly for the command
        return jsonify(alexa_response_text(
            "Jarvis is ready. What would you like him to do?",
            end_session=False
        ))

    if req_type == "IntentRequest":
        intent = req.get("intent", {})
        intent_name = intent.get("name", "")
        # try to extract slot value (flexible)
        cmd_text = ""
        slots = intent.get("slots", {}) or {}
        # Alexa slot 'command' typical path:
        if "command" in slots and isinstance(slots["command"], dict):
            cmd_text = slots["command"].get("value", "") or ""
        # fallback: some test payloads nest differently
        if not cmd_text:
            # try older style: data['command']
            cmd_text = data.get("command","") or ""

        if not cmd_text:
            # nothing captured
            return jsonify(alexa_response_text("Please say it again.", end_session=False))

        cmd_text = str(cmd_text).strip()
        # run Jarvis async (avoid Alexa timeout); you can change to sync if you know commands finish quickly
        threading.Thread(target=invoke_jarvis, args=(cmd_text,), daemon=True).start()
        return jsonify(alexa_response_text(f"Okay, running: {cmd_text}")), 200

    if req_type == "SessionEndedRequest":
        return jsonify({}), 200

    # unknown format
    return jsonify({"response":"Unsupported request format"}), 400

if __name__ == "__main__":
    # run dev server
    app.run(host="0.0.0.0", port=5000, debug=True)
    